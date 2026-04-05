import json
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "reddit_investigator"
    MONGO_EMBEDDINGS_COLLECTION: str = "post_embeddings"
    
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_COLLECTION: str = "reddit_posts"

    GEMINI_API_KEY: str
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIM: int = 384

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        raw = value.strip()
        if not raw:
            return []

        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(origin).strip().rstrip("/") for origin in parsed if str(origin).strip()]
            except json.JSONDecodeError:
                pass

        return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
