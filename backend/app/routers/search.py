from fastapi import APIRouter, HTTPException
from core.schemas import SearchRequest, SearchResult
from ml.semantic_search import search
from typing import List

router = APIRouter()

@router.post("/", response_model=List[SearchResult])
async def search_posts(req: SearchRequest):
    if not req.query or len(req.query.strip()) < 3:
         raise HTTPException(status_code=400, detail="Query must exceed 3 characters")
         
    filters = {}
    if req.subreddit_filter:
         filters["subreddit"] = req.subreddit_filter
         
    try:
         results = await search(req.query, req.top_k, filters)
         return results
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))
