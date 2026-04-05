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
from sklearn.manifold import trustworthiness
from sklearn.neighbors import NearestNeighbors
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
_UMAP_CONFIG_CACHE: dict[str, dict[str, Any]] = {}
_UMAP_CONFIG_LOCK = threading.Lock()

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

_UMAP_PARAM_CANDIDATES: tuple[tuple[int, float], ...] = (
    (10, 0.0),
    (15, 0.0),
    (30, 0.05),
    (45, 0.1),
)
_UMAP_TUNE_SAMPLE_SIZE = 1500
_UMAP_QUALITY_K = 15


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
    with _UMAP_CONFIG_LOCK:
        _UMAP_CONFIG_CACHE.clear()
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


def _as_optional_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(number):
        return None
    return number


def _cosine_knn(embeddings: np.ndarray, n_neighbors: int) -> tuple[np.ndarray, np.ndarray]:
    total = int(embeddings.shape[0])
    neighbors = max(2, min(int(n_neighbors), total))
    model = NearestNeighbors(n_neighbors=neighbors, metric="cosine", algorithm="brute")
    model.fit(embeddings)
    distances, indices = model.kneighbors(embeddings)
    return indices, distances


def _knn_overlap(high_neighbors: np.ndarray, low_neighbors: np.ndarray) -> float:
    if high_neighbors.size == 0 or low_neighbors.size == 0:
        return 0.0

    k = min(int(high_neighbors.shape[1]), int(low_neighbors.shape[1]))
    if k <= 0:
        return 0.0

    overlaps: list[float] = []
    for idx in range(int(high_neighbors.shape[0])):
        hi = {int(item) for item in high_neighbors[idx][:k]}
        lo = {int(item) for item in low_neighbors[idx][:k]}
        overlaps.append(len(hi & lo) / k)
    if not overlaps:
        return 0.0
    return float(np.mean(overlaps))


def _fit_umap_with_precomputed_knn(
    embeddings: np.ndarray,
    *,
    n_neighbors: int,
    n_components: int,
    min_dist: float,
) -> np.ndarray:
    knn_indices, knn_distances = _cosine_knn(embeddings, n_neighbors)
    effective_neighbors = int(knn_indices.shape[1])
    model = UMAP(
        n_neighbors=effective_neighbors,
        n_components=n_components,
        min_dist=float(min_dist),
        metric="cosine",
        random_state=42,
        n_jobs=1,
        precomputed_knn=(knn_indices, knn_distances, None),
    )
    return model.fit_transform(embeddings)


def _tune_umap_config(corpus_key: str, embeddings: np.ndarray) -> dict[str, Any]:
    total = int(embeddings.shape[0])
    default_config = {
        "n_neighbors": 15,
        "min_dist": 0.0,
        "score": None,
        "trustworthiness": None,
        "knn_overlap": None,
        "metric_k": min(_UMAP_QUALITY_K, max(total - 1, 1)),
        "sample_size": min(_UMAP_TUNE_SAMPLE_SIZE, total),
        "candidate_count": len(_UMAP_PARAM_CANDIDATES),
    }
    if total < 10:
        return default_config

    sample_size = min(_UMAP_TUNE_SAMPLE_SIZE, total)
    seed = int(corpus_key[:8], 16) if len(corpus_key) >= 8 else 42
    if sample_size < total:
        rng = np.random.default_rng(seed)
        sample_indices = np.sort(rng.choice(total, size=sample_size, replace=False))
        sample = embeddings[sample_indices]
    else:
        sample = embeddings

    metric_k = min(_UMAP_QUALITY_K, max(sample.shape[0] - 1, 1))
    default_config["metric_k"] = metric_k
    if metric_k < 2:
        return default_config

    high_indices, _ = _cosine_knn(sample, metric_k + 1)
    high_neighbors = high_indices[:, 1:]

    best: Optional[dict[str, Any]] = None
    for n_neighbors, min_dist in _UMAP_PARAM_CANDIDATES:
        try:
            coords = _fit_umap_with_precomputed_knn(
                sample,
                n_neighbors=n_neighbors,
                n_components=2,
                min_dist=min_dist,
            )
            trust = float(
                trustworthiness(
                    sample,
                    coords,
                    n_neighbors=metric_k,
                    metric="cosine",
                )
            )
            low_model = NearestNeighbors(
                n_neighbors=min(metric_k + 1, sample.shape[0]),
                metric="euclidean",
            )
            low_model.fit(coords)
            low_neighbors = low_model.kneighbors(return_distance=False)[:, 1:]
            overlap = _knn_overlap(high_neighbors, low_neighbors)
            score = (0.7 * trust) + (0.3 * overlap)
            candidate = {
                "n_neighbors": int(n_neighbors),
                "min_dist": float(min_dist),
                "score": float(score),
                "trustworthiness": float(trust),
                "knn_overlap": float(overlap),
                "metric_k": int(metric_k),
                "sample_size": int(sample.shape[0]),
                "candidate_count": len(_UMAP_PARAM_CANDIDATES),
            }
            if best is None or candidate["score"] > best["score"]:
                best = candidate
        except Exception:
            continue

    return best if best is not None else default_config


def _get_or_build_umap_config(corpus_key: str, embeddings: np.ndarray) -> dict[str, Any]:
    with _UMAP_CONFIG_LOCK:
        cached = _UMAP_CONFIG_CACHE.get(corpus_key)
    if cached is not None:
        return cached

    tuned = _tune_umap_config(corpus_key, embeddings)
    with _UMAP_CONFIG_LOCK:
        _UMAP_CONFIG_CACHE.clear()
        _UMAP_CONFIG_CACHE[corpus_key] = tuned
    return tuned


