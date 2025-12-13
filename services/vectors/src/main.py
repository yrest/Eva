"""Main FastAPI MCP server for vector operations."""

from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from .config import settings
from .auth import require_query_permission, require_update_permission
from .client import vector_client
from .tools import (
    upsert_vectors_tool,
    search_vectors_tool,
    delete_vectors_tool,
    create_collection_tool,
    delete_collection_tool,
    get_collection_info_tool,
    list_collections_tool
)


# Create FastAPI app
app = FastAPI(
    title="Eva Vector Service",
    description="Secure vector storage and search via Qdrant with dual-token authentication",
    version="0.1.0"
)


# Request/Response models
class UpsertVectorsRequest(BaseModel):
    collection: str = Field(..., description="Collection name")
    points: List[Dict[str, Any]] = Field(
        ..., description="Points with id, vector, and optional payload"
    )


class SearchVectorsRequest(BaseModel):
    collection: str = Field(..., description="Collection name")
    query_vector: List[float] = Field(..., description="Query vector")
    limit: int = Field(10, description="Maximum results", ge=1, le=100)
    score_threshold: Optional[float] = Field(None, description="Minimum similarity score")
    filter_conditions: Optional[Dict[str, Any]] = Field(
        None, description="Metadata filter conditions"
    )


class DeleteVectorsRequest(BaseModel):
    collection: str = Field(..., description="Collection name")
    point_ids: Optional[List[str]] = Field(None, description="Point IDs to delete")
    filter_conditions: Optional[Dict[str, Any]] = Field(
        None, description="Filter conditions for deletion"
    )


class CreateCollectionRequest(BaseModel):
    name: str = Field(..., description="Collection name")
    vector_size: int = Field(..., description="Vector dimensions", ge=1)
    distance: Optional[str] = Field(None, description="Distance metric (Cosine, Euclid, Dot)")


class GetCollectionRequest(BaseModel):
    name: str = Field(..., description="Collection name")


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint with Qdrant status."""
    qdrant_available = await vector_client.health_check()

    return {
        "status": "healthy",
        "service": "vectors",
        "version": "0.1.0",
        "qdrant": {
            "available": qdrant_available,
            "url": settings.qdrant_url
        }
    }


# MCP Tool: Upsert Vectors
@app.post("/mcp/tools/upsert_vectors")
async def mcp_upsert_vectors(
    request: UpsertVectorsRequest,
    credentials: HTTPAuthorizationCredentials = Depends(require_update_permission)
):
    """
    Insert or update vectors in a collection.
    Requires update token.
    """
    return await upsert_vectors_tool(
        collection=request.collection,
        points=request.points,
        credentials=credentials
    )


# MCP Tool: Search Vectors
@app.post("/mcp/tools/search_vectors")
async def mcp_search_vectors(
    request: SearchVectorsRequest,
    credentials: HTTPAuthorizationCredentials = Depends(require_query_permission)
):
    """
    Search for similar vectors.
    Requires query token.
    """
    return await search_vectors_tool(
        collection=request.collection,
        query_vector=request.query_vector,
        credentials=credentials,
        limit=request.limit,
        score_threshold=request.score_threshold,
        filter_conditions=request.filter_conditions
    )


# MCP Tool: Delete Vectors
@app.post("/mcp/tools/delete_vectors")
async def mcp_delete_vectors(
    request: DeleteVectorsRequest,
    credentials: HTTPAuthorizationCredentials = Depends(require_update_permission)
):
    """
    Delete vectors by IDs or filter.
    Requires update token.
    """
    return await delete_vectors_tool(
        collection=request.collection,
        credentials=credentials,
        point_ids=request.point_ids,
        filter_conditions=request.filter_conditions
    )


# MCP Tool: Create Collection
@app.post("/mcp/tools/create_collection")
async def mcp_create_collection(
    request: CreateCollectionRequest,
    credentials: HTTPAuthorizationCredentials = Depends(require_update_permission)
):
    """
    Create a new collection.
    Requires update token.
    """
    return await create_collection_tool(
        name=request.name,
        vector_size=request.vector_size,
        credentials=credentials,
        distance=request.distance
    )


# MCP Tool: Delete Collection
@app.post("/mcp/tools/delete_collection")
async def mcp_delete_collection(
    request: GetCollectionRequest,
    credentials: HTTPAuthorizationCredentials = Depends(require_update_permission)
):
    """
    Delete a collection.
    Requires update token.
    """
    return await delete_collection_tool(
        name=request.name,
        credentials=credentials
    )


# MCP Tool: Get Collection Info
@app.post("/mcp/tools/get_collection_info")
async def mcp_get_collection_info(
    request: GetCollectionRequest,
    credentials: HTTPAuthorizationCredentials = Depends(require_query_permission)
):
    """
    Get collection information.
    Requires query token.
    """
    return await get_collection_info_tool(
        name=request.name,
        credentials=credentials
    )


# MCP Tool: List Collections
@app.get("/mcp/tools/list_collections")
async def mcp_list_collections(
    credentials: HTTPAuthorizationCredentials = Depends(require_query_permission)
):
    """
    List all collections.
    Requires query token.
    """
    return await list_collections_tool(credentials=credentials)


# MCP Server Info (for discovery)
@app.get("/mcp/info")
async def mcp_info():
    """Return MCP server information and available tools."""
    return {
        "name": "eva-vectors",
        "version": "0.1.0",
        "description": "Secure vector storage and search via Qdrant",
        "tools": [
            {
                "name": "upsert_vectors",
                "description": "Insert or update vectors",
                "endpoint": "/mcp/tools/upsert_vectors",
                "permission": "update"
            },
            {
                "name": "search_vectors",
                "description": "Search for similar vectors",
                "endpoint": "/mcp/tools/search_vectors",
                "permission": "query"
            },
            {
                "name": "delete_vectors",
                "description": "Delete vectors by ID or filter",
                "endpoint": "/mcp/tools/delete_vectors",
                "permission": "update"
            },
            {
                "name": "create_collection",
                "description": "Create a new collection",
                "endpoint": "/mcp/tools/create_collection",
                "permission": "update"
            },
            {
                "name": "delete_collection",
                "description": "Delete a collection",
                "endpoint": "/mcp/tools/delete_collection",
                "permission": "update"
            },
            {
                "name": "get_collection_info",
                "description": "Get collection information",
                "endpoint": "/mcp/tools/get_collection_info",
                "permission": "query"
            },
            {
                "name": "list_collections",
                "description": "List all collections",
                "endpoint": "/mcp/tools/list_collections",
                "permission": "query"
            }
        ],
        "security": {
            "type": "bearer",
            "tokens": ["query", "update"],
            "description": "Separate tokens for query and update operations"
        },
        "features": {
            "local_only": True,
            "qdrant_backend": True,
            "metadata_filtering": True,
            "audit_logging": True,
            "privacy_guaranteed": True
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True,
        log_level="info"
    )
