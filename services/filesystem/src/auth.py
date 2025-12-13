"""Authentication and authorization for filesystem operations."""

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Literal

from .config import settings


# Token types
TokenType = Literal["read", "write"]

# Security scheme
bearer_scheme = HTTPBearer()


class AuthManager:
    """Manages authentication tokens and permissions."""

    def validate_token(
        self,
        credentials: HTTPAuthorizationCredentials,
        required_permission: TokenType
    ) -> None:
        """
        Validate bearer token and check permissions.

        Args:
            credentials: HTTP bearer credentials
            required_permission: Required permission level ('read' or 'write')

        Raises:
            HTTPException: If token is invalid or lacks permission
        """
        token = credentials.credentials

        # Check if token is valid
        is_read_token = token == settings.read_token
        is_write_token = token == settings.write_token

        if not (is_read_token or is_write_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check permission level
        if required_permission == "write" and not is_write_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Write permission required. Current token only has read access.",
            )

    def get_token_type(self, credentials: HTTPAuthorizationCredentials) -> TokenType:
        """
        Determine the type of token provided.

        Args:
            credentials: HTTP bearer credentials

        Returns:
            Token type ('read' or 'write')
        """
        token = credentials.credentials

        if token == settings.write_token:
            return "write"
        elif token == settings.read_token:
            return "read"
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )


# Global auth manager instance
auth = AuthManager()


# Dependency for read operations
async def require_read_permission(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
) -> HTTPAuthorizationCredentials:
    """Dependency that requires read permission."""
    auth.validate_token(credentials, "read")
    return credentials


# Dependency for write operations
async def require_write_permission(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
) -> HTTPAuthorizationCredentials:
    """Dependency that requires write permission."""
    auth.validate_token(credentials, "write")
    return credentials
