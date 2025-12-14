#!/usr/bin/env python3
"""Quick test to verify local tools are registered."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.guardrails import get_tool_definitions

def test_local_tools():
    """Test that local tools are registered correctly."""
    tools = get_tool_definitions()

    # Check local tools exist
    local_tools = ["search_eva_docs", "read_eva_file", "list_eva_files"]

    print("Checking tool registration...")
    for tool_name in local_tools:
        assert tool_name in tools, f"Tool {tool_name} not found!"
        tool_def = tools[tool_name]

        # Verify they don't require servers
        assert not tool_def.get("requires_server"), f"{tool_name} should not require server!"

        # Verify they're READ_ONLY
        assert tool_def.get("safety_level") == "READ_ONLY", f"{tool_name} should be READ_ONLY!"

        print(f"✓ {tool_name}: {tool_def['description']}")

    # Count all tools
    remote_tools = [t for t in tools if tools[t].get("requires_server")]
    local_tools_found = [t for t in tools if not tools[t].get("requires_server")]

    print(f"\nTotal tools: {len(tools)}")
    print(f"Remote tools (require server_id): {len(remote_tools)}")
    print(f"Local tools (self-introspection): {len(local_tools_found)}")

    print("\nLocal tools:")
    for tool in local_tools_found:
        print(f"  - {tool}: {tools[tool]['required_params']}")

    print("\n✓ All tests passed!")

if __name__ == "__main__":
    test_local_tools()
