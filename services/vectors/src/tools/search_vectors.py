"""Search vectors tool."""

import time
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from ..client import vector_client
from ..audit import audit


async def search_vectors_tool(
    collection: str,
    query_vector: List[float],
    credentials: HTTPAuthorizationCredentials,
    limit: int = 10,
    score_threshold: Optional[float] = None,
    filter_conditions: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Search for similar vectors.

    Args:
        collection: Collection name
        query_vector: Query vector
        credentials: Authentication credentials
        limit: Maximum results
        score_threshold: Minimum similarity score
        filter_conditions: Optional metadata filters

    Returns:
        Search results with scores and payloads
    """
    start_time = time.time()

    try:
        # Validate collection exists
        if not vector_client.collection_exists(collection):
            raise HTTPException(
                status_code=404,
                detail=f"Collection '{collection}' does not exist"
            )

        # Perform search
        results = vector_client.search_vectors(
            collection=collection,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            filter_conditions=filter_conditions
        )

        processing_time = (time.time() - start_time) * 1000

        # Log success
        await audit.log_search(
            collection=collection,
            credentials=credentials,
            success=True,
            result_count=len(results),
            limit=limit,
            processing_time_ms=processing_time
        )

        return {
            "success": True,
            "collection": collection,
            "results": results,
            "count": len(results),
            "processing_time_ms": round(processing_time, 2)
        }

    except HTTPException:
        raise
    except Exception as e:
        # Log failure
        await audit.log_search(
            collection=collection,
            credentials=credentials,
            success=False,
            limit=limit,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )
