"""Collection management tools."""

from typing import Dict, Any
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from ..client import vector_client
from ..audit import audit
from ..config import settings


async def create_collection_tool(
    name: str,
    vector_size: int,
    credentials: HTTPAuthorizationCredentials,
    distance: str = None
) -> Dict[str, Any]:
    """Create a new collection."""
    try:
        # Check if collection already exists
        if vector_client.collection_exists(name):
            raise HTTPException(
                status_code=400,
                detail=f"Collection '{name}' already exists"
            )

        # Create collection
        info = vector_client.create_collection(
            name=name,
            vector_size=vector_size,
            distance=distance
        )

        # Log success
        await audit.log_collection_op(
            operation="create_collection",
            collection=name,
            credentials=credentials,
            success=True,
            details=info
        )

        return {
            "success": True,
            **info
        }

    except HTTPException:
        raise
    except Exception as e:
        # Log failure
        await audit.log_collection_op(
            operation="create_collection",
            collection=name,
            credentials=credentials,
            success=False,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Collection creation failed: {str(e)}"
        )


async def delete_collection_tool(
    name: str,
    credentials: HTTPAuthorizationCredentials
) -> Dict[str, Any]:
    """Delete a collection."""
    try:
        # Check if collection exists
        if not vector_client.collection_exists(name):
            raise HTTPException(
                status_code=404,
                detail=f"Collection '{name}' does not exist"
            )

        # Delete collection
        vector_client.delete_collection(name)

        # Log success
        await audit.log_collection_op(
            operation="delete_collection",
            collection=name,
            credentials=credentials,
            success=True
        )

        return {
            "success": True,
            "collection": name,
            "deleted": True
        }

    except HTTPException:
        raise
    except Exception as e:
        # Log failure
        await audit.log_collection_op(
            operation="delete_collection",
            collection=name,
            credentials=credentials,
            success=False,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Collection deletion failed: {str(e)}"
        )


async def get_collection_info_tool(
    name: str,
    credentials: HTTPAuthorizationCredentials
) -> Dict[str, Any]:
    """Get collection information."""
    try:
        # Check if collection exists
        if not vector_client.collection_exists(name):
            raise HTTPException(
                status_code=404,
                detail=f"Collection '{name}' does not exist"
            )

        # Get collection info
        info = vector_client.get_collection_info(name)

        return {
            "success": True,
            **info
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get collection info: {str(e)}"
        )


async def list_collections_tool(
    credentials: HTTPAuthorizationCredentials
) -> Dict[str, Any]:
    """List all collections."""
    try:
        collections = vector_client.list_collections()

        return {
            "success": True,
            "collections": collections,
            "count": len(collections)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list collections: {str(e)}"
        )
