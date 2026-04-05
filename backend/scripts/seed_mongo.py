import os
import sys

# Add the backend root to the python path so it can import 'core' and 'ml'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pymongo
from core.config import settings
from core.schemas import PostDocument

client = pymongo.MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]
POSTS_TEXT_INDEX_NAME = "posts_text_search"


def _ensure_posts_indexes():
    db.posts.create_index("post_id", unique=True)
    db.posts.create_index([("subreddit", pymongo.ASCENDING)])

    indexes = db.posts.index_information()
    text_indexes = [
        (name, spec)
        for name, spec in indexes.items()
        if "textIndexVersion" in spec
    ]
    desired = indexes.get(POSTS_TEXT_INDEX_NAME)
    desired_is_multilingual = (
        desired is not None
        and "textIndexVersion" in desired
        and str(desired.get("default_language", "english")).lower() == "none"
        and len(text_indexes) == 1
    )
    if desired_is_multilingual:
        return

    for index_name, _ in text_indexes:
        db.posts.drop_index(index_name)

    db.posts.create_index(
        [("title_clean", pymongo.TEXT), ("selftext_clean", pymongo.TEXT), ("combined_text", pymongo.TEXT)],
        weights={"title_clean": 3, "selftext_clean": 1, "combined_text": 1},
        default_language="none",
        name=POSTS_TEXT_INDEX_NAME,
    )

def seed_mongo():
    try:
         _ensure_posts_indexes()
    except Exception as exc:
         print(f"[WARN] Failed to ensure Mongo indexes before seeding: {exc}")
         
    inserted, skipped, failed = 0, 0, 0
    batch = []
    
    try:
        with open("../data/processed/data_cleaned.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    data = json.loads(line.strip())
                    doc = PostDocument(**data).model_dump()
                    batch.append(doc)
                    
                    if len(batch) >= 500:
                         try:
                              db.posts.insert_many(batch, ordered=False)
                              inserted += len(batch)
                         except pymongo.errors.BulkWriteError as bwe:
                              inserts = bwe.details['nInserted']
                              fails = len(bwe.details['writeErrors'])
                              inserted += inserts
                              skipped += fails
                         batch = []
                except Exception as e:
                    failed += 1
                    
        if batch:
             try:
                  db.posts.insert_many(batch, ordered=False)
                  inserted += len(batch)
             except pymongo.errors.BulkWriteError as bwe:
                  inserts = bwe.details['nInserted']
                  fails = len(bwe.details['writeErrors'])
                  inserted += inserts
                  skipped += fails
                  
    except Exception as e:
        print(f"File Error: {e}")
        
    print(f"Total Inserted: {inserted}")
    print(f"Skipped (Dups): {skipped}")
    print(f"Failed: {failed}")

if __name__ == "__main__":
    seed_mongo()
