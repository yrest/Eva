# Vector Integration Guide

This guide shows how to use Eva's embedding and vector services together to index and search files.

## Architecture Overview

```
┌─────────────────────┐
│  Filesystem Service │ ──┐
│  (Read files)       │   │
└─────────────────────┘   │
                          │ 1. Read file content
                          │
                          ▼
┌─────────────────────┐
│  Embedding Service  │
│  (Generate vectors) │
└──────────┬──────────┘
           │ 2. Create embeddings
           │
           ▼
┌─────────────────────┐
│   Vector Service    │
│  (Store & search)   │
└──────────┬──────────┘
           │ 3. Store in Qdrant
           │
           ▼
┌─────────────────────┐
│  Qdrant Container   │
│  (Vector database)  │
└─────────────────────┘
```

## Quick Start

### 1. Start Services

```bash
# Start all required services
docker compose up qdrant embeddings vectors filesystem

# Or run locally for development
# Terminal 1: Qdrant
docker run -p 6333:6333 qdrant/qdrant:latest

# Terminal 2: Embeddings
cd services/embeddings && python -m src.main

# Terminal 3: Vectors
cd services/vectors && python -m src.main

# Terminal 4: Filesystem
cd services/filesystem && python -m src.main
```

### 2. Configure Environment

```bash
# Copy example environment
cp .env.example .env

# Generate secure tokens
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env with your tokens
```

### 3. Create Vector Collection

```bash
curl -X POST http://localhost:8007/mcp/tools/create_collection \
  -H "Authorization: Bearer YOUR_UPDATE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "filesystem_code",
    "vector_size": 384,
    "distance": "Cosine"
  }'
```

## Complete Workflow Example

### Python Integration

```python
import httpx
import hashlib
from pathlib import Path

# Service URLs
FILESYSTEM_URL = "http://localhost:8005"
EMBEDDINGS_URL = "http://localhost:8006"
VECTORS_URL = "http://localhost:8007"

# Tokens
FILESYSTEM_READ_TOKEN = "your-read-token"
EMBED_TOKEN = "your-embed-token"
VECTOR_UPDATE_TOKEN = "your-update-token"
VECTOR_QUERY_TOKEN = "your-query-token"

async def index_file(file_path: str):
    """Index a file: read -> embed -> store."""

    async with httpx.AsyncClient() as client:
        # 1. Read file content
        read_response = await client.post(
            f"{FILESYSTEM_URL}/mcp/tools/read_file",
            headers={"Authorization": f"Bearer {FILESYSTEM_READ_TOKEN}"},
            json={"path": file_path, "include_hash": True}
        )
        file_data = read_response.json()
        content = file_data["content"]
        file_hash = file_data["hash"]

        # 2. Generate embedding
        embed_response = await client.post(
            f"{EMBEDDINGS_URL}/mcp/tools/embed_text",
            headers={"Authorization": f"Bearer {EMBED_TOKEN}"},
            json={
                "text": content,
                "chunk_enabled": False  # Single file embedding
            }
        )
        embed_data = embed_response.json()
        embedding = embed_data["embedding"]

        # 3. Store in vector database
        vector_response = await client.post(
            f"{VECTORS_URL}/mcp/tools/upsert_vectors",
            headers={"Authorization": f"Bearer {VECTOR_UPDATE_TOKEN}"},
            json={
                "collection": "filesystem_code",
                "points": [{
                    "id": file_hash,
                    "vector": embedding,
                    "payload": {
                        "file_path": file_path,
                        "file_hash": file_hash,
                        "file_name": Path(file_path).name,
                        "file_extension": Path(file_path).suffix
                    }
                }]
            }
        )

        return vector_response.json()


async def search_similar_files(query_text: str, limit: int = 5):
    """Search for similar files by text query."""

    async with httpx.AsyncClient() as client:
        # 1. Generate query embedding
        embed_response = await client.post(
            f"{EMBEDDINGS_URL}/mcp/tools/embed_text",
            headers={"Authorization": f"Bearer {EMBED_TOKEN}"},
            json={"text": query_text, "chunk_enabled": False}
        )
        query_embedding = embed_response.json()["embedding"]

        # 2. Search vectors
        search_response = await client.post(
            f"{VECTORS_URL}/mcp/tools/search_vectors",
            headers={"Authorization": f"Bearer {VECTOR_QUERY_TOKEN}"},
            json={
                "collection": "filesystem_code",
                "query_vector": query_embedding,
                "limit": limit,
                "score_threshold": 0.7
            }
        )

        return search_response.json()["results"]


async def index_directory(directory_path: str):
    """Index all files in a directory."""

    async with httpx.AsyncClient() as client:
        # 1. List directory
        list_response = await client.post(
            f"{FILESYSTEM_URL}/mcp/tools/list_directory",
            headers={"Authorization": f"Bearer {FILESYSTEM_READ_TOKEN}"},
            json={
                "path": directory_path,
                "recursive": True,
                "include_hidden": False
            }
        )

        files = list_response.json()["files"]

        # 2. Index each file
        results = []
        for file_info in files:
            if file_info["type"] == "file":
                result = await index_file(file_info["path"])
                results.append(result)
                print(f"Indexed: {file_info['path']}")

        return results


# Usage examples
async def main():
    # Index a single file
    result = await index_file("/path/to/file.py")
    print("Indexed file:", result)

    # Index entire directory
    results = await index_directory("/path/to/code")
    print(f"Indexed {len(results)} files")

    # Search for similar code
    similar = await search_similar_files("authentication function")
    for match in similar:
        print(f"Score: {match['score']:.2f} - {match['payload']['file_path']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Advanced Features

### Chunked Embedding for Large Files

```python
async def index_large_file(file_path: str):
    """Index a large file with chunking."""

    async with httpx.AsyncClient() as client:
        # Read file
        read_response = await client.post(
            f"{FILESYSTEM_URL}/mcp/tools/read_file",
            headers={"Authorization": f"Bearer {FILESYSTEM_READ_TOKEN}"},
            json={"path": file_path}
        )
        content = read_response.json()["content"]

        # Generate embeddings with chunking
        embed_response = await client.post(
            f"{EMBEDDINGS_URL}/mcp/tools/embed_text",
            headers={"Authorization": f"Bearer {EMBED_TOKEN}"},
            json={
                "text": content,
                "chunk_enabled": True,
                "chunk_size": 512,
                "return_chunks": True
            }
        )

        chunks_data = embed_response.json()["chunks"]

        # Store each chunk as a separate vector
        points = []
        for i, chunk in enumerate(chunks_data):
            chunk_id = f"{file_path}#chunk{i}"
            points.append({
                "id": chunk_id,
                "vector": chunk["embedding"],
                "payload": {
                    "file_path": file_path,
                    "chunk_index": i,
                    "total_chunks": len(chunks_data),
                    "chunk_text": chunk["text"][:100]  # Store preview
                }
            })

        # Upsert all chunks
        vector_response = await client.post(
            f"{VECTORS_URL}/mcp/tools/upsert_vectors",
            headers={"Authorization": f"Bearer {VECTOR_UPDATE_TOKEN}"},
            json={
                "collection": "filesystem_code",
                "points": points
            }
        )

        return vector_response.json()
