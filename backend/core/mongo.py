import pymongo
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import settings

client = AsyncIOMotorClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]
posts_collection = db["posts"]
POSTS_TEXT_INDEX_NAME = "posts_text_search"


async def ensure_posts_indexes() -> None:
    await posts_collection.create_index("post_id", unique=True)
    await posts_collection.create_index([("subreddit", pymongo.ASCENDING)])

    indexes = await posts_collection.index_information()
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
        await posts_collection.drop_index(index_name)

    await posts_collection.create_index(
        [("title_clean", pymongo.TEXT), ("selftext_clean", pymongo.TEXT), ("combined_text", pymongo.TEXT)],
        weights={"title_clean": 3, "selftext_clean": 1, "combined_text": 1},
        default_language="none",
        name=POSTS_TEXT_INDEX_NAME,
    )

async def get_db():
    try:
         yield db
    finally:
         pass
