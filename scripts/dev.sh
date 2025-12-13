#!/bin/bash
set -e

echo "Starting Eva development environment..."

# Start infrastructure services
docker compose up -d redis postgres

# Wait for services
echo "Waiting for infrastructure..."
sleep 3

# Start all services in development mode
pnpm dev