```

### Metadata Filtering

```python
async def search_python_files_only(query_text: str):
    """Search only Python files."""

    async with httpx.AsyncClient() as client:
        # Generate query embedding
        embed_response = await client.post(
            f"{EMBEDDINGS_URL}/mcp/tools/embed_text",
            headers={"Authorization": f"Bearer {EMBED_TOKEN}"},
            json={"text": query_text}
        )
        query_embedding = embed_response.json()["embedding"]

        # Search with filter
        search_response = await client.post(
            f"{VECTORS_URL}/mcp/tools/search_vectors",
            headers={"Authorization": f"Bearer {VECTOR_QUERY_TOKEN}"},
            json={
                "collection": "filesystem_code",
                "query_vector": query_embedding,
                "limit": 10,
                "filter_conditions": {
                    "must": [
                        {
                            "key": "file_extension",
                            "match": {"value": ".py"}
                        }
                    ]
                }
            }
        )

        return search_response.json()["results"]
```

## Distributed Setup

### Running on Separate Machines

**Machine 1: Core Eva + Vector Service (exposed endpoint)**
```bash
# .env
QDRANT_URL=http://192.168.1.101:6333
OLLAMA_URL=http://192.168.1.100:11434
```

**Machine 2: Mac with Ollama (embedding generation)**
```bash
# Start Ollama
ollama serve

# Pull embedding model
ollama pull nomic-embed-text

# Expose on network
# Edit ~/.ollama/config.yaml to bind to 0.0.0.0
```

**Machine 3: Qdrant Storage (dedicated vector database)**
```bash
# Run Qdrant
docker run -p 6333:6333 \
  -v /path/to/storage:/qdrant/storage \
  qdrant/qdrant:latest
```

## Collection Schemas

### Recommended Collections

#### filesystem_code
```python
{
    "name": "filesystem_code",
    "vector_size": 384,
    "distance": "Cosine",
    "payload_schema": {
        "file_path": "str",
        "file_hash": "str",
        "file_name": "str",
        "file_extension": "str",
        "language": "str",
        "chunk_index": "int (optional)",
        "indexed_at": "datetime"
    }
}
```

#### filesystem_docs
```python
{
    "name": "filesystem_docs",
    "vector_size": 384,
    "distance": "Cosine",
    "payload_schema": {
        "file_path": "str",
        "file_type": "str",
        "title": "str",
        "chunk_index": "int (optional)",
        "indexed_at": "datetime"
    }
}
```

## Monitoring

### Check Service Health

```bash
# Embeddings
curl http://localhost:8006/health

# Vectors
curl http://localhost:8007/health

# Qdrant
curl http://localhost:6333/health
```

### View Audit Logs

```bash
# Embedding operations
tail -f logs/embeddings_audit.jsonl | jq

# Vector operations
tail -f logs/vectors_audit.jsonl | jq
```

## Troubleshooting

### Embedding Service Not Connecting to Ollama

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Pull the model if needed
ollama pull nomic-embed-text
```

### Vector Service Can't Connect to Qdrant

```bash
# Check Qdrant is running
docker ps | grep qdrant

# Check collections
curl http://localhost:6333/collections
```

### Dimension Mismatch Error

Ensure the collection vector_size matches your embedding model:
- `nomic-embed-text`: 384 dimensions
- `all-MiniLM-L6-v2`: 384 dimensions
- `all-mpnet-base-v2`: 768 dimensions

## Security Best Practices

1. **Use different tokens** for each service
2. **Rotate tokens** periodically
3. **Monitor audit logs** for suspicious activity
4. **Limit allowed paths** in filesystem service
5. **Use firewall rules** in distributed setups
6. **Enable HTTPS** for production deployments

## Next Steps

- Integrate with chat service for RAG
- Add incremental indexing (watch filesystem changes)
- Implement hybrid search (vector + text)
- Add collection management UI
- Set up automated reindexing
