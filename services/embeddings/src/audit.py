"""Audit logging system for embedding operations."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi.security import HTTPAuthorizationCredentials

from .config import settings


class AuditLogger:
    """Comprehensive audit logging for embedding operations."""

    def __init__(self):
        # Ensure log directory exists
        log_path = Path(settings.audit_log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Configure logger
        self.logger = logging.getLogger("embeddings.audit")
        self.logger.setLevel(logging.INFO)

        # File handler with JSON formatting
        handler = logging.FileHandler(settings.audit_log_path)
        handler.setLevel(logging.INFO)

        # Simple formatter - we'll use JSON in the message itself
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)

    def log_operation(
        self,
        operation: str,
        credentials: Optional[HTTPAuthorizationCredentials],
        success: bool,
        backend: str,
        model: str,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Log an embedding operation.

        Args:
            operation: Type of operation (embed_text, embed_batch, etc.)
            credentials: Authentication credentials used
            success: Whether operation succeeded
            backend: Backend used (ollama, lmstudio)
            model: Model name used
            details: Additional operation details
            error: Error message if operation failed
        """
        # Build audit entry
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "backend": backend,
            "model": model,
            "success": success,
            "privacy_guarantee": {
                "data_location": "local",
                "external_calls": False,
                "model_type": f"local_{backend}"
            }
        }

        # Add optional fields
        if details:
            entry["details"] = details

        if error:
            entry["error"] = error

        # Log as JSON
        self.logger.info(json.dumps(entry))

    async def log_embed(
        self,
        credentials: HTTPAuthorizationCredentials,
        success: bool,
        backend: str,
        model: str,
        text_count: int = 1,
        total_tokens: Optional[int] = None,
        vector_dimensions: Optional[int] = None,
        processing_time_ms: Optional[float] = None,
        chunked: bool = False,
        chunk_count: Optional[int] = None,
        error: Optional[str] = None
    ) -> None:
        """Log an embedding operation."""
        details = {
            "text_count": text_count,
            "chunked": chunked
        }

        if total_tokens is not None:
            details["total_tokens"] = total_tokens
        if vector_dimensions is not None:
            details["vector_dimensions"] = vector_dimensions
        if processing_time_ms is not None:
            details["processing_time_ms"] = round(processing_time_ms, 2)
        if chunk_count is not None:
            details["chunk_count"] = chunk_count

        self.log_operation(
            operation="embed_text",
            credentials=credentials,
            success=success,
            backend=backend,
            model=model,
            details=details,
            error=error
        )


# Global audit logger instance
audit = AuditLogger()
