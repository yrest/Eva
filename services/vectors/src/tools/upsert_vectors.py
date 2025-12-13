"""Upsert vectors tool."""

import time
from typing import List, Dict, Any
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from ..client import vector_client
from ..audit import audit


async def upsert_vectors_tool(
    collection: str,
    points: List[Dict[str, Any]],
    credentials: HTTPAuthorizationCredentials
) -> Dict[str, Any]:
    """
    Insert or update vectors in a collection.

    Args:
        collection: Collection name
        points: List of points with id, vector, and optional payload
        credentials: Authentication credentials

    Returns:
        Success response with count
    """
    start_time = time.time()

    try:
        # Validate collection exists
        if not vector_client.collection_exists(collection):
            raise HTTPException(
                status_code=404,
                detail=f"Collection '{collection}' does not exist"
            )

        # Validate points structure
        if not points:
            raise HTTPException(
                status_code=400,
                detail="Points list cannot be empty"
            )

        for point in points:
            if "id" not in point or "vector" not in point:
                raise HTTPException(
                    status_code=400,
                    detail="Each point must have 'id' and 'vector' fields"
                )

        # Get dimensions from first vector
        dimensions = len(points[0]["vector"])

        # Upsert vectors
        count = vector_client.upsert_vectors(collection, points)

        processing_time = (time.time() - start_time) * 1000

        # Log success
        await audit.log_upsert(
            collection=collection,
            credentials=credentials,
            success=True,
            vector_count=count,
            dimensions=dimensions,
            processing_time_ms=processing_time
        )

        return {
            "success": True,
            "collection": collection,
            "upserted_count": count,
            "processing_time_ms": round(processing_time, 2)
        }

    except HTTPException:
        raise
    except Exception as e:
        # Log failure
        await audit.log_upsert(
            collection=collection,
            credentials=credentials,
            success=False,
            vector_count=len(points),
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Upsert failed: {str(e)}"
        )
