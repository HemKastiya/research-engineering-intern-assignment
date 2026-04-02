from typing import List, Dict
from ml.embedder import embed
from core.chroma import get_chroma
from core.mongo import db
from core.schemas import SearchResult, PostDocument
from core.config import settings

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
        n_results=top_k,
        where=where_clause if where_clause else None
    )
    
    if not chroma_results["ids"] or not chroma_results["ids"][0]:
        return []
        
    post_ids = chroma_results["ids"][0]
    distances = chroma_results["distances"][0] 
     
    # 4. Fetch full documents from MongoDB
    # Note: Chroma returns cosine distances (closer to 0 is better if configured internally)
    cursor = db.posts.find({"post_id": {"$in": post_ids}})
    docs_list = await cursor.to_list(length=top_k)
    
    # Map by post_id to preserve ranking order
    doc_map = {doc["post_id"]: doc for doc in docs_list}
    
    # 5. Build final result list maintaining Chroma ranking order
    final_results = []
    for pid, dist in zip(post_ids, distances):
        # Cosine distance to similarity score
        relevance_score = 1.0 - (dist / 2.0)
        if pid in doc_map:
            post = PostDocument(**doc_map[pid])
            final_results.append(SearchResult(post=post, relevance_score=relevance_score))
            
    return final_results
