"""Integration tests for FastAPI endpoints."""

import pytest
from httpx import AsyncClient
from pathlib import Path

from src.main import app
from src.config import settings


@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def read_headers():
    """Headers with read token."""
    return {"Authorization": f"Bearer {settings.read_token}"}


@pytest.fixture
def write_headers():
    """Headers with write token."""
    return {"Authorization": f"Bearer {settings.write_token}"}


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "filesystem"


@pytest.mark.asyncio
async def test_mcp_info(client):
    """Test MCP info endpoint."""
    response = await client.get("/mcp/info")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "eva-filesystem"
    assert len(data["tools"]) == 4
    assert data["features"]["path_sandboxing"] is True


@pytest.mark.asyncio
async def test_read_file_without_auth(client):
    """Test read file without authentication fails."""
    response = await client.post(
        "/mcp/tools/read_file",
        json={"path": "/tmp/test.txt"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_write_file_with_read_token(client, read_headers):
    """Test write file with read token fails."""
    response = await client.post(
        "/mcp/tools/write_file",
        headers=read_headers,
        json={
            "path": "/tmp/test.txt",
            "content": "test content"
        }
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_directory_without_auth(client):
    """Test list directory without authentication fails."""
    response = await client.post(
        "/mcp/tools/list_directory",
        json={"path": "/tmp"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_search_files_without_auth(client):
    """Test search files without authentication fails."""
    response = await client.post(
        "/mcp/tools/search_files",
        json={"query": "test"}
    )
    assert response.status_code == 403
