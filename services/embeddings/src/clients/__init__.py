"""Embedding clients."""

from .ollama import OllamaClient
from .lmstudio import LMStudioClient

__all__ = ["OllamaClient", "LMStudioClient"]
