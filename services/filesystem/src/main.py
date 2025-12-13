"""Main FastAPI MCP server for secure filesystem operations."""

from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from .config import settings
from .auth import require_read_permission, require_write_permission
from .storage.index import index
from .tools import (
    read_file_tool,
    write_file_tool,
    list_directory_tool,
    search_files_tool
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await index.initialize()
    yield


# Create FastAPI app
app = FastAPI(
    title="Eva Filesystem Service",
    description="Secure file system access via MCP with dual-token authentication",
    version="0.1.0",
    lifespan=lifespan
)


# Request/Response models
class ReadFileRequest(BaseModel):
    path: str = Field(..., description="Path to the file to read")
    include_hash: bool = Field(True, description="Calculate and return file hash")
    update_index: bool = Field(True, description="Update metadata index")


class WriteFileRequest(BaseModel):
    path: str = Field(..., description="Path to the file to write")
    content: str = Field(..., description="File content (text or base64 binary)")
    is_binary: bool = Field(False, description="If true, content is base64-encoded")
    create_parents: bool = Field(False, description="Create parent directories if needed")
    overwrite: bool = Field(True, description="Overwrite existing file")


class ListDirectoryRequest(BaseModel):
    path: str = Field(..., description="Path to the directory to list")
    recursive: bool = Field(False, description="List subdirectories recursively")
    include_hidden: bool = Field(False, description="Include hidden files")
    max_depth: int = Field(3, description="Maximum recursion depth", ge=1, le=10)


class SearchFilesRequest(BaseModel):
    query: str = Field(..., description="Search query")
    limit: int = Field(100, description="Maximum results", ge=1, le=1000)
    search_content: bool = Field(False, description="Search file content (not yet implemented)")


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "filesystem",
        "version": "0.1.0",
        "allowed_paths": settings.allowed_paths_list
    }


# MCP Tool: Read File
@app.post("/mcp/tools/read_file")
async def mcp_read_file(
    request: ReadFileRequest,
    credentials: HTTPAuthorizationCredentials = Depends(require_read_permission)
):
    """
    Read a file with security validation and auditing.
    Requires read token.
    """
    return await read_file_tool(
        path=request.path,
        credentials=credentials,
        include_hash=request.include_hash,
        update_index=request.update_index
    )


# MCP Tool: Write File
@app.post("/mcp/tools/write_file")
async def mcp_write_file(
    request: WriteFileRequest,
    credentials: HTTPAuthorizationCredentials = Depends(require_write_permission)
):
    """
    Write a file with security validation and auditing.
    Requires write token.
    """
    return await write_file_tool(
        path=request.path,
        content=request.content,
        credentials=credentials,
        is_binary=request.is_binary,
        create_parents=request.create_parents,
        overwrite=request.overwrite
    )


# MCP Tool: List Directory
@app.post("/mcp/tools/list_directory")
async def mcp_list_directory(
    request: ListDirectoryRequest,
    credentials: HTTPAuthorizationCredentials = Depends(require_read_permission)
):
    """
    List directory contents with security validation and auditing.
    Requires read token.
    """
    return await list_directory_tool(
        path=request.path,
        credentials=credentials,
        recursive=request.recursive,
        include_hidden=request.include_hidden,
        max_depth=request.max_depth
    )


# MCP Tool: Search Files
@app.post("/mcp/tools/search_files")
async def mcp_search_files(
    request: SearchFilesRequest,
    credentials: HTTPAuthorizationCredentials = Depends(require_read_permission)
):
    """
    Search for files by path or content.
    Requires read token.
    """
    return await search_files_tool(
        query=request.query,
        credentials=credentials,
        limit=request.limit,
        search_content=request.search_content
    )


# MCP Server Info (for discovery)
@app.get("/mcp/info")
async def mcp_info():
    """Return MCP server information and available tools."""
    return {
        "name": "eva-filesystem",
        "version": "0.1.0",
        "description": "Secure filesystem access with dual-token authentication",
        "tools": [
            {
                "name": "read_file",
                "description": "Read a file with security validation",
                "endpoint": "/mcp/tools/read_file",
                "permission": "read"
            },
            {
                "name": "write_file",
                "description": "Write a file with security validation",
                "endpoint": "/mcp/tools/write_file",
                "permission": "write"
            },
            {
                "name": "list_directory",
                "description": "List directory contents recursively",
                "endpoint": "/mcp/tools/list_directory",
                "permission": "read"
            },
            {
                "name": "search_files",
                "description": "Search files by path or content",
                "endpoint": "/mcp/tools/search_files",
                "permission": "read"
            }
        ],
        "security": {
            "type": "bearer",
            "tokens": ["read", "write"],
            "description": "Separate tokens for read and write operations"
        },
        "features": {
            "path_sandboxing": True,
            "symlink_protection": True,
            "audit_logging": True,
            "file_hashing": True,
            "metadata_indexing": True,
            "deduplication": True,
            "qdrant_ready": True
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
