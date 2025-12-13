"""Tests for security validation."""

import pytest
from pathlib import Path
from fastapi import HTTPException

from src.security import SecurityValidator
from src.config import settings


class TestSecurityValidator:
    """Test suite for SecurityValidator."""

    @pytest.fixture
    def validator(self, tmp_path):
        """Create a security validator with temp allowed paths."""
        # Mock settings
        original_paths = settings.allowed_paths
        settings.allowed_paths = str(tmp_path)

        validator = SecurityValidator()

        yield validator

        # Restore settings
        settings.allowed_paths = original_paths

    def test_validate_read_path_success(self, validator, tmp_path):
        """Test successful path validation for read."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        result = validator.validate_read_path(str(test_file))
        assert result == test_file.resolve()

    def test_validate_read_path_outside_allowed(self, validator, tmp_path):
        """Test path validation fails for paths outside allowed dirs."""
        outside_path = "/tmp/outside/test.txt"

        with pytest.raises(HTTPException) as exc_info:
            validator.validate_read_path(outside_path)

        assert exc_info.value.status_code == 403

    def test_validate_read_path_not_exists(self, validator, tmp_path):
        """Test path validation fails for non-existent files."""
        non_existent = tmp_path / "does_not_exist.txt"

        with pytest.raises(HTTPException) as exc_info:
            validator.validate_read_path(str(non_existent))

        assert exc_info.value.status_code == 404

    def test_validate_write_path_success(self, validator, tmp_path):
        """Test successful path validation for write."""
        test_file = tmp_path / "new_file.txt"

        result = validator.validate_write_path(str(test_file))
        assert result == test_file.resolve()

    def test_validate_write_path_outside_allowed(self, validator, tmp_path):
        """Test write validation fails for paths outside allowed dirs."""
        outside_path = "/tmp/outside/test.txt"

        with pytest.raises(HTTPException) as exc_info:
            validator.validate_write_path(outside_path)

        assert exc_info.value.status_code == 403

    def test_validate_file_size_success(self, validator):
        """Test file size validation passes for small files."""
        # Should not raise
        validator.validate_file_size(1024)  # 1KB

    def test_validate_file_size_too_large(self, validator):
        """Test file size validation fails for large files."""
        # Exceed max size
        too_large = settings.max_file_size_bytes + 1

        with pytest.raises(HTTPException) as exc_info:
            validator.validate_file_size(too_large)

        assert exc_info.value.status_code == 413
