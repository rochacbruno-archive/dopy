"""Tests for taskmodel module."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from dopy.taskmodel import Task


class TestTaskModel:
    """Test the Task model class."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = Mock()
        db.commit = Mock()
        return db

    @pytest.fixture
    def mock_row(self):
        """Create a mock row object."""
        row = Mock()
        row.name = 'Test Task'
        row.tag = 'work'
        row.status = 'new'
        row.reminder = 'today'
        row.notes = ['Note 1', 'Note 2']
        row.update_record = Mock()
        row.delete_record = Mock()
        return row

    @pytest.fixture
    def task(self, mock_db, mock_row):
        """Create a Task instance with mocks."""
        return Task(mock_db, mock_row)

    def test_task_initialization(self, task, mock_db, mock_row):
        """Test Task initialization."""
        assert task.db == mock_db
        assert task.row == mock_row

    def test_name_getter(self, task):
        """Test getting task name."""
        assert task.name == 'Test Task'

    def test_name_setter(self, task, mock_db, mock_row):
        """Test setting task name."""
        task.name = 'New Name'
        mock_row.update_record.assert_called_once_with(name='New Name')
        mock_db.commit.assert_called_once()

    def test_tag_getter(self, task):
        """Test getting task tag."""
        assert task.tag == 'work'

    def test_tag_setter(self, task, mock_db, mock_row):
        """Test setting task tag."""
        task.tag = 'personal'
        mock_row.update_record.assert_called_once_with(tag='personal')
        mock_db.commit.assert_called_once()

    def test_status_getter(self, task):
        """Test getting task status."""
        assert task.status == 'new'

    def test_status_setter(self, task, mock_db, mock_row):
        """Test setting task status."""
        task.status = 'done'
        mock_row.update_record.assert_called_once_with(status='done')
        mock_db.commit.assert_called_once()

    def test_reminder_getter(self, task):
        """Test getting task reminder."""
        assert task.reminder == 'today'

    def test_reminder_setter(self, task, mock_db, mock_row):
        """Test setting task reminder."""
        task.reminder = 'tomorrow'
        mock_row.update_record.assert_called_once_with(reminder='tomorrow')
        mock_db.commit.assert_called_once()

    def test_notes_getter(self, task):
        """Test getting task notes."""
        assert task.notes == ['Note 1', 'Note 2']

    def test_notes_setter(self, task, mock_db, mock_row):
        """Test setting task notes."""
        new_notes = ['Updated note']
        task.notes = new_notes
        mock_row.update_record.assert_called_once_with(notes=new_notes)
        mock_db.commit.assert_called_once()

    def test_delete(self, task, mock_db, mock_row):
        """Test deleting a task."""
        task.delete()
        mock_row.delete_record.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_str_representation(self, task, mock_row):
        """Test string representation of task."""
        mock_row.__str__ = Mock(return_value='<Row {...}>')
        result = str(task)
        assert isinstance(result, str)

    def test_multiple_updates(self, task, mock_db, mock_row):
        """Test multiple property updates."""
        # Reset mocks
        mock_db.commit.reset_mock()
        mock_row.update_record.reset_mock()

        # Update multiple properties
        task.name = 'Updated Name'
        task.status = 'working'
        task.tag = 'urgent'

        # Should have called update and commit for each
        assert mock_row.update_record.call_count == 3
        assert mock_db.commit.call_count == 3

    def test_property_updates_are_committed(self, task, mock_db):
        """Test that all property updates trigger commits."""
        mock_db.commit.reset_mock()

        # Update each property
        task.name = 'New'
        task.tag = 'New'
        task.status = 'New'
        task.reminder = 'New'
        task.notes = ['New']

        # Should have 5 commits (one for each property)
        assert mock_db.commit.call_count == 5


class TestTaskDocstring:
    """Test Task class documentation."""

    def test_docstring_exists(self):
        """Test that Task class has a docstring."""
        assert Task.__doc__ is not None
        assert len(Task.__doc__) > 0

    def test_docstring_contains_usage_info(self):
        """Test that docstring contains usage information."""
        doc = Task.__doc__
        # Should mention basic operations
        assert 'task' in doc.lower() or 'print' in doc.lower()


class TestTaskEdgeCases:
    """Test edge cases for Task model."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database."""
        db = Mock()
        db.commit = Mock()
        return db

    @pytest.fixture
    def mock_row_with_none(self):
        """Create a mock row with None values."""
        row = Mock()
        row.name = None
        row.tag = None
        row.status = None
        row.reminder = None
        row.notes = None
        row.update_record = Mock()
        row.delete_record = Mock()
        return row

    def test_task_with_none_values(self, mock_db, mock_row_with_none):
        """Test Task with None values."""
        task = Task(mock_db, mock_row_with_none)
        assert task.name is None
        assert task.tag is None
        assert task.status is None
        assert task.reminder is None
        assert task.notes is None

    def test_task_with_empty_notes(self, mock_db):
        """Test Task with empty notes list."""
        row = Mock()
        row.notes = []
        row.update_record = Mock()
        task = Task(mock_db, row)
        assert task.notes == []

    def test_task_setter_with_none(self, mock_db):
        """Test setting properties to None."""
        row = Mock()
        row.update_record = Mock()
        task = Task(mock_db, row)

        task.reminder = None
        row.update_record.assert_called_with(reminder=None)
        mock_db.commit.assert_called()

    def test_task_setter_with_empty_string(self, mock_db):
        """Test setting properties to empty string."""
        row = Mock()
        row.update_record = Mock()
        task = Task(mock_db, row)

        task.name = ''
        row.update_record.assert_called_with(name='')
        mock_db.commit.assert_called()
