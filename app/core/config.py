from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # ---------------------------------------------------------
    # Application
    # ---------------------------------------------------------

    app_name: str = "Sawai Associates AI Assistant"
    app_env: str = "development"
    debug: bool = True

    host: str = "127.0.0.1"
    port: int = 8000

    # ---------------------------------------------------------
    # LLM / Groq
    # ---------------------------------------------------------

    llm_provider: str = "groq"
    groq_api_key: str
    llm_model: str = "openai/gpt-oss-120b"

    # ---------------------------------------------------------
    # RAG / Knowledge Base
    # ---------------------------------------------------------

    knowledge_base_dir: str = "knowledge_base"
    chroma_persist_dir: str = "data/chroma"
    chroma_collection: str = "sawai_knowledge"

    embedding_model: str = (
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    chunk_size: int = 900
    chunk_overlap: int = 150

    # RAG retrieval
    rag_top_k: int = 5
    rag_min_relevance_score: float = 0.30
    rag_max_context_chars: int = 12000

    # ---------------------------------------------------------
    # Database
    # ---------------------------------------------------------

    database_path: str = "data/sawai.db"

    # ---------------------------------------------------------
    # Lead notifications
    # ---------------------------------------------------------

    notification_channel: str = "none"

    notification_webhook_url: str | None = None

    whatsapp_url: str | None = None

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    lead_notification_to_email: str | None = None
    smtp_use_tls: bool = True

    # ---------------------------------------------------------
    # Production API
    # ---------------------------------------------------------

    cors_origins: str = (
        "http://localhost:5500,"
        "http://127.0.0.1:5500,"
        "https://sawaiassociates.com,"
        "https://www.sawaiassociates.com"
    )

    chat_rate_limit: str = "20/minute"

    max_chat_message_length: int = 2000

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    # ---------------------------------------------------------
    # Pydantic configuration
    # ---------------------------------------------------------

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