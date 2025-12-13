"""Pydantic models for API requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ============================================================================
# Task Models
# ============================================================================

class TaskCreate(BaseModel):
    """Request to create a new task."""

    type: str = Field(..., description="Task type (e.g., 'email_response', 'code_fix')")
    priority: int = Field(5, ge=1, le=10, description="Priority (1=highest, 10=lowest)")
    input_data: Dict[str, Any] = Field(..., description="Task input parameters")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    created_by: Optional[str] = Field(None, description="Creator identifier")
    llm_backend: Optional[Literal["lmstudio", "openai", "anthropic"]] = Field(
        None, description="LLM backend to use (default from config)"
    )
    llm_model: Optional[str] = Field(None, description="Specific model to use")


class TaskResponse(BaseModel):
    """Task information response."""

    id: UUID
    type: str
    priority: int
    status: str
    input_data: Dict[str, Any]
    context: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime]
    created_by: Optional[str]

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """List of tasks response."""

    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# Execution Models
# ============================================================================

class ExecutionResponse(BaseModel):
    """Execution information response."""

    id: UUID
    task_id: UUID
    llm_backend: str
    llm_model: str
    conversation: List[Dict[str, Any]]
    tool_calls: List[Dict[str, Any]]
    status: str
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# Approval Models
# ============================================================================

class ApprovalResponse(BaseModel):
    """Approval information response."""

    id: UUID
    execution_id: UUID
    tool_name: str
    tool_params: Dict[str, Any]
    safety_level: int
    status: str
    requested_at: datetime
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[str]
    review_comment: Optional[str]

    class Config:
        from_attributes = True


class ApprovalDecision(BaseModel):
    """Approval decision (approve/reject)."""

    reviewed_by: str = Field(..., description="Reviewer identifier")
    comment: Optional[str] = Field(None, description="Review comment")


class ApprovalListResponse(BaseModel):
    """List of approvals response."""

    approvals: List[ApprovalResponse]
    total: int


# ============================================================================
# Tool Models
# ============================================================================

class ToolExecutionResponse(BaseModel):
    """Tool execution response."""

    id: UUID
    execution_id: UUID
    approval_id: Optional[UUID]
    tool_name: str
    tool_params: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    sandbox_used: bool
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============================================================================
# Health & Info Models
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    database: bool
    redis: bool
    llm_backends: Dict[str, bool]


class MCPToolInfo(BaseModel):
    """MCP tool information."""

    name: str
    description: str
    endpoint: str
    permission: str
    safety_level: int


class MCPInfoResponse(BaseModel):
    """MCP server information."""

    name: str
    version: str
    description: str
    tools: List[MCPToolInfo]
    security: Dict[str, Any]
    features: Dict[str, Any]
