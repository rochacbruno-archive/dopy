"""Tests for taskmodel module."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from pydantic import ValidationError
from dolist.taskmodel import Task


class TestTaskModel:
    """Test the Task model class with Pydantic."""

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
        row.id = 1
        row.name = 'Test Task'
        row.tag = 'work'
        row.status = 'new'
        row.reminder = 'today'
        row.reminder_repeat = None
        row.notes = ['Note 1', 'Note 2']
        row.created_on = datetime(2024, 1, 1, 12, 0, 0)
        row.deleted = False
        row.priority = 0
        row.size = 'U'
        row.update_record = Mock()
        row.delete_record = Mock()
        # Make .get() method work
        row.get = lambda k, d=None: getattr(row, k, d)
        return row

    @pytest.fixture
    def task(self, mock_db, mock_row):
        """Create a Task instance with mocks."""
        return Task.from_row(mock_db, mock_row)

    def test_task_initialization_from_row(self, mock_db, mock_row):
        """Test Task initialization from database row."""
        task = Task.from_row(mock_db, mock_row)

        assert task.id == 1
        assert task.name == 'Test Task'
        assert task.tag == 'work'
        assert task.status == 'new'
        assert task.reminder == 'today'
        assert task.notes == ['Note 1', 'Note 2']
        assert task.deleted is False
        assert task._db == mock_db
        assert task._row == mock_row

    def test_task_direct_initialization(self):
        """Test direct Task initialization."""
        task = Task(
            name='Direct Task',
            tag='personal',
            status='in-progress'
        )

        assert task.name == 'Direct Task'
        assert task.tag == 'personal'
        assert task.status == 'in-progress'
        assert task.notes == []
        assert task.deleted is False

    def test_task_validation_status(self):
        """Test that status is validated."""
        # Valid status should work
        task = Task(name='Test', status='new')
        assert task.status == 'new'

        # Invalid status should raise ValidationError
        with pytest.raises(ValidationError):
            Task(name='Test', status='invalid_status')

    def test_update_name(self, task, mock_db, mock_row):
        """Test updating task name."""
        task.update_name('New Name')

        assert task.name == 'New Name'
        mock_row.update_record.assert_called_once_with(name='New Name')
        mock_db.commit.assert_called_once()

    def test_update_tag(self, task, mock_db, mock_row):
        """Test updating task tag."""
        task.update_tag('personal')

        assert task.tag == 'personal'
        mock_row.update_record.assert_called_once_with(tag='personal')
        mock_db.commit.assert_called_once()

    def test_update_status(self, task, mock_db, mock_row):
        """Test updating task status."""
        task.update_status('done')

        assert task.status == 'done'
        mock_row.update_record.assert_called_once_with(status='done')
        mock_db.commit.assert_called_once()

    def test_update_reminder(self, task, mock_db, mock_row):
        """Test updating task reminder."""
        task.update_reminder('tomorrow')

        assert task.reminder == 'tomorrow'
        mock_row.update_record.assert_called_once_with(reminder='tomorrow')
        mock_db.commit.assert_called_once()

    def test_update_notes(self, task, mock_db, mock_row):
        """Test updating task notes."""
        new_notes = ['Updated note']
        task.update_notes(new_notes)

        assert task.notes == new_notes
        mock_row.update_record.assert_called_once_with(notes=new_notes)
        mock_db.commit.assert_called_once()

    def test_add_note(self, task, mock_db, mock_row):
        """Test adding a note to task."""
        initial_notes = task.notes.copy()
        task.add_note('New note')

        assert len(task.notes) == len(initial_notes) + 1
        assert 'New note' in task.notes
        mock_row.update_record.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_remove_note(self, task, mock_db, mock_row):
        """Test removing a note by index."""
        initial_count = len(task.notes)
        task.remove_note(0)

        assert len(task.notes) == initial_count - 1
        mock_row.update_record.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_remove_note_invalid_index(self, task, mock_db, mock_row):
        """Test removing a note with invalid index."""
        initial_notes = task.notes.copy()
        task.remove_note(999)  # Invalid index

        # Notes should remain unchanged
        assert task.notes == initial_notes
        # Should not update database
        mock_row.update_record.assert_not_called()

    def test_delete(self, task, mock_db, mock_row):
        """Test deleting a task."""
        task.delete()

        assert task.deleted is True
        mock_row.delete_record.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_str_representation(self, task):
        """Test string representation of task."""
        result = str(task)
        assert isinstance(result, str)
        assert 'Test Task' in result
        assert 'work' in result

    def test_repr_representation(self, task):
        """Test repr representation of task."""
        result = repr(task)
        assert isinstance(result, str)
        assert 'Test Task' in result

    def test_task_without_db_connection(self):
        """Test Task without database connection."""
        task = Task(name='No DB Task', tag='test', status='new')

        # Should not raise error
        assert task.name == 'No DB Task'
        assert task._db is None
        assert task._row is None

    def test_multiple_updates(self, task, mock_db, mock_row):
        """Test multiple property updates."""
        # Reset mocks
        mock_db.commit.reset_mock()
        mock_row.update_record.reset_mock()

        # Update multiple properties
        task.update_name('Updated Name')
        task.update_status('working')
        task.update_tag('urgent')

        # Should have called update and commit for each
        assert mock_row.update_record.call_count == 3
        assert mock_db.commit.call_count == 3


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
        row.id = 1
        row.name = 'Task with nulls'
        row.tag = 'default'
        row.status = 'new'
        row.reminder = None
        row.reminder_repeat = None
        row.notes = None
        row.created_on = datetime.now()
        row.deleted = False
        row.priority = 0
        row.size = 'U'
        row.update_record = Mock()
        row.delete_record = Mock()
        # Make .get() method work
        row.get = lambda k, d=None: getattr(row, k, d)
        return row

    def test_task_with_none_values(self, mock_db, mock_row_with_none):
        """Test Task with None values."""
        task = Task.from_row(mock_db, mock_row_with_none)

        assert task.name == 'Task with nulls'
        assert task.reminder is None
        assert task.notes == []  # None is converted to empty list

    def test_task_with_empty_notes(self, mock_db):
        """Test Task with empty notes list."""
        row = Mock()
        row.id = 1
        row.name = 'Test'
        row.tag = 'default'
        row.status = 'new'
        row.reminder = None
        row.reminder_repeat = None
        row.notes = []
        row.created_on = datetime.now()
        row.deleted = False
        row.priority = 0
        row.size = 'U'
        row.update_record = Mock()
        row.get = lambda k, d=None: getattr(row, k, d)

        task = Task.from_row(mock_db, row)
        assert task.notes == []

    def test_task_update_with_none(self, mock_db):
        """Test updating properties to None."""
        row = Mock()
        row.id = 1
        row.name = 'Test'
        row.tag = 'default'
        row.status = 'new'
        row.reminder = 'something'
        row.reminder_repeat = None
        row.notes = []
        row.created_on = datetime.now()
        row.deleted = False
        row.priority = 0
        row.size = 'U'
        row.update_record = Mock()
        row.get = lambda k, d=None: getattr(row, k, d)

        task = Task.from_row(mock_db, row)
        task.update_reminder(None)

        row.update_record.assert_called_with(reminder=None)
        mock_db.commit.assert_called()

    def test_task_default_values(self):
        """Test Task default values."""
        task = Task(name='Minimal Task')

        assert task.name == 'Minimal Task'
        assert task.tag == 'default'
        assert task.status == 'new'
        assert task.reminder is None
        assert task.notes == []
        assert task.deleted is False
        assert task.id is None

    def test_task_pydantic_model_dump(self):
        """Test exporting Task to dict."""
        task = Task(
            name='Export Test',
            tag='work',
            status='in-progress'
        )

        data = task.model_dump()

        assert data['name'] == 'Export Test'
        assert data['tag'] == 'work'
        assert data['status'] == 'in-progress'
        assert isinstance(data, dict)

    def test_task_status_validation_all_valid_statuses(self):
        """Test all valid status values."""
        valid_statuses = ['new', 'in-progress', 'done', 'cancel', 'post']

        for status in valid_statuses:
            task = Task(name='Test', status=status)
            assert task.status == status

    def test_task_created_on_auto_set(self):
        """Test that created_on is automatically set."""
        task = Task(name='Test')

        assert task.created_on is not None
        assert isinstance(task.created_on, datetime)
