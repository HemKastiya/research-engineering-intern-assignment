import asyncio
import copy
import threading
from typing import Any, Optional

from bertopic import BERTopic
from hdbscan import HDBSCAN
from umap import UMAP

from core.config import settings
from ml.embedder import embed

_CLUSTER_CACHE: dict[int, dict[str, Any]] = {}
_CACHE_LOCK = threading.Lock()
_INFLIGHT_TASKS: dict[int, asyncio.Task[dict[str, Any]]] = {}
_INFLIGHT_LOCK = threading.Lock()


class SynchronousMongo:
    def __init__(self):
        import pymongo

        self.client = pymongo.MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB]


def _get_cached(n_topics: int) -> Optional[dict[str, Any]]:
    with _CACHE_LOCK:
        cached = _CLUSTER_CACHE.get(n_topics)
    if cached is None:
        return None
    return copy.deepcopy(cached)


def _set_cached(n_topics: int, result: dict[str, Any]) -> None:
    with _CACHE_LOCK:
        _CLUSTER_CACHE[n_topics] = copy.deepcopy(result)


def clear_cluster_cache() -> None:
    with _CACHE_LOCK:
        _CLUSTER_CACHE.clear()


def _topic_label(topic_id: int, topic_name: str) -> str:
    if topic_id == -1:
        return "-1_Outliers"
    return f"{topic_id}_{topic_name}"


def run_clustering(n_topics: int) -> dict[str, Any]:
    requested_n_topics = n_topics

    cached = _get_cached(requested_n_topics)
    if cached:
        return cached

    sync_mongo = SynchronousMongo()
    try:
        db = sync_mongo.db
        docs = list(db.posts.find({}))
    finally:
        sync_mongo.client.close()

    if len(docs) < 10:
        empty_result = {
            "cluster_labels": [],
            "top_terms": {},
            "post_counts": {},
            "sample_posts": {},
            "samples": {},
            "umap_2d": [],
            "post_ids": [],
        }
        _set_cached(requested_n_topics, empty_result)
        return empty_result

    texts = [d.get("combined_text", "") for d in docs]
    post_ids = [str(d.get("post_id", "")) for d in docs]

    embeddings = embed(texts)

    n_posts = len(texts)
    if n_topics >= n_posts:
        n_topics = max(1, n_posts // 2)

    min_cluster_size = max(5, n_posts // 200)

    umap_model = UMAP(
        n_neighbors=15,
        n_components=5,
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )
    umap_2d = UMAP(
        n_neighbors=15,
        n_components=2,
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

    topic_model = BERTopic(
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        language="english",
        calculate_probabilities=False,
        nr_topics=n_topics if n_topics > 1 else None,
    )

    topics, _ = topic_model.fit_transform(texts, embeddings)
    coords_2d = umap_2d.fit_transform(embeddings)

    topic_info = topic_model.get_topic_info()
    topic_name_map = {
        int(row["Topic"]): str(row["Name"]) for _, row in topic_info.iterrows()
    }

    top_terms: dict[str, list[str]] = {}
    post_counts: dict[str, int] = {}
    sample_posts: dict[str, list[dict[str, Any]]] = {}

    for _, row in topic_info.iterrows():
        topic_id = int(row["Topic"])
        topic_name = topic_name_map.get(topic_id, "Unknown")
        label = _topic_label(topic_id, topic_name)

        post_counts[label] = int(row["Count"])
        words = topic_model.get_topic(topic_id)
        top_terms[label] = [w[0] for w in words[:10]] if words else []
        sample_posts[label] = []

    cluster_labels: list[int] = []
    for index, topic_id in enumerate(topics):
        topic_id_int = int(topic_id)
        topic_name = topic_name_map.get(topic_id_int, "Unknown")
        label = _topic_label(topic_id_int, topic_name)

        cluster_labels.append(topic_id_int)

        if label in sample_posts and len(sample_posts[label]) < 5:
            sample_posts[label].append(docs[index])

    result_dict: dict[str, Any] = {
        "cluster_labels": cluster_labels,
        "top_terms": top_terms,
        "post_counts": post_counts,
        "sample_posts": sample_posts,
        "samples": sample_posts,
        "umap_2d": coords_2d.tolist(),
        "post_ids": post_ids,
    }

    _set_cached(requested_n_topics, result_dict)
    return result_dict


async def run_clustering_async(n_topics: int) -> dict[str, Any]:
    cached = _get_cached(n_topics)
    if cached:
        return cached

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
