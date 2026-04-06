from core.pinecone import ensure_index, get_pinecone_index

# Deprecated: kept for backward compatibility after Pinecone migration.


def get_chroma():
    return get_pinecone_index()


def ensure_collection():
    return ensure_index()
