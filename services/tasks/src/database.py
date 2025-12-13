"""Database models and session management."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func

from .config import settings


# Database setup
engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Database Models
# ============================================================================


class Task(Base):
    """Task model."""

    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(100), nullable=False, index=True)
    priority = Column(Integer, default=5, nullable=False)
    status = Column(
        String(50),
        default="pending",
        nullable=False,
        index=True,
    )  # pending, running, waiting_approval, completed, failed
    input_data = Column(JSONB, nullable=False)
    context = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    archived_at = Column(DateTime(timezone=True))
    created_by = Column(String(255))

    # Relationships
    executions = relationship("Execution", back_populates="task", cascade="all, delete-orphan")


class Execution(Base):
    """Execution model."""

    __tablename__ = "executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    llm_backend = Column(
        String(50), nullable=False
    )  # lmstudio, openai, anthropic
    llm_model = Column(String(100), nullable=False)
    conversation = Column(JSONB, default=list, nullable=False)
    tool_calls = Column(JSONB, default=list, nullable=False)
    status = Column(
        String(50), default="running", nullable=False
    )  # running, waiting_approval, completed, failed
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    task = relationship("Task", back_populates="executions")
    approvals = relationship("Approval", back_populates="execution", cascade="all, delete-orphan")
    tool_executions = relationship(
        "ToolExecution", back_populates="execution", cascade="all, delete-orphan"
    )


class Approval(Base):
    """Approval model."""

    __tablename__ = "approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("executions.id"), nullable=False)
    tool_name = Column(String(100), nullable=False)
    tool_params = Column(JSONB, nullable=False)
    safety_level = Column(Integer, nullable=False)  # 1-4
    status = Column(
        String(50), default="pending", nullable=False, index=True
    )  # pending, approved, rejected
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True))
    reviewed_by = Column(String(255))
    review_comment = Column(Text)

    # Relationships
    execution = relationship("Execution", back_populates="approvals")
    tool_executions = relationship("ToolExecution", back_populates="approval")


class ToolExecution(Base):
    """Tool execution model."""

    __tablename__ = "tool_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("executions.id"), nullable=False)
    approval_id = Column(UUID(as_uuid=True), ForeignKey("approvals.id"))
    tool_name = Column(String(100), nullable=False)
    tool_params = Column(JSONB, nullable=False)
    result = Column(JSONB)
    error_message = Column(Text)
    sandbox_used = Column(Boolean, default=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    execution = relationship("Execution", back_populates="tool_executions")
    approval = relationship("Approval", back_populates="tool_executions")


# ============================================================================
# Database Initialization
# ============================================================================


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def drop_db():
    """Drop all database tables (use with caution!)."""
    Base.metadata.drop_all(bind=engine)
