"""Audit logging system for tracking all filesystem operations."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi.security import HTTPAuthorizationCredentials

from .config import settings


class AuditLogger:
    """Comprehensive audit logging for filesystem operations."""

    def __init__(self):
        # Ensure log directory exists
        log_path = Path(settings.audit_log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Configure logger
        self.logger = logging.getLogger("filesystem.audit")
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
        path: str,
        credentials: Optional[HTTPAuthorizationCredentials],
        success: bool,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Log a filesystem operation.

        Args:
            operation: Type of operation (read_file, write_file, etc.)
            path: File path accessed
            credentials: Authentication credentials used
            success: Whether operation succeeded
            details: Additional operation details (file size, hash, etc.)
            error: Error message if operation failed
        """
        # Determine token type (safely)
        token_type = "unknown"
        if credentials:
            token = credentials.credentials
            if token == settings.read_token:
                token_type = "read"
            elif token == settings.write_token:
                token_type = "write"

        # Build audit entry
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "path": str(path),
            "token_type": token_type,
            "success": success,
        }

        # Add optional fields
        if details:
            entry["details"] = details

        if error:
            entry["error"] = error

        # Log as JSON
        self.logger.info(json.dumps(entry))

    async def log_read(
        self,
        path: str,
        credentials: HTTPAuthorizationCredentials,
        success: bool,
        file_size: Optional[int] = None,
        file_hash: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """Log a read operation."""
        details = {}
        if file_size is not None:
            details["file_size"] = file_size
        if file_hash:
            details["file_hash"] = file_hash

        self.log_operation(
            operation="read_file",
            path=path,
            credentials=credentials,
            success=success,
            details=details if details else None,
            error=error
        )

    async def log_write(
        self,
        path: str,
        credentials: HTTPAuthorizationCredentials,
        success: bool,
        file_size: Optional[int] = None,
        file_hash: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """Log a write operation."""
        details = {}
        if file_size is not None:
            details["file_size"] = file_size
        if file_hash:
            details["file_hash"] = file_hash

        self.log_operation(
            operation="write_file",
            path=path,
            credentials=credentials,
            success=success,
            details=details if details else None,
            error=error
        )

    async def log_list(
        self,
        path: str,
        credentials: HTTPAuthorizationCredentials,
        success: bool,
        item_count: Optional[int] = None,
        error: Optional[str] = None
    ) -> None:
        """Log a directory listing operation."""
        details = {}
        if item_count is not None:
            details["item_count"] = item_count

        self.log_operation(
            operation="list_directory",
            path=path,
            credentials=credentials,
            success=success,
            details=details if details else None,
            error=error
        )

    async def log_search(
        self,
        query: str,
        credentials: HTTPAuthorizationCredentials,
        success: bool,
        result_count: Optional[int] = None,
        error: Optional[str] = None
    ) -> None:
        """Log a search operation."""
        details = {}
        if result_count is not None:
            details["result_count"] = result_count

        self.log_operation(
            operation="search_files",
            path=f"query:{query}",
            credentials=credentials,
            success=success,
            details=details if details else None,
            error=error
        )


# Global audit logger instance
audit = AuditLogger()
