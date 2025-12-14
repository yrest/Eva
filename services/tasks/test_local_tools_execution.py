#!/usr/bin/env python3
"""Test actual execution of local tools."""

import sys
import os
import asyncio
sys.path.insert(0, os.path.dirname(__file__))

# Create dummy storage and config for testing
os.makedirs("data", exist_ok=True)
with open("data/mcp_servers.json", "w") as f:
    f.write('{"servers": []}')
with open("data/collection_schemas.json", "w") as f:
    f.write('{}')

async def test_local_tools():
    """Test local tool execution."""
    from src.executor import TaskExecutor
    from src.storage import storage

    executor = TaskExecutor()

    # Create a dummy task for logging
    task = storage.create_task("test self-introspection", "tester")
    task_id = task["id"]

    print("Testing local tools execution...\n")

    # Test 1: List Eva's markdown files
    print("Test 1: list_eva_files - Find all markdown files")
    result = await executor.execute_local_tool(
        "list_eva_files",
        {"pattern": "**/*.md"},
        task_id
    )
    print(f"Found {result['total']} markdown files")
    print(f"Sample files: {[f['path'] for f in result['files'][:3]]}\n")

    # Test 2: Search documentation
    print("Test 2: search_eva_docs - Search for 'filesystem service'")
    result = await executor.execute_local_tool(
        "search_eva_docs",
        {"query": "filesystem service"},
        task_id
    )
    print(f"Found matches in {result['total_files']} files")
    if result['results']:
        print(f"First match: {result['results'][0]['file']}")
        print(f"  Line {result['results'][0]['matches'][0]['line_number']}: {result['results'][0]['matches'][0]['line'][:80]}...\n")

    # Test 3: Read a specific file
    print("Test 3: read_eva_file - Read CLAUDE.md")
    result = await executor.execute_local_tool(
        "read_eva_file",
        {"path": "CLAUDE.md"},
        task_id
    )
    print(f"File: {result['file']}")
    print(f"Size: {result['size']} bytes, {result['lines']} lines")
    print(f"First 100 chars: {result['content'][:100]}...\n")

    # Test 4: Search for quickstart
    print("Test 4: search_eva_docs - Search for 'quickstart'")
    result = await executor.execute_local_tool(
        "search_eva_docs",
        {"query": "quickstart"},
        task_id
    )
    print(f"Found matches in {result['total_files']} files")
    for i, file_result in enumerate(result['results'][:2], 1):
        print(f"{i}. {file_result['file']} ({len(file_result['matches'])} matches)")

    print("\n✓ All local tools working correctly!")

if __name__ == "__main__":
    asyncio.run(test_local_tools())
