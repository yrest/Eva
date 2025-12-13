# Eva Task Management Service

**Port:** 8008

Enterprise-grade autonomous task execution service with human-in-the-loop approval workflow.

## Overview

The Task Management Service is Eva's core orchestration engine that:
- Manages task lifecycle from creation to completion
- Routes tasks to appropriate LLM backends (OpenAI, Anthropic, LM Studio)
- Executes tools in sandboxed environments with safety levels
- Implements approval workflows for sensitive operations
- Maintains detailed execution history and audit trails

## Features

### Core Capabilities
- **Multi-LLM Support**: OpenAI-compatible API for LM Studio, OpenAI, Anthropic
- **Approval Workflow**: Human-in-the-loop for sensitive operations
- **Tool Safety Levels**: Graduated permissions (READ_ONLY → DANGEROUS)
- **Sandboxed Execution**: Docker-based isolation for code execution
- **Task Queue**: Redis-based reliable task processing
- **Data Retention**: Configurable hot/cold storage (default: 3-6 months)

### Tool Framework
Tools are categorized by safety level:
1. **READ_ONLY**: Search, fetch data (auto-approved)
2. **SAFE_WRITE**: Create drafts (requires approval)
3. **EXTERNAL_API**: Send emails, API calls (requires approval)
4. **DANGEROUS**: Code execution, destructive ops (always sandboxed + approval)

## Architecture

```
┌─────────────┐
│   Client    │ ──── submits task ────> Task API (8008)
└─────────────┘
       │
       ▼
┌─────────────┐
│ Task Queue  │ ──── Redis
│ (Pending)   │
└─────────────┐
       │
       ▼
┌─────────────────────┐
│  Task Executor      │
│  - Fetch context    │ ──> Memory Service (8004)
│  - Build prompt     │ ──> Vector Service (8007)
│  - Call LLM         │ ──> LM Studio / OpenAI / Anthropic
│  - Execute tools    │
└─────────────────────┘
       │
       ├─ [Approval Required] ──> Approval Queue
       │                           │
       │                           ▼
       │                      Human reviews ──> Approve/Reject
       │                           │
       │                           ▼
       ├─ [Execute Tool]
       │   ├─ Vector Search ──> vectors:8007
       │   ├─ Send Email ──> SMTP
       │   ├─ Create Ticket ──> External API
       │   └─ Run Code ──> Docker Sandbox
       │
       ▼
┌─────────────┐
│   Result    │ ──> PostgreSQL (tasks, executions, approvals)
└─────────────┘
```

## Database Schema

### Tasks Table
```sql
CREATE TABLE tasks (
  id UUID PRIMARY KEY,
  type VARCHAR(100),              -- 'email_response', 'ticket_creation', 'code_fix'
  priority INT DEFAULT 5,         -- 1 (highest) to 10 (lowest)
  status VARCHAR(50),             -- 'pending', 'running', 'waiting_approval', 'completed', 'failed'
  input_data JSONB,               -- Task parameters
  context JSONB,                  -- Additional context from vector search, etc.
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  archived_at TIMESTAMP,          -- For data retention
  created_by VARCHAR(255)
);
```

### Executions Table
```sql
CREATE TABLE executions (
  id UUID PRIMARY KEY,
  task_id UUID REFERENCES tasks(id),
  llm_backend VARCHAR(50),        -- 'lmstudio', 'openai', 'anthropic'
  llm_model VARCHAR(100),         -- Model name/ID
  conversation JSONB,             -- Message history
  tool_calls JSONB,               -- Tools invoked with parameters
  status VARCHAR(50),             -- 'running', 'waiting_approval', 'completed', 'failed'
  error_message TEXT,
  started_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP
);
```

### Approvals Table
```sql
CREATE TABLE approvals (
  id UUID PRIMARY KEY,
  execution_id UUID REFERENCES executions(id),
  tool_name VARCHAR(100),
  tool_params JSONB,
  safety_level INT,               -- 1-4 (READ_ONLY to DANGEROUS)
  status VARCHAR(50),             -- 'pending', 'approved', 'rejected'
  requested_at TIMESTAMP DEFAULT NOW(),
  reviewed_at TIMESTAMP,
  reviewed_by VARCHAR(255),
  review_comment TEXT
);
```

### Tool Executions Table
```sql
CREATE TABLE tool_executions (
  id UUID PRIMARY KEY,
  execution_id UUID REFERENCES executions(id),
  approval_id UUID REFERENCES approvals(id),
  tool_name VARCHAR(100),
  tool_params JSONB,
  result JSONB,
  error_message TEXT,
  sandbox_used BOOLEAN DEFAULT false,
  started_at TIMESTAMP DEFAULT NOW(),
  completed_at TIMESTAMP
);
```

## API Endpoints

