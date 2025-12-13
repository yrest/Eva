"""MCP tool for searching files with security and auditing."""

from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from ..security import security
from ..audit import audit
from ..storage.index import index


async def search_files_tool(
    query: str,
    credentials: HTTPAuthorizationCredentials,
    limit: int = 100,
    search_content: bool = False
) -> Dict[str, Any]:
    """
    Search for files by path or content.

    Args:
        query: Search query (path pattern or content search)
        credentials: Authentication credentials
        limit: Maximum number of results (default 100)
        search_content: If True, search file content (requires indexing)

    Returns:
        Dictionary containing:
            - query: Original search query
            - results: List of matching files
            - total_count: Number of results
            - truncated: Whether results were limited

    Raises:
        HTTPException: If search fails
    """
    try:
        # Search in index
        results = await index.search_files(query, limit=limit)

        # Filter results to only include accessible paths
        accessible_results = []
        for result in results:
            try:
                # Verify path is still accessible
                security.validate_read_path(result["path"])
                accessible_results.append(result)
            except HTTPException:
                # Skip inaccessible files
                continue

        # Audit log
        await audit.log_search(
            query=query,
            credentials=credentials,
            success=True,
            result_count=len(accessible_results)
        )

        return {
            "query": query,
            "results": accessible_results,
            "total_count": len(accessible_results),
            "truncated": len(accessible_results) >= limit,
            "limit": limit
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        # Log failure
        await audit.log_search(
            query=query,
            credentials=credentials,
            success=False,
            error=str(e)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
