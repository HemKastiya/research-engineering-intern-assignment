from fastapi import APIRouter
from ml.network_builder import build_graph, remove_node
from typing import Optional

router = APIRouter()

@router.get("")
async def get_network(subreddit: Optional[str] = None, query: Optional[str] = None, min_edge_weight: int = 1):
    graph = build_graph(query, subreddit)
    # filter edges below threshold
    filtered_edges = [e for e in graph["edges"] if e["weight"] >= min_edge_weight]
    graph["edges"] = filtered_edges
    return graph

@router.delete("/node/{author_id}")
async def delete_network_node(author_id: str, subreddit: Optional[str] = None, query: Optional[str] = None):
    # This simulates recomputation on subgraph drop by first building full, then pruning and recomputing pagerank
    graph = build_graph(query, subreddit)
    updated = remove_node(graph, author_id)
    return updated
