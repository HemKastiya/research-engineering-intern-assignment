"""Health check: MongoDB, ChromaDB, Gemini API key."""
import os
import sys

# Add backend root to Python path so scripts can import core/ml packages.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
import google.generativeai as genai
import pymongo

from core.config import settings
from core.embedding_store import count_mongo_embeddings, ensure_embeddings_indexes

POSTS_TEXT_INDEX_NAME = "posts_text_search"


def _has_multilingual_posts_text_index(posts_collection) -> bool:
    indexes = posts_collection.index_information()
    text_indexes = [
        (name, spec)
        for name, spec in indexes.items()
        if "textIndexVersion" in spec
    ]
    desired = indexes.get(POSTS_TEXT_INDEX_NAME)
    if not desired or "textIndexVersion" not in desired:
        return False

    default_language = str(desired.get("default_language", "english")).lower()
    if default_language != "none":
        return False

    # Mongo supports only one text index per collection.
    return len(text_indexes) == 1


def _ensure_multilingual_posts_text_index(posts_collection) -> None:
    if _has_multilingual_posts_text_index(posts_collection):
        print("[OK] Mongo text index is configured for multilingual lexical matching.")
        return

    indexes = posts_collection.index_information()
    text_index_names = [
        name
        for name, spec in indexes.items()
        if "textIndexVersion" in spec
    ]
    for index_name in text_index_names:
        posts_collection.drop_index(index_name)
        print(f"[INFO] Dropped outdated Mongo text index: {index_name}")

    posts_collection.create_index(
        [("title_clean", pymongo.TEXT), ("selftext_clean", pymongo.TEXT), ("combined_text", pymongo.TEXT)],
        weights={"title_clean": 3, "selftext_clean": 1, "combined_text": 1},
        default_language="none",
        name=POSTS_TEXT_INDEX_NAME,
    )
    print("[OK] Created multilingual Mongo text index: posts_text_search")


def verify_setup() -> None:
    errors = 0

    # 1. MongoDB
    try:
        client = pymongo.MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB]
        count = db.posts.count_documents({})
        print(f"[OK] MongoDB connection (records: {count})")

        ensure_embeddings_indexes(db)
        embedding_count = count_mongo_embeddings(db)
        print(f"[OK] MongoDB embedding backup collection (vectors: {embedding_count})")

        _ensure_multilingual_posts_text_index(db.posts)
    except Exception as exc:
        print(f"[ERR] MongoDB: {exc}")
        errors += 1

    # 2. ChromaDB
    try:
        chroma_client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=str(settings.CHROMA_PORT),
        )
        collection = chroma_client.get_collection(settings.CHROMA_COLLECTION)
        if hasattr(collection, "count"):
            c_count = collection.count()
        else:
            c_count = len(collection.get()["ids"])
        print(f"[OK] ChromaDB connection (vectors: {c_count})")
    except Exception as exc:
        print(f"[ERR] ChromaDB: {exc}")
        errors += 1

    # 3. Gemini
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content("Say OK")
        if not response.text:
            raise ValueError("Empty API response")
        print("[OK] Gemini API key validation")
    except Exception as exc:
        print(f"[ERR] Gemini validation: {exc}")
        errors += 1

    if errors > 0:
        print(f"\nSetup failed with {errors} error(s).")
        sys.exit(1)

    print("\nAll dependencies are connected. Server is ready to launch.")


if __name__ == "__main__":
    verify_setup()
