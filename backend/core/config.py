from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "reddit_investigator"
    MONGO_EMBEDDINGS_COLLECTION: str = "post_embeddings"
    
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION: str = "reddit_posts"

    # Backward-compat: keep reading legacy Redis env var if present,
    # even though Redis/Celery are no longer used by the backend.
    REDIS_URL: str | None = None

    GEMINI_API_KEY: str
    
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIM: int = 384

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
