"""Main FastAPI server for task management."""

import uuid
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .auth import require_admin_permission, require_read_permission, require_write_permission
from .config import settings
from .database import Approval, Execution, Task, ToolExecution, get_db, init_db
from .executor import TaskExecutor
from .llm_router import LLMRouter
from .models import (
    ApprovalDecision,
    ApprovalListResponse,
    ApprovalResponse,
    ExecutionResponse,
    HealthResponse,
    MCPInfoResponse,
    MCPToolInfo,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    ToolExecutionResponse,
)
from .queue import TaskQueue
from .tools import tool_registry

# Import tools to register them
from .tools import execute_code, search_vectors, send_email


# Create FastAPI app
app = FastAPI(
    title="Eva Task Management Service",
    description="Autonomous task execution with approval workflow",
    version="0.1.0",
)


# Initialize on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()


# ============================================================================
# Health Check
# ============================================================================


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    # Check database
    db_healthy = True
    try:
        from .database import engine

        with engine.connect() as conn:
            conn.execute("SELECT 1")
    except Exception:
        db_healthy = False

    # Check Redis
    queue = TaskQueue()
    redis_healthy = queue.health_check()

    # Check LLM backends
    llm_backends = {}

    for backend in ["lmstudio", "openai", "anthropic"]:
        try:
            router = LLMRouter(backend=backend)
            llm_backends[backend] = await router.health_check()
        except Exception:
            llm_backends[backend] = False

    return {
        "status": "healthy" if (db_healthy and redis_healthy) else "degraded",
        "service": "tasks",
        "version": "0.1.0",
        "database": db_healthy,
        "redis": redis_healthy,
        "llm_backends": llm_backends,
    }


# ============================================================================
# Task Management
# ============================================================================


