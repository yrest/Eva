"""Tool framework for task execution."""

from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field


class SafetyLevel(IntEnum):
    """Tool safety levels."""

    READ_ONLY = 1  # No side effects (auto-approved)
    SAFE_WRITE = 2  # Create drafts (approval required)
    EXTERNAL_API = 3  # External API calls (approval required)
    DANGEROUS = 4  # Code execution, destructive ops (sandboxed + approval)


class ToolDefinition(BaseModel):
    """Tool definition."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    safety_level: SafetyLevel = Field(..., description="Safety level")
    parameters: Dict[str, Any] = Field(..., description="JSON Schema for parameters")
    requires_approval: bool = Field(..., description="Whether approval is required")
    requires_sandbox: bool = Field(False, description="Whether sandboxing is required")


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, ToolDefinition] = {}
        self._handlers: Dict[str, Callable] = {}

    def register(
        self,
        name: str,
        description: str,
        safety_level: SafetyLevel,
        parameters: Dict[str, Any],
        handler: Callable,
    ) -> None:
        """Register a tool.

        Args:
            name: Tool name
            description: Tool description
            safety_level: Safety level
            parameters: JSON Schema for parameters
            handler: Function to handle tool execution
        """
        requires_approval = safety_level > SafetyLevel.READ_ONLY
        requires_sandbox = safety_level == SafetyLevel.DANGEROUS

        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            safety_level=safety_level,
            parameters=parameters,
            requires_approval=requires_approval,
            requires_sandbox=requires_sandbox,
        )
        self._handlers[name] = handler

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get tool definition."""
        return self._tools.get(name)

    def get_handler(self, name: str) -> Optional[Callable]:
        """Get tool handler."""
        return self._handlers.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        """List all registered tools."""
        return list(self._tools.values())

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Get tools in OpenAI function calling format."""
        openai_tools = []

        for tool in self._tools.values():
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            })

        return openai_tools


# Global tool registry
tool_registry = ToolRegistry()
