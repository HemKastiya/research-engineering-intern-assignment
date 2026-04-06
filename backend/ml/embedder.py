from functools import lru_cache
from fastembed import TextEmbedding
import numpy as np
from core.config import settings

@lru_cache(maxsize=1)
def __get_model():
    return TextEmbedding(model_name=settings.EMBEDDING_MODEL)


def warmup_embedder() -> None:
    """
    Eagerly load the sentence-transformer model so the first request does not
    pay model initialization latency.
    """
    __get_model()

def embed(texts: list[str]) -> np.ndarray:
    """
    Embeds a list of texts into a numpy array utilizing batching internally.
    """
    if not texts:
        return np.array([])
    model = __get_model()
    # fastembed natively handles batching and returns a generator of numpy arrays
    embeddings = list(model.embed(texts))
    return np.array(embeddings)
