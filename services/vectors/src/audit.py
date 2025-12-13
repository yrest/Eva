"""Audit logging system for vector operations."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi.security import HTTPAuthorizationCredentials

from .config import settings


class AuditLogger:
    """Comprehensive audit logging for vector operations."""

    def __init__(self):
        # Ensure log directory exists
        log_path = Path(settings.audit_log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Configure logger
        self.logger = logging.getLogger("vectors.audit")
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
        collection: str,
        credentials: Optional[HTTPAuthorizationCredentials],
        success: bool,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Log a vector operation.

        Args:
            operation: Type of operation (upsert, search, delete, etc.)
            collection: Collection name
            credentials: Authentication credentials used
            success: Whether operation succeeded
            details: Additional operation details
            error: Error message if operation failed
        """
        # Determine token type (safely)
        token_type = "unknown"
        if credentials:
            token = credentials.credentials
            if token == settings.query_token:
                token_type = "query"
            elif token == settings.update_token:
                token_type = "update"

        # Build audit entry
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "collection": collection,
            "token_type": token_type,
            "success": success,
            "privacy_guarantee": {
                "data_location": "local",
                "external_calls": False,
                "storage": "qdrant_local"
            }
        }

        # Add optional fields
        if details:
            entry["details"] = details

        if error:
            entry["error"] = error

        # Log as JSON
        self.logger.info(json.dumps(entry))

    async def log_upsert(
        self,
        collection: str,
        credentials: HTTPAuthorizationCredentials,
        success: bool,
        vector_count: int,
        dimensions: Optional[int] = None,
        processing_time_ms: Optional[float] = None,
        error: Optional[str] = None
    ) -> None:
        """Log an upsert operation."""
        details = {"vector_count": vector_count}
        if dimensions is not None:
            details["dimensions"] = dimensions
        if processing_time_ms is not None:
            details["processing_time_ms"] = round(processing_time_ms, 2)

        self.log_operation(
            operation="upsert_vectors",
            collection=collection,
            credentials=credentials,
            success=success,
            details=details,
            error=error
        )

    async def log_search(
        self,
        collection: str,
        credentials: HTTPAuthorizationCredentials,
        success: bool,
        result_count: Optional[int] = None,
        limit: Optional[int] = None,
        processing_time_ms: Optional[float] = None,
        error: Optional[str] = None
    ) -> None:
        """Log a search operation."""
        details = {}
        if result_count is not None:
            details["result_count"] = result_count
        if limit is not None:
            details["limit"] = limit
        if processing_time_ms is not None:
            details["processing_time_ms"] = round(processing_time_ms, 2)

        self.log_operation(
            operation="search_vectors",
            collection=collection,
            credentials=credentials,
            success=success,
            details=details if details else None,
            error=error
        )

    async def log_delete(
        self,
        collection: str,
        credentials: HTTPAuthorizationCredentials,
        success: bool,
        deleted_count: Optional[int] = None,
        error: Optional[str] = None
    ) -> None:
        """Log a delete operation."""
        details = {}
        if deleted_count is not None:
            details["deleted_count"] = deleted_count

        self.log_operation(
            operation="delete_vectors",
            collection=collection,
            credentials=credentials,
            success=success,
            details=details if details else None,
            error=error
        )

    async def log_collection_op(
        self,
        operation: str,
        collection: str,
        credentials: HTTPAuthorizationCredentials,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """Log a collection operation (create, delete, info)."""
        self.log_operation(
            operation=operation,
            collection=collection,
            credentials=credentials,
            success=success,
            details=details,
            error=error
        )


# Global audit logger instance
audit = AuditLogger()
