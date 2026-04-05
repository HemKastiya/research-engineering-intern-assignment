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

        indexes = db.posts.index_information()
        has_text_index = any("textIndexVersion" in idx for idx in indexes.values())
        if not has_text_index:
            print("[WARN] No Mongo text index found on posts; creating weighted text index now...")
            db.posts.create_index(
                [("title_clean", pymongo.TEXT), ("selftext_clean", pymongo.TEXT), ("combined_text", pymongo.TEXT)],
                weights={"title_clean": 3, "selftext_clean": 1, "combined_text": 1},
                name="posts_text_search",
            )
            print("[OK] Created Mongo text index: posts_text_search")
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
