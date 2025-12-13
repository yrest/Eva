"""Configuration management for the filesystem service."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server configuration
    service_host: str = "0.0.0.0"
    service_port: int = 8005

    # Security tokens
    read_token: str
    write_token: str
    jwt_secret: str

    # File access control
    allowed_paths: str  # Comma-separated paths
    max_file_size_mb: int = 100
    rate_limit_per_minute: int = 60

    # Storage
    sqlite_db_path: str = "./data/filesystem.db"
    audit_log_path: str = "./data/audit.log"

    # Future: Qdrant integration
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    enable_vector_index: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def allowed_paths_list(self) -> List[str]:
        """Parse allowed paths from comma-separated string."""
        return [p.strip() for p in self.allowed_paths.split(",") if p.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size to bytes."""
        return self.max_file_size_mb * 1024 * 1024


# Global settings instance
settings = Settings()
