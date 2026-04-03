from typing import List, Dict
from ml.embedder import embed
from core.chroma import get_chroma
from core.mongo import db
from core.schemas import SearchResult, PostDocument
from core.config import settings


def _canonical_post_id(chroma_id: str) -> str:
    chroma_id = str(chroma_id)
    if chroma_id.endswith("_title") or chroma_id.endswith("_body"):
        return chroma_id.rsplit("_", 1)[0]
    return chroma_id


def _dedup_chroma_hits(ids: list[str], distances: list[float]) -> list[tuple[str, float]]:
    best_by_post: dict[str, float] = {}
    for index, chunk_id in enumerate(ids):
        dist = 2.0
        if index < len(distances) and distances[index] is not None:
            dist = float(distances[index])

        post_id = _canonical_post_id(chunk_id)
        current = best_by_post.get(post_id)
        if current is None or dist < current:
            best_by_post[post_id] = dist

    ranked = sorted(best_by_post.items(), key=lambda item: item[1])
    return ranked


async def search(query: str, top_k: int, filters: Dict) -> List[SearchResult]:
    if not query.strip():
        return []
    
    # 1. Embed query 
    query_vector = embed([query])[0].tolist()
    
    # 2. Build Chroma Where clause
    where_clause = {}
    if "subreddit" in filters:
        where_clause["subreddit"] = filters["subreddit"]
        
    chroma_client = get_chroma()
    collection = chroma_client.get_collection(settings.CHROMA_COLLECTION)
    
    # 3. Query Chroma
    chroma_results = collection.query(
        query_embeddings=[query_vector],
        n_results=max(top_k * 3, top_k),
        where=where_clause if where_clause else None
    )
    
    if not chroma_results["ids"] or not chroma_results["ids"][0]:
        return []
        
    chunk_ids = [str(item) for item in chroma_results["ids"][0]]
    distances = [
        float(item) if item is not None else 2.0
        for item in chroma_results["distances"][0]
    ]
    dedup_hits = _dedup_chroma_hits(chunk_ids, distances)
    if not dedup_hits:
        return []

    post_ids = [post_id for post_id, _ in dedup_hits[:top_k]]
    distance_map = {post_id: dist for post_id, dist in dedup_hits}
     
    # 4. Fetch full documents from MongoDB
    # Note: Chroma returns cosine distances (closer to 0 is better if configured internally)
    cursor = db.posts.find({"post_id": {"$in": post_ids}})
    docs_list = await cursor.to_list(length=top_k)
    
    # Map by post_id to preserve ranking order
    doc_map = {str(doc["post_id"]): doc for doc in docs_list}
    
    # 5. Build final result list maintaining Chroma ranking order
    final_results = []
    for pid in post_ids:
        dist = distance_map.get(pid, 2.0)
        # Cosine distance to similarity score
        relevance_score = 1.0 - (dist / 2.0)
        if pid in doc_map:
            post = PostDocument(**doc_map[pid])
            final_results.append(SearchResult(post=post, relevance_score=relevance_score))
            
    return final_results
