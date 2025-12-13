"""Pytest configuration and shared fixtures."""

import pytest
import os
from pathlib import Path


@pytest.fixture(scope="session", autouse=True)
def setup_test_env(tmp_path_factory):
    """Set up test environment variables."""
    # Create temp directory for tests
    temp_dir = tmp_path_factory.mktemp("test_data")

    # Set test environment variables
    os.environ["ALLOWED_PATHS"] = str(temp_dir)
    os.environ["READ_TOKEN"] = "test_read_token"
    os.environ["WRITE_TOKEN"] = "test_write_token"
    os.environ["JWT_SECRET"] = "test_secret"
    os.environ["SQLITE_DB_PATH"] = str(temp_dir / "test.db")
    os.environ["AUDIT_LOG_PATH"] = str(temp_dir / "audit.log")

    yield

    # Cleanup is automatic with tmp_path_factory
