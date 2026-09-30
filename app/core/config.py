from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "Sawai Associates AI Assistant"
    app_env: str = "development"
    debug: bool = True

    host: str = "127.0.0.1"
    port: int = 8000

    llm_provider: str = "groq"
    groq_api_key: str
    llm_model: str = "openai/gpt-oss-20b"

    knowledge_base_dir: str = "knowledge_base"
    chroma_persist_dir: str = "data/chroma"
    chroma_collection: str = "sawai_knowledge"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    chunk_size: int = 900
    chunk_overlap: int = 150

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()