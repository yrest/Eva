"""Vector search tool (READ_ONLY)."""

from typing import Any, Dict, List

import httpx

from ..config import settings
from . import SafetyLevel, tool_registry


async def search_vectors_handler(
    query: str,
    collection: str,
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Search vector database.

    Args:
        query: Search query
        collection: Collection name
        limit: Maximum results

    Returns:
        Search results
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.vector_service_url}/mcp/tools/search",
                headers={"Authorization": f"Bearer {settings.vector_query_token}"},
                json={
                    "collection": collection,
                    "query_text": query,
                    "limit": limit,
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": f"Vector search failed: {response.status_code}",
                    "results": [],
                }

    except Exception as e:
        return {
            "error": f"Vector search error: {str(e)}",
            "results": [],
        }


# Register tool
tool_registry.register(
    name="search_vectors",
    description="Search the vector database for relevant documents",
    safety_level=SafetyLevel.READ_ONLY,
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query text",
            },
            "collection": {
                "type": "string",
                "description": "Collection to search (e.g., 'emails', 'tickets')",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results",
                "default": 5,
            },
        },
        "required": ["query", "collection"],
    },
    handler=search_vectors_handler,
)
