# Eva Filesystem Service

**Secure, enterprise-grade file system access via MCP for Eva (The Goddess Orchestrator)**

A platform-independent Python-powered FastAPI MCP server providing secure filesystem operations with dual-token authentication, comprehensive auditing, and vector indexing readiness.

## 🔒 Security Features

- **Dual-Token Authentication**: Separate read and write tokens following principle of least privilege
- **Path Sandboxing**: Strict path validation - only access whitelisted directories
- **Symlink Protection**: Prevents path traversal attacks via symbolic links
- **File Size Limits**: Configurable maximum file size to prevent resource exhaustion
- **Comprehensive Audit Logging**: Every operation logged with timestamp, path, token type, and outcome
- **Rate Limiting**: Built-in request throttling (configurable)

## 🚀 Features

- **File Operations**: Read, write with full security validation
- **Directory Listing**: Recursive directory traversal with depth limits
- **File Search**: Query files by path (content search ready for Qdrant integration)
- **Metadata Indexing**: SQLite-based caching with file hashing (BLAKE3)
- **File Sampling**: Extract samples for indexing without reading entire files
- **Deduplication Detection**: Hash-based duplicate file detection
- **Vector Index Ready**: Pre-configured for Qdrant integration

## 📦 Installation

### Prerequisites

- Python 3.10+
- pip or poetry

### Setup

```bash
cd services/filesystem

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your configuration
```

### Configuration

Edit `.env` file:

```env
# Security - CHANGE THESE!
READ_TOKEN=your_secure_read_token_here
WRITE_TOKEN=your_secure_write_token_here
JWT_SECRET=your_secret_key_here

# File Access Control
ALLOWED_PATHS=/home/user/documents,/home/user/workspace
MAX_FILE_SIZE_MB=100

# Storage paths
SQLITE_DB_PATH=./data/filesystem.db
AUDIT_LOG_PATH=./data/audit.log
```

## 🏃 Running the Service

### Development Mode

```bash
cd services/filesystem
python -m src.main
```

Server runs at `http://localhost:8005`

### Production Mode

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8005 --workers 4
```

### Docker (Future)

```bash
docker compose up filesystem
```

## 🔧 API Usage

### Authentication

All requests require Bearer token authentication:

```bash
# Read operations (use READ_TOKEN)
curl -H "Authorization: Bearer YOUR_READ_TOKEN" \
  -X POST http://localhost:8005/mcp/tools/read_file \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/file.txt"}'

# Write operations (use WRITE_TOKEN)
curl -H "Authorization: Bearer YOUR_WRITE_TOKEN" \
  -X POST http://localhost:8005/mcp/tools/write_file \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/file.txt", "content": "Hello Eva!"}'
```

### Available Tools

#### 1. Read File

```bash
POST /mcp/tools/read_file

{
  "path": "/path/to/file.txt",
  "include_hash": true,
  "update_index": true
}
```

**Response:**
```json
{
  "path": "/path/to/file.txt",
  "content": "file contents...",
  "size": 1234,
  "mime_type": "text/plain",
  "hash": "blake3_hash_here",
  "is_text": true,
  "last_modified": 1234567890.0
}
```

#### 2. Write File

```bash
POST /mcp/tools/write_file

{
  "path": "/path/to/file.txt",
  "content": "Hello Eva!",
  "is_binary": false,
  "create_parents": false,
  "overwrite": true
}
```

**Response:**
```json
{
  "path": "/path/to/file.txt",
  "size": 10,
  "hash": "blake3_hash_here",
  "success": true
}
```

#### 3. List Directory

```bash
POST /mcp/tools/list_directory

{
  "path": "/path/to/dir",
  "recursive": true,
  "include_hidden": false,
  "max_depth": 3
}
```

**Response:**
```json
{
  "path": "/path/to/dir",
  "items": [
    {
      "name": "file.txt",
      "path": "/path/to/dir/file.txt",
      "is_directory": false,
      "is_file": true,
      "size": 1234,
      "last_modified": 1234567890.0,
      "permissions": "644",
      "depth": 0
    }
  ],
  "total_count": 1,
  "recursive": true
}
```

#### 4. Search Files

```bash
POST /mcp/tools/search_files

{
  "query": "*.txt",
  "limit": 100
}
```

**Response:**
```json
{
  "query": "*.txt",
  "results": [
    {
      "path": "/path/to/file.txt",
      "hash": "blake3_hash",
      "size": 1234,
      "mime_type": "text/plain"
    }
  ],
  "total_count": 1,
  "truncated": false
}
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_security.py
```

## 📊 Architecture

```
┌─────────────────────────────────────────────────┐
│           Eva Filesystem Service                 │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────┐      ┌──────────────┐        │
│  │   FastAPI    │─────▶│  MCP Tools   │        │
│  │   Server     │      │              │        │
│  └──────┬───────┘      └──────┬───────┘        │
│         │                     │                 │
│  ┌──────▼───────┐      ┌─────▼────────┐        │
│  │     Auth     │      │   Security   │        │
│  │   Manager    │      │  Validator   │        │
│  └──────────────┘      └──────────────┘        │
│                                                  │
│  ┌──────────────┐      ┌──────────────┐        │
│  │    Audit     │      │   Hasher     │        │
│  │   Logger     │      │   (BLAKE3)   │        │
│  └──────┬───────┘      └──────┬───────┘        │
│         │                     │                 │
│  ┌──────▼──────────────────────▼──────┐        │
│  │      SQLite Metadata Index          │        │
│  └─────────────────────────────────────┘        │
│                                                  │
│         ┌────────────────────┐                  │
│         │  Qdrant (Future)   │                  │
│         │  Vector Indexing   │                  │
│         └────────────────────┘                  │
└─────────────────────────────────────────────────┘
```

## 🔮 Future Enhancements (Qdrant Integration)

The service is designed to integrate seamlessly with Qdrant for vector-based semantic search:

1. **Content Embeddings**: Generate embeddings for indexed files
2. **Semantic Search**: Search by meaning, not just file names
3. **Similarity Detection**: Find similar documents
4. **Smart Deduplication**: Detect near-duplicates using embeddings

Configuration ready in `.env`:
```env
QDRANT_HOST=localhost
QDRANT_PORT=6333
ENABLE_VECTOR_INDEX=false  # Set to true when ready
```

## 📝 Audit Logs

All operations are logged to `AUDIT_LOG_PATH` in JSON format:

```json
{
  "timestamp": "2025-12-13T10:30:00.000000",
  "operation": "read_file",
  "path": "/path/to/file.txt",
  "token_type": "read",
  "success": true,
  "details": {
    "file_size": 1234,
    "file_hash": "blake3_hash"
  }
}
```

## 🛡️ Security Best Practices

1. **Token Management**
   - Use strong, random tokens (32+ characters)
   - Rotate tokens regularly
   - Never commit tokens to version control
   - Use different tokens per environment

2. **Path Configuration**
   - Only whitelist necessary directories
   - Avoid whitelisting root or home directories
   - Use absolute paths in configuration

3. **File Size Limits**
   - Set appropriate limits based on use case
   - Monitor disk usage and logs

4. **Audit Logs**
   - Regularly review audit logs
   - Set up log rotation
   - Monitor for suspicious patterns

## 📄 License

Part of the Eva project - Enterprise AI Assistant

## 🤝 Contributing

This is part of Eva's microservices architecture. For contributions, please follow the main Eva repository guidelines.

## 🆘 Support

For issues, questions, or feature requests, please use the main Eva repository issue tracker.

---

**Built for Eva, the Goddess Orchestrator** 🌟