@app.post("/tasks", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    credentials: HTTPAuthorizationCredentials = Depends(require_write_permission),
    db: Session = Depends(get_db),
):
    """Create a new task."""
    # Create task
    task = Task(
        type=task_data.type,
        priority=task_data.priority,
        status="pending",
        input_data=task_data.input_data,
        context=task_data.context,
        created_by=task_data.created_by,
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    # Add to queue
    queue = TaskQueue()
    queue.enqueue(str(task.id), task.priority)

    return task


@app.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    credentials: HTTPAuthorizationCredentials = Depends(require_read_permission),
    db: Session = Depends(get_db),
):
    """List tasks with optional filters."""
    query = db.query(Task)

    if status:
        query = query.filter(Task.status == status)

    if type:
        query = query.filter(Task.type == type)

    # Get total count
    total = query.count()

    # Paginate
    tasks = (
        query.order_by(Task.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "tasks": tasks,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    credentials: HTTPAuthorizationCredentials = Depends(require_read_permission),
    db: Session = Depends(get_db),
):
    """Get task details."""
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@app.delete("/tasks/{task_id}")
async def cancel_task(
    task_id: uuid.UUID,
    credentials: HTTPAuthorizationCredentials = Depends(require_write_permission),
    db: Session = Depends(get_db),
):
    """Cancel a task."""
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Cannot cancel completed task")

    # Update status
    task.status = "failed"
    task.updated_at = datetime.utcnow()
    db.commit()

    # Remove from queue
    queue = TaskQueue()
    queue.mark_completed(str(task_id))

    return {"status": "cancelled", "task_id": str(task_id)}


# ============================================================================
# Executions
# ============================================================================


@app.get("/executions/{execution_id}", response_model=ExecutionResponse)
async def get_execution(
    execution_id: uuid.UUID,
    credentials: HTTPAuthorizationCredentials = Depends(require_read_permission),
    db: Session = Depends(get_db),
):
    """Get execution details."""
    execution = db.query(Execution).filter(Execution.id == execution_id).first()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return execution


@app.get("/executions/{execution_id}/logs")
async def get_execution_logs(
    execution_id: uuid.UUID,
    credentials: HTTPAuthorizationCredentials = Depends(require_read_permission),
    db: Session = Depends(get_db),
):
    """Get execution logs (conversation history)."""
    execution = db.query(Execution).filter(Execution.id == execution_id).first()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return {
        "execution_id": str(execution.id),
        "conversation": execution.conversation,
        "tool_calls": execution.tool_calls,
    }


# ============================================================================
# Approvals
# ============================================================================


@app.get("/approvals", response_model=ApprovalListResponse)
async def list_approvals(
    status: Optional[str] = Query("pending"),
    credentials: HTTPAuthorizationCredentials = Depends(require_read_permission),
    db: Session = Depends(get_db),
):
    """List approvals."""
    query = db.query(Approval)

    if status:
        query = query.filter(Approval.status == status)

    approvals = query.order_by(Approval.requested_at.desc()).all()

    return {
        "approvals": approvals,
        "total": len(approvals),
    }


@app.get("/approvals/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: uuid.UUID,
    credentials: HTTPAuthorizationCredentials = Depends(require_read_permission),
    db: Session = Depends(get_db),
):
    """Get approval details."""
    approval = db.query(Approval).filter(Approval.id == approval_id).first()

    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    return approval


@app.post("/approvals/{approval_id}/approve")
async def approve_action(
    approval_id: uuid.UUID,
    decision: ApprovalDecision,
    credentials: HTTPAuthorizationCredentials = Depends(require_write_permission),
    db: Session = Depends(get_db),
):
    """Approve a tool call."""
    executor = TaskExecutor()

    success = await executor.approve_tool_call(
        approval_id=approval_id,
        reviewed_by=decision.reviewed_by,
        comment=decision.comment,
        db=db,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to approve")

    return {"status": "approved", "approval_id": str(approval_id)}


@app.post("/approvals/{approval_id}/reject")
async def reject_action(
    approval_id: uuid.UUID,
    decision: ApprovalDecision,
    credentials: HTTPAuthorizationCredentials = Depends(require_write_permission),
    db: Session = Depends(get_db),
):
    """Reject a tool call."""
    executor = TaskExecutor()

    success = await executor.reject_tool_call(
        approval_id=approval_id,
        reviewed_by=decision.reviewed_by,
        comment=decision.comment,
        db=db,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to reject")

    return {"status": "rejected", "approval_id": str(approval_id)}


# ============================================================================
# Admin
# ============================================================================


@app.post("/admin/process-queue")
async def process_queue(
    max_tasks: int = Query(10, ge=1, le=100),
    credentials: HTTPAuthorizationCredentials = Depends(require_admin_permission),
    db: Session = Depends(get_db),
):
    """Process tasks from queue (manual trigger for testing)."""
    executor = TaskExecutor()
    queue = TaskQueue()

    processed = []

    for _ in range(max_tasks):
        # Get next task
        task_id = queue.dequeue()

        if not task_id:
            break

        # Get task from database
        task = db.query(Task).filter(Task.id == uuid.UUID(task_id)).first()

        if not task:
            queue.mark_completed(task_id)
            continue

        # Execute task
        success = await executor.execute_task(task, db)

        processed.append({
            "task_id": task_id,
            "success": success,
        })

    return {
        "processed": len(processed),
        "tasks": processed,
    }


# ============================================================================
# MCP Info
# ============================================================================


@app.get("/mcp/info", response_model=MCPInfoResponse)
async def mcp_info():
    """Return MCP server information."""
    # Get registered tools
    tools = []
    for tool_def in tool_registry.list_tools():
        tools.append(
            MCPToolInfo(
                name=tool_def.name,
                description=tool_def.description,
                endpoint=f"/tools/{tool_def.name}",
                permission="write" if tool_def.requires_approval else "read",
                safety_level=tool_def.safety_level,
            )
        )

    return {
        "name": "eva-tasks",
        "version": "0.1.0",
        "description": "Task management and execution with approval workflow",
        "tools": tools,
        "security": {
            "type": "bearer",
            "tokens": ["read", "write", "admin"],
            "description": "Three-tier token system (read < write < admin)",
        },
        "features": {
            "multi_llm": True,
            "approval_workflow": True,
            "tool_sandboxing": settings.docker_enabled,
            "queue_based": True,
            "data_retention": settings.archive_enabled,
        },
    }


# ============================================================================
# Run Server
# ============================================================================


if __name__ == "__main__":
    import uvicorn
    from datetime import datetime

    uvicorn.run(
        "main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True,
        log_level="info",
    )
