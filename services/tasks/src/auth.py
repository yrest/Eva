"""Authentication and authorization for task service."""

from typing import Literal
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings


security = HTTPBearer()


async def verify_token(
    credentials: HTTPAuthorizationCredentials,
    required_permission: Literal["read", "write", "admin"],
) -> HTTPAuthorizationCredentials:
    """Verify bearer token has required permission level."""
    token = credentials.credentials

    # Check token validity based on permission level
    valid_tokens = {
        "read": [settings.tasks_read_token, settings.tasks_write_token, settings.tasks_admin_token],
        "write": [settings.tasks_write_token, settings.tasks_admin_token],
        "admin": [settings.tasks_admin_token],
    }

    if token not in valid_tokens[required_permission]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Invalid token for {required_permission} permission",
        )

    return credentials


async def require_read_permission(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> HTTPAuthorizationCredentials:
    """Require read permission."""
    return await verify_token(credentials, "read")


async def require_write_permission(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> HTTPAuthorizationCredentials:
    """Require write permission."""
    return await verify_token(credentials, "write")


async def require_admin_permission(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> HTTPAuthorizationCredentials:
    """Require admin permission."""
    return await verify_token(credentials, "admin")
