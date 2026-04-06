from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import UpdateOne

from core.config import settings
from core.pinecone import get_pinecone_namespace, get_namespace_vector_count


def get_embeddings_collection(db):
    return db[settings.MONGO_EMBEDDINGS_COLLECTION]


def ensure_embeddings_indexes(db) -> None:
    collection = get_embeddings_collection(db)
    try:
        collection.create_index("post_id")
    except Exception:
        pass
    try:
        collection.create_index("chunk_type")
    except Exception:
        pass
    try:
        collection.create_index("updated_at")
    except Exception:
        pass


def count_mongo_embeddings(db) -> int:
    return int(get_embeddings_collection(db).count_documents({}))


def clear_mongo_embeddings(db) -> None:
    get_embeddings_collection(db).delete_many({})


def count_pinecone_vectors(index, namespace: str | None = None) -> int:
    return get_namespace_vector_count(index, namespace)


def count_chroma_vectors(collection) -> int:
    # Backwards-compat alias (collection is now a Pinecone index).
    return count_pinecone_vectors(collection)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if hasattr(value, "tolist"):
        converted = value.tolist()
        if isinstance(converted, list):
            return converted
        return [converted]
    if isinstance(value, tuple):
        return list(value)
    try:
        return list(value)
    except TypeError:
        return [value]


def _canonical_post_id(vector_id: str) -> str:
    value = str(vector_id or "")
    if value.endswith("_title") or value.endswith("_body"):
        return value.rsplit("_", 1)[0]
    return value


def _infer_chunk_type(vector_id: str) -> str:
    value = str(vector_id or "")
    if value.endswith("_title"):
        return "title"
    if value.endswith("_body"):
        return "body"
    return ""


def upsert_mongo_embeddings(
    db,
    ids: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict[str, Any]],
    documents: list[str] | None = None,
) -> int:
    if not ids:
        return 0

    ensure_embeddings_indexes(db)
    collection = get_embeddings_collection(db)
    now = datetime.now(timezone.utc)

    operations: list[UpdateOne] = []
    for index, vector_id in enumerate(ids):
        if index >= len(embeddings):
            continue

        vector = embeddings[index]
        if vector is None:
            continue

        metadata = {}
        if index < len(metadatas) and metadatas[index] is not None:
            metadata = dict(metadatas[index])

        doc_text = ""
        if documents is not None and index < len(documents):
            doc_text = str(documents[index] or "")

        post_id = str(metadata.get("post_id") or _canonical_post_id(vector_id))
        chunk_type = str(metadata.get("chunk_type") or _infer_chunk_type(vector_id))
        if post_id and "post_id" not in metadata:
            metadata["post_id"] = post_id
        if chunk_type and "chunk_type" not in metadata:
            metadata["chunk_type"] = chunk_type

        payload = {
            "vector_id": str(vector_id),
            "post_id": post_id,
            "chunk_type": chunk_type,
            "embedding": [float(item) for item in vector],
            "metadata": metadata,
            "document": doc_text,
            "updated_at": now,
        }

        operations.append(
            UpdateOne(
                {"_id": str(vector_id)},
                {"$set": payload},
                upsert=True,
            )
        )

    if not operations:
        return 0

    collection.bulk_write(operations, ordered=False)
    return len(operations)


def restore_pinecone_from_mongo_embeddings(
    db,
    pinecone_index,
    batch_size: int = 256,
    namespace: str | None = None,
) -> int:
    collection = get_embeddings_collection(db)
    total = int(collection.count_documents({}))
    if total == 0:
        return 0

    restored = 0
    vectors: list[dict[str, Any]] = []
    namespace = namespace or get_pinecone_namespace()

    cursor = collection.find(
        {},
        {"_id": 1, "embedding": 1, "metadata": 1, "post_id": 1, "chunk_type": 1, "document": 1},
    ).sort("_id", 1)

    for row in cursor:
        vector_id = str(row.get("_id", "")).strip()
        vector = row.get("embedding")
        if not vector_id or vector is None:
            continue

        metadata = dict(row.get("metadata") or {})
        if "post_id" not in metadata and row.get("post_id"):
            metadata["post_id"] = str(row.get("post_id"))
        if "chunk_type" not in metadata and row.get("chunk_type"):
            metadata["chunk_type"] = str(row.get("chunk_type"))

        vectors.append(
            {
                "id": vector_id,
                "values": [float(item) for item in vector],
                "metadata": metadata,
            }
        )

        if len(vectors) >= batch_size:
            pinecone_index.upsert(vectors=vectors, namespace=namespace)
            restored += len(vectors)
            vectors = []

    if vectors:
        pinecone_index.upsert(vectors=vectors, namespace=namespace)
        restored += len(vectors)

    return restored


def restore_chroma_from_mongo_embeddings(
    db,
    chroma_collection,
    batch_size: int = 256,
) -> int:
    # Backwards-compat alias (collection is now a Pinecone index).
    return restore_pinecone_from_mongo_embeddings(
        db,
        chroma_collection,
        batch_size=batch_size,
    )


def seed_mongo_embeddings_from_pinecone(
    db,
    pinecone_index,
    batch_size: int = 256,
    only_if_empty: bool = True,
    namespace: str | None = None,
) -> int:
    if only_if_empty and count_mongo_embeddings(db) > 0:
        return 0

    copied = 0
    namespace = namespace or get_pinecone_namespace()

    try:
        id_pages = pinecone_index.list(namespace=namespace)
    except Exception:
        return 0

    def _chunks(items: list[str], size: int) -> list[list[str]]:
        return [items[i : i + size] for i in range(0, len(items), size)]

    for ids in id_pages:
        if not ids:
            continue

        for batch in _chunks([str(item) for item in ids], min(1000, batch_size)):
            payload = pinecone_index.fetch(ids=batch, namespace=namespace)
            if isinstance(payload, dict):
                vectors_map = payload.get("vectors") or {}
            else:
                vectors_map = getattr(payload, "vectors", {}) or {}

            batch_ids: list[str] = []
            embeddings: list[list[float]] = []
            metadatas: list[dict[str, Any]] = []
            documents: list[str] = []

            for vector_id, vector_payload in vectors_map.items():
                if not vector_payload:
                    continue
                batch_ids.append(str(vector_id))

                if isinstance(vector_payload, dict):
                    values = vector_payload.get("values") or []
                    metadata = dict(vector_payload.get("metadata") or {})
                else:
                    values = getattr(vector_payload, "values", []) or []
                    metadata = dict(getattr(vector_payload, "metadata", {}) or {})

                embeddings.append([float(item) for item in values])
                metadatas.append(metadata)
                documents.append(str(metadata.get("document", "") or ""))

            if batch_ids:
                copied += upsert_mongo_embeddings(
                    db,
                    ids=batch_ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents,
                )

    return copied


def seed_mongo_embeddings_from_chroma(
    db,
    chroma_collection,
    batch_size: int = 256,
    only_if_empty: bool = True,
) -> int:
    # Backwards-compat alias (collection is now a Pinecone index).
    return seed_mongo_embeddings_from_pinecone(
        db,
        chroma_collection,
        batch_size=batch_size,
        only_if_empty=only_if_empty,
    )
