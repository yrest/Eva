"""Configuration for vector service."""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Vector service configuration."""

    # Service
    service_name: str = "eva-vectors"
    service_host: str = "0.0.0.0"
    service_port: int = 8007

    # Authentication (dual-token)
    query_token: str = os.getenv("VECTOR_QUERY_TOKEN", "")
    update_token: str = os.getenv("VECTOR_UPDATE_TOKEN", "")

    # Qdrant connection
    qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key: str = os.getenv("QDRANT_API_KEY", "")  # Optional
    qdrant_timeout: int = 30

    # Default collection settings
    default_vector_size: int = 384  # nomic-embed-text dimensions
    default_distance: str = "Cosine"  # Cosine, Euclid, Dot

    # Rate limiting
    rate_limit_queries_per_min: int = 1000
    rate_limit_updates_per_min: int = 100

    # Logging
    audit_log_path: str = os.getenv("AUDIT_LOG_PATH", "./logs/vectors_audit.jsonl")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
