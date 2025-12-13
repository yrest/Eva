"""Configuration for embedding service."""

import os
from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Embedding service configuration."""

    # Service
    service_name: str = "eva-embeddings"
    service_host: str = "0.0.0.0"
    service_port: int = 8006

    # Authentication
    embed_token: str = os.getenv("EMBED_TOKEN", "")

    # Embedding backends
    default_backend: Literal["ollama", "lmstudio"] = "ollama"
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    lmstudio_url: str = os.getenv("LMSTUDIO_URL", "http://localhost:1234")

    # Default models
    default_ollama_model: str = "nomic-embed-text"
    default_lmstudio_model: str = "text-embedding-nomic-embed-text-v1.5"

    # Chunking settings
    default_chunk_size: int = 512
    chunk_overlap: int = 50
    max_text_length: int = 100000  # Safety limit

    # Rate limiting
    rate_limit_per_min: int = 1000

    # Logging
    audit_log_path: str = os.getenv("AUDIT_LOG_PATH", "./logs/embeddings_audit.jsonl")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Timeouts
    embedding_timeout: int = 30  # seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
