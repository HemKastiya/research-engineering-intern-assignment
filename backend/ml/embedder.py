from functools import lru_cache
from sentence_transformers import SentenceTransformer
import numpy as np
from core.config import settings

@lru_cache(maxsize=1)
def __get_model():
    return SentenceTransformer(settings.EMBEDDING_MODEL)

def embed(texts: list[str]) -> np.ndarray:
    """
    Embeds a list of texts into a numpy array utilizing batching internally.
    """
    if not texts:
        return np.array([])
    model = __get_model()
    # sentence-transformers natively handles batching and returns a numpy matrix
    embeddings = model.encode(texts, show_progress_bar=False)
    return embeddings
