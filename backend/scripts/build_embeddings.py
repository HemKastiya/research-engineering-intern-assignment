"""One-time script. MongoDB -> Embed -> upserts into Pinecone + Mongo backup."""
import os
import sys

# Add the backend root to the python path so it can import 'core' and 'ml'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymongo
from core.config import settings
from core.embedding_store import (
    clear_mongo_embeddings,
    ensure_embeddings_indexes,
    upsert_mongo_embeddings,
)
from core.pinecone import ensure_index, get_pinecone_namespace
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

         collection = ensure_index()
         try:
              collection.delete(delete_all=True, namespace=get_pinecone_namespace())
              print("Deleted existing Pinecone namespace for clean rebuild.")
         except Exception:
              pass
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
         print(f"Upserted embeddings into Pinecone + Mongo backup in {end - start:.2f} seconds.")
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
          vectors_payload = [
               {"id": vector_id, "values": vector, "metadata": metadata}
               for vector_id, vector, metadata in zip(ids, vectors, metadatas)
          ]
          collection.upsert(vectors=vectors_payload, namespace=get_pinecone_namespace())
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
