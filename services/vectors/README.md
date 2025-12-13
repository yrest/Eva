# Eva Vector Service

Secure vector storage and search service powered by Qdrant.

## Features

- 🏠 **Local Storage** - All vectors stored in local Qdrant instance
- 🔐 **Dual-Token Auth** - Separate tokens for query and update operations
- 📝 **Extensive Logging** - Audit trail for all operations
- 🗂️ **Collections** - Purpose-driven collections with metadata
- 🔍 **Semantic Search** - Fast similarity search with filtering
- 🚀 **MCP Compatible** - Model Context Protocol endpoints

## Quick Start

### Local Development

```bash
# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant:latest

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your tokens

# Run the service
python -m src.main
```

Service will be available at `http://localhost:8007`

### Docker

```bash
# From project root
docker compose up qdrant vectors
```

## Configuration

See `.env.example` for all available options.

Key settings:
- `VECTOR_QUERY_TOKEN` - Token for search/read operations
- `VECTOR_UPDATE_TOKEN` - Token for insert/update/delete operations
- `QDRANT_URL` - Qdrant server URL (default: http://localhost:6333)

## API Endpoints

### Collection Management

**Create Collection**
```bash
POST /mcp/tools/create_collection
Authorization: Bearer <UPDATE_TOKEN>

{
  "name": "filesystem_code",
  "vector_size": 384,
  "distance": "Cosine"
}
```

**List Collections**
```bash
GET /mcp/tools/list_collections
Authorization: Bearer <QUERY_TOKEN>
```

**Get Collection Info**
```bash
POST /mcp/tools/get_collection_info
Authorization: Bearer <QUERY_TOKEN>

{
  "name": "filesystem_code"
}
```

### Vector Operations

**Upsert Vectors**
```bash
POST /mcp/tools/upsert_vectors
Authorization: Bearer <UPDATE_TOKEN>

{
  "collection": "filesystem_code",
  "points": [
    {
      "id": "file_abc",
      "vector": [0.1, 0.2, ...],
      "payload": {
        "file_path": "/path/to/file.py",
        "file_hash": "sha256:...",
        "language": "python"
      }
    }
  ]
}
```

**Search Vectors**
```bash
POST /mcp/tools/search_vectors
Authorization: Bearer <QUERY_TOKEN>

{
  "collection": "filesystem_code",
  "query_vector": [0.1, 0.2, ...],
  "limit": 10,
  "score_threshold": 0.7,
  "filter_conditions": {
    "must": [
      {"key": "language", "match": {"value": "python"}}
    ]
  }
}
```

**Delete Vectors**
```bash
POST /mcp/tools/delete_vectors
Authorization: Bearer <UPDATE_TOKEN>

{
  "collection": "filesystem_code",
  "point_ids": ["file_abc", "file_def"]
}
```

## Usage Example

```python
import httpx

async def index_file(file_path: str, embedding: list):
    """Index a file with its embedding."""
    async with httpx.AsyncClient() as client:
        # Upsert vector
        response = await client.post(
            "http://localhost:8007/mcp/tools/upsert_vectors",
            headers={"Authorization": "Bearer update-token"},
            json={
                "collection": "filesystem_code",
                "points": [{
                    "id": file_path,
                    "vector": embedding,
                    "payload": {
                        "file_path": file_path,
                        "indexed_at": datetime.utcnow().isoformat()
                    }
                }]
            }
        )
        return response.json()

async def search_similar_files(query_embedding: list):
    """Search for similar files."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8007/mcp/tools/search_vectors",
            headers={"Authorization": "Bearer query-token"},
            json={
                "collection": "filesystem_code",
                "query_vector": query_embedding,
                "limit": 5
            }
        )
        return response.json()
```

## Collection Strategy

Organize vectors by purpose:

- `filesystem_code` - Source code files
- `filesystem_docs` - Documentation files
- `chat_history` - User conversations
- `knowledge_base` - Personal knowledge

Each collection has:
- Specific vector dimensions
- Custom metadata schema
- Purpose-driven organization

## Distributed Setup

To run on separate hardware:

1. Run Qdrant on target machine:
   ```bash
   docker run -p 6333:6333 -v /path/to/storage:/qdrant/storage qdrant/qdrant:latest
   ```

2. Update `.env` in vector service:
   ```bash
   QDRANT_URL=http://192.168.1.101:6333
   ```

## Privacy Guarantee

✅ All vectors stored locally
✅ No external calls
✅ Complete data privacy
✅ Audit logs track all operations

## Architecture

```
Client Request
    ↓
Token Authentication (Query/Update)
    ↓
Vector Operation (Search/Upsert/Delete)
    ↓
Qdrant (Local Container)
    ↓
Audit Logging
    ↓
Response
```

## Performance

- Fast similarity search (< 100ms for millions of vectors)
- Supports metadata filtering
- Efficient batch operations
- Persistent storage with Qdrant
