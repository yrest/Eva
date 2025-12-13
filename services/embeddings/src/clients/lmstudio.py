"""LM Studio client for embedding generation."""

import httpx
from typing import List, Dict, Any
from ..config import settings


class LMStudioClient:
    """Client for LM Studio embedding API (OpenAI-compatible)."""

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or settings.lmstudio_url
        self.model = model or settings.default_lmstudio_model
        self.timeout = settings.embedding_timeout

    async def embed(self, text: str) -> Dict[str, Any]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Dict with 'embedding' and metadata
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/embeddings",
                json={
                    "model": self.model,
                    "input": text
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            embedding = data["data"][0]["embedding"]

            return {
                "embedding": embedding,
                "model": self.model,
                "backend": "lmstudio",
                "dimensions": len(embedding),
                "usage": data.get("usage", {})
            }

    async def embed_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding results
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/embeddings",
                json={
                    "model": self.model,
                    "input": texts
                },
                timeout=self.timeout * 2  # Longer timeout for batches
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data["data"]:
                results.append({
                    "embedding": item["embedding"],
                    "model": self.model,
                    "backend": "lmstudio",
                    "dimensions": len(item["embedding"]),
                    "index": item["index"]
                })

            return results

    async def health_check(self) -> bool:
        """Check if LM Studio is available."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v1/models",
                    timeout=5
                )
                return response.status_code == 200
        except Exception:
            return False
