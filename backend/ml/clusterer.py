import asyncio
import copy
import hashlib
import threading
from typing import Any, Optional

import numpy as np
from bertopic import BERTopic
from bertopic.vectorizers import ClassTfidfTransformer
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
from umap import UMAP

from core.config import settings
from ml.embedder import embed

_CLUSTER_CACHE: dict[tuple[str, int], dict[str, Any]] = {}
_CACHE_LOCK = threading.Lock()
_INFLIGHT_TASKS: dict[int, asyncio.Task[dict[str, Any]]] = {}
_INFLIGHT_LOCK = threading.Lock()

_BASE_TOPIC_MODEL_CACHE: dict[str, BERTopic] = {}
_BASE_TOPIC_MODEL_LOCK = threading.Lock()

_VECTOR_MAP_CACHE: Optional[dict[str, np.ndarray]] = None
_VECTOR_MAP_LOCK = threading.Lock()
_CORPUS_EMBEDDINGS_CACHE: dict[str, np.ndarray] = {}
_CORPUS_EMBEDDINGS_LOCK = threading.Lock()
_UMAP_2D_CACHE: dict[str, np.ndarray] = {}
_UMAP_2D_LOCK = threading.Lock()

_POINT_LABELS_CACHE: dict[str, dict[str, str]] = {}
_POINT_LABELS_LOCK = threading.Lock()

_EMBEDDING_VIEW_CACHE: dict[tuple[str, int], dict[str, Any]] = {}
_EMBEDDING_VIEW_CACHE_LOCK = threading.Lock()
_EMBEDDING_VIEW_INFLIGHT: dict[int, asyncio.Task[dict[str, Any]]] = {}
_EMBEDDING_VIEW_INFLIGHT_LOCK = threading.Lock()

_TOPIC_STOP_WORDS = set(ENGLISH_STOP_WORDS) | {
    "amp",
    "im",
    "ive",
    "dont",
    "didnt",
    "doesnt",
    "cant",
    "couldnt",
    "wouldnt",
    "shouldnt",
    "reddit",
    "subreddit",
    "deleted",
    "removed",
    "post",
    "posts",
    "comment",
    "comments",
    "https",
    "http",
    "www",
    "com",
}


class SynchronousMongo:
    def __init__(self):
        import pymongo

        self.client = pymongo.MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB]


def _load_docs(projection: Optional[dict[str, int]] = None) -> list[dict[str, Any]]:
    sync_mongo = SynchronousMongo()
    try:
        if projection is None:
            return list(sync_mongo.db.posts.find({}))
        return list(sync_mongo.db.posts.find({}, projection))
    finally:
        sync_mongo.client.close()


def _topic_label(topic_id: int, topic_name: str) -> str:
    if topic_id == -1:
        return "-1_Outliers"
    return f"{topic_id}_{topic_name}"


def _corpus_key(post_ids: list[str]) -> str:
    hasher = hashlib.sha256()
    for post_id in post_ids:
        hasher.update(post_id.encode("utf-8", errors="ignore"))
        hasher.update(b"\0")
    return hasher.hexdigest()


def _get_cached(corpus_key: str, n_topics: int) -> Optional[dict[str, Any]]:
    with _CACHE_LOCK:
        cached = _CLUSTER_CACHE.get((corpus_key, n_topics))
    if cached is None:
        return None
    return copy.deepcopy(cached)


def _set_cached(corpus_key: str, n_topics: int, result: dict[str, Any]) -> None:
    with _CACHE_LOCK:
        _CLUSTER_CACHE[(corpus_key, n_topics)] = copy.deepcopy(result)


def clear_cluster_cache() -> None:
    global _VECTOR_MAP_CACHE

    with _CACHE_LOCK:
        _CLUSTER_CACHE.clear()
    with _BASE_TOPIC_MODEL_LOCK:
        _BASE_TOPIC_MODEL_CACHE.clear()
    with _VECTOR_MAP_LOCK:
        _VECTOR_MAP_CACHE = None
    with _CORPUS_EMBEDDINGS_LOCK:
        _CORPUS_EMBEDDINGS_CACHE.clear()
    with _UMAP_2D_LOCK:
        _UMAP_2D_CACHE.clear()
    with _POINT_LABELS_LOCK:
        _POINT_LABELS_CACHE.clear()
    with _EMBEDDING_VIEW_CACHE_LOCK:
        _EMBEDDING_VIEW_CACHE.clear()


