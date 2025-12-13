"""Task executor with approval workflow."""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from .config import settings
from .database import Approval, Execution, Task, ToolExecution
from .llm_router import LLMRouter
from .queue import TaskContextCache, TaskQueue
from .tools import SafetyLevel, tool_registry


class TaskExecutor:
    """Execute tasks with LLM and tool calls."""

    def __init__(self):
        """Initialize task executor."""
        self.queue = TaskQueue()
        self.context_cache = TaskContextCache()

    async def execute_task(self, task: Task, db: Session) -> bool:
        """
        Execute a task.

        Args:
            task: Task to execute
            db: Database session

        Returns:
            True if execution completed successfully
        """
        try:
            # Update task status
            task.status = "running"
            db.commit()

            # Create execution record
            execution = Execution(
                task_id=task.id,
                llm_backend=settings.default_llm_backend,
                llm_model="",  # Will be set by router
                conversation=[],
                tool_calls=[],
                status="running",
            )
            db.add(execution)
            db.commit()

            # Initialize LLM router
            llm_router = LLMRouter()
            execution.llm_model = llm_router.model
            db.commit()

            # Build initial conversation
            messages = self._build_initial_messages(task)
            execution.conversation = messages
            db.commit()

            # Get available tools
            tools = tool_registry.get_openai_tools()

            # Main execution loop
            max_iterations = 10
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # Call LLM
                response = await llm_router.chat_completion(
                    messages=messages,
                    tools=tools,
                )

                # Add response to conversation
                messages.append(response)
                execution.conversation = messages
                db.commit()

                # Check if LLM wants to call tools
                if not response.get("tool_calls"):
                    # No tool calls, execution complete
                    break

                # Process tool calls
                tool_results = await self._process_tool_calls(
                    response["tool_calls"],
                    execution,
                    db,
                )

                # Add tool results to conversation
                for result in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": result["tool_call_id"],
                        "content": json.dumps(result["result"]),
                    })

                execution.conversation = messages
                db.commit()

            # Mark execution as completed
            execution.status = "completed"
            execution.completed_at = datetime.utcnow()
            db.commit()

            # Update task status
            task.status = "completed"
            task.updated_at = datetime.utcnow()
            db.commit()

            # Remove from queue
            self.queue.mark_completed(str(task.id))

            return True

        except Exception as e:
            # Mark execution as failed
            if execution:
                execution.status = "failed"
                execution.error_message = str(e)
                execution.completed_at = datetime.utcnow()
                db.commit()

            # Update task status
            task.status = "failed"
            task.updated_at = datetime.utcnow()
            db.commit()

            # Remove from queue
            self.queue.mark_completed(str(task.id))

            return False

    def _build_initial_messages(self, task: Task) -> List[Dict[str, str]]:
        """Build initial conversation messages."""
        # System message
        system_message = {
            "role": "system",
            "content": (
                "You are Eva, an AI assistant helping with task automation. "
                "You have access to various tools to help complete tasks. "
                "When you need to perform an action, use the appropriate tool. "
                "Be concise and focused on the task at hand."
            ),
        }

        # User message with task details
        user_message = {
            "role": "user",
            "content": self._format_task_prompt(task),
        }

        return [system_message, user_message]

    def _format_task_prompt(self, task: Task) -> str:
        """Format task as a prompt for the LLM."""
        prompt = f"Task Type: {task.type}\n\n"

        # Add input data
        prompt += "Task Details:\n"
        for key, value in task.input_data.items():
            prompt += f"- {key}: {value}\n"

        # Add context if available
        if task.context:
            prompt += "\nAdditional Context:\n"
            for key, value in task.context.items():
                prompt += f"- {key}: {value}\n"

        prompt += "\nPlease help me complete this task."

        return prompt

    async def _process_tool_calls(
        self,
        tool_calls: List[Dict[str, Any]],
        execution: Execution,
        db: Session,
    ) -> List[Dict[str, Any]]:
        """Process tool calls with approval workflow."""
        results = []

        for tool_call in tool_calls:
            function_name = tool_call["function"]["name"]
            function_args = json.loads(tool_call["function"]["arguments"])

            # Get tool definition
            tool_def = tool_registry.get_tool(function_name)

            if not tool_def:
                results.append({
                    "tool_call_id": tool_call["id"],
                    "result": {"error": f"Unknown tool: {function_name}"},
                })
                continue

            # Check if approval is required
            if tool_def.requires_approval:
                # Create approval request
                approval = Approval(
                    execution_id=execution.id,
                    tool_name=function_name,
                    tool_params=function_args,
                    safety_level=tool_def.safety_level,
                    status="pending",
                )
                db.add(approval)
                db.commit()

                # Update execution status
                execution.status = "waiting_approval"
                db.commit()

                # For now, return a message indicating approval is needed
                # In a real system, this would pause execution
                results.append({
                    "tool_call_id": tool_call["id"],
                    "result": {
                        "status": "pending_approval",
                        "approval_id": str(approval.id),
                        "message": f"Approval required for {function_name}",
                    },
                })
                continue

            # Execute tool
            result = await self._execute_tool(
                function_name,
                function_args,
                tool_def.requires_sandbox,
                execution,
                db,
            )

            results.append({
                "tool_call_id": tool_call["id"],
                "result": result,
            })

        return results

    async def _execute_tool(
        self,
        tool_name: str,
        tool_params: Dict[str, Any],
        requires_sandbox: bool,
        execution: Execution,
        db: Session,
        approval_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Execute a tool."""
        # Create tool execution record
        tool_exec = ToolExecution(
            execution_id=execution.id,
            approval_id=approval_id,
            tool_name=tool_name,
            tool_params=tool_params,
            sandbox_used=requires_sandbox,
        )
        db.add(tool_exec)
        db.commit()

        try:
            # Get tool handler
            handler = tool_registry.get_handler(tool_name)

            if not handler:
                raise ValueError(f"No handler for tool: {tool_name}")

            # Execute tool
            result = await handler(**tool_params)

            # Update tool execution
            tool_exec.result = result
            tool_exec.completed_at = datetime.utcnow()
            db.commit()

            return result

        except Exception as e:
            # Update tool execution with error
            tool_exec.error_message = str(e)
            tool_exec.completed_at = datetime.utcnow()
            db.commit()

            return {"error": str(e)}

    async def approve_tool_call(
        self,
        approval_id: uuid.UUID,
        reviewed_by: str,
        comment: Optional[str],
        db: Session,
    ) -> bool:
        """
        Approve a tool call and execute it.

        Args:
            approval_id: Approval record ID
            reviewed_by: Reviewer identifier
            comment: Review comment
            db: Database session

        Returns:
            True if approved and executed successfully
        """
        # Get approval
        approval = db.query(Approval).filter(Approval.id == approval_id).first()

        if not approval or approval.status != "pending":
            return False

        # Update approval
        approval.status = "approved"
        approval.reviewed_at = datetime.utcnow()
        approval.reviewed_by = reviewed_by
        approval.review_comment = comment
        db.commit()

        # Get execution
        execution = db.query(Execution).filter(Execution.id == approval.execution_id).first()

        if not execution:
            return False

        # Get tool definition
        tool_def = tool_registry.get_tool(approval.tool_name)

        if not tool_def:
            return False

        # Execute the tool
        result = await self._execute_tool(
            approval.tool_name,
            approval.tool_params,
            tool_def.requires_sandbox,
            execution,
            db,
            approval_id=approval.id,
        )

        # Update execution status
        execution.status = "running"
        db.commit()

        # TODO: Resume execution with tool result
        # This would require continuing the conversation

        return True

    async def reject_tool_call(
        self,
        approval_id: uuid.UUID,
        reviewed_by: str,
        comment: Optional[str],
        db: Session,
    ) -> bool:
        """Reject a tool call."""
        # Get approval
        approval = db.query(Approval).filter(Approval.id == approval_id).first()

        if not approval or approval.status != "pending":
            return False

        # Update approval
        approval.status = "rejected"
        approval.reviewed_at = datetime.utcnow()
        approval.reviewed_by = reviewed_by
        approval.review_comment = comment
        db.commit()

        # Get execution
        execution = db.query(Execution).filter(Execution.id == approval.execution_id).first()

        if not execution:
            return False

        # Mark execution as failed
        execution.status = "failed"
        execution.error_message = f"Tool call rejected: {comment or 'No comment'}"
        execution.completed_at = datetime.utcnow()
        db.commit()

        # Update task status
        task = db.query(Task).filter(Task.id == execution.task_id).first()
        if task:
            task.status = "failed"
            task.updated_at = datetime.utcnow()
            db.commit()

        return True
