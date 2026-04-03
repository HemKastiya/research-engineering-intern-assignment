"""In-process asyncio task orchestration for embedding + clustering jobs."""
from __future__ import annotations

import asyncio
import threading
from typing import Any, Optional

import chromadb
import pymongo

from core.config import settings
from ml.clusterer import clear_cluster_cache, run_clustering
from ml.embedder import embed

_TASK_STATE_LOCK = threading.Lock()
_embedding_task: Optional[asyncio.Task[None]] = None
_last_embedding_error: Optional[str] = None


def _process_batch(collection, docs: list[dict[str, Any]]) -> None:
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
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )


def _embed_all_sync() -> None:
    client = pymongo.MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB]
    try:
        chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=str(settings.CHROMA_PORT),
        )
        # Full rebuild path: reset collection to avoid stale mixed-schema vectors.
        try:
            chroma_client.delete_collection(settings.CHROMA_COLLECTION)
        except Exception:
            pass
        collection = chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

        cursor = db.posts.find()
        batch_size = 64
        docs: list[dict[str, Any]] = []

        for doc in cursor:
            docs.append(doc)
            if len(docs) >= batch_size:
                _process_batch(collection, docs)
                docs = []

        if docs:
            _process_batch(collection, docs)

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
