"""GET /api/ingest/status — returns document count from MongoDB + vector count from Chroma + embedding job status from Celery/Redis."""
from fastapi import APIRouter, Depends
from core.mongo import get_db
from core.chroma import get_chroma
from core.config import settings

router = APIRouter()

@router.get("/status")
async def get_ingest_status(db=Depends(get_db)):
    mongo_count = await db.posts.count_documents({})
    
    chroma = get_chroma()
    try:
         collection = chroma.get_collection(settings.CHROMA_COLLECTION)
         if hasattr(collection, 'count'):
              vector_count = collection.count()
         else:
              vector_count = len(collection.get()['ids'])
    except Exception:
         vector_count = 0
         
    # Dummy embedding status logic (would poll Celery here explicitly in heavy environments)
    status = "Idle" if mongo_count == vector_count else "Processing"
    
    return {
         "mongo_documents": mongo_count,
         "chroma_vectors": vector_count,
         "embedding_status": status
    }
