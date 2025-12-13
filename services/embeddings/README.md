# Eva Embedding Service

Local-first embedding generation service with support for Ollama and LM Studio.

## Features

- 🏠 **100% Local** - No external API calls, complete privacy
- 🔐 **Secure** - Token-based authentication
- 📝 **Audit Logging** - Extensive operation logging
- ✂️ **Auto Chunking** - Intelligent text chunking for large documents
- 🔌 **Dual Backend** - Support for Ollama and LM Studio
- 🚀 **MCP Compatible** - Model Context Protocol endpoints

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your tokens and backend URLs

# Run the service
python -m src.main
```

Service will be available at `http://localhost:8006`

### Docker

```bash
# From project root
docker compose up embeddings
```

## Configuration

See `.env.example` for all available options.

Key settings:
- `EMBED_TOKEN` - Authentication token
- `DEFAULT_BACKEND` - `ollama` or `lmstudio`
- `OLLAMA_URL` - Ollama server URL (default: http://localhost:11434)
- `LMSTUDIO_URL` - LM Studio server URL (default: http://localhost:1234)

## API Endpoints

### Health Check
```bash
GET /health
```

### Embed Text
```bash
POST /mcp/tools/embed_text
Authorization: Bearer <EMBED_TOKEN>

{
  "text": "Your text here",
  "backend": "ollama",  // optional
  "chunk_enabled": true,
  "chunk_size": 512,
  "return_chunks": false
}
```

## Usage Example

```python
import httpx

async def embed_document(text: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8006/mcp/tools/embed_text",
            headers={"Authorization": "Bearer your-token"},
            json={
                "text": text,
                "chunk_enabled": True
            }
        )
        return response.json()
```

## Distributed Setup

To run on separate hardware (e.g., Mac with GPU):

1. Update `.env`:
   ```bash
   SERVICE_HOST=0.0.0.0
   SERVICE_PORT=8006
   ```

2. Expose port and run:
   ```bash
   python -m src.main
   ```

3. Point Eva core to this service:
   ```bash
   # In Eva core .env
   EMBEDDING_SERVICE_URL=http://192.168.1.100:8006
   ```

## Supported Models

### Ollama
- `nomic-embed-text` (default)
- Any other Ollama embedding model

### LM Studio
- `text-embedding-nomic-embed-text-v1.5` (default)
- Any OpenAI-compatible embedding model loaded in LM Studio

## Privacy Guarantee

✅ All data stays local
✅ No external API calls
✅ Complete privacy
✅ Audit logs track all operations

## Architecture

```
Client Request
    ↓
Token Authentication
    ↓
Text Chunking (if needed)
    ↓
Embedding Generation (Ollama/LM Studio)
    ↓
Audit Logging
    ↓
Response with Embeddings
```
