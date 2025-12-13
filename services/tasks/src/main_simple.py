"""Simplified FastAPI server for task management with file storage."""

import asyncio
from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel

from .auth import require_read_permission, require_write_permission, require_admin_permission
from .config import settings
from .storage import storage
from .executor import executor


# ============================================================================
# Request/Response Models
# ============================================================================

class TaskCreate(BaseModel):
    """Create task request."""
    user_input: str
    created_by: Optional[str] = "user"


class TaskResponse(BaseModel):
    """Task response."""
    id: str
    user_input: str
    status: str
    created_at: str
    updated_at: str
    created_by: str
    result: Optional[str] = None
    error: Optional[str] = None


class ApprovalResponse(BaseModel):
    """Approval response."""
    id: str
    task_id: str
    tool_name: str
    tool_params: dict
    safety_level: str
    status: str
    reason: Optional[str] = None


class ApprovalDecision(BaseModel):
    """Approval decision."""
    reviewed_by: str
    comment: Optional[str] = None


class ServerCreate(BaseModel):
    """Create MCP server registration."""
    name: str
    type: str
    url: str
    auth_token: str
    capabilities: Optional[dict] = None


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="Eva Task Management Service",
    description="Autonomous task orchestration with file-based storage",
    version="0.2.0",
)


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check if we can list servers (storage working)
    storage_healthy = True
    try:
        storage.list_servers()
    except Exception:
        storage_healthy = False

    return {
        "status": "healthy" if storage_healthy else "degraded",
        "service": "tasks",
        "version": "0.2.0",
        "storage": "filesystem",
        "storage_healthy": storage_healthy,
        "default_llm_backend": settings.default_llm_backend
    }


# ============================================================================
# Task Management
# ============================================================================

@app.post("/tasks", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    credentials: HTTPAuthorizationCredentials = Depends(require_write_permission)
):
    """
    Create a new task.

    The task will be executed asynchronously by Eva's orchestration engine.
    """
    task = storage.create_task(
        user_input=task_data.user_input,
        created_by=task_data.created_by
    )

    # Start execution in background
    asyncio.create_task(executor.execute_task(task["id"]))

    return task


@app.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = None,
    limit: int = 100,
    credentials: HTTPAuthorizationCredentials = Depends(require_read_permission)
):
    """List all tasks, optionally filtered by status."""
    tasks = storage.list_tasks(status=status, limit=limit)
    return tasks


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(require_read_permission)
):
    """Get task by ID."""
    task = storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(require_write_permission)
):
    """Delete a task."""
    success = storage.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "deleted", "task_id": task_id}


@app.get("/tasks/{task_id}/conversation")
async def get_task_conversation(
    task_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(require_read_permission)
):
    """Get task conversation history."""
    task = storage.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "conversation": task.get("conversation", [])}


# ============================================================================
# Approval Management
# ============================================================================

@app.get("/approvals", response_model=List[ApprovalResponse])
async def list_approvals(
    status: str = "pending",
    task_id: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(require_read_permission)
):
    """List approvals, optionally filtered."""
    approvals = storage.list_approvals(status=status, task_id=task_id)
    return approvals


@app.get("/approvals/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(require_read_permission)
):
    """Get approval by ID."""
    approval = storage.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@app.post("/approvals/{approval_id}/approve")
async def approve(
    approval_id: str,
    decision: ApprovalDecision,
    credentials: HTTPAuthorizationCredentials = Depends(require_write_permission)
):
    """Approve a tool execution."""
    approval = storage.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval["status"] != "pending":
        raise HTTPException(status_code=400, detail="Approval already processed")

    # Update approval
    from datetime import datetime

    storage.update_approval(approval_id, {
        "status": "approved",
        "reviewed_at": datetime.utcnow().isoformat(),
        "reviewed_by": decision.reviewed_by,
        "review_comment": decision.comment
    })

    # Resume task execution
    task_id = approval["task_id"]
    asyncio.create_task(executor.resume_after_approval(task_id, approval_id))

    return {"status": "approved", "approval_id": approval_id}


@app.post("/approvals/{approval_id}/reject")
async def reject(
    approval_id: str,
    decision: ApprovalDecision,
    credentials: HTTPAuthorizationCredentials = Depends(require_write_permission)
):
    """Reject a tool execution."""
    from datetime import datetime

    approval = storage.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval["status"] != "pending":
        raise HTTPException(status_code=400, detail="Approval already processed")

    # Update approval
    storage.update_approval(approval_id, {
        "status": "rejected",
        "reviewed_at": datetime.utcnow().isoformat(),
        "reviewed_by": decision.reviewed_by,
        "review_comment": decision.comment
    })

    # Update task to failed
    task_id = approval["task_id"]
    storage.update_task(task_id, {
        "status": "failed",
        "error": f"Tool '{approval['tool_name']}' was rejected: {decision.comment or 'No reason provided'}"
    })

    return {"status": "rejected", "approval_id": approval_id}


# ============================================================================
# MCP Server Registry
# ============================================================================

@app.post("/admin/mcp-servers")
async def register_server(
    server_data: ServerCreate,
    credentials: HTTPAuthorizationCredentials = Depends(require_admin_permission)
):
    """Register a new MCP server."""
    try:
        server = storage.add_server(
            name=server_data.name,
            type=server_data.type,
            url=server_data.url,
            auth_token=server_data.auth_token,
            capabilities=server_data.capabilities
        )
        return server
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/admin/mcp-servers")
async def list_servers(
    enabled_only: bool = True,
    server_type: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(require_read_permission)
):
    """List registered MCP servers."""
    servers = storage.list_servers(enabled_only=enabled_only, server_type=server_type)
    return {"servers": servers}


@app.get("/admin/mcp-servers/{server_id}")
async def get_server(
    server_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(require_read_permission)
):
    """Get server by ID."""
    server = storage.get_server(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@app.delete("/admin/mcp-servers/{server_id}")
async def remove_server(
    server_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(require_admin_permission)
):
    """Remove a server from registry."""
    success = storage.remove_server(server_id)
    if not success:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"status": "removed", "server_id": server_id}


@app.patch("/admin/mcp-servers/{server_id}")
async def update_server(
    server_id: str,
    updates: dict,
    credentials: HTTPAuthorizationCredentials = Depends(require_admin_permission)
):
    """Update server properties."""
    try:
        server = storage.update_server(server_id, updates)
        return server
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# Logs
# ============================================================================

@app.get("/logs")
async def get_logs(
    task_id: Optional[str] = None,
    limit: int = 100,
    credentials: HTTPAuthorizationCredentials = Depends(require_read_permission)
):
    """Get log entries."""
    logs = storage.read_logs(task_id=task_id, limit=limit)
    return {"logs": logs}


# ============================================================================
# MCP Server Info
# ============================================================================

@app.get("/mcp/info")
async def mcp_info():
    """Return MCP server information."""
    return {
        "name": "eva-task-orchestrator",
        "version": "0.2.0",
        "description": "AI-powered task orchestration with multi-service coordination",
        "capabilities": {
            "task_execution": True,
            "approval_workflow": True,
            "multi_llm_support": True,
            "service_orchestration": True,
            "filesystem_storage": True
        },
        "llm_backends": {
            "default": settings.default_llm_backend,
            "available": ["lmstudio", "openai", "anthropic"]
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main_simple:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=True,
        log_level="info"
    )
