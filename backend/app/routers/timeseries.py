from fastapi import APIRouter, Depends, Query
from core.mongo import get_db
from ml.summarizer import summarize_trend
from typing import Optional

router = APIRouter()

@router.get("/")
async def get_timeseries(
    query: Optional[str] = None,
    subreddit: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db = Depends(get_db)
):
    match = {}
    if subreddit:
        match["subreddit"] = subreddit
    if query:
        match["$text"] = {"$search": query}
    if from_date or to_date:
        match["created_date"] = {}
        if from_date: match["created_date"]["$gte"] = from_date
        if to_date: match["created_date"]["$lte"] = to_date
        
    pipeline = []
    if match: pipeline.append({"$match": match})
    
    pipeline.extend([
        {"$group": {
            "_id": "$created_date", 
            "count": {"$sum": 1}, 
            "avg_score": {"$avg": "$score"}, 
            "avg_engagement": {"$avg": "$engagement"}
        }},
        {"$sort": {"_id": 1}}
    ])
    
    cursor = db.posts.aggregate(pipeline)
    results = await cursor.to_list(length=None)
    
    return [
         {
              "date": r["_id"],
              "count": r["count"],
              "avg_score": r["avg_score"],
              "avg_engagement": r["avg_engagement"]
         } for r in results
    ]

@router.get("/topics")
async def get_timeseries_topics():
    # Placeholder: implementation requires mapping cluster arrays back over time
    return []

@router.get("/summary")
async def get_timeseries_summary(
    query: Optional[str] = None,
    subreddit: Optional[str] = None,
    db = Depends(get_db)
):
    # Fetch data directly internally and then summarize
    data = await get_timeseries(query, subreddit, None, None, db)
    summary = summarize_trend(data, query or subreddit or "all topics")
    return {"summary": summary}
