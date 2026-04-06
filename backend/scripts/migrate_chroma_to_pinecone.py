"""One-time migration: ChromaDB -> Pinecone (also updates Mongo embedding backup)."""
import os
import sys
from typing import Any

# Add the backend root to the python path so it can import 'core' and 'ml'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import chromadb
except Exception as exc:  # pragma: no cover - optional dependency
    raise SystemExit(
        "chromadb is required for this migration. Install with `pip install chromadb` "
        f"and rerun. Error: {exc}"
    )

import pymongo

from core.config import settings
from core.embedding_store import ensure_embeddings_indexes, upsert_mongo_embeddings
from core.pinecone import ensure_index, get_pinecone_namespace


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


def migrate(batch_size: int = 256) -> int:
    chroma_host = os.getenv("CHROMA_HOST", "localhost")
    chroma_port = os.getenv("CHROMA_PORT", "8000")
    chroma_ssl = os.getenv("CHROMA_SSL", "false").lower() in ("1", "true", "yes")
    chroma_collection = os.getenv("CHROMA_COLLECTION", "reddit_posts")

    chroma_client = chromadb.HttpClient(
        host=chroma_host,
        port=str(chroma_port),
        ssl=chroma_ssl,
    )
    collection = chroma_client.get_collection(chroma_collection)

    index = ensure_index()
    namespace = get_pinecone_namespace()

    if os.getenv("PINECONE_DELETE_EXISTING", "false").lower() in ("1", "true", "yes"):
        try:
            index.delete(delete_all=True, namespace=namespace)
        except Exception:
            pass

    mongo_client = pymongo.MongoClient(settings.MONGO_URI)
    db = mongo_client[settings.MONGO_DB]
    ensure_embeddings_indexes(db)

    migrated = 0
    offset = 0

    total = None
    if hasattr(collection, "count"):
        try:
            total = int(collection.count())
        except Exception:
            total = None

    while True:
        payload = collection.get(
            include=["embeddings", "metadatas", "documents"],
            limit=batch_size,
            offset=offset,
        )

        ids = [str(item) for item in _as_list(payload.get("ids"))]
        if not ids:
            break

        embeddings = _as_list(payload.get("embeddings"))
        metadatas = _as_list(payload.get("metadatas"))
        documents = _as_list(payload.get("documents"))

        vectors: list[dict[str, Any]] = []
        for idx, vector_id in enumerate(ids):
            if idx >= len(embeddings):
                continue
            vector = embeddings[idx]
            if vector is None:
                continue
            metadata = {}
            if idx < len(metadatas) and metadatas[idx] is not None:
                metadata = dict(metadatas[idx])
            vectors.append(
                {
                    "id": vector_id,
                    "values": [float(item) for item in vector],
                    "metadata": metadata,
                }
            )

        if vectors:
            index.upsert(vectors=vectors, namespace=namespace)
            try:
                upsert_mongo_embeddings(
                    db,
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents,
                )
            except Exception as exc:
                print(f"[WARN] Failed to upsert Mongo embedding backup: {exc}")

        migrated += len(ids)
        offset += len(ids)
        if total is not None and offset >= total:
            break

    mongo_client.close()
    return migrated


if __name__ == "__main__":
    total = migrate()
    print(f"Migrated {total} vectors from Chroma to Pinecone.")
