"""One-time script. MongoDB -> Embed -> upserts into Chroma + Mongo backup."""
import os
import sys

# Add the backend root to the python path so it can import 'core' and 'ml'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
import pymongo
from core.config import settings
from core.embedding_store import (
    clear_mongo_embeddings,
    ensure_embeddings_indexes,
    upsert_mongo_embeddings,
)
from ml.embedder import embed
import time

def build_embeddings():
    client = pymongo.MongoClient(settings.MONGO_URI)
    try:
         db = client[settings.MONGO_DB]
         total_docs = db.posts.count_documents({})
         
         if total_docs == 0:
              print("MongoDB is empty. Seed Mongo first.")
              sys.exit(1)
              
         ensure_embeddings_indexes(db)

         chroma_client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=str(settings.CHROMA_PORT))
         try:
              chroma_client.delete_collection(settings.CHROMA_COLLECTION)
              print("Deleted existing Chroma collection for clean rebuild.")
         except Exception:
              pass
         collection = chroma_client.get_or_create_collection(
              name=settings.CHROMA_COLLECTION,
              metadata={"hnsw:space": "cosine"}
         )
         clear_mongo_embeddings(db)
         
         batch_size = 64
         docs = []
         
         cursor = db.posts.find()
         start = time.time()
         
         for doc in cursor:
               docs.append(doc)
               if len(docs) >= batch_size:
                    _process_batch(collection, db, docs)
                    docs = []
                    
         if docs:
               _process_batch(collection, db, docs)
               
         end = time.time()
         print(f"Upserted embeddings into Chroma + Mongo backup in {end - start:.2f} seconds.")
    finally:
         client.close()

def _process_batch(collection, db, docs):
     title_texts = []
     title_docs = []
     body_texts = []
     body_docs = []

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

     ids = []
     texts = []
     metadatas = []
     vectors = []

     title_vectors = embed(title_texts).tolist()
     for doc, text, vector in zip(title_docs, title_texts, title_vectors):
          post_id = str(doc["post_id"])
          ids.append(f"{post_id}_title")
          texts.append(text)
          vectors.append(vector)
          metadatas.append({
               "post_id": post_id,
               "chunk_type": "title",
               "author": doc.get("author", ""),
               "subreddit": doc.get("subreddit", ""),
               "created_date": str(doc.get("created_date", "")),
               "score": doc.get("score", 0),
          })

     if body_texts:
          body_vectors = embed(body_texts).tolist()
          for doc, text, vector in zip(body_docs, body_texts, body_vectors):
               post_id = str(doc["post_id"])
               ids.append(f"{post_id}_body")
               texts.append(text)
               vectors.append(vector)
               metadatas.append({
                    "post_id": post_id,
                    "chunk_type": "body",
                    "author": doc.get("author", ""),
                    "subreddit": doc.get("subreddit", ""),
                    "created_date": str(doc.get("created_date", "")),
                    "score": doc.get("score", 0),
               })

     if ids:
          collection.upsert(
               ids=ids,
               embeddings=vectors,
               metadatas=metadatas,
               documents=texts
          )
          try:
               upsert_mongo_embeddings(
                    db,
                    ids=ids,
                    embeddings=vectors,
                    metadatas=metadatas,
                    documents=texts,
               )
          except Exception as exc:
               print(f"[WARN] Failed to upsert embedding backup into MongoDB: {exc}")

if __name__ == "__main__":
     build_embeddings()
