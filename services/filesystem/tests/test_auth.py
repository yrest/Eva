"""Tests for authentication."""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.auth import AuthManager
from src.config import settings


class TestAuthManager:
    """Test suite for AuthManager."""

    @pytest.fixture
    def auth_manager(self):
        """Create an auth manager."""
        return AuthManager()

    def test_validate_read_token(self, auth_manager):
        """Test read token validation."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=settings.read_token
        )

        # Should not raise
        auth_manager.validate_token(credentials, "read")

    def test_validate_write_token(self, auth_manager):
        """Test write token validation."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=settings.write_token
        )

        # Should not raise
        auth_manager.validate_token(credentials, "write")

    def test_validate_invalid_token(self, auth_manager):
        """Test invalid token raises error."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid_token_12345"
        )

        with pytest.raises(HTTPException) as exc_info:
            auth_manager.validate_token(credentials, "read")

        assert exc_info.value.status_code == 401

    def test_read_token_cannot_write(self, auth_manager):
        """Test read token cannot perform write operations."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=settings.read_token
        )

        with pytest.raises(HTTPException) as exc_info:
            auth_manager.validate_token(credentials, "write")

        assert exc_info.value.status_code == 403

    def test_write_token_can_read(self, auth_manager):
        """Test write token can perform read operations."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=settings.write_token
        )

        # Should not raise
        auth_manager.validate_token(credentials, "read")

    def test_get_token_type_read(self, auth_manager):
        """Test getting token type for read token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=settings.read_token
        )

        token_type = auth_manager.get_token_type(credentials)
        assert token_type == "read"

    def test_get_token_type_write(self, auth_manager):
        """Test getting token type for write token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=settings.write_token
        )

        token_type = auth_manager.get_token_type(credentials)
        assert token_type == "write"
