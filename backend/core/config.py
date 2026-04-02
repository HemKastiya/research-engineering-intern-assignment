from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "reddit_investigator"
    
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION: str = "reddit_posts"
    
    REDIS_URL: str = "redis://localhost:6379/0"
    
    GEMINI_API_KEY: str
    
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
