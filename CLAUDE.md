# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Prerequisites

Please:
 - DO NOT assume anything, unless explicitly instructed.
 - If something is unclear, always ask for clarification.
 - Never commit code without users review and approvals.

## Project Overview

Eva is a vendor agnostic personal AI assistant built for enterprise scale. 
Eva is OS - Orchestrator System, having capabilities of goddess, connecting various services and components, presenting and consuming predefined set of APIs over MCP.
It is a monorepo, containing multiple microservices with a React frontend.

## Architecture

```
eva/
├── apps/
│   └── web/              # React frontend (Vite)
├── packages/
│   ├── shared/           # Shared types and utilities (TypeScript)
│   ├── ui/               # React component library
│   └── ai-sdk/           # AI integration SDK
├── services/
│   ├── api-gateway/      # Request routing (Node.js/Fastify)
│   ├── auth/             # Authentication (Node.js/Fastify)
│   ├── chat/             # AI chat handling (Python/FastAPI)
│   ├── embeddings/       # Local embedding generation via Ollama/LM Studio (Python/FastAPI)
│   ├── filesystem/       # Secure file access MCP server (Python/FastAPI)
│   ├── knowledge/        # Document/RAG service (Go/Fiber)
│   ├── memory/           # Context management (Python/FastAPI)
│   └── vectors/          # Vector storage and search via Qdrant (Python/FastAPI)
└── infrastructure/
    ├── docker/           # Dockerfiles
    └── k8s/              # Kubernetes manifests
```

## Commands

### Development
```bash
pnpm install              # Install all dependencies
pnpm dev                  # Run all services in dev mode
pnpm build                # Build all packages
pnpm test                 # Run tests across monorepo
pnpm lint                 # Lint all packages
```

### Individual Services
```bash
# TypeScript services
pnpm --filter @eva/web dev
pnpm --filter @eva/api-gateway dev

# Python services
cd services/chat && python -m src.main
cd services/memory && python -m src.main
cd services/filesystem && python -m src.main
cd services/embeddings && python -m src.main
cd services/vectors && python -m src.main

# Go service
cd services/knowledge && go run cmd/main.go
```

### Docker
```bash
docker compose up                    # Start all services
docker compose up -d redis postgres  # Start infra only
```

## Service Ports
- Web: 3000
- API Gateway: 8000
- Auth: 8001
- Chat: 8002
- Knowledge: 8003
- Memory: 8004
- Filesystem: 8005
- Embeddings: 8006
- Vectors: 8007

## Infrastructure Ports
- Redis: 6379
- PostgreSQL: 5432
- Qdrant: 6333 (HTTP), 6334 (gRPC)

## Package Dependencies
- `@eva/shared` - Base package, no internal dependencies
- `@eva/ui` - Depends on `@eva/shared`
- `@eva/ai-sdk` - Depends on `@eva/shared`
- All services depend on `@eva/shared`
- `@eva/web` depends on `@eva/shared`, `@eva/ui`

## Environment Variables
Copy `.env.example` to `.env` and configure:

### Core Infrastructure
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- `JWT_SECRET` - Auth token signing
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` - AI providers

### Filesystem Service (Port 8005)
- `FILESYSTEM_READ_TOKEN` - Read operations token
- `FILESYSTEM_WRITE_TOKEN` - Write operations token
- `FILESYSTEM_ALLOWED_PATHS` - Comma-separated allowed paths

### Embedding Service (Port 8006)
- `EMBED_TOKEN` - Authentication token
- `OLLAMA_URL` - Ollama server URL (default: http://localhost:11434)
- `LMSTUDIO_URL` - LM Studio server URL (default: http://localhost:1234)
- `DEFAULT_EMBEDDING_BACKEND` - Backend to use (ollama/lmstudio)

### Vector Service (Port 8007)
- `VECTOR_QUERY_TOKEN` - Query/search operations token
- `VECTOR_UPDATE_TOKEN` - Update/delete operations token
- `QDRANT_URL` - Qdrant server URL (default: http://localhost:6333)

## Privacy & Local-First Architecture

Eva is designed with privacy and local-first principles:

### Local Embedding Generation
- **Embeddings Service** uses local models via Ollama or LM Studio
- No external API calls for embeddings
- All data stays on your machine

### Local Vector Storage
- **Vectors Service** stores all embeddings in local Qdrant instance
- No cloud dependencies
- Complete data ownership

### Distributed Deployment
Services can run on separate hardware for resource optimization:
- Core Eva services on main machine (ports 8000-8004)
- Embedding service on GPU-enabled Mac (port 8006)
- Vector service with Qdrant on storage-optimized machine (port 8007)

Update URLs in `.env` to point to remote services:
```bash
OLLAMA_URL=http://192.168.1.100:11434
QDRANT_URL=http://192.168.1.101:6333
```
