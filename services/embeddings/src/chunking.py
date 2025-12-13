"""Text chunking utilities for embedding generation."""

from typing import List
from .config import settings


def chunk_text(
    text: str,
    chunk_size: int = None,
    overlap: int = None,
    preserve_words: bool = True
) -> List[str]:
    """
    Split text into chunks for embedding.

    Args:
        text: Text to chunk
        chunk_size: Maximum characters per chunk
        overlap: Number of overlapping characters between chunks
        preserve_words: Try to break on word boundaries

    Returns:
        List of text chunks
    """
    chunk_size = chunk_size or settings.default_chunk_size
    overlap = overlap or settings.chunk_overlap

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        # Calculate end position
        end = start + chunk_size

        # If this is not the last chunk and we want to preserve words
        if end < len(text) and preserve_words:
            # Find the last space before the end position
            last_space = text.rfind(' ', start, end)
            if last_space > start:
                end = last_space

        # Extract chunk
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start position (with overlap)
        start = end - overlap if overlap > 0 else end

        # Prevent infinite loop
        if start <= 0 or end >= len(text):
            break

    return chunks


def estimate_tokens(text: str) -> int:
    """
    Rough estimation of token count.

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    # Rough approximation: ~4 characters per token for English
    return len(text) // 4