def _get_or_build_umap_2d(corpus_key: str, embeddings: np.ndarray) -> np.ndarray:
    with _UMAP_2D_LOCK:
        cached = _UMAP_2D_CACHE.get(corpus_key)
    if cached is not None:
        return cached

    config = _get_or_build_umap_config(corpus_key, embeddings)
    try:
        coords = _fit_umap_with_precomputed_knn(
            embeddings,
            n_neighbors=int(config.get("n_neighbors", 15)),
            n_components=2,
            min_dist=float(config.get("min_dist", 0.0)),
        )
    except Exception:
        # Fallback to conservative defaults if tuned parameters fail.
        coords = _fit_umap_with_precomputed_knn(
            embeddings,
            n_neighbors=15,
            n_components=2,
            min_dist=0.0,
        )
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
    config = _get_or_build_umap_config(corpus_key, embeddings)
    topic_neighbors = int(config.get("n_neighbors", 15))
    topic_min_dist = float(config.get("min_dist", 0.0))
    topic_knn_indices, topic_knn_distances = _cosine_knn(embeddings, topic_neighbors)

    umap_model = UMAP(
        n_neighbors=int(topic_knn_indices.shape[1]),
        n_components=5,
        min_dist=topic_min_dist,
        metric="cosine",
        random_state=42,
        n_jobs=1,
        precomputed_knn=(topic_knn_indices, topic_knn_distances, None),
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=min_cluster_size,
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
        core_dist_n_jobs=1,
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


def _point_confidences(topic_model: BERTopic, expected_size: int) -> list[float]:
    if expected_size <= 0:
        return []

    hdbscan_model = getattr(topic_model, "hdbscan_model", None)
    raw_confidences = getattr(hdbscan_model, "probabilities_", None)
    if raw_confidences is None:
        return [0.0] * expected_size

    confidences = np.asarray(raw_confidences, dtype=np.float32).flatten()
    if confidences.size < expected_size:
        padding = np.zeros(expected_size - confidences.size, dtype=np.float32)
        confidences = np.concatenate((confidences, padding), axis=0)
    if confidences.size > expected_size:
        confidences = confidences[:expected_size]

    clipped = np.clip(confidences, 0.0, 1.0)
    return [float(value) for value in clipped]


def _projection_quality_payload(
    corpus_key: str,
    embeddings: np.ndarray,
    cluster_labels: list[int],
) -> dict[str, Any]:
    config = _get_or_build_umap_config(corpus_key, embeddings)
    outlier_ratio = (
        float(np.mean(np.asarray(cluster_labels, dtype=np.int32) == -1))
        if cluster_labels
        else 0.0
    )
    return {
        "umap_n_neighbors": int(config.get("n_neighbors", 15)),
        "umap_min_dist": float(config.get("min_dist", 0.0)),
        "trustworthiness_at_k": _as_optional_float(config.get("trustworthiness")),
        "knn_overlap_at_k": _as_optional_float(config.get("knn_overlap")),
        "tuning_score": _as_optional_float(config.get("score")),
        "metric_k": int(config.get("metric_k", _UMAP_QUALITY_K)),
        "sample_size": int(config.get("sample_size", min(len(cluster_labels), _UMAP_TUNE_SAMPLE_SIZE))),
        "point_count": int(len(cluster_labels)),
        "outlier_ratio": outlier_ratio,
    }


def _build_cluster_result(
    topic_model: BERTopic,
    topics: list[int],
    docs: list[dict[str, Any]],
    embeddings: np.ndarray,
    coords_2d: np.ndarray,
    post_ids: list[str],
    point_confidences: list[float],
    projection_quality: dict[str, Any],
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
        "point_confidences": point_confidences,
        "projection_quality": projection_quality,
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
    reduction_error: Optional[str] = None
    if target_topics >= natural_topics:
        working_model = base_model
    else:
        working_model = copy.deepcopy(base_model)
        try:
            working_model.reduce_topics(texts, nr_topics=target_topics)
        except Exception as exc:
            # Gracefully fall back to natural topics when BERTopic reduction fails.
            reduction_error = str(exc)
            working_model = base_model
            target_topics = natural_topics

    assignments = [int(topic_id) for topic_id in working_model.topics_]
    point_confidences = _point_confidences(working_model, len(assignments))
    projection_quality = _projection_quality_payload(corpus_key, embeddings, assignments)
    result = _build_cluster_result(
        topic_model=working_model,
        topics=assignments,
        docs=docs,
        embeddings=embeddings,
        coords_2d=coords_2d,
        post_ids=post_ids,
        point_confidences=point_confidences,
        projection_quality=projection_quality,
    )
    result["natural_topics"] = natural_topics
    result["target_topics"] = target_topics
    if reduction_error:
        result["topic_reduction_error"] = reduction_error

    _set_cached(corpus_key, n_topics, result)
    if target_topics != n_topics:
        _set_cached(corpus_key, target_topics, result)
    return result


def run_embedding_projection(n_clusters: int) -> dict[str, Any]:
    cluster_result = run_clustering(n_clusters)
    post_ids = list(cluster_result.get("post_ids", []))
    if not post_ids:
        return {
            "umap_2d": [],
            "cluster_labels": [],
            "post_ids": [],
            "point_labels": [],
            "point_confidences": [],
            "projection_quality": {},
        }

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
        "point_confidences": cluster_result.get("point_confidences", []),
        "projection_quality": cluster_result.get("projection_quality", {}),
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
