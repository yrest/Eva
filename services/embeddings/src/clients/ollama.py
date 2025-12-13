"""Ollama client for embedding generation."""

import httpx
from typing import List, Dict, Any
from ..config import settings


class OllamaClient:
    """Client for Ollama embedding API."""

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or settings.ollama_url
        self.model = model or settings.default_ollama_model
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
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            return {
                "embedding": data["embedding"],
                "model": self.model,
                "backend": "ollama",
                "dimensions": len(data["embedding"])
            }

    async def embed_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding results
        """
        results = []
        for text in texts:
            result = await self.embed(text)
            results.append(result)
        return results

    async def health_check(self) -> bool:
        """Check if Ollama is available."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5
                )
                return response.status_code == 200
        except Exception:
            return False
