"""Task execution engine - orchestrates LLM and tool execution."""

import json
import asyncio
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime

from .storage import storage
from .guardrails import (
    TaskGuardrails,
    get_tool_definitions,
    get_tools_for_openai
)
from .prompts import build_system_prompt
from .llm_router import LLMRouter
from .config import settings


class ToolExecutionError(Exception):
    """Error during tool execution."""
    pass


class TaskExecutor:
    """Orchestrates task execution with LLM and tool calls."""

    def __init__(self):
        """Initialize executor."""
        self.llm = LLMRouter()
        self.guardrails = TaskGuardrails()

    async def execute_task(self, task_id: str) -> Dict:
        """
        Execute a task from start to completion.

        Args:
            task_id: Task ID to execute

        Returns:
            Task result dict
        """
        task = storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Update status to running
        storage.update_task(task_id, {"status": "running"})
        storage.log_event(task_id, "execution_started", {})

        try:
            # Get registered servers
            servers = storage.list_servers(enabled_only=True)
            servers_by_id = {s["id"]: s for s in servers}

            # Get collection schemas
            collection_schemas = storage.list_collection_schemas()

            # Build system prompt with context
            system_prompt = build_system_prompt(servers, collection_schemas)

            # Initialize conversation
            if not task["conversation"]:
                task["conversation"] = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": task["user_input"]}
                ]
                storage.update_task(task_id, {"conversation": task["conversation"]})

            # Get tool definitions
            tool_defs = get_tool_definitions()
            openai_tools = get_tools_for_openai(servers_by_id)

            # Main execution loop
            max_iterations = 50  # Prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                storage.log_event(task_id, "llm_iteration", {"iteration": iteration})

                # Get LLM response
                llm_response = await self.llm.chat_completion(
                    messages=task["conversation"],
                    tools=openai_tools,
                    backend=settings.default_llm_backend
                )

                storage.log_event(task_id, "llm_response", {
                    "has_tool_calls": bool(llm_response.get("tool_calls")),
                    "content_length": len(llm_response.get("content", ""))
                })

                # Add assistant response to conversation
                task["conversation"].append({
                    "role": "assistant",
                    "content": llm_response.get("content") or "",
                    "tool_calls": llm_response.get("tool_calls")
                })
                storage.update_task(task_id, {"conversation": task["conversation"]})

                # Validate response with guardrails
                is_valid, error_msg, response_type = self.guardrails.validate_response(
                    llm_response,
                    tool_defs,
                    servers_by_id
                )

                # Handle different response types
                if response_type == "clarification":
                    # LLM needs clarification - suspend task
                    storage.update_task(task_id, {
                        "status": "suspended",
                        "result": error_msg
                    })
                    storage.log_event(task_id, "task_suspended", {
                        "reason": "clarification_needed"
                    })
                    return {"status": "suspended", "message": error_msg}

                elif response_type == "error":
                    # Validation error - tell LLM
                    task["conversation"].append({
                        "role": "user",
                        "content": f"Error: {error_msg}. Please try again."
                    })
                    storage.update_task(task_id, {"conversation": task["conversation"]})
                    continue

                elif response_type == "message":
                    # No tool calls - task complete
                    result = llm_response.get("content", "")
                    storage.update_task(task_id, {
                        "status": "completed",
                        "result": result
                    })
                    storage.log_event(task_id, "task_completed", {})
                    return {"status": "completed", "result": result}

                elif response_type == "tool_calls":
                    # Execute tool calls
                    tool_calls = llm_response.get("tool_calls", [])

                    for tool_call in tool_calls:
                        tool_name = tool_call["function"]["name"]
                        tool_args = json.loads(tool_call["function"]["arguments"])

                        # Check if approval needed
                        if self.guardrails.requires_approval(tool_name, tool_defs):
                            # Create approval request
                            safety_level = self.guardrails.check_safety_level(tool_name, tool_defs)

                            approval = storage.create_approval(
                                task_id=task_id,
                                tool_name=tool_name,
                                tool_params=tool_args,
                                safety_level=safety_level,
                                reason=f"Tool '{tool_name}' requires approval (level: {safety_level})"
                            )

                            storage.update_task(task_id, {"status": "waiting_approval"})
                            storage.log_event(task_id, "approval_requested", {
                                "approval_id": approval["id"],
                                "tool_name": tool_name
                            })

                            return {
                                "status": "waiting_approval",
                                "approval_id": approval["id"],
                                "tool_name": tool_name
                            }

                        # Execute tool (no approval needed)
                        try:
                            result = await self.execute_tool(
                                tool_name=tool_name,
                                tool_args=tool_args,
                                servers=servers_by_id,
                                task_id=task_id
                            )

                            # Add tool result to conversation
                            task["conversation"].append({
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "name": tool_name,
                                "content": json.dumps(result)
                            })
                            storage.update_task(task_id, {"conversation": task["conversation"]})

                        except ToolExecutionError as e:
                            # Tool failed - tell LLM
                            task["conversation"].append({
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "name": tool_name,
                                "content": f"ERROR: {str(e)}"
                            })
                            storage.update_task(task_id, {"conversation": task["conversation"]})

            # Max iterations reached
            storage.update_task(task_id, {
                "status": "failed",
                "error": f"Maximum iterations ({max_iterations}) reached"
            })
            storage.log_event(task_id, "task_failed", {
                "reason": "max_iterations"
            })

            return {
                "status": "failed",
                "error": "Task execution exceeded maximum iterations"
            }

        except Exception as e:
            # Unexpected error
            storage.update_task(task_id, {
                "status": "failed",
                "error": str(e)
            })
            storage.log_event(task_id, "task_failed", {
                "reason": "exception",
                "error": str(e)
            })

            return {"status": "failed", "error": str(e)}

    async def execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        servers: Dict[str, Dict],
        task_id: str,
        max_retries: int = 3
    ) -> Dict:
        """
        Execute a tool call with retry logic.

        Args:
            tool_name: Name of the tool
            tool_args: Tool arguments
            servers: Dict of registered servers
            task_id: Task ID (for logging)
            max_retries: Maximum retry attempts

        Returns:
            Tool execution result

        Raises:
            ToolExecutionError: If tool execution fails
        """
        server_id = tool_args.pop("server_id", None)

        if not server_id or server_id not in servers:
            raise ToolExecutionError(f"Invalid or missing server_id: {server_id}")

        server = servers[server_id]

        storage.log_event(task_id, "tool_call_started", {
            "tool_name": tool_name,
            "server": server["name"],
            "server_id": server_id
        })

        # Map tool name to MCP endpoint
        endpoint_map = {
            "list_directory": "/mcp/tools/list_directory",
            "read_file": "/mcp/tools/read_file",
            "search_files": "/mcp/tools/search_files",
            "write_file": "/mcp/tools/write_file",
            "embed_text": "/mcp/tools/embed_text",
            "search_vectors": "/mcp/tools/search_vectors",
            "upsert_vectors": "/mcp/tools/upsert_vectors",
            "delete_vectors": "/mcp/tools/delete_vectors",
            "create_collection": "/mcp/tools/create_collection",
            "list_collections": "/mcp/tools/list_collections",
            "get_collection_info": "/mcp/tools/get_collection_info",
        }

        if tool_name not in endpoint_map:
            raise ToolExecutionError(f"Unknown tool: {tool_name}")

        endpoint = endpoint_map[tool_name]
        url = f"{server['url']}{endpoint}"

        # Retry loop
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        url,
                        headers={"Authorization": f"Bearer {server['auth_token']}"},
                        json=tool_args
                    )

                    response.raise_for_status()
                    result = response.json()

                    storage.log_event(task_id, "tool_call_success", {
                        "tool_name": tool_name,
                        "server": server["name"],
                        "attempt": attempt + 1
                    })

                    return result

            except Exception as e:
                if attempt == max_retries - 1:
                    # Final attempt failed
                    storage.log_event(task_id, "tool_call_failed", {
                        "tool_name": tool_name,
                        "server": server["name"],
                        "error": str(e),
                        "attempts": max_retries
                    })

                    raise ToolExecutionError(
                        f"Tool '{tool_name}' on server '{server['name']}' failed after {max_retries} attempts: {str(e)}"
                    )

                # Retry with exponential backoff
                await asyncio.sleep(2 ** attempt)

    async def resume_after_approval(self, task_id: str, approval_id: str) -> Dict:
        """
        Resume task execution after approval.

        Args:
            task_id: Task ID
            approval_id: Approval ID

        Returns:
            Task result dict
        """
        approval = storage.get_approval(approval_id)
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")

        if approval["status"] == "rejected":
            storage.update_task(task_id, {
                "status": "failed",
                "error": f"Tool '{approval['tool_name']}' was rejected by user"
            })
            return {"status": "failed", "error": "Tool execution rejected"}

        if approval["status"] != "approved":
            raise ValueError(f"Approval {approval_id} is not in approved state")

        # Get task and servers
        task = storage.get_task(task_id)
        servers = storage.list_servers(enabled_only=True)
        servers_by_id = {s["id"]: s for s in servers}

        # Execute the approved tool
        try:
            result = await self.execute_tool(
                tool_name=approval["tool_name"],
                tool_args=approval["tool_params"].copy(),
                servers=servers_by_id,
                task_id=task_id
            )

            # Add result to conversation
            task["conversation"].append({
                "role": "tool",
                "name": approval["tool_name"],
                "content": json.dumps(result)
            })
            storage.update_task(task_id, {
                "conversation": task["conversation"],
                "status": "running"
            })

            # Continue execution
            return await self.execute_task(task_id)

        except ToolExecutionError as e:
            storage.update_task(task_id, {
                "status": "failed",
                "error": str(e)
            })
            return {"status": "failed", "error": str(e)}


# Global executor instance
executor = TaskExecutor()
