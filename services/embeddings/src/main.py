"""Main FastAPI MCP server for embedding generation."""

from typing import Literal, Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from .config import settings
from .auth import require_embed_permission
from .clients import OllamaClient, LMStudioClient
from .tools import embed_text_tool


# Create FastAPI app
app = FastAPI(
    title="Eva Embedding Service",
    description="Local embedding generation via Ollama/LM Studio with chunking support",
    version="0.1.0"
)


# Request/Response models
class EmbedTextRequest(BaseModel):
    text: str = Field(..., description="Text to embed")
    backend: Optional[Literal["ollama", "lmstudio"]] = Field(
        None, description="Backend to use (default from config)"
    )
    model: Optional[str] = Field(None, description="Model name (backend-specific)")
    chunk_enabled: bool = Field(True, description="Enable automatic chunking")
    chunk_size: Optional[int] = Field(None, description="Custom chunk size")
    return_chunks: bool = Field(
        False, description="Return individual chunk embeddings with text"
    )


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    backends: dict


# Health check
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with backend status."""
    ollama_client = OllamaClient()
    lmstudio_client = LMStudioClient()

    ollama_available = await ollama_client.health_check()
    lmstudio_available = await lmstudio_client.health_check()

    return {
        "status": "healthy",
        "service": "embeddings",
        "version": "0.1.0",
        "backends": {
            "ollama": {
                "available": ollama_available,
                "url": settings.ollama_url,
                "default_model": settings.default_ollama_model
            },
            "lmstudio": {
                "available": lmstudio_available,
                "url": settings.lmstudio_url,
                "default_model": settings.default_lmstudio_model
            }
        }
    }


# MCP Tool: Embed Text
@app.post("/mcp/tools/embed_text")
async def mcp_embed_text(
    request: EmbedTextRequest,
    credentials: HTTPAuthorizationCredentials = Depends(require_embed_permission)
):
    """
    Generate embeddings for text with automatic chunking.
    Requires embed token.
    """
    return await embed_text_tool(
        text=request.text,
        credentials=credentials,
        backend=request.backend,
        model=request.model,
        chunk_enabled=request.chunk_enabled,
        chunk_size=request.chunk_size,
        return_chunks=request.return_chunks
    )


# MCP Server Info (for discovery)
@app.get("/mcp/info")
async def mcp_info():
    """Return MCP server information and available tools."""
    return {
        "name": "eva-embeddings",
        "version": "0.1.0",
        "description": "Local embedding generation via Ollama/LM Studio",
        "tools": [
            {
                "name": "embed_text",
                "description": "Generate embeddings with automatic chunking",
                "endpoint": "/mcp/tools/embed_text",
                "permission": "embed"
            }
        ],
        "security": {
            "type": "bearer",
            "tokens": ["embed"],
            "description": "Single token for embedding operations"
        },
        "features": {
            "local_only": True,
            "ollama_support": True,
            "lmstudio_support": True,
            "automatic_chunking": True,
            "audit_logging": True,
            "privacy_guaranteed": True
        },
        "backends": {
            "default": settings.default_backend,
            "available": ["ollama", "lmstudio"]
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
