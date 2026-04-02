from motor.motor_asyncio import AsyncIOMotorClient
from core.config import settings

client = AsyncIOMotorClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]
posts_collection = db["posts"]

async def get_db():
    try:
         yield db
    finally:
         pass
