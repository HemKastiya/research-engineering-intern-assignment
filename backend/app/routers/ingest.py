"""GET /api/ingest/status returns Mongo count, vector count, and embedding status."""
from fastapi import APIRouter, Depends

from core.chroma import get_chroma
from core.config import settings
from core.mongo import get_db
from ml.tasks import get_embedding_status

router = APIRouter()


@router.get("/status")
async def get_ingest_status(db=Depends(get_db)):
    mongo_count = await db.posts.count_documents({})

    chroma = get_chroma()
    try:
        collection = chroma.get_collection(settings.CHROMA_COLLECTION)
        if hasattr(collection, "count"):
            vector_count = collection.count()
        else:
            vector_count = len(collection.get()["ids"])
    except Exception:
        vector_count = 0

    task_status = get_embedding_status()
    if task_status == "Processing":
        status = "Processing"
    elif task_status == "Failed":
        status = "Failed"
    else:
        status = "Idle" if mongo_count == vector_count else "Processing"

    return {
        "mongo_documents": mongo_count,
        "chroma_vectors": vector_count,
        "embedding_status": status,
    }
