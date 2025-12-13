"""Configuration for task management service."""

import os
from typing import Literal
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Task service configuration."""

    # Service
    service_name: str = "eva-tasks"
    service_host: str = "0.0.0.0"
    service_port: int = 8008

    # Authentication
    tasks_read_token: str = os.getenv("TASKS_READ_TOKEN", "")
    tasks_write_token: str = os.getenv("TASKS_WRITE_TOKEN", "")
    tasks_admin_token: str = os.getenv("TASKS_ADMIN_TOKEN", "")

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://eva:eva@localhost:5432/eva"
    )

    # Redis Queue
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    task_queue_name: str = "eva:tasks"
    max_workers: int = 4

    # LLM Backends
    default_llm_backend: Literal["lmstudio", "openai", "anthropic"] = "lmstudio"

    # LM Studio
    lmstudio_url: str = os.getenv("LMSTUDIO_URL", "http://localhost:1234")
    lmstudio_api_key: str = os.getenv("LMSTUDIO_API_KEY", "lm-studio")
    default_lmstudio_model: str = "mistral-7b-instruct"

    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    default_openai_model: str = "gpt-4-turbo-preview"

    # Anthropic
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    default_anthropic_model: str = "claude-3-5-sonnet-20241022"

    # Tool Sandboxing
    docker_enabled: bool = True
    docker_network: str = "none"
    docker_cpu_limit: float = 1.0
    docker_memory_limit: str = "512m"
    docker_timeout: int = 60  # seconds
    sandbox_image: str = "python:3.11-slim"

    # Data Retention
    hot_storage_days: int = 90  # 3 months
    cold_storage_days: int = 180  # 6 months (total)
    archive_enabled: bool = True
    archive_schedule_cron: str = "0 2 * * *"  # 2 AM daily

    # Services Integration
    memory_service_url: str = os.getenv(
        "MEMORY_SERVICE_URL", "http://localhost:8004"
    )
    vector_service_url: str = os.getenv(
        "VECTOR_SERVICE_URL", "http://localhost:8007"
    )
    vector_query_token: str = os.getenv("VECTOR_QUERY_TOKEN", "")
    filesystem_service_url: str = os.getenv(
        "FILESYSTEM_SERVICE_URL", "http://localhost:8005"
    )
    filesystem_read_token: str = os.getenv("FILESYSTEM_READ_TOKEN", "")

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    audit_log_path: str = os.getenv("AUDIT_LOG_PATH", "./logs/tasks_audit.jsonl")

    # Rate Limiting
    rate_limit_per_min: int = 100

    # LLM Request Timeouts
    llm_timeout: int = 120  # seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
