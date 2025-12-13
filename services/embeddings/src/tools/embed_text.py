"""Embedding tool with chunking support."""

import time
from typing import List, Dict, Any, Literal, Optional
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from ..config import settings
from ..audit import audit
from ..clients import OllamaClient, LMStudioClient
from ..chunking import chunk_text, estimate_tokens


async def embed_text_tool(
    text: str,
    credentials: HTTPAuthorizationCredentials,
    backend: Literal["ollama", "lmstudio"] = None,
    model: str = None,
    chunk_enabled: bool = True,
    chunk_size: int = None,
    return_chunks: bool = False
) -> Dict[str, Any]:
    """
    Generate embeddings for text with automatic chunking.

    Args:
        text: Text to embed
        credentials: Authentication credentials
        backend: Embedding backend to use
        model: Model name (backend-specific)
        chunk_enabled: Whether to automatically chunk large texts
        chunk_size: Custom chunk size
        return_chunks: Whether to return individual chunk embeddings

    Returns:
        Dict with embeddings and metadata
    """
    start_time = time.time()

    # Validate text length
    if len(text) > settings.max_text_length:
        raise HTTPException(
            status_code=400,
            detail=f"Text too long. Maximum {settings.max_text_length} characters."
        )

    # Select backend
    backend = backend or settings.default_backend

    try:
        # Initialize client
        if backend == "ollama":
            client = OllamaClient(model=model)
        elif backend == "lmstudio":
            client = LMStudioClient(model=model)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown backend: {backend}")

        # Check if chunking is needed
        chunk_size = chunk_size or settings.default_chunk_size
        needs_chunking = chunk_enabled and len(text) > chunk_size

        if needs_chunking:
            # Chunk the text
            chunks = chunk_text(text, chunk_size=chunk_size)

            # Embed each chunk
            chunk_embeddings = await client.embed_batch(chunks)

            # Calculate metrics
            processing_time = (time.time() - start_time) * 1000
            total_tokens = sum(estimate_tokens(chunk) for chunk in chunks)
            vector_dimensions = chunk_embeddings[0]["dimensions"]

            # Log operation
            await audit.log_embed(
                credentials=credentials,
                success=True,
                backend=backend,
                model=chunk_embeddings[0]["model"],
                text_count=1,
                total_tokens=total_tokens,
                vector_dimensions=vector_dimensions,
                processing_time_ms=processing_time,
                chunked=True,
                chunk_count=len(chunks)
            )

            result = {
                "success": True,
                "chunked": True,
                "chunk_count": len(chunks),
                "backend": backend,
                "model": chunk_embeddings[0]["model"],
                "dimensions": vector_dimensions,
                "processing_time_ms": round(processing_time, 2)
            }

            if return_chunks:
                result["chunks"] = [
                    {
                        "text": chunks[i],
                        "embedding": chunk_embeddings[i]["embedding"],
                        "index": i
                    }
                    for i in range(len(chunks))
                ]
            else:
                # Return just the embeddings array
                result["embeddings"] = [ce["embedding"] for ce in chunk_embeddings]

            return result

        else:
            # Single embedding (no chunking needed)
            embedding_result = await client.embed(text)

            processing_time = (time.time() - start_time) * 1000
            total_tokens = estimate_tokens(text)

            # Log operation
            await audit.log_embed(
                credentials=credentials,
                success=True,
                backend=backend,
                model=embedding_result["model"],
                text_count=1,
                total_tokens=total_tokens,
                vector_dimensions=embedding_result["dimensions"],
                processing_time_ms=processing_time,
                chunked=False
            )

            return {
                "success": True,
                "chunked": False,
                "embedding": embedding_result["embedding"],
                "backend": backend,
                "model": embedding_result["model"],
                "dimensions": embedding_result["dimensions"],
                "processing_time_ms": round(processing_time, 2)
            }

    except HTTPException:
        raise
    except Exception as e:
        # Log failure
        await audit.log_embed(
            credentials=credentials,
            success=False,
            backend=backend,
            model=model or "unknown",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")
