"""MCP tool for writing files with security and auditing."""

import base64
from pathlib import Path
from typing import Dict, Any, Optional
import aiofiles
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from ..security import security
from ..audit import audit
from ..hashing import hasher
from ..storage.index import index


async def write_file_tool(
    path: str,
    content: str,
    credentials: HTTPAuthorizationCredentials,
    is_binary: bool = False,
    create_parents: bool = False,
    overwrite: bool = True
) -> Dict[str, Any]:
    """
    Write a file with security validation and auditing.

    Args:
        path: Path to the file to write
        content: File content (text or base64-encoded binary)
        credentials: Authentication credentials
        is_binary: If True, content is base64-encoded binary
        create_parents: If True, create parent directories if they don't exist
        overwrite: If False, fail if file already exists

    Returns:
        Dictionary containing:
            - path: Written file path
            - size: File size in bytes
            - hash: BLAKE3 hash
            - success: True if write succeeded

    Raises:
        HTTPException: If access is denied or file cannot be written
    """
    try:
        # Validate path security (check_exists if overwrite=False)
        file_path = security.validate_write_path(
            path,
            check_exists=(not overwrite)
        )

        # Create parent directories if requested
        if create_parents:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert content to bytes
        if is_binary:
            try:
                content_bytes = base64.b64decode(content)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid base64 content: {str(e)}"
                )
        else:
            content_bytes = content.encode('utf-8')

        # Validate file size
        file_size = len(content_bytes)
        security.validate_file_size(file_size)

        # Write file
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content_bytes)

        # Calculate hash
        file_hash = await hasher.hash_content(content_bytes)

        # Update index
        file_stat = file_path.stat()

        # Sample first 1KB for indexing
        sample, _ = await hasher.sample_file(file_path, sample_size=1024)

        await index.upsert_file(
            path=str(file_path),
            file_hash=file_hash,
            size=file_size,
            mime_type=None,  # Will be detected on read
            last_modified=file_stat.st_mtime,
            sample_content=sample,
            metadata={
                "is_binary": is_binary,
                "permissions": oct(file_stat.st_mode)[-3:]
            }
        )

        # Record access
        file_record = await index.get_file_by_path(str(file_path))
        if file_record:
            await index.record_access(file_record["id"], "write")

        # Audit log
        await audit.log_write(
            path=str(file_path),
            credentials=credentials,
            success=True,
            file_size=file_size,
            file_hash=file_hash
        )

        return {
            "path": str(file_path),
            "size": file_size,
            "hash": file_hash,
            "success": True
        }

    except HTTPException:
        # Re-raise HTTP exceptions (security validation failures)
        raise

    except Exception as e:
        # Log failure
        await audit.log_write(
            path=path,
            credentials=credentials,
            success=False,
            error=str(e)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write file: {str(e)}"
        )
