from fastapi import APIRouter
from fastapi import Query
from typing import Any
from core.schemas import ClusterResult
from ml.clusterer import run_clustering_async, run_embedding_projection_async

router = APIRouter()


def _build_topics_from_legacy_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    top_terms = result.get("top_terms") or {}
    post_counts = result.get("post_counts") or {}
    topics: list[dict[str, Any]] = []
    outlier_topic: dict[str, Any] | None = None

    for label, count in post_counts.items():
        topic_id = 0
        topic_name = str(label)
        if "_" in str(label):
            raw_id, raw_name = str(label).split("_", 1)
            try:
                topic_id = int(raw_id)
                topic_name = raw_name
            except ValueError:
                topic_name = str(label)
        topic_payload = (
            {
                "topic_id": topic_id,
                "name": topic_name,
                "count": int(count),
                "representation": list(top_terms.get(label, [])),
            }
        )
        if topic_id == -1:
            outlier_topic = topic_payload
        else:
            topics.append(topic_payload)

    if not topics and outlier_topic is not None:
        topics.append(outlier_topic)
    topics.sort(key=lambda topic: topic["count"], reverse=True)
    return topics

@router.get("/", response_model=ClusterResult)
async def get_clusters(n_topics: int = 10):
    n_topics = max(2, min(n_topics, 50))
    result = await run_clustering_async(n_topics)
    if not isinstance(result.get("topics"), list):
        result["topics"] = _build_topics_from_legacy_result(result)
    return ClusterResult(**result)
    
@router.get("/embeddings")
async def get_cluster_embeddings(
    n_clusters: int = Query(10, ge=2, le=50),
    n_topics: int | None = Query(None, ge=2, le=50),
):
    # Backward compatibility: accept legacy n_topics for older clients.
    if n_topics is not None:
        n_clusters = n_topics
    result = await run_embedding_projection_async(n_clusters)
    return {
        "umap_2d": result.get("umap_2d", []),
        "cluster_labels": result.get("cluster_labels", []),
        "post_ids": result.get("post_ids", []),
        "point_labels": result.get("point_labels", []),
    }
