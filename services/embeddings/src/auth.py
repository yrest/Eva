"""Authentication for embedding service."""

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings


# Security scheme
bearer_scheme = HTTPBearer()


class AuthManager:
    """Manages authentication for embedding operations."""

    def validate_token(self, credentials: HTTPAuthorizationCredentials) -> None:
        """
        Validate bearer token.

        Args:
            credentials: HTTP bearer credentials

        Raises:
            HTTPException: If token is invalid
        """
        token = credentials.credentials

        if token != settings.embed_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )


# Global auth manager instance
auth = AuthManager()


# Dependency for embedding operations
async def require_embed_permission(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
) -> HTTPAuthorizationCredentials:
    """Dependency that requires embed permission."""
    auth.validate_token(credentials)
    return credentials
