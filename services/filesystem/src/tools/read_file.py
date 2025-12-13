"""MCP tool for reading files with security and auditing."""

import os
import magic
from pathlib import Path
from typing import Dict, Any
import aiofiles
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from ..security import security
from ..audit import audit
from ..hashing import hasher
from ..storage.index import index


async def read_file_tool(
    path: str,
    credentials: HTTPAuthorizationCredentials,
    include_hash: bool = True,
    update_index: bool = True
) -> Dict[str, Any]:
    """
    Read a file with security validation and auditing.

    Args:
        path: Path to the file to read
        credentials: Authentication credentials
        include_hash: Whether to calculate and return file hash
        update_index: Whether to update metadata index

    Returns:
        Dictionary containing:
            - content: File content (as string if text, base64 if binary)
            - size: File size in bytes
            - hash: BLAKE3 hash (if include_hash=True)
            - mime_type: Detected MIME type
            - metadata: Additional file metadata

    Raises:
        HTTPException: If access is denied or file cannot be read
    """
    try:
        # Validate path security
        file_path = security.validate_read_path(path)

        # Get file stats
        file_stat = file_path.stat()
        file_size = file_stat.st_size

        # Validate file size
        security.validate_file_size(file_size)

        # Detect MIME type
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(str(file_path))

        # Read file content
        async with aiofiles.open(file_path, 'rb') as f:
            content_bytes = await f.read()

        # Calculate hash if requested
        file_hash = None
        if include_hash:
            file_hash = await hasher.hash_content(content_bytes)

        # Determine if content is text or binary
        is_text = mime_type.startswith('text/') or mime_type in [
            'application/json',
            'application/xml',
            'application/javascript'
        ]

        # Convert content appropriately
        if is_text:
            try:
                content = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                # Fallback to latin-1 if utf-8 fails
                content = content_bytes.decode('latin-1')
        else:
            # Base64 encode binary content
            import base64
            content = base64.b64encode(content_bytes).decode('ascii')

        # Update index if requested
        if update_index and file_hash:
            # Sample first 1KB for indexing
            sample, _ = await hasher.sample_file(file_path, sample_size=1024)

            await index.upsert_file(
                path=str(file_path),
                file_hash=file_hash,
                size=file_size,
                mime_type=mime_type,
                last_modified=file_stat.st_mtime,
                sample_content=sample,
                metadata={
                    "is_text": is_text,
                    "permissions": oct(file_stat.st_mode)[-3:]
                }
            )

            # Record access
            file_record = await index.get_file_by_path(str(file_path))
            if file_record:
                await index.record_access(file_record["id"], "read")

        # Build response
        response = {
            "path": str(file_path),
            "content": content,
            "size": file_size,
            "mime_type": mime_type,
            "is_text": is_text,
            "last_modified": file_stat.st_mtime
        }

        if file_hash:
            response["hash"] = file_hash

        # Audit log
        await audit.log_read(
            path=str(file_path),
            credentials=credentials,
            success=True,
            file_size=file_size,
            file_hash=file_hash
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions (security validation failures)
        raise

    except Exception as e:
        # Log failure
        await audit.log_read(
            path=path,
            credentials=credentials,
            success=False,
            error=str(e)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read file: {str(e)}"
        )
