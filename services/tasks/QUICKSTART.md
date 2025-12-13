# Eva Task Orchestrator - Quick Start

**Ultra-simplified file-based task management for Eva!**

## What We Built

- **File-based storage** - No PostgreSQL, no Redis, just JSON files
- **MCP server registry** - Register filesystem, embedding, and vector services
- **Dynamic task orchestration** - LLM-powered, no hard-coded task types
- **Guardrails** - Validate LLM plans before execution
- **Few-shot examples** - Teach Eva common patterns
- **Approval workflow** - Human-in-the-loop for write operations

## Directory Structure

```
services/tasks/
├── data/                    # All data lives here
│   ├── mcp_servers.json    # Registered services
│   ├── tasks/              # One JSON file per task
│   ├── approvals/          # Approval requests
│   └── logs/               # JSONL logs
├── src/
│   ├── storage.py          # File-based storage
│   ├── executor.py         # Task orchestration engine
│   ├── guardrails.py       # LLM validation
│   ├── prompts.py          # Few-shot examples
│   ├── main_simple.py      # FastAPI app
│   └── ...
└── eva-register.py         # CLI for managing servers
```

## Setup

### 1. Install Dependencies

```bash
cd services/tasks
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env

# Edit .env:
TASKS_READ_TOKEN=your-read-token
TASKS_WRITE_TOKEN=your-write-token
TASKS_ADMIN_TOKEN=your-admin-token

# LLM Backend
DEFAULT_LLM_BACKEND=lmstudio
LMSTUDIO_URL=http://localhost:1234
```

### 3. Start the Service

```bash
# Run simplified version
python -m src.main_simple

# Or with uvicorn
uvicorn src.main_simple:app --reload --port 8008
```

## Register Services

### Register Filesystem Servers

```bash
# Office desktop
./eva-register.py add "Office Desktop" filesystem \
  http://192.168.1.10:8005 read-token-123

# Laptop
./eva-register.py add "Laptop" filesystem \
  http://192.168.1.11:8005 read-token-456

# Home server
./eva-register.py add "Home Server" filesystem \
  http://192.168.1.12:8005 read-token-789
```

### Register Embedding Service

```bash
./eva-register.py add "Local Ollama" embedding \
  http://localhost:8006 embed-token
```

### Register Vector Service

```bash
./eva-register.py add "Local Qdrant" vector \
  http://localhost:8007 vector-update-token
```

### List All Servers

```bash
./eva-register.py list
```

### Register Collection Schemas

Tell Eva about your vector collections so it knows what fields exist:

```bash
# Register email collection
./eva-register.py add-collection abc \
  '{"sender":"str", "subject":"str", "body":"str", "date":"datetime"}' \
  --description "Daily email archive"

# Register Teams messages
./eva-register.py add-collection teams_messages \
  '{"sender":"str", "channel":"str", "message":"str", "date":"datetime", "reactions":"int"}' \
  --description "Teams chat history"

# List registered collections
./eva-register.py list-collections

# Remove a collection schema
./eva-register.py remove-collection abc
```

**Why register schemas?** Eva uses this to:
- Know what fields are available for filtering
- Understand the structure of your data
- Generate better queries
- Format results appropriately

## Create Tasks

### Via API

```bash
curl -X POST http://localhost:8008/tasks \
  -H "Authorization: Bearer $TASKS_WRITE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Index all my filesystems",
    "created_by": "user@example.com"
  }'
```

### Via Python

```python
import httpx

async def create_task(instruction: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8008/tasks",
            headers={"Authorization": "Bearer your-write-token"},
            json={"user_input": instruction}
        )
        return response.json()

# Create task
task = await create_task("Index all my filesystems")
print(f"Task created: {task['id']}")
```

## Example Tasks

### 1. Index All Filesystems

```bash
curl -X POST http://localhost:8008/tasks \
  -H "Authorization: Bearer $TASKS_WRITE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Index all my filesystems"}'
```

Eva will:
1. List all registered filesystem servers
2. For each server, recursively list all files
3. For each file: read → embed → store in vector DB
4. Return stats

### 2. Search for Code

```bash
curl -X POST http://localhost:8008/tasks \
  -H "Authorization: Bearer $TASKS_WRITE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Find authentication functions"}'
```

Eva will:
1. Convert query to embedding
2. Search vector DB
3. Return matching files

### 3. Index Specific Server

```bash
curl -X POST http://localhost:8008/tasks \
  -H "Authorization: Bearer $TASKS_WRITE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Index only the office desktop filesystem"}'
```

## Monitor Tasks

### List All Tasks

```bash
curl http://localhost:8008/tasks \
  -H "Authorization: Bearer $TASKS_READ_TOKEN"
```

### Get Task Details

```bash
curl http://localhost:8008/tasks/{task_id} \
  -H "Authorization: Bearer $TASKS_READ_TOKEN"
```

### View Task Conversation

```bash
curl http://localhost:8008/tasks/{task_id}/conversation \
  -H "Authorization: Bearer $TASKS_READ_TOKEN"
```

### View Logs

```bash
curl http://localhost:8008/logs?task_id={task_id} \
  -H "Authorization: Bearer $TASKS_READ_TOKEN"
```

## Approval Workflow

### List Pending Approvals

```bash
curl http://localhost:8008/approvals \
  -H "Authorization: Bearer $TASKS_READ_TOKEN"
```

### Approve

```bash
curl -X POST http://localhost:8008/approvals/{approval_id}/approve \
  -H "Authorization: Bearer $TASKS_WRITE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reviewed_by": "admin@example.com",
    "comment": "Looks good"
  }'
```

### Reject

```bash
curl -X POST http://localhost:8008/approvals/{approval_id}/reject \
  -H "Authorization: Bearer $TASKS_WRITE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reviewed_by": "admin@example.com",
    "comment": "Too risky"
  }'
```

## How It Works

1. **User creates task** with natural language instruction
2. **Eva analyzes** instruction using LLM + system prompt with examples
3. **Guardrails validate** the LLM's plan
4. **Eva orchestrates** tool calls to registered services
5. **Services execute** dumbly and return results
6. **Eva decides** next action based on results
7. **Approval workflow** for write operations
8. **Task completes** with result or error

## Key Concepts

### Services Are Dumb

Services don't orchestrate or make decisions. They just:
- Filesystem: Read file → return content
- Embedding: Take text → return vector
- Vector: Take vector → store it

### Eva Is Smart

Eva (task service) does ALL orchestration:
- Decides which services to call
- Coordinates the workflow
- Handles errors
- Asks for clarification if needed

### No Hard-Coded Task Types

Don't hardcode "index_filesystems" or "search_code". Just:
- Give Eva natural language instruction
- Eva figures out what to do from examples
- Eva calls appropriate tools

## Debugging

### View Raw Task File

```bash
cat data/tasks/{task_id}.json | jq
```

### View Logs

```bash
tail -f data/logs/tasks.jsonl | jq
```

### Check Server Registry

```bash
cat data/mcp_servers.json | jq
```

## Architecture

```
User → Eva (Task Service) → Orchestrates ALL calls
                │
                ├─→ Filesystem Service 1 → Returns data
                ├─→ Filesystem Service 2 → Returns data
                ├─→ Embedding Service → Returns vector
                └─→ Vector Service → Stores data
```

## What's Next?

- Run your first task: "Index all my filesystems"
- Watch the logs to see Eva orchestrate
- Try different natural language instructions
- Add more filesystem servers
- Build on this foundation!

---

**Built for Eva, The Goddess Orchestrator** 🌟