def _load_vector_map_from_chroma() -> dict[str, np.ndarray]:
    try:
        from core.chroma import get_chroma

        chroma = get_chroma()
        collection = chroma.get_collection(settings.CHROMA_COLLECTION)
        total = collection.count() if hasattr(collection, "count") else None
        if total is not None and total > 0:
            payload = collection.get(limit=total, include=["embeddings", "metadatas"])
        else:
            payload = collection.get(include=["embeddings", "metadatas"])
    except Exception:
        return {}

    raw_embeddings = payload.get("embeddings")
    raw_metadatas = payload.get("metadatas")
    if raw_embeddings is None or raw_metadatas is None:
        return {}

    if isinstance(raw_embeddings, np.ndarray):
        embeddings = raw_embeddings.tolist()
    else:
        embeddings = list(raw_embeddings)
    if isinstance(raw_metadatas, np.ndarray):
        metadatas = raw_metadatas.tolist()
    else:
        metadatas = list(raw_metadatas)
    if len(embeddings) == 0 or len(metadatas) == 0:
        return {}

    limit = min(len(embeddings), len(metadatas))
    sums: dict[str, np.ndarray] = {}
    counts: dict[str, int] = {}

    for index in range(limit):
        vector = embeddings[index]
        metadata = metadatas[index] or {}
        post_id = str(metadata.get("post_id", "")).strip()
        if not post_id or vector is None:
            continue

        vector_np = np.asarray(vector, dtype=np.float32)
        if post_id in sums:
            sums[post_id] += vector_np
            counts[post_id] += 1
        else:
            sums[post_id] = vector_np.copy()
            counts[post_id] = 1

    return {
        post_id: (sums[post_id] / counts[post_id]).astype(np.float32, copy=False)
        for post_id in sums
    }


def _get_vector_map() -> dict[str, np.ndarray]:
    global _VECTOR_MAP_CACHE
    with _VECTOR_MAP_LOCK:
        if _VECTOR_MAP_CACHE is not None:
            return _VECTOR_MAP_CACHE

    loaded = _load_vector_map_from_chroma()
    with _VECTOR_MAP_LOCK:
        if _VECTOR_MAP_CACHE is None:
            _VECTOR_MAP_CACHE = loaded
        return _VECTOR_MAP_CACHE


def _resolve_embeddings(post_ids: list[str], texts: list[str]) -> np.ndarray:
    vector_map = _get_vector_map()
    vectors: list[Optional[np.ndarray]] = [None] * len(post_ids)
    missing_indices: list[int] = []
    missing_texts: list[str] = []

    for idx, (post_id, text) in enumerate(zip(post_ids, texts)):
        vector = vector_map.get(post_id)
        if vector is None:
            missing_indices.append(idx)
            missing_texts.append(text)
        else:
            vectors[idx] = vector

    if missing_texts:
        fallback_vectors = embed(missing_texts)
        for offset, idx in enumerate(missing_indices):
            vectors[idx] = np.asarray(fallback_vectors[offset], dtype=np.float32)

    if not vectors:
        return np.empty((0, settings.EMBEDDING_DIM), dtype=np.float32)

    first = next((vector for vector in vectors if vector is not None), None)
    if first is None:
        return np.empty((0, settings.EMBEDDING_DIM), dtype=np.float32)

    dim = int(first.shape[0])
    matrix = np.empty((len(vectors), dim), dtype=np.float32)
    zero_vector = np.zeros(dim, dtype=np.float32)
    for idx, vector in enumerate(vectors):
        matrix[idx] = zero_vector if vector is None else vector
    return matrix


def _get_or_build_corpus_embeddings(
    corpus_key: str, post_ids: list[str], texts: list[str]
) -> np.ndarray:
    with _CORPUS_EMBEDDINGS_LOCK:
        cached = _CORPUS_EMBEDDINGS_CACHE.get(corpus_key)
    if cached is not None:
        return cached

    matrix = _resolve_embeddings(post_ids, texts)
    with _CORPUS_EMBEDDINGS_LOCK:
        _CORPUS_EMBEDDINGS_CACHE.clear()
        _CORPUS_EMBEDDINGS_CACHE[corpus_key] = matrix
    return matrix


