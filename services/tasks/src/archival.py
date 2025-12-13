"""Data archival and retention management."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import and_
from sqlalchemy.orm import Session

from .config import settings
from .database import Task, Execution, Approval, ToolExecution


class DataArchiver:
    """Manage data archival and retention."""

    def __init__(self, archive_path: str = "./archive"):
        """Initialize data archiver.

        Args:
            archive_path: Path to archive directory
        """
        self.archive_path = Path(archive_path)
        self.archive_path.mkdir(parents=True, exist_ok=True)

    def archive_old_tasks(self, db: Session) -> Dict[str, int]:
        """
        Archive tasks older than hot storage period.

        Args:
            db: Database session

        Returns:
            Stats about archived tasks
        """
        if not settings.archive_enabled:
            return {"archived": 0, "deleted": 0}

        # Calculate cutoff dates
        hot_storage_cutoff = datetime.utcnow() - timedelta(days=settings.hot_storage_days)
        cold_storage_cutoff = datetime.utcnow() - timedelta(days=settings.cold_storage_days)

        # Archive tasks to cold storage (3-6 months old)
        tasks_to_archive = (
            db.query(Task)
            .filter(
                and_(
                    Task.created_at < hot_storage_cutoff,
                    Task.created_at >= cold_storage_cutoff,
                    Task.archived_at.is_(None),
                )
            )
            .all()
        )

        archived_count = 0

        for task in tasks_to_archive:
            # Export task data
            self._export_task(task, db)

            # Mark as archived
            task.archived_at = datetime.utcnow()
            archived_count += 1

        db.commit()

        # Delete tasks older than cold storage period
        tasks_to_delete = (
            db.query(Task)
            .filter(Task.created_at < cold_storage_cutoff)
            .all()
        )

        deleted_count = len(tasks_to_delete)

        for task in tasks_to_delete:
            # Export if not already archived
            if not task.archived_at:
                self._export_task(task, db)

            # Delete task (cascade will delete related records)
            db.delete(task)

        db.commit()

        return {
            "archived": archived_count,
            "deleted": deleted_count,
        }

    def _export_task(self, task: Task, db: Session) -> None:
        """Export task and related data to JSON file."""
        # Get related data
        executions = (
            db.query(Execution)
            .filter(Execution.task_id == task.id)
            .all()
        )

        execution_data = []

        for execution in executions:
            # Get approvals
            approvals = (
                db.query(Approval)
                .filter(Approval.execution_id == execution.id)
                .all()
            )

            # Get tool executions
            tool_executions = (
                db.query(ToolExecution)
                .filter(ToolExecution.execution_id == execution.id)
                .all()
            )

            execution_data.append({
                "id": str(execution.id),
                "llm_backend": execution.llm_backend,
                "llm_model": execution.llm_model,
                "conversation": execution.conversation,
                "tool_calls": execution.tool_calls,
                "status": execution.status,
                "error_message": execution.error_message,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "approvals": [
                    {
                        "id": str(approval.id),
                        "tool_name": approval.tool_name,
                        "tool_params": approval.tool_params,
                        "safety_level": approval.safety_level,
                        "status": approval.status,
                        "requested_at": approval.requested_at.isoformat() if approval.requested_at else None,
                        "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
                        "reviewed_by": approval.reviewed_by,
                        "review_comment": approval.review_comment,
                    }
                    for approval in approvals
                ],
                "tool_executions": [
                    {
                        "id": str(tool_exec.id),
                        "tool_name": tool_exec.tool_name,
                        "tool_params": tool_exec.tool_params,
                        "result": tool_exec.result,
                        "error_message": tool_exec.error_message,
                        "sandbox_used": tool_exec.sandbox_used,
                        "started_at": tool_exec.started_at.isoformat() if tool_exec.started_at else None,
                        "completed_at": tool_exec.completed_at.isoformat() if tool_exec.completed_at else None,
                    }
                    for tool_exec in tool_executions
                ],
            })

        # Build export data
        export_data = {
            "task": {
                "id": str(task.id),
                "type": task.type,
                "priority": task.priority,
                "status": task.status,
                "input_data": task.input_data,
                "context": task.context,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                "created_by": task.created_by,
            },
            "executions": execution_data,
            "archived_at": datetime.utcnow().isoformat(),
        }

        # Create archive directory structure (year/month)
        archive_date = task.created_at
        year_month_dir = self.archive_path / str(archive_date.year) / f"{archive_date.month:02d}"
        year_month_dir.mkdir(parents=True, exist_ok=True)

        # Write to file
        filename = year_month_dir / f"task_{task.id}.json"

        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2)

    def get_archive_stats(self) -> Dict[str, Any]:
        """Get statistics about archived data."""
        total_files = 0
        total_size = 0

        for file_path in self.archive_path.rglob("task_*.json"):
            total_files += 1
            total_size += file_path.stat().st_size

        return {
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "archive_path": str(self.archive_path),
        }

    def search_archive(
        self,
        task_type: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> List[Dict[str, Any]]:
        """Search archived tasks."""
        results = []

        for file_path in self.archive_path.rglob("task_*.json"):
            with open(file_path, "r") as f:
                data = json.load(f)

            task = data["task"]

            # Apply filters
            if task_type and task["type"] != task_type:
                continue

            task_date = datetime.fromisoformat(task["created_at"])

            if start_date and task_date < start_date:
                continue

            if end_date and task_date > end_date:
                continue

            results.append({
                "task_id": task["id"],
                "type": task["type"],
                "status": task["status"],
                "created_at": task["created_at"],
                "archived_at": data["archived_at"],
                "file_path": str(file_path),
            })

        return results
