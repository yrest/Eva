"""SQLite-based metadata indexing and caching."""

import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..config import settings


class MetadataIndex:
    """SQLite index for file metadata and change tracking."""

    def __init__(self):
        self.db_path = settings.sqlite_db_path

    async def initialize(self) -> None:
        """Initialize database schema."""
        # Ensure data directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    hash TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    mime_type TEXT,
                    last_modified REAL NOT NULL,
                    indexed_at TEXT NOT NULL,
                    sample_content BLOB,
                    metadata JSON
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_files_hash ON files(hash)
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS access_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    operation TEXT NOT NULL,
                    accessed_at TEXT NOT NULL,
                    FOREIGN KEY (file_id) REFERENCES files(id)
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_access_file ON access_stats(file_id)
            """)

            await db.commit()

    async def upsert_file(
        self,
        path: str,
        file_hash: str,
        size: int,
        mime_type: Optional[str],
        last_modified: float,
        sample_content: Optional[bytes] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Insert or update file metadata.

        Args:
            path: File path
            file_hash: BLAKE3 hash
            size: File size in bytes
            mime_type: MIME type (if detected)
            last_modified: Last modified timestamp
            sample_content: Sample of file content
            metadata: Additional metadata as JSON

        Returns:
            File ID
        """
        import json

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO files (
                    path, hash, size, mime_type, last_modified,
                    indexed_at, sample_content, metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    hash = excluded.hash,
                    size = excluded.size,
                    mime_type = excluded.mime_type,
                    last_modified = excluded.last_modified,
                    indexed_at = excluded.indexed_at,
                    sample_content = excluded.sample_content,
                    metadata = excluded.metadata
            """, (
                path,
                file_hash,
                size,
                mime_type,
                last_modified,
                datetime.utcnow().isoformat(),
                sample_content,
                json.dumps(metadata) if metadata else None
            ))

            await db.commit()

            # Get file ID
            async with db.execute(
                "SELECT id FROM files WHERE path = ?",
                (path,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def get_file_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve file metadata by path.

        Args:
            path: File path

        Returns:
            File metadata dict or None if not found
        """
        import json

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM files WHERE path = ?",
                (path,)
            ) as cursor:
                row = await cursor.fetchone()

                if not row:
                    return None

                return {
                    "id": row[0],
                    "path": row[1],
                    "hash": row[2],
                    "size": row[3],
                    "mime_type": row[4],
                    "last_modified": row[5],
                    "indexed_at": row[6],
                    "sample_content": row[7],
                    "metadata": json.loads(row[8]) if row[8] else None
                }

    async def get_file_by_hash(self, file_hash: str) -> List[Dict[str, Any]]:
        """
        Find all files with the same hash (duplicates).

        Args:
            file_hash: BLAKE3 hash

        Returns:
            List of file metadata dicts
        """
        import json

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM files WHERE hash = ?",
                (file_hash,)
            ) as cursor:
                rows = await cursor.fetchall()

                return [
                    {
                        "id": row[0],
                        "path": row[1],
                        "hash": row[2],
                        "size": row[3],
                        "mime_type": row[4],
                        "last_modified": row[5],
                        "indexed_at": row[6],
                        "sample_content": row[7],
                        "metadata": json.loads(row[8]) if row[8] else None
                    }
                    for row in rows
                ]

    async def search_files(
        self,
        query: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search files by path or metadata.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching files
        """
        import json

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM files WHERE path LIKE ? LIMIT ?",
                (f"%{query}%", limit)
            ) as cursor:
                rows = await cursor.fetchall()

                return [
                    {
                        "id": row[0],
                        "path": row[1],
                        "hash": row[2],
                        "size": row[3],
                        "mime_type": row[4],
                        "last_modified": row[5],
                        "indexed_at": row[6],
                        "metadata": json.loads(row[8]) if row[8] else None
                    }
                    for row in rows
                ]

    async def record_access(self, file_id: int, operation: str) -> None:
        """
        Record file access for analytics.

        Args:
            file_id: File ID
            operation: Operation type (read, write, etc.)
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO access_stats (file_id, operation, accessed_at)
                VALUES (?, ?, ?)
            """, (file_id, operation, datetime.utcnow().isoformat()))

            await db.commit()


# Global index instance
index = MetadataIndex()
