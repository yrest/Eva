#!/usr/bin/env python3
"""CLI for Eva Task Management Service."""

import argparse
import json
import sys
from datetime import datetime
from typing import Optional

import httpx

# Default configuration
DEFAULT_BASE_URL = "http://localhost:8008"
DEFAULT_TOKEN = ""  # Should be set via environment or argument


class TaskCLI:
    """CLI client for task management service."""

    def __init__(self, base_url: str, token: str):
        """Initialize CLI client.

        Args:
            base_url: Base URL of task service
            token: Authentication token
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    def create_task(
        self,
        task_type: str,
        input_data: dict,
        priority: int = 5,
        created_by: Optional[str] = None,
    ) -> dict:
        """Create a new task."""
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/tasks",
                headers=self.headers,
                json={
                    "type": task_type,
                    "priority": priority,
                    "input_data": input_data,
                    "created_by": created_by,
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to create task: {response.text}")

    def list_tasks(self, status: Optional[str] = None) -> dict:
        """List tasks."""
        params = {}
        if status:
            params["status"] = status

        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/tasks",
                headers=self.headers,
                params=params,
                timeout=10.0,
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to list tasks: {response.text}")

    def get_task(self, task_id: str) -> dict:
        """Get task details."""
        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/tasks/{task_id}",
                headers=self.headers,
                timeout=10.0,
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to get task: {response.text}")

    def list_approvals(self, status: str = "pending") -> dict:
        """List approvals."""
        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/approvals",
                headers=self.headers,
                params={"status": status},
                timeout=10.0,
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to list approvals: {response.text}")

    def approve(self, approval_id: str, reviewed_by: str, comment: Optional[str] = None) -> dict:
        """Approve a tool call."""
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/approvals/{approval_id}/approve",
                headers=self.headers,
                json={
                    "reviewed_by": reviewed_by,
                    "comment": comment,
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to approve: {response.text}")

    def reject(self, approval_id: str, reviewed_by: str, comment: Optional[str] = None) -> dict:
        """Reject a tool call."""
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/approvals/{approval_id}/reject",
                headers=self.headers,
                json={
                    "reviewed_by": reviewed_by,
                    "comment": comment,
                },
                timeout=10.0,
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to reject: {response.text}")

    def process_queue(self, max_tasks: int = 10) -> dict:
        """Process tasks from queue (admin only)."""
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/admin/process-queue",
                headers=self.headers,
                params={"max_tasks": max_tasks},
                timeout=60.0,
            )

            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to process queue: {response.text}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Eva Task Management CLI")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Base URL of task service",
    )
    parser.add_argument(
        "--token",
        default=DEFAULT_TOKEN,
        help="Authentication token",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create task
    create_parser = subparsers.add_parser("create", help="Create a new task")
    create_parser.add_argument("type", help="Task type")
    create_parser.add_argument("input_data", help="Input data (JSON string)")
    create_parser.add_argument("--priority", type=int, default=5, help="Priority (1-10)")
    create_parser.add_argument("--created-by", help="Creator identifier")

    # List tasks
    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument("--status", help="Filter by status")

    # Get task
    get_parser = subparsers.add_parser("get", help="Get task details")
    get_parser.add_argument("task_id", help="Task ID")

    # List approvals
    approvals_parser = subparsers.add_parser("approvals", help="List approvals")
    approvals_parser.add_argument("--status", default="pending", help="Filter by status")

    # Approve
    approve_parser = subparsers.add_parser("approve", help="Approve a tool call")
    approve_parser.add_argument("approval_id", help="Approval ID")
    approve_parser.add_argument("--reviewed-by", required=True, help="Reviewer identifier")
    approve_parser.add_argument("--comment", help="Review comment")

    # Reject
    reject_parser = subparsers.add_parser("reject", help="Reject a tool call")
    reject_parser.add_argument("approval_id", help="Approval ID")
    reject_parser.add_argument("--reviewed-by", required=True, help="Reviewer identifier")
    reject_parser.add_argument("--comment", help="Review comment")

    # Process queue
    process_parser = subparsers.add_parser("process", help="Process task queue (admin)")
    process_parser.add_argument("--max-tasks", type=int, default=10, help="Max tasks to process")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize CLI client
    cli = TaskCLI(args.base_url, args.token)

    try:
        # Execute command
        if args.command == "create":
            input_data = json.loads(args.input_data)
            result = cli.create_task(
                args.type,
                input_data,
                args.priority,
                args.created_by,
            )
            print(json.dumps(result, indent=2))

        elif args.command == "list":
            result = cli.list_tasks(args.status)
            print(json.dumps(result, indent=2))

        elif args.command == "get":
            result = cli.get_task(args.task_id)
            print(json.dumps(result, indent=2))

        elif args.command == "approvals":
            result = cli.list_approvals(args.status)
            print(json.dumps(result, indent=2))

        elif args.command == "approve":
            result = cli.approve(
                args.approval_id,
                args.reviewed_by,
                args.comment,
            )
            print(json.dumps(result, indent=2))

        elif args.command == "reject":
            result = cli.reject(
                args.approval_id,
                args.reviewed_by,
                args.comment,
            )
            print(json.dumps(result, indent=2))

        elif args.command == "process":
            result = cli.process_queue(args.max_tasks)
            print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