### Task Management
```
POST   /tasks                    # Create new task
GET    /tasks                    # List tasks (with filters)
GET    /tasks/{id}               # Get task details
DELETE /tasks/{id}               # Cancel task
```

### Approvals
```
GET    /approvals                # List pending approvals
GET    /approvals/{id}           # Get approval details
POST   /approvals/{id}/approve   # Approve action
POST   /approvals/{id}/reject    # Reject action
```

### Executions
```
GET    /executions/{id}          # Get execution details
GET    /executions/{id}/logs     # Get execution logs
```

### Admin
```
GET    /health                   # Health check
POST   /archive                  # Trigger archival
GET    /mcp/info                 # MCP server info
```

## Environment Variables

```bash
# Service Configuration
TASKS_READ_TOKEN=change-me-secure-read-token
TASKS_WRITE_TOKEN=change-me-secure-write-token
TASKS_ADMIN_TOKEN=change-me-secure-admin-token

# Database
DATABASE_URL=postgresql://eva:eva@localhost:5432/eva

# Redis Queue
REDIS_URL=redis://localhost:6379
TASK_QUEUE_NAME=eva:tasks

# LLM Backends (OpenAI-compatible)
LMSTUDIO_URL=http://localhost:1234
LMSTUDIO_API_KEY=lm-studio  # Optional
DEFAULT_LMSTUDIO_MODEL=mistral-7b-instruct

OPENAI_API_KEY=sk-...
DEFAULT_OPENAI_MODEL=gpt-4-turbo-preview

ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Default LLM backend
DEFAULT_LLM_BACKEND=lmstudio

# Tool Sandboxing
DOCKER_ENABLED=true
DOCKER_NETWORK=none              # Isolate containers
DOCKER_CPU_LIMIT=1.0
DOCKER_MEMORY_LIMIT=512m
DOCKER_TIMEOUT=60                # seconds

# Data Retention
HOT_STORAGE_DAYS=90              # 3 months
COLD_STORAGE_DAYS=180            # 6 months (after hot)
ARCHIVE_ENABLED=true

# Services Integration
MEMORY_SERVICE_URL=http://localhost:8004
VECTOR_SERVICE_URL=http://localhost:8007
VECTOR_QUERY_TOKEN=...
```

## Tool Safety Levels

### Level 1: READ_ONLY (Auto-approved)
- `search_vectors` - Search vector database
- `get_context` - Fetch context from memory
- `read_file` - Read allowed files (via filesystem service)

### Level 2: SAFE_WRITE (Requires approval)
- `draft_email` - Create email draft
- `draft_ticket` - Create ticket draft
- `save_context` - Save to memory service

### Level 3: EXTERNAL_API (Requires approval)
- `send_email` - Send email via SMTP
- `create_ticket` - Create ticket in external system
- `api_call` - Generic API call

### Level 4: DANGEROUS (Sandboxed + approval)
- `execute_code` - Run code in Docker
- `modify_file` - Modify files (via filesystem service)
- `shell_command` - Execute shell command

## Usage Examples

### Create a Task
```bash
curl -X POST http://localhost:8008/tasks \
  -H "Authorization: Bearer $TASKS_WRITE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "email_response",
    "priority": 5,
    "input_data": {
      "email_id": "123",
      "sender": "customer@example.com",
      "subject": "Help with product X",
      "body": "I cant figure out how to..."
    }
  }'
```

### List Pending Approvals
```bash
curl -X GET http://localhost:8008/approvals?status=pending \
  -H "Authorization: Bearer $TASKS_READ_TOKEN"
```

### Approve an Action
```bash
curl -X POST http://localhost:8008/approvals/{id}/approve \
  -H "Authorization: Bearer $TASKS_WRITE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reviewed_by": "admin@eva.local",
    "comment": "Looks good"
  }'
```

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python -m src.migrations.run

# Start service
python -m src.main

# Or with uvicorn
uvicorn src.main:app --reload --port 8008
```

## Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

## Security Considerations

1. **Token-based Authentication**: Read/Write/Admin tokens
2. **Approval Workflow**: All non-READ_ONLY tools require approval
3. **Docker Sandboxing**: Code execution isolated with resource limits
4. **Audit Logging**: All operations logged to PostgreSQL
5. **Input Validation**: Pydantic models for all requests
6. **Network Isolation**: Sandboxed containers have no network access

## Roadmap

- [ ] Phase 1: Core task service with approval workflow ✅
- [ ] Phase 2: Tool framework with safety levels
- [ ] Phase 3: Multi-LLM routing
- [ ] Phase 4: Advanced scheduling (cron, events)
- [ ] Phase 5: Multi-step workflows
- [ ] Phase 6: Self-improvement capabilities

## License

Part of the Eva AI Assistant project.
