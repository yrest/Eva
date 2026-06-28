"""Simple filesystem-based storage for Eva task management."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid


class FileStorage:
    """Filesystem-based storage for tasks, MCP servers, and logs."""

    def __init__(self, base_path: str = "./data"):
        """Initialize storage with base directory."""
        self.base = Path(base_path)
        self.base.mkdir(exist_ok=True)
        (self.base / "tasks").mkdir(exist_ok=True)
        (self.base / "approvals").mkdir(exist_ok=True)
        (self.base / "logs").mkdir(exist_ok=True)

        # Ensure registry exists
        self.registry_file = self.base / "mcp_servers.json"
        if not self.registry_file.exists():
            self.registry_file.write_text(json.dumps({"servers": []}, indent=2))

        # Ensure collection schemas file exists
        self.collections_file = self.base / "collection_schemas.json"
        if not self.collections_file.exists():
            self.collections_file.write_text(json.dumps({"collections": {}}, indent=2))

        # Ensure skills registry exists
        self.skills_file = self.base / "skills.json"
        if not self.skills_file.exists():
            self.skills_file.write_text(json.dumps({"skills": []}, indent=2))

    # ===== MCP Server Registry =====

    def list_servers(self, enabled_only: bool = True, server_type: str = None) -> List[Dict]:
        """
        Get all registered MCP servers.

        Args:
            enabled_only: Only return enabled servers
            server_type: Filter by type (filesystem, embedding, vector)

        Returns:
            List of server dictionaries
        """
        data = json.loads(self.registry_file.read_text())
        servers = data.get("servers", [])

        if enabled_only:
            servers = [s for s in servers if s.get("enabled", True)]

        if server_type:
            servers = [s for s in servers if s.get("type") == server_type]

        return servers

    def get_server(self, server_id: str) -> Optional[Dict]:
        """
        Get server by ID.

        Args:
            server_id: Server ID

        Returns:
            Server dict or None if not found
        """
        servers = self.list_servers(enabled_only=False)
        return next((s for s in servers if s["id"] == server_id), None)

    def get_server_by_name(self, name: str) -> Optional[Dict]:
        """
        Get server by name.

        Args:
            name: Server name

        Returns:
            Server dict or None if not found
        """
        servers = self.list_servers(enabled_only=False)
        return next((s for s in servers if s["name"] == name), None)

    def add_server(
        self,
        name: str,
        type: str,
        url: str,
        auth_token: str,
        capabilities: Dict[str, Any] = None
    ) -> Dict:
        """
        Register a new MCP server.

        Args:
            name: Human-readable name
            type: Server type (filesystem, embedding, vector)
            url: Base URL of the service
            auth_token: Authentication token
            capabilities: Optional capabilities dict

        Returns:
            Created server dict
        """
        data = json.loads(self.registry_file.read_text())

        # Check for duplicate name
        if any(s["name"] == name for s in data["servers"]):
            raise ValueError(f"Server with name '{name}' already exists")

        server = {
            "id": str(uuid.uuid4()),
            "name": name,
            "type": type,
            "url": url.rstrip("/"),  # Remove trailing slash
            "auth_token": auth_token,
            "capabilities": capabilities or {},
            "enabled": True,
            "registered_at": datetime.utcnow().isoformat()
        }

        data["servers"].append(server)
        self.registry_file.write_text(json.dumps(data, indent=2))

        self.log_event("system", "server_registered", {
            "server_id": server["id"],
            "name": name,
            "type": type
        })

        return server

    def update_server(self, server_id: str, updates: Dict) -> Dict:
        """
        Update server properties.

        Args:
            server_id: Server ID
            updates: Fields to update

        Returns:
            Updated server dict
        """
        data = json.loads(self.registry_file.read_text())

        for server in data["servers"]:
            if server["id"] == server_id:
                server.update(updates)
                self.registry_file.write_text(json.dumps(data, indent=2))
                return server

        raise ValueError(f"Server {server_id} not found")

    def remove_server(self, server_id: str) -> bool:
        """
        Remove server from registry.

        Args:
            server_id: Server ID

        Returns:
            True if removed, False if not found
        """
        data = json.loads(self.registry_file.read_text())
        original_count = len(data["servers"])
        data["servers"] = [s for s in data["servers"] if s["id"] != server_id]

        if len(data["servers"]) == original_count:
            return False  # Not found

        self.registry_file.write_text(json.dumps(data, indent=2))

        self.log_event("system", "server_removed", {"server_id": server_id})
        return True

    # ===== Collection Schema Registry =====

    def register_collection_schema(
        self,
        collection_name: str,
        schema: Dict[str, str],
        description: str = ""
    ) -> Dict:
        """
        Register metadata schema for a collection.

        Args:
            collection_name: Name of the collection
            schema: Field name -> field type mapping
            description: Human-readable description

        Returns:
            Collection schema dict
        """
        data = json.loads(self.collections_file.read_text())

        collection_info = {
            "name": collection_name,
            "schema": schema,
            "description": description,
            "registered_at": datetime.utcnow().isoformat()
        }

        data["collections"][collection_name] = collection_info
        self.collections_file.write_text(json.dumps(data, indent=2))

        self.log_event("system", "collection_registered", {
            "collection_name": collection_name
        })

        return collection_info

    def get_collection_schema(self, collection_name: str) -> Optional[Dict]:
        """Get schema for a collection."""
        data = json.loads(self.collections_file.read_text())
        return data["collections"].get(collection_name)

    def list_collection_schemas(self) -> Dict[str, Dict]:
        """Get all registered collection schemas."""
        data = json.loads(self.collections_file.read_text())
        return data.get("collections", {})

    def remove_collection_schema(self, collection_name: str) -> bool:
        """Remove a collection schema."""
        data = json.loads(self.collections_file.read_text())

        if collection_name not in data["collections"]:
            return False

        del data["collections"][collection_name]
        self.collections_file.write_text(json.dumps(data, indent=2))

        self.log_event("system", "collection_schema_removed", {
            "collection_name": collection_name
        })

        return True

    # ===== Skills Registry =====

    def list_skills(self, enabled_only: bool = True) -> List[Dict]:
        """Get all registered skills."""
        data = json.loads(self.skills_file.read_text())
        skills = data.get("skills", [])

        if enabled_only:
            skills = [s for s in skills if s.get("enabled", True)]

        return skills

    def get_skill(self, skill_id: str) -> Optional[Dict]:
        """Get skill by ID."""
        skills = self.list_skills(enabled_only=False)
        return next((s for s in skills if s["id"] == skill_id), None)

    def get_skill_by_name(self, name: str) -> Optional[Dict]:
        """Get skill by name."""
        skills = self.list_skills(enabled_only=False)
        return next((s for s in skills if s["name"] == name), None)

    def add_skill(
        self,
        name: str,
        description: str,
        tool_names: List[str] = None,
        senses: List[str] = None,
        triggers: List[str] = None,
    ) -> Dict:
        """Register a new skill."""
        data = json.loads(self.skills_file.read_text())

        if any(s["name"] == name for s in data["skills"]):
            raise ValueError(f"Skill with name '{name}' already exists")

        skill = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "tool_names": tool_names or [],
            "senses": senses or [],
            "triggers": triggers or [],
            "enabled": True,
            "registered_at": datetime.utcnow().isoformat()
        }

        data["skills"].append(skill)
        self.skills_file.write_text(json.dumps(data, indent=2))

        self.log_event("system", "skill_registered", {
            "skill_id": skill["id"],
            "name": name
        })

        return skill

    def update_skill(self, skill_id: str, updates: Dict) -> Dict:
        """Update skill properties."""
        data = json.loads(self.skills_file.read_text())

        for skill in data["skills"]:
            if skill["id"] == skill_id:
                skill.update(updates)
                self.skills_file.write_text(json.dumps(data, indent=2))
                return skill

        raise ValueError(f"Skill {skill_id} not found")

    def remove_skill(self, skill_id: str) -> bool:
        """Remove skill from registry."""
        data = json.loads(self.skills_file.read_text())
        original_count = len(data["skills"])
        data["skills"] = [s for s in data["skills"] if s["id"] != skill_id]

        if len(data["skills"]) == original_count:
            return False

        self.skills_file.write_text(json.dumps(data, indent=2))

        self.log_event("system", "skill_removed", {"skill_id": skill_id})
        return True

    # ===== Task Management =====

    def create_task(self, user_input: str, created_by: str = "user") -> Dict:
        """
        Create a new task.

        Args:
            user_input: The user's task description
            created_by: Who created the task

        Returns:
            Created task dict
        """
        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "user_input": user_input,
            "status": "pending",  # pending, running, waiting_approval, suspended, completed, failed
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "created_by": created_by,
            "conversation": [],
            "result": None,
            "error": None,
            "stats": {}
        }

        task_file = self.base / "tasks" / f"{task_id}.json"
        task_file.write_text(json.dumps(task, indent=2))

        self.log_event(task_id, "task_created", {
            "user_input": user_input,
            "created_by": created_by
        })

        return task

    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task dict or None if not found
        """
        task_file = self.base / "tasks" / f"{task_id}.json"
        if not task_file.exists():
            return None
        return json.loads(task_file.read_text())

    def update_task(self, task_id: str, updates: Dict) -> Dict:
        """
        Update task fields.

        Args:
            task_id: Task ID
            updates: Fields to update

        Returns:
            Updated task dict
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.update(updates)
        task["updated_at"] = datetime.utcnow().isoformat()

        task_file = self.base / "tasks" / f"{task_id}.json"
        task_file.write_text(json.dumps(task, indent=2))

        return task

    def add_message(self, task_id: str, role: str, content: str, tool_calls: List = None):
        """
        Add a message to task conversation.

        Args:
            task_id: Task ID
            role: Message role (system, user, assistant, tool)
            content: Message content
            tool_calls: Optional tool calls
        """
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        message = {"role": role, "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls

        task["conversation"].append(message)
        self.update_task(task_id, {"conversation": task["conversation"]})

    def list_tasks(self, status: str = None, limit: int = 100) -> List[Dict]:
        """
        List all tasks, optionally filtered by status.

        Args:
            status: Filter by status (pending, running, completed, etc.)
            limit: Maximum tasks to return

        Returns:
            List of task dicts
        """
        tasks = []
        for task_file in (self.base / "tasks").glob("*.json"):
            task = json.loads(task_file.read_text())
            if status is None or task["status"] == status:
                tasks.append(task)

        # Sort by created_at descending
        tasks.sort(key=lambda t: t["created_at"], reverse=True)
        return tasks[:limit]

    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task.

        Args:
            task_id: Task ID

        Returns:
            True if deleted, False if not found
        """
        task_file = self.base / "tasks" / f"{task_id}.json"
        if not task_file.exists():
            return False

        task_file.unlink()
        self.log_event(task_id, "task_deleted", {})
        return True

    # ===== Approval Management =====

    def create_approval(
        self,
        task_id: str,
        tool_name: str,
        tool_params: Dict,
        safety_level: str,
        reason: str = None
    ) -> Dict:
        """
        Create an approval request.

        Args:
            task_id: Associated task ID
            tool_name: Name of tool requiring approval
            tool_params: Tool parameters
            safety_level: Safety level (SAFE_WRITE, EXTERNAL_API, DANGEROUS)
            reason: Optional reason for approval

        Returns:
            Created approval dict
        """
        approval_id = str(uuid.uuid4())
        approval = {
            "id": approval_id,
            "task_id": task_id,
            "tool_name": tool_name,
            "tool_params": tool_params,
            "safety_level": safety_level,
            "reason": reason,
            "status": "pending",  # pending, approved, rejected
            "requested_at": datetime.utcnow().isoformat(),
            "reviewed_at": None,
            "reviewed_by": None,
            "review_comment": None
        }

        approval_file = self.base / "approvals" / f"{approval_id}.json"
        approval_file.write_text(json.dumps(approval, indent=2))

        self.log_event(task_id, "approval_requested", {
            "approval_id": approval_id,
            "tool_name": tool_name,
            "safety_level": safety_level
        })

        return approval

    def get_approval(self, approval_id: str) -> Optional[Dict]:
        """Get approval by ID."""
        approval_file = self.base / "approvals" / f"{approval_id}.json"
        if not approval_file.exists():
            return None
        return json.loads(approval_file.read_text())

    def update_approval(self, approval_id: str, updates: Dict) -> Dict:
        """Update approval."""
        approval = self.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")

        approval.update(updates)

        approval_file = self.base / "approvals" / f"{approval_id}.json"
        approval_file.write_text(json.dumps(approval, indent=2))

        return approval

    def list_approvals(self, status: str = "pending", task_id: str = None) -> List[Dict]:
        """List approvals, optionally filtered."""
        approvals = []
        for approval_file in (self.base / "approvals").glob("*.json"):
            approval = json.loads(approval_file.read_text())

            if status and approval["status"] != status:
                continue

            if task_id and approval["task_id"] != task_id:
                continue

            approvals.append(approval)

        # Sort by requested_at descending
        approvals.sort(key=lambda a: a["requested_at"], reverse=True)
        return approvals

    # ===== Logging =====

    def log_event(self, task_id: str, event: str, data: Dict = None):
        """
        Append event to log file.

        Args:
            task_id: Task ID (or "system" for system events)
            event: Event type
            data: Additional event data
        """
        log_file = self.base / "logs" / "tasks.jsonl"

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "event": event
        }

        if data:
            log_entry.update(data)

        with log_file.open("a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def read_logs(self, task_id: str = None, limit: int = 100) -> List[Dict]:
        """
        Read log entries.

        Args:
            task_id: Filter by task ID
            limit: Maximum entries to return

        Returns:
            List of log entries (most recent first)
        """
        log_file = self.base / "logs" / "tasks.jsonl"
        if not log_file.exists():
            return []

        logs = []
        with log_file.open("r") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if task_id is None or entry.get("task_id") == task_id:
                        logs.append(entry)

        # Return most recent first
        logs.reverse()
        return logs[:limit]


# Global storage instance
storage = FileStorage()
