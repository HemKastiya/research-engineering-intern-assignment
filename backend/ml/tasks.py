"""Celery task definitions. embed_all.delay(), rebuild_clusters.delay(n_topics)."""
from celery import Celery
import pymongo
from core.config import settings
from ml.embedder import embed
from ml.clusterer import run_clustering
from celeryconfig import broker_url

celery_app = Celery('tasks', broker=broker_url)
celery_app.config_from_object('celeryconfig')

@celery_app.task
def embed_all():
     import chromadb
     
     # Sync Mongo Client
     client = pymongo.MongoClient(settings.MONGO_URI)
     db = client[settings.MONGO_DB]
     
     # Chroma Setup
     chroma_client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=str(settings.CHROMA_PORT))
     collection = chroma_client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"}
     )
     
     cursor = db.posts.find()
     batch_size = 64
     
     docs = []
     for doc in cursor:
          docs.append(doc)
          if len(docs) >= batch_size:
               _process_batch(collection, docs)
               docs = []
               
     if docs:
          _process_batch(collection, docs)

def _process_batch(collection, docs):
     ids = [str(d['post_id']) for d in docs]
     texts = [d.get('combined_text', '') for d in docs]
     metadatas = [{
          "author": d.get('author', ''),
          "subreddit": d.get('subreddit', ''),
          "created_date": str(d.get('created_date', '')),
          "score": d.get('score', 0)
     } for d in docs]
     
     embeddings = embed(texts).tolist()
     collection.upsert(
          ids=ids,
          embeddings=embeddings,
          metadatas=metadatas,
          documents=texts
     )

@celery_app.task
def rebuild_clusters(n_topics: int):
     return run_clustering(n_topics)
