from fastapi import APIRouter
from core.schemas import ClusterResult
from ml.clusterer import run_clustering_async

router = APIRouter()

@router.get("/", response_model=ClusterResult)
async def get_clusters(n_topics: int = 10):
    n_topics = max(2, min(n_topics, 50))
    result = await run_clustering_async(n_topics)
    return ClusterResult(**result)
    
@router.get("/embeddings")
async def get_cluster_embeddings(n_topics: int = 10):
    n_topics = max(2, min(n_topics, 50))
    result = await run_clustering_async(n_topics)
    return {
        "umap_2d": result.get("umap_2d", []),
        "cluster_labels": result.get("cluster_labels", []),
        "post_ids": result.get("post_ids", [])
    }
