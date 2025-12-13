"""Security layer for file system access control."""

import os
from pathlib import Path
from typing import List, Optional
from fastapi import HTTPException, status

from .config import settings


class SecurityValidator:
    """Validates and sanitizes file system operations."""

    def __init__(self):
        self.allowed_paths = [
            Path(p).resolve() for p in settings.allowed_paths_list
        ]

    def _is_path_allowed(self, path: Path) -> bool:
        """Check if path is within allowed directories."""
        try:
            resolved = path.resolve()
            return any(
                resolved == allowed or resolved.is_relative_to(allowed)
                for allowed in self.allowed_paths
            )
        except (ValueError, RuntimeError):
            return False

    def _is_symlink_attack(self, path: Path) -> bool:
        """Detect potential symlink traversal attacks."""
        try:
            # Check if any component in the path is a symlink
            # that points outside allowed paths
            current = path
            while current != current.parent:
                if current.is_symlink():
                    target = current.readlink()
                    if not self._is_path_allowed(target):
                        return True
                current = current.parent
            return False
        except (OSError, RuntimeError):
            return True

    def validate_read_path(self, path: str) -> Path:
        """
        Validate a path for read operations.

        Args:
            path: Path to validate

        Returns:
            Resolved Path object

        Raises:
            HTTPException: If path is invalid or not allowed
        """
        try:
            file_path = Path(path).resolve()
        except (ValueError, RuntimeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid path: {str(e)}"
            )

        # Check if path is within allowed directories
        if not self._is_path_allowed(file_path):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: path not in allowed directories"
            )

        # Check for symlink attacks
        if self._is_symlink_attack(file_path):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: potential symlink traversal detected"
            )

        # Check if file exists for read operations
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File or directory not found"
            )

        return file_path

    def validate_write_path(self, path: str, check_exists: bool = False) -> Path:
        """
        Validate a path for write operations.

        Args:
            path: Path to validate
            check_exists: If True, verify file doesn't already exist

        Returns:
            Resolved Path object

        Raises:
            HTTPException: If path is invalid or not allowed
        """
        try:
            file_path = Path(path).resolve()
        except (ValueError, RuntimeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid path: {str(e)}"
            )

        # Check if path is within allowed directories
        if not self._is_path_allowed(file_path):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: path not in allowed directories"
            )

        # Check for symlink attacks in parent directories
        parent = file_path.parent
        if self._is_symlink_attack(parent):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: potential symlink traversal detected"
            )

        # Ensure parent directory exists
        if not parent.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent directory does not exist"
            )

        # Check if file already exists (if requested)
        if check_exists and file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="File already exists"
            )

        return file_path

    def validate_file_size(self, size_bytes: int) -> None:
        """
        Validate file size is within limits.

        Args:
            size_bytes: File size in bytes

        Raises:
            HTTPException: If file size exceeds limit
        """
        if size_bytes > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {settings.max_file_size_mb}MB"
            )


# Global security validator instance
security = SecurityValidator()
