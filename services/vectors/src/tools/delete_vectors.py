"""Delete vectors tool."""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from ..client import vector_client
from ..audit import audit


async def delete_vectors_tool(
    collection: str,
    credentials: HTTPAuthorizationCredentials,
    point_ids: Optional[List[str]] = None,
    filter_conditions: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Delete vectors by IDs or filter.

    Args:
        collection: Collection name
        credentials: Authentication credentials
        point_ids: List of point IDs to delete
        filter_conditions: Filter conditions for deletion

    Returns:
        Success response
    """
    try:
        # Validate collection exists
        if not vector_client.collection_exists(collection):
            raise HTTPException(
                status_code=404,
                detail=f"Collection '{collection}' does not exist"
            )

        # Validate input
        if not point_ids and not filter_conditions:
            raise HTTPException(
                status_code=400,
                detail="Must provide either point_ids or filter_conditions"
            )

        # Delete vectors
        vector_client.delete_vectors(
            collection=collection,
            point_ids=point_ids,
            filter_conditions=filter_conditions
        )

        deleted_count = len(point_ids) if point_ids else None

        # Log success
        await audit.log_delete(
            collection=collection,
            credentials=credentials,
            success=True,
            deleted_count=deleted_count
        )

        return {
            "success": True,
            "collection": collection,
            "deleted_count": deleted_count or "unknown (filter-based)"
        }

    except HTTPException:
        raise
    except Exception as e:
        # Log failure
        await audit.log_delete(
            collection=collection,
            credentials=credentials,
            success=False,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Delete failed: {str(e)}"
        )
