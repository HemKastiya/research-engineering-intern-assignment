import chromadb
from chromadb.config import Settings
from core.config import settings

# ChromaDB uses a slightly different architecture; we'll connect utilizing HttpClient for the external docker container
chroma_client = chromadb.HttpClient(
    host=settings.CHROMA_HOST, 
    port=str(settings.CHROMA_PORT)
)

def get_chroma():
    return chroma_client

def ensure_collection():
    """
    Creates the Chroma collection with correct cosine distance metric if it doesn't exist.
    """
    # Chroma uses L2 by default, we configure cosine via metadata
    collection = chroma_client.get_or_create_collection(
        name=settings.CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"}
    )
    return collection
