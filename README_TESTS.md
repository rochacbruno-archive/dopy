# Testing Guide

This document describes the test suite for the dopy project.

## Overview

The project uses `pytest` as the testing framework with comprehensive test coverage for all major components.

## Running Tests

### Quick Start

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_colors.py

# Run specific test class
uv run pytest tests/test_printtable.py::TestPrintTable

# Run specific test function
uv run pytest tests/test_do.py::TestAddFunction::test_add_basic_task
```

### Test Options

```bash
# Show local variables in failures
uv run pytest --showlocals

# Stop at first failure
uv run pytest -x

# Run only failed tests from last run
uv run pytest --lf

# Show test output even for passing tests
uv run pytest -v -s

# Run tests matching a pattern
uv run pytest -k "test_add"
```

## Test Structure

```
tests/
├── __init__.py           # Test package marker
├── conftest.py           # Shared fixtures and configuration
├── test_colors.py        # Tests for colors module (22 tests)
├── test_do.py            # Tests for do.py functions (14 tests)
├── test_printtable.py    # Tests for printtable module (33 tests)
└── test_taskmodel.py     # Tests for taskmodel module (18 tests)
```

**Total: 87 tests**

## Test Coverage by Module

### `test_colors.py` (22 tests)
Tests color formatting functions:
- `HEAD`, `FOOTER`, `REDBOLD`, `BOLD`, `ID`, `NAME`, `TAG` functions
- `NOTE` function with alternating colors
- `STATUS` function with all status types (new, done, cancel, working, post)
- Edge cases (empty strings, special characters)

### `test_printtable.py` (33 tests)
Tests ASCII table rendering:
- `cleaned()` - ANSI color code removal
- `get_column()` - Column extraction from matrix
- `max_cell_length()` - Finding maximum cell width
- `align_cell_content()` - Text alignment (left, right, center)
- `print_table_row()` - Row printing with borders
- `print_table()` - Full table rendering
- Integration tests with colored output

### `test_taskmodel.py` (18 tests)
Tests Task model class:
- Property getters and setters (name, tag, status, reminder, notes)
- Database commit behavior
- Task deletion
- String representation
- Edge cases (None values, empty strings)

### `test_do.py` (14 tests)
Tests main application functions:
- `database()` - DAL initialization and schema
- `add()` - Task creation
- `rm()` - Task deletion (soft delete)
- `done()` - Marking tasks complete
- `main()` - Command routing
- `main_entry()` - Entry point
- Configuration handling

## Shared Fixtures

Located in `tests/conftest.py`:

- `temp_dir` - Temporary directory for file operations
- `mock_database` - Mock database object
- `mock_task_row` - Mock task row with sample data
- `sample_task_data` - Dictionary of sample task data
- `capture_output` - Capture stdout/stderr

## Test Markers

Tests can be categorized with markers:

```bash
# Run only unit tests
uv run pytest -m unit

# Run only integration tests
uv run pytest -m integration

# Skip slow tests
uv run pytest -m "not slow"

# Run tests that require database
uv run pytest -m requires_db
```

Available markers:
- `unit` - Unit tests for individual components
- `integration` - Integration tests for multiple components
- `slow` - Tests that take longer to run
- `requires_db` - Tests requiring database access

## Writing New Tests

### Test File Template

```python
"""Tests for module_name."""
import pytest
from dopy.module_name import function_to_test


class TestFunctionName:
    """Test the function_name() function."""

    def test_basic_functionality(self):
        """Test basic function behavior."""
        result = function_to_test('input')
        assert result == 'expected'

    def test_edge_case(self):
        """Test edge case handling."""
        result = function_to_test('')
        assert result is not None
```

### Using Fixtures

```python
def test_with_fixture(mock_database, sample_task_data):
    """Test using shared fixtures."""
    # Use fixtures directly as parameters
    assert mock_database is not None
    assert 'name' in sample_task_data
```

### Mocking Example

```python
from unittest.mock import Mock, patch

def test_with_mocking():
    """Test using mocks."""
    import dopy.do

    # Mock global variables
    mock_db = Mock()
    mock_tasks = Mock()
    dopy.do.db = mock_db
    dopy.do.tasks = mock_tasks

    # Your test code here
```

## Pytest Configuration

Configuration is in `pytest.ini`:

- Test discovery patterns: `test_*.py`
- Verbose output by default
- Warnings filters for legacy code
- Custom markers registration

## Continuous Integration

To add CI/CD with GitHub Actions, create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12', '3.13']

    steps:
    - uses: actions/checkout@v4
    - name: Install uv
      uses: astral-sh/setup-uv@v3
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: uv sync
    - name: Run tests
      run: uv run pytest -v
```

## Test Development Tips

1. **Run tests frequently** during development
2. **Write tests first** (TDD) for new features
3. **Keep tests isolated** - no dependencies between tests
4. **Use descriptive names** - test name should describe what it tests
5. **One assert per test** when possible for clarity
6. **Mock external dependencies** (database, file system, network)
7. **Test edge cases** - empty inputs, None values, invalid data

## Known Limitations

Due to the DAL (Database Abstraction Layer) compatibility issues with Python 3:
- Some integration tests requiring actual database operations are limited
- Row object tests use mocks instead of real DAL objects
- Full end-to-end tests are pending DAL migration (see PYTHON3_MIGRATION.md)

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Python Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [PYTHON3_MIGRATION.md](PYTHON3_MIGRATION.md) - Migration status and issues
