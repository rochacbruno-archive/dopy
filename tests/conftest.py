"""Pytest configuration and shared fixtures."""

import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    dirpath = tempfile.mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath)


@pytest.fixture
def mock_database():
    """Create a mock database object."""
    db = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def mock_task_row():
    """Create a mock task row object."""
    row = Mock()
    row.id = 1
    row.name = "Test Task"
    row.tag = "default"
    row.status = "new"
    row.reminder = None
    row.notes = []
    row.created_on = Mock()
    row.deleted = False
    row.update_record = Mock()
    row.delete_record = Mock()
    return row


@pytest.fixture
def sample_task_data():
    """Provide sample task data for testing."""
    return {
        "name": "Sample Task",
        "tag": "work",
        "status": "new",
        "reminder": "today",
        "notes": ["Note 1", "Note 2"],
    }


@pytest.fixture
def capture_output():
    """Fixture to capture stdout/stderr."""
    from io import StringIO
    import sys

    old_stdout = sys.stdout
    old_stderr = sys.stderr

    stdout = StringIO()
    stderr = StringIO()

    sys.stdout = stdout
    sys.stderr = stderr

    yield stdout, stderr

    sys.stdout = old_stdout
    sys.stderr = old_stderr


# Markers for test categorization
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line(
        "markers", "requires_db: mark test as requiring database access"
    )