def _get_or_build_umap_2d(corpus_key: str, embeddings: np.ndarray) -> np.ndarray:
    with _UMAP_2D_LOCK:
        cached = _UMAP_2D_CACHE.get(corpus_key)
    if cached is not None:
        return cached

    umap_2d = UMAP(
        n_neighbors=15,
        n_components=2,
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )
    coords = umap_2d.fit_transform(embeddings)
    with _UMAP_2D_LOCK:
        _UMAP_2D_CACHE.clear()
        _UMAP_2D_CACHE[corpus_key] = coords
    return coords


def _build_base_topic_model(
    corpus_key: str, texts: list[str], embeddings: np.ndarray, n_posts: int
) -> BERTopic:
    with _BASE_TOPIC_MODEL_LOCK:
        cached = _BASE_TOPIC_MODEL_CACHE.get(corpus_key)
    if cached is not None:
        return cached

    min_cluster_size = max(15, min(25, n_posts // 400))

    umap_model = UMAP(
        n_neighbors=15,
        n_components=5,
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=min_cluster_size,
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )
    vectorizer_model = CountVectorizer(
        stop_words=sorted(_TOPIC_STOP_WORDS),
        ngram_range=(1, 2),
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]{2,}\b",
        min_df=2,
        max_df=0.9,
    )
    ctfidf_model = ClassTfidfTransformer(reduce_frequent_words=True)

    topic_model = BERTopic(
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model,
        ctfidf_model=ctfidf_model,
        language="english",
        calculate_probabilities=False,
        nr_topics=None,
    )
    topic_model.fit_transform(texts, embeddings)

    with _BASE_TOPIC_MODEL_LOCK:
        _BASE_TOPIC_MODEL_CACHE.clear()
        _BASE_TOPIC_MODEL_CACHE[corpus_key] = topic_model
    return topic_model


def _natural_topic_count(topic_model: BERTopic) -> int:
    info = topic_model.get_topic_info()
    count = 0
    for _, row in info.iterrows():
        topic_id = int(row["Topic"])
        if topic_id != -1:
            count += 1
    return max(1, count)


def _extract_topic_terms(topic_model: BERTopic, topic_id: int, limit: int = 10) -> list[str]:
    words = topic_model.get_topic(topic_id)
    if not words:
        return []

    terms: list[str] = []
    seen: set[str] = set()
    for word, _ in words:
        token = str(word).strip().lower()
        if not token or token in seen:
            continue
        if token in _TOPIC_STOP_WORDS:
            continue
        if len(token) < 3:
            continue
        if any(ch.isdigit() for ch in token):
            continue
        seen.add(token)
        terms.append(token)
        if len(terms) >= limit:
            break
    return terms


def _post_preview(doc: dict[str, Any]) -> dict[str, Any]:
    raw_title = str(doc.get("title_clean") or "").strip()
    if not raw_title:
        raw_title = str(doc.get("combined_text") or "").strip()
    if not raw_title:
        raw_title = "(untitled)"
    title = raw_title if len(raw_title) <= 220 else f"{raw_title[:217]}..."

    return {
        "post_id": str(doc.get("post_id", "")),
        "title": title,
        "author": str(doc.get("author") or "unknown"),
        "subreddit": str(doc.get("subreddit") or "unknown"),
        "score": int(doc.get("score", 0) or 0),
        "num_comments": int(doc.get("num_comments", 0) or 0),
        "created_date": str(doc.get("created_date") or ""),
        "permalink": str(doc.get("full_permalink") or doc.get("permalink") or ""),
    }


def _representative_post_indices_by_topic(
    topic_assignments: list[int],
    embeddings: np.ndarray,
    top_k: int = 10,
) -> dict[int, list[int]]:
    topic_to_indices: dict[int, list[int]] = {}
    for idx, topic_id in enumerate(topic_assignments):
        topic_to_indices.setdefault(int(topic_id), []).append(idx)

    topic_to_ranked: dict[int, list[int]] = {}
    for topic_id, indices in topic_to_indices.items():
        if not indices:
            topic_to_ranked[topic_id] = []
            continue
        if len(indices) == 1:
            topic_to_ranked[topic_id] = indices
            continue

        topic_vectors = embeddings[indices]
        if topic_vectors.ndim == 1:
            topic_vectors = topic_vectors.reshape(1, -1)

        centroid = topic_vectors.mean(axis=0)
        centroid_norm = float(np.linalg.norm(centroid))
        if centroid_norm <= 1e-12:
            topic_to_ranked[topic_id] = indices[:top_k]
            continue

        vector_norms = np.linalg.norm(topic_vectors, axis=1)
        denom = np.maximum(vector_norms * centroid_norm, 1e-12)
        similarities = np.dot(topic_vectors, centroid) / denom
        ranking = np.argsort(-similarities)
        topic_to_ranked[topic_id] = [indices[int(i)] for i in ranking[:top_k]]

    return topic_to_ranked


def _build_cluster_result(
    topic_model: BERTopic,
    topics: list[int],
    docs: list[dict[str, Any]],
    embeddings: np.ndarray,
    coords_2d: np.ndarray,
    post_ids: list[str],
) -> dict[str, Any]:
    topic_info = topic_model.get_topic_info()
    topic_name_map = {
        int(row["Topic"]): str(row["Name"]) for _, row in topic_info.iterrows()
    }
    cluster_labels = [int(topic_id) for topic_id in topics]
    representative_indices = _representative_post_indices_by_topic(
        cluster_labels,
        embeddings,
        top_k=10,
    )

    topics_payload: list[dict[str, Any]] = []
    outlier_topic: Optional[dict[str, Any]] = None
    top_terms: dict[str, list[str]] = {}
    post_counts: dict[str, int] = {}
    sample_posts: dict[str, list[dict[str, Any]]] = {}

    for _, row in topic_info.iterrows():
        topic_id = int(row["Topic"])
        topic_name = topic_name_map.get(topic_id, "Unknown")
        label = _topic_label(topic_id, topic_name)
        terms = _extract_topic_terms(topic_model, topic_id, limit=10)
        ranked_indices = representative_indices.get(topic_id, [])
        top_post_previews = [_post_preview(docs[idx]) for idx in ranked_indices]

        post_counts[label] = int(row["Count"])
        top_terms[label] = terms
        sample_posts[label] = [docs[idx] for idx in ranked_indices[:5]]

        payload = {
            "topic_id": topic_id,
            "name": topic_name,
            "count": int(row["Count"]),
            "representation": terms,
            "top_posts": top_post_previews,
        }
        if topic_id == -1:
            outlier_topic = payload
        else:
            topics_payload.append(payload)

    return {
        "topics": sorted(
            topics_payload if topics_payload or outlier_topic is None else [outlier_topic],
            key=lambda topic: topic["count"],
            reverse=True,
        ),
        "cluster_labels": cluster_labels,
        "top_terms": top_terms,
        "post_counts": post_counts,
        "sample_posts": sample_posts,
        "samples": sample_posts,
        "umap_2d": coords_2d.tolist(),
        "post_ids": post_ids,
    }


def _point_label_map(corpus_key: str) -> dict[str, str]:
    with _POINT_LABELS_LOCK:
        cached = _POINT_LABELS_CACHE.get(corpus_key)
    if cached is not None:
        return cached

    docs = _load_docs({"post_id": 1, "author": 1, "subreddit": 1})
    labels = {
        str(doc.get("post_id", "")): (
            f"u/{str(doc.get('author') or 'unknown')} in r/{str(doc.get('subreddit') or 'unknown')}"
        )
        for doc in docs
    }

    with _POINT_LABELS_LOCK:
        _POINT_LABELS_CACHE.clear()
        _POINT_LABELS_CACHE[corpus_key] = labels
    return labels


def run_clustering(n_topics: int) -> dict[str, Any]:
    docs = _load_docs()
    if len(docs) < 10:
        return {
            "topics": [],
            "cluster_labels": [],
            "top_terms": {},
            "post_counts": {},
            "sample_posts": {},
            "samples": {},
            "umap_2d": [],
            "post_ids": [],
        }

    texts = [str(doc.get("combined_text", "")) for doc in docs]
    post_ids = [str(doc.get("post_id", "")) for doc in docs]
    corpus_key = _corpus_key(post_ids)

    cached = _get_cached(corpus_key, n_topics)
    if cached is not None:
        return cached

    embeddings = _get_or_build_corpus_embeddings(corpus_key, post_ids, texts)
    coords_2d = _get_or_build_umap_2d(corpus_key, embeddings)
    base_model = _build_base_topic_model(corpus_key, texts, embeddings, len(texts))
    natural_topics = _natural_topic_count(base_model)

    target_topics = max(2, min(n_topics, natural_topics)) if natural_topics > 1 else 1
    if target_topics >= natural_topics:
        working_model = base_model
    else:
        working_model = copy.deepcopy(base_model)
        working_model.reduce_topics(texts, nr_topics=target_topics)

    assignments = [int(topic_id) for topic_id in working_model.topics_]
    result = _build_cluster_result(
        topic_model=working_model,
        topics=assignments,
        docs=docs,
        embeddings=embeddings,
        coords_2d=coords_2d,
        post_ids=post_ids,
    )

    _set_cached(corpus_key, n_topics, result)
    if target_topics != n_topics:
        _set_cached(corpus_key, target_topics, result)
    return result


def run_embedding_projection(n_clusters: int) -> dict[str, Any]:
    cluster_result = run_clustering(n_clusters)
    post_ids = list(cluster_result.get("post_ids", []))
    if not post_ids:
        return {"umap_2d": [], "cluster_labels": [], "post_ids": [], "point_labels": []}

    corpus_key = _corpus_key(post_ids)
    cache_key = (corpus_key, n_clusters)

    with _EMBEDDING_VIEW_CACHE_LOCK:
        cached = _EMBEDDING_VIEW_CACHE.get(cache_key)
    if cached is not None:
        return copy.deepcopy(cached)

    label_map = _point_label_map(corpus_key)
    point_labels = [label_map.get(post_id, "u/unknown in r/unknown") for post_id in post_ids]

    result = {
        "umap_2d": cluster_result.get("umap_2d", []),
        "cluster_labels": cluster_result.get("cluster_labels", []),
        "post_ids": post_ids,
        "point_labels": point_labels,
    }
    with _EMBEDDING_VIEW_CACHE_LOCK:
        _EMBEDDING_VIEW_CACHE[cache_key] = copy.deepcopy(result)
    return result


async def run_clustering_async(n_topics: int) -> dict[str, Any]:
    with _INFLIGHT_LOCK:
        task = _INFLIGHT_TASKS.get(n_topics)
        if task is None or task.done():
            loop = asyncio.get_running_loop()
            task = loop.create_task(
                asyncio.to_thread(run_clustering, n_topics),
                name=f"run_clustering_{n_topics}",
            )
            _INFLIGHT_TASKS[n_topics] = task

    try:
        return await task
    finally:
        if task.done():
            with _INFLIGHT_LOCK:
                if _INFLIGHT_TASKS.get(n_topics) is task:
                    _INFLIGHT_TASKS.pop(n_topics, None)


async def run_embedding_projection_async(n_clusters: int) -> dict[str, Any]:
    with _EMBEDDING_VIEW_INFLIGHT_LOCK:
        task = _EMBEDDING_VIEW_INFLIGHT.get(n_clusters)
        if task is None or task.done():
            loop = asyncio.get_running_loop()
            task = loop.create_task(
                asyncio.to_thread(run_embedding_projection, n_clusters),
                name=f"run_embedding_projection_{n_clusters}",
            )
            _EMBEDDING_VIEW_INFLIGHT[n_clusters] = task

    try:
        return await task
    finally:
        if task.done():
            with _EMBEDDING_VIEW_INFLIGHT_LOCK:
                if _EMBEDDING_VIEW_INFLIGHT.get(n_clusters) is task:
                    _EMBEDDING_VIEW_INFLIGHT.pop(n_clusters, None)
