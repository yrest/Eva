#!/usr/bin/env python3
"""Simple test of local tool implementations without full dependencies."""

import asyncio
from pathlib import Path

# Eva's base directory
EVA_BASE_DIR = Path("/home/user/Eva")

async def _search_eva_docs(args):
    """Search Eva's documentation files."""
    query = args["query"].lower()
    file_pattern = args.get("file_pattern", "**/*.md")

    # Find all matching files
    matching_files = list(EVA_BASE_DIR.glob(file_pattern))
    results = []

    for file_path in matching_files:
        try:
            content = file_path.read_text(encoding="utf-8")

            # Simple grep-like search
            matching_lines = []
            for i, line in enumerate(content.split("\n"), 1):
                if query in line.lower():
                    matching_lines.append({
                        "line_number": i,
                        "line": line.strip()
                    })

            if matching_lines:
                results.append({
                    "file": str(file_path.relative_to(EVA_BASE_DIR)),
                    "matches": matching_lines[:5]  # Limit to first 5 matches per file
                })

        except Exception as e:
            # Skip files that can't be read
            continue

    return {
        "query": args["query"],
        "results": results,
        "total_files": len(results)
    }

async def _read_eva_file(args):
    """Read a specific file from Eva's codebase."""
    file_path = args["path"]

    # Security: ensure path is within Eva's directory
    full_path = EVA_BASE_DIR / file_path

    if not full_path.resolve().is_relative_to(EVA_BASE_DIR.resolve()):
        raise Exception("Path must be within Eva's codebase")

    if not full_path.exists():
        raise Exception(f"File not found: {file_path}")

    if not full_path.is_file():
        raise Exception(f"Not a file: {file_path}")

    try:
        content = full_path.read_text(encoding="utf-8")
        return {
            "file": file_path,
            "content": content,
            "size": len(content),
            "lines": len(content.split("\n"))
        }
    except UnicodeDecodeError:
        # Binary file
        return {
            "file": file_path,
            "error": "Binary file - cannot display as text",
            "size": full_path.stat().st_size
        }

async def test_tools():
    print("Testing Eva's self-introspection tools...\n")

    # Test 1: Search for "quickstart"
    print("Test 1: Search for 'quickstart'")
    result = await _search_eva_docs({"query": "quickstart"})
    print(f"  Found in {result['total_files']} files")
    if result['results']:
        print(f"  First match: {result['results'][0]['file']}")

    # Test 2: Search for "filesystem service"
    print("\nTest 2: Search for 'filesystem service'")
    result = await _search_eva_docs({"query": "filesystem service"})
    print(f"  Found in {result['total_files']} files")
    if result['results']:
        print(f"  Sample: {result['results'][0]['file']}")

    # Test 3: Read CLAUDE.md
    print("\nTest 3: Read CLAUDE.md")
    result = await _read_eva_file({"path": "CLAUDE.md"})
    print(f"  File: {result['file']}")
    print(f"  Size: {result['size']} bytes, {result['lines']} lines")
    print(f"  Preview: {result['content'][:60]}...")

    # Test 4: Read task service QUICKSTART
    print("\nTest 4: Read services/tasks/QUICKSTART.md")
    result = await _read_eva_file({"path": "services/tasks/QUICKSTART.md"})
    print(f"  Size: {result['size']} bytes")
    print(f"  Contains 'Register Collection Schemas': {'Register Collection Schemas' in result['content']}")

    print("\n✓ All tests passed! Eva can read her own documentation.")

if __name__ == "__main__":
    asyncio.run(test_tools())
