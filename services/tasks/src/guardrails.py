"""Guardrails for validating LLM plans before execution."""

from typing import List, Dict, Any, Tuple, Optional


class TaskGuardrails:
    """Validate LLM plans to ensure they're safe and executable."""

    # Phrases that indicate LLM needs clarification
    CLARIFICATION_PHRASES = [
        "unclear",
        "need more information",
        "can you clarify",
        "which",
        "not sure",
        "could you specify",
        "please provide",
        "what do you mean",
        "ambiguous"
    ]

    @staticmethod
    def validate_tool_calls(
        tool_calls: List[Dict],
        available_tools: Dict[str, Dict],
        registered_servers: Dict[str, Dict]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate tool calls from LLM response.

        Args:
            tool_calls: List of tool calls from LLM
            available_tools: Dict of available tool definitions
            registered_servers: Dict of registered MCP servers

        Returns:
            (is_valid, error_message)
        """
        if not tool_calls:
            return True, None

        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name")
            if not tool_name:
                return False, "Tool call missing function name"

            # Check if tool exists
            if tool_name not in available_tools:
                return False, f"Unknown tool: {tool_name}"

            tool_def = available_tools[tool_name]

            # Parse arguments
            try:
                import json
                args = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
            except json.JSONDecodeError:
                return False, f"Invalid JSON in tool arguments for {tool_name}"

            # Check required parameters
            required = tool_def.get("required_params", [])
            missing = set(required) - set(args.keys())
            if missing:
                return False, f"Missing required parameters for {tool_name}: {missing}"

            # Check server parameter if needed
            if tool_def.get("requires_server"):
                server_id = args.get("server_id")
                if not server_id:
                    return False, f"Tool {tool_name} requires 'server_id' parameter"

                if server_id not in registered_servers:
                    return False, f"Unknown server: {server_id}"

                server = registered_servers[server_id]
                if not server.get("enabled"):
                    return False, f"Server {server['name']} is disabled"

        return True, None

    @staticmethod
    def check_for_clarification(content: str) -> bool:
        """
        Check if LLM is asking for clarification.

        Args:
            content: LLM response content

        Returns:
            True if clarification needed
        """
        content_lower = content.lower()
        return any(phrase in content_lower for phrase in TaskGuardrails.CLARIFICATION_PHRASES)

    @staticmethod
    def validate_response(
        response: Dict,
        available_tools: Dict[str, Dict],
        registered_servers: Dict[str, Dict]
    ) -> Tuple[bool, Optional[str], str]:
        """
        Validate complete LLM response.

        Args:
            response: LLM response dict
            available_tools: Available tool definitions
            registered_servers: Registered MCP servers

        Returns:
            (is_valid, error_or_clarification, response_type)
            response_type: "tool_calls", "clarification", "message", "error"
        """
        content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])

        # Check if asking for clarification
        if TaskGuardrails.check_for_clarification(content):
            return False, content, "clarification"

        # Check if there are tool calls to validate
        if tool_calls:
            is_valid, error = TaskGuardrails.validate_tool_calls(
                tool_calls,
                available_tools,
                registered_servers
            )

            if not is_valid:
                return False, error, "error"

            return True, None, "tool_calls"

        # Just a message, no actions
        return True, None, "message"

    @staticmethod
    def check_safety_level(tool_name: str, tool_definitions: Dict[str, Dict]) -> str:
        """
        Get safety level for a tool.

        Args:
            tool_name: Name of the tool
            tool_definitions: Tool definitions

        Returns:
            Safety level: "READ_ONLY", "SAFE_WRITE", "EXTERNAL_API", "DANGEROUS"
        """
        tool_def = tool_definitions.get(tool_name, {})
        return tool_def.get("safety_level", "DANGEROUS")  # Default to most restrictive

    @staticmethod
    def requires_approval(tool_name: str, tool_definitions: Dict[str, Dict]) -> bool:
        """
        Check if tool requires approval.

        Args:
            tool_name: Name of the tool
            tool_definitions: Tool definitions

        Returns:
            True if approval required
        """
        safety_level = TaskGuardrails.check_safety_level(tool_name, tool_definitions)
        # Only READ_ONLY tools are auto-approved
        return safety_level != "READ_ONLY"


# Tool definitions with safety levels
TOOL_DEFINITIONS = {
    "list_directory": {
        "description": "List files in a directory on a filesystem server",
        "requires_server": True,
        "required_params": ["server_id", "path"],
        "optional_params": ["recursive", "include_hidden", "max_depth"],
        "safety_level": "READ_ONLY"
    },
    "read_file": {
        "description": "Read file content from a filesystem server",
        "requires_server": True,
        "required_params": ["server_id", "path"],
        "optional_params": ["include_hash", "update_index"],
        "safety_level": "READ_ONLY"
    },
    "search_files": {
        "description": "Search for files by path pattern",
        "requires_server": True,
        "required_params": ["server_id", "query"],
        "optional_params": ["limit"],
        "safety_level": "READ_ONLY"
    },
    "embed_text": {
        "description": "Generate embedding vector from text using embedding service",
        "requires_server": True,
        "required_params": ["server_id", "text"],
        "optional_params": ["chunk_enabled", "chunk_size", "return_chunks"],
        "safety_level": "READ_ONLY"
    },
    "search_vectors": {
        "description": "Search vector database for similar items",
        "requires_server": True,
        "required_params": ["server_id", "collection", "query_vector"],
        "optional_params": ["limit", "score_threshold", "filter_conditions"],
        "safety_level": "READ_ONLY"
    },
    "upsert_vectors": {
        "description": "Insert or update vectors in vector database",
        "requires_server": True,
        "required_params": ["server_id", "collection", "points"],
        "optional_params": [],
        "safety_level": "SAFE_WRITE"
    },
    "create_collection": {
        "description": "Create a new vector collection",
        "requires_server": True,
        "required_params": ["server_id", "name", "vector_size"],
        "optional_params": ["distance"],
        "safety_level": "SAFE_WRITE"
    },
    "write_file": {
        "description": "Write content to a file on filesystem server",
        "requires_server": True,
        "required_params": ["server_id", "path", "content"],
        "optional_params": ["is_binary", "create_parents", "overwrite"],
        "safety_level": "DANGEROUS"
    },
    "delete_vectors": {
        "description": "Delete vectors from collection",
        "requires_server": True,
        "required_params": ["server_id", "collection"],
        "optional_params": ["point_ids", "filter_conditions"],
        "safety_level": "DANGEROUS"
    }
}


def get_tool_definitions() -> Dict[str, Dict]:
    """Get all tool definitions."""
    return TOOL_DEFINITIONS


def get_tools_for_openai(registered_servers: Dict[str, Dict]) -> List[Dict]:
    """
    Convert tool definitions to OpenAI function calling format.

    Args:
        registered_servers: Dict of registered servers by ID

    Returns:
        List of tool definitions for OpenAI API
    """
    tools = []

    for tool_name, tool_def in TOOL_DEFINITIONS.items():
        # Build parameters schema
        properties = {}
        required = []

        # Add server_id parameter if needed
        if tool_def.get("requires_server"):
            properties["server_id"] = {
                "type": "string",
                "description": f"Server ID to execute on. Available: {list(registered_servers.keys())}",
                "enum": list(registered_servers.keys())
            }
            required.append("server_id")

        # Add tool-specific required params
        for param in tool_def.get("required_params", []):
            if param == "server_id":
                continue  # Already added

            # Infer type from param name (simple heuristic)
            param_type = "string"
            if param in ["limit", "max_depth", "vector_size", "chunk_size"]:
                param_type = "integer"
            elif param in ["recursive", "include_hidden", "update_index", "chunk_enabled", "return_chunks", "is_binary", "create_parents", "overwrite"]:
                param_type = "boolean"
            elif param in ["query_vector", "points"]:
                param_type = "array"
            elif param in ["filter_conditions"]:
                param_type = "object"

            properties[param] = {
                "type": param_type,
                "description": f"Parameter: {param}"
            }
            required.append(param)

        # Add optional params
        for param in tool_def.get("optional_params", []):
            if param in properties:
                continue

            param_type = "string"
            if param in ["limit", "max_depth", "vector_size", "chunk_size"]:
                param_type = "integer"
            elif param in ["recursive", "include_hidden", "update_index", "chunk_enabled", "return_chunks", "is_binary", "create_parents", "overwrite"]:
                param_type = "boolean"

            properties[param] = {
                "type": param_type,
                "description": f"Optional parameter: {param}"
            }

        tools.append({
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_def["description"],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        })

    return tools
