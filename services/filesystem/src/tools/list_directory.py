"""MCP tool for listing directory contents with security and auditing."""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from ..security import security
from ..audit import audit


async def list_directory_tool(
    path: str,
    credentials: HTTPAuthorizationCredentials,
    recursive: bool = False,
    include_hidden: bool = False,
    max_depth: int = 3
) -> Dict[str, Any]:
    """
    List directory contents with security validation and auditing.

    Args:
        path: Path to the directory to list
        credentials: Authentication credentials
        recursive: If True, list subdirectories recursively
        include_hidden: If True, include hidden files (starting with .)
        max_depth: Maximum recursion depth (default 3)

    Returns:
        Dictionary containing:
            - path: Directory path
            - items: List of items in directory
            - total_count: Total number of items

    Raises:
        HTTPException: If access is denied or directory cannot be listed
    """
    try:
        # Validate path security
        dir_path = security.validate_read_path(path)

        # Verify it's a directory
        if not dir_path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path is not a directory"
            )

        # List items
        items = []

        def should_include(item: Path) -> bool:
            """Check if item should be included based on filters."""
            if not include_hidden and item.name.startswith('.'):
                return False
            return True

        def list_dir(current_path: Path, depth: int = 0) -> None:
            """Recursively list directory contents."""
            if recursive and depth >= max_depth:
                return

            try:
                for item in current_path.iterdir():
                    if not should_include(item):
                        continue

                    # Get item stats
                    try:
                        stat = item.stat()
                        is_dir = item.is_dir()
                        is_file = item.is_file()
                        is_symlink = item.is_symlink()

                        item_data = {
                            "name": item.name,
                            "path": str(item),
                            "is_directory": is_dir,
                            "is_file": is_file,
                            "is_symlink": is_symlink,
                            "size": stat.st_size if is_file else 0,
                            "last_modified": stat.st_mtime,
                            "permissions": oct(stat.st_mode)[-3:],
                            "depth": depth
                        }

                        items.append(item_data)

                        # Recurse into subdirectories if requested
                        if recursive and is_dir and not is_symlink:
                            # Verify subdirectory is still within allowed paths
                            try:
                                security.validate_read_path(str(item))
                                list_dir(item, depth + 1)
                            except HTTPException:
                                # Skip directories outside allowed paths
                                pass

                    except (OSError, PermissionError):
                        # Skip items we can't stat
                        continue

            except (OSError, PermissionError) as e:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {str(e)}"
                )

        # Start listing
        list_dir(dir_path)

        # Sort items by name
        items.sort(key=lambda x: (not x["is_directory"], x["name"]))

        # Audit log
        await audit.log_list(
            path=str(dir_path),
            credentials=credentials,
            success=True,
            item_count=len(items)
        )

        return {
            "path": str(dir_path),
            "items": items,
            "total_count": len(items),
            "recursive": recursive,
            "max_depth": max_depth if recursive else 0
        }

    except HTTPException:
        # Re-raise HTTP exceptions (security validation failures)
        raise

    except Exception as e:
        # Log failure
        await audit.log_list(
            path=path,
            credentials=credentials,
            success=False,
            error=str(e)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list directory: {str(e)}"
        )
