"""File hashing and integrity checking using BLAKE3."""

import blake3
from pathlib import Path
from typing import Optional, Tuple
import aiofiles


class FileHasher:
    """Handles file hashing for integrity and deduplication."""

    CHUNK_SIZE = 65536  # 64KB chunks for efficient hashing

    async def hash_file(self, file_path: Path) -> str:
        """
        Calculate BLAKE3 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            Hexadecimal hash string
        """
        hasher = blake3.blake3()

        async with aiofiles.open(file_path, 'rb') as f:
            while True:
                chunk = await f.read(self.CHUNK_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)

        return hasher.hexdigest()

    async def hash_content(self, content: bytes) -> str:
        """
        Calculate BLAKE3 hash of content.

        Args:
            content: Byte content to hash

        Returns:
            Hexadecimal hash string
        """
        hasher = blake3.blake3()
        hasher.update(content)
        return hasher.hexdigest()

    async def verify_file_integrity(
        self,
        file_path: Path,
        expected_hash: str
    ) -> bool:
        """
        Verify file integrity against expected hash.

        Args:
            file_path: Path to the file
            expected_hash: Expected hash value

        Returns:
            True if hash matches, False otherwise
        """
        actual_hash = await self.hash_file(file_path)
        return actual_hash == expected_hash

    async def sample_file(
        self,
        file_path: Path,
        sample_size: int = 1024
    ) -> Tuple[bytes, str]:
        """
        Extract a sample from the beginning of a file and its hash.

        Args:
            file_path: Path to the file
            sample_size: Number of bytes to sample (default 1KB)

        Returns:
            Tuple of (sample content, full file hash)
        """
        # Read sample
        async with aiofiles.open(file_path, 'rb') as f:
            sample = await f.read(sample_size)

        # Get full file hash
        file_hash = await self.hash_file(file_path)

        return sample, file_hash


# Global hasher instance
hasher = FileHasher()
