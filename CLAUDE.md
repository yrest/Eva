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
│   ├── knowledge/        # Document/RAG service (Go/Fiber)
│   └── memory/           # Context management (Python/FastAPI)
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

## Package Dependencies
- `@eva/shared` - Base package, no internal dependencies
- `@eva/ui` - Depends on `@eva/shared`
- `@eva/ai-sdk` - Depends on `@eva/shared`
- All services depend on `@eva/shared`
- `@eva/web` depends on `@eva/shared`, `@eva/ui`

## Environment Variables
Copy `.env.example` to `.env` and configure:
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- `JWT_SECRET` - Auth token signing
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` - AI providers
