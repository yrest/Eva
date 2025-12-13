"""Authentication and authorization for vector operations."""

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Literal

from .config import settings


# Token types
TokenType = Literal["query", "update"]

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
            required_permission: Required permission level ('query' or 'update')

        Raises:
            HTTPException: If token is invalid or lacks permission
        """
        token = credentials.credentials

        # Check if token is valid
        is_query_token = token == settings.query_token
        is_update_token = token == settings.update_token

        if not (is_query_token or is_update_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check permission level
        if required_permission == "update" and not is_update_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Update permission required. Current token only has query access.",
            )

    def get_token_type(self, credentials: HTTPAuthorizationCredentials) -> TokenType:
        """
        Determine the type of token provided.

        Args:
            credentials: HTTP bearer credentials

        Returns:
            Token type ('query' or 'update')
        """
        token = credentials.credentials

        if token == settings.update_token:
            return "update"
        elif token == settings.query_token:
            return "query"
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )


# Global auth manager instance
auth = AuthManager()


# Dependency for query operations
async def require_query_permission(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
) -> HTTPAuthorizationCredentials:
    """Dependency that requires query permission."""
    auth.validate_token(credentials, "query")
    return credentials


# Dependency for update operations
async def require_update_permission(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)
) -> HTTPAuthorizationCredentials:
    """Dependency that requires update permission."""
    auth.validate_token(credentials, "update")
    return credentials
