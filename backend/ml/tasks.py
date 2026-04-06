"""In-process asyncio task orchestration for embedding + clustering jobs."""
from __future__ import annotations

import asyncio
import threading
from typing import Any, Optional

import pymongo

from core.config import settings
from core.embedding_store import (
    clear_mongo_embeddings,
    count_mongo_embeddings,
    ensure_embeddings_indexes,
    restore_pinecone_from_mongo_embeddings,
    seed_mongo_embeddings_from_pinecone,
    upsert_mongo_embeddings,
)
from core.pinecone import ensure_index, get_pinecone_index, get_pinecone_namespace
from ml.clusterer import clear_cluster_cache, run_clustering
from ml.embedder import embed

_TASK_STATE_LOCK = threading.Lock()
_embedding_task: Optional[asyncio.Task[None]] = None
_last_embedding_error: Optional[str] = None


def _process_batch(pinecone_index, mongo_db, docs: list[dict[str, Any]]) -> None:
    title_texts: list[str] = []
    title_docs: list[dict[str, Any]] = []
    body_texts: list[str] = []
    body_docs: list[dict[str, Any]] = []

    for doc in docs:
        title_text = str(doc.get("title_clean") or "").strip()
        if not title_text:
            title_text = str(doc.get("combined_text") or "").strip()
        if not title_text:
            title_text = "(untitled)"

        title_texts.append(title_text)
        title_docs.append(doc)

        body_text = str(doc.get("selftext_clean") or "").strip()
        if body_text and len(body_text.split()) > 5:
            body_texts.append(body_text)
            body_docs.append(doc)

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []
    embeddings: list[list[float]] = []

    title_vectors = embed(title_texts).tolist()
    for doc, text, vector in zip(title_docs, title_texts, title_vectors):
        post_id = str(doc["post_id"])
        ids.append(f"{post_id}_title")
        documents.append(text)
        embeddings.append(vector)
        metadatas.append(
            {
                "post_id": post_id,
                "chunk_type": "title",
                "author": doc.get("author", ""),
                "subreddit": doc.get("subreddit", ""),
                "created_date": str(doc.get("created_date", "")),
                "score": doc.get("score", 0),
            }
        )

    if body_texts:
        body_vectors = embed(body_texts).tolist()
        for doc, text, vector in zip(body_docs, body_texts, body_vectors):
            post_id = str(doc["post_id"])
            ids.append(f"{post_id}_body")
            documents.append(text)
            embeddings.append(vector)
            metadatas.append(
                {
                    "post_id": post_id,
                    "chunk_type": "body",
                    "author": doc.get("author", ""),
                    "subreddit": doc.get("subreddit", ""),
                    "created_date": str(doc.get("created_date", "")),
                    "score": doc.get("score", 0),
                }
            )

    if ids:
        vectors = [
            {"id": vector_id, "values": vector, "metadata": metadata}
            for vector_id, vector, metadata in zip(ids, embeddings, metadatas)
        ]
        pinecone_index.upsert(vectors=vectors, namespace=get_pinecone_namespace())
        try:
            upsert_mongo_embeddings(
                mongo_db,
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents,
            )
        except Exception as exc:
            # Mongo is backup/source for restore; do not fail serving rebuild if this step fails.
            print(f"[WARN] Failed to upsert embedding backup into MongoDB: {exc}")


def _embed_all_sync() -> None:
    client = pymongo.MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    try:
        ensure_embeddings_indexes(db)

        collection = ensure_index()
        # Full rebuild path: reset namespace to avoid stale mixed-schema vectors.
        try:
            collection.delete(delete_all=True, namespace=get_pinecone_namespace())
        except Exception:
            pass
        clear_mongo_embeddings(db)

        cursor = db.posts.find()
        batch_size = 64
        docs: list[dict[str, Any]] = []

        for doc in cursor:
            docs.append(doc)
            if len(docs) >= batch_size:
                _process_batch(collection, db, docs)
                docs = []

        if docs:
            _process_batch(collection, db, docs)

        # Embedding refresh implies data may have changed; invalidate cluster cache.
        clear_cluster_cache()
    finally:
        client.close()


def _on_embedding_task_done(task: asyncio.Task[None]) -> None:
    global _last_embedding_error
    error_message: Optional[str] = None
    if task.cancelled():
        error_message = "Embedding task cancelled"
    else:
        exc = task.exception()
        if exc is not None:
            error_message = str(exc)

    with _TASK_STATE_LOCK:
        _last_embedding_error = error_message


async def embed_all_async() -> None:
    await asyncio.to_thread(_embed_all_sync)


def schedule_embed_all() -> asyncio.Task[None]:
    """Schedule embedding once; returns existing in-flight task when available."""
    global _embedding_task, _last_embedding_error
    loop = asyncio.get_running_loop()

    with _TASK_STATE_LOCK:
        if _embedding_task is not None and not _embedding_task.done():
            return _embedding_task

        _last_embedding_error = None
        _embedding_task = loop.create_task(embed_all_async(), name="embed_all")
        _embedding_task.add_done_callback(_on_embedding_task_done)
        return _embedding_task


def get_embedding_status() -> str:
    with _TASK_STATE_LOCK:
        task = _embedding_task
        last_error = _last_embedding_error

    if task is not None and not task.done():
        return "Processing"
    if last_error:
        return "Failed"
    return "Idle"


def embed_all() -> None:
    """Synchronous helper retained for scripts/manual calls."""
    _embed_all_sync()


def rebuild_clusters(n_topics: int) -> dict[str, Any]:
    """Synchronous helper retained for scripts/manual calls."""
    return run_clustering(n_topics)


async def rebuild_clusters_async(n_topics: int) -> dict[str, Any]:
    return await asyncio.to_thread(run_clustering, n_topics)


def restore_pinecone_from_mongo() -> int:
    """
    Rehydrates Pinecone vectors from Mongo embedding backup.
    Returns number of vectors restored.
    """
    client = pymongo.MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    try:
        ensure_embeddings_indexes(db)
        if count_mongo_embeddings(db) == 0:
            return 0

        collection = ensure_index()
        return restore_pinecone_from_mongo_embeddings(
            db,
            collection,
            namespace=get_pinecone_namespace(),
        )
    finally:
        client.close()


def seed_mongo_from_pinecone_if_empty() -> int:
    """
    One-time bootstrap path: if Mongo embedding backup is empty but Pinecone has vectors,
    copy current Pinecone vectors into Mongo backup storage.
    """
    client = pymongo.MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    try:
        ensure_embeddings_indexes(db)
        if count_mongo_embeddings(db) > 0:
            return 0

        collection = get_pinecone_index()
        return seed_mongo_embeddings_from_pinecone(
            db,
            collection,
            only_if_empty=True,
            namespace=get_pinecone_namespace(),
        )
    finally:
        client.close()


def restore_chroma_from_mongo() -> int:
    # Backwards-compat alias.
    return restore_pinecone_from_mongo()


def seed_mongo_from_chroma_if_empty() -> int:
    # Backwards-compat alias.
    return seed_mongo_from_pinecone_if_empty()
