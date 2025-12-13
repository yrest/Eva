#!/bin/bash
set -e

echo "Setting up Eva development environment..."

# Install Node.js dependencies
echo "Installing Node.js dependencies..."
pnpm install

# Set up Python services
echo "Setting up Python services..."
cd services/chat && pip install -e ".[dev]" && cd ../..
cd services/memory && pip install -e ".[dev]" && cd ../..

# Set up Go service
echo "Setting up Go service..."
cd services/knowledge && go mod download && cd ../..

# Copy environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file - please update with your API keys"
fi

echo "Setup complete!"
