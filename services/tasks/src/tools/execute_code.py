"""Execute code tool (DANGEROUS - requires sandboxing)."""

import tempfile
from pathlib import Path
from typing import Any, Dict, Literal, Optional

import docker

from ..config import settings
from . import SafetyLevel, tool_registry


async def execute_code_handler(
    code: str,
    language: Literal["python", "bash"] = "python",
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Execute code in a sandboxed Docker container.

    Args:
        code: Code to execute
        language: Programming language
        timeout: Timeout in seconds (default from config)

    Returns:
        Execution result with stdout, stderr, exit code
    """
    if not settings.docker_enabled:
        return {
            "success": False,
            "error": "Docker sandboxing is disabled",
        }

    timeout = timeout or settings.docker_timeout

    try:
        # Create temporary file for code
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py" if language == "python" else ".sh",
            delete=False,
        ) as f:
            f.write(code)
            code_file = f.name

        # Initialize Docker client
        client = docker.from_env()

        # Determine command based on language
        if language == "python":
            command = f"python /code/{Path(code_file).name}"
        else:  # bash
            command = f"bash /code/{Path(code_file).name}"

        # Run container
        container = client.containers.run(
            image=settings.sandbox_image,
            command=command,
            volumes={
                str(Path(code_file).parent): {
                    "bind": "/code",
                    "mode": "ro",
                }
            },
            network_mode=settings.docker_network,
            mem_limit=settings.docker_memory_limit,
            cpu_period=100000,
            cpu_quota=int(settings.docker_cpu_limit * 100000),
            pids_limit=100,
            read_only=True,
            tmpfs={"/tmp": "rw,size=100m"},
            user="nobody",
            detach=True,
            remove=False,
        )

        # Wait for completion
        result = container.wait(timeout=timeout)

        # Get logs
        stdout = container.logs(stdout=True, stderr=False).decode("utf-8")
        stderr = container.logs(stdout=False, stderr=True).decode("utf-8")

        # Clean up
        container.remove()
        Path(code_file).unlink()

        return {
            "success": result["StatusCode"] == 0,
            "exit_code": result["StatusCode"],
            "stdout": stdout,
            "stderr": stderr,
            "language": language,
            "timeout": timeout,
        }

    except docker.errors.ContainerError as e:
        return {
            "success": False,
            "error": "Container execution failed",
            "exit_code": e.exit_status,
            "stderr": e.stderr.decode("utf-8") if e.stderr else "",
        }

    except docker.errors.ImageNotFound:
        return {
            "success": False,
            "error": f"Docker image not found: {settings.sandbox_image}",
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Code execution error: {str(e)}",
        }


# Register tool
tool_registry.register(
    name="execute_code",
    description="Execute code in a sandboxed Docker container (Python or Bash)",
    safety_level=SafetyLevel.DANGEROUS,
    parameters={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Code to execute",
            },
            "language": {
                "type": "string",
                "enum": ["python", "bash"],
                "description": "Programming language",
                "default": "python",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds",
            },
        },
        "required": ["code"],
    },
    handler=execute_code_handler,
)
