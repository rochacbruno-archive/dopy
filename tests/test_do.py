"""Tests for do.py module functions."""
import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime


class TestDatabaseFunction:
    """Test the database() function."""

    @patch('dopy.do.DAL')
    def test_database_creates_dal_instance(self, mock_dal_class):
        """Test that database() creates a DAL instance."""
        from dopy.do import database, DBDIR

        mock_db = Mock()
        mock_dal_class.return_value = mock_db
        mock_db.define_table = Mock(return_value='tasks_table')

        db, tasks = database('sqlite://test.db')

        # Should create DAL with correct parameters
        mock_dal_class.assert_called_once_with('sqlite://test.db', folder=DBDIR)
        # Should define the tasks table
        assert mock_db.define_table.called
        assert db == mock_db
        assert tasks == 'tasks_table'

    @patch('dopy.do.DAL')
    def test_database_defines_correct_schema(self, mock_dal_class):
        """Test that database() defines correct table schema."""
        from dopy.do import database, Field

        mock_db = Mock()
        mock_dal_class.return_value = mock_db
        mock_db.define_table = Mock(return_value='tasks_table')

        db, tasks = database('sqlite://test.db')

        # Check the table definition
        call_args = mock_db.define_table.call_args
        assert call_args[0][0] == 'dopy_tasks'
        # Should have Field objects in the call
        assert len(call_args[0]) > 1  # Table name + fields


class TestAddFunction:
    """Test the add() function."""

    @patch('dopy.do.datetime')
    def test_add_basic_task(self, mock_datetime):
        """Test adding a basic task."""
        import dopy.do
        from dopy.do import add

        # Mock datetime
        mock_now = Mock()
        mock_datetime.datetime.now.return_value = mock_now

        # Mock global db and tasks
        mock_db = Mock()
        mock_tasks = Mock()
        mock_tasks.insert = Mock(return_value=1)

        dopy.do.db = mock_db
        dopy.do.tasks = mock_tasks

        # Test arguments - need to use defaultdict or just provide empty values
        arguments = {
            '<name>': 'Test task',
            '<tag>': '',  # Empty string will be treated as falsy
            '<status>': '',
            '--reminder': None
        }

        result = add(arguments)

        # Should insert with correct values
        mock_tasks.insert.assert_called_once()
        call_kwargs = mock_tasks.insert.call_args[1]
        assert call_kwargs['name'] == 'Test task'
        assert call_kwargs['tag'] == 'default'
        assert call_kwargs['status'] == 'new'
        assert call_kwargs['created_on'] == mock_now

        # Should commit
        mock_db.commit.assert_called_once()
        assert 'Task 1 inserted' in result

    @patch('dopy.do.datetime')
    def test_add_task_with_all_fields(self, mock_datetime):
        """Test adding a task with all fields specified."""
        import dopy.do
        from dopy.do import add

        mock_now = Mock()
        mock_datetime.datetime.now.return_value = mock_now

        mock_db = Mock()
        mock_tasks = Mock()
        mock_tasks.insert = Mock(return_value=5)

        dopy.do.db = mock_db
        dopy.do.tasks = mock_tasks

        arguments = {
            '<name>': 'Important task',
            '<tag>': 'work',
            '<status>': 'working',
            '--reminder': 'tomorrow'
        }

        result = add(arguments)

        call_kwargs = mock_tasks.insert.call_args[1]
        assert call_kwargs['name'] == 'Important task'
        assert call_kwargs['tag'] == 'work'
        assert call_kwargs['status'] == 'working'
        assert call_kwargs['reminder'] == 'tomorrow'
        assert 'Task 5 inserted' in result


class TestRemoveFunction:
    """Test the rm() function."""

    def test_rm_existing_task(self):
        """Test removing an existing task."""
        import dopy.do
        from dopy.do import rm

        # Mock task
        mock_task = Mock()
        mock_task.update_record = Mock()

        mock_db = Mock()
        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=mock_task)

        dopy.do.db = mock_db
        dopy.do.tasks = mock_tasks

        arguments = {'<id>': '1'}
        result = rm(arguments)

        # Should soft delete the task
        mock_task.update_record.assert_called_once_with(deleted=True)
        mock_db.commit.assert_called_once()
        assert 'deleted' in result.lower()

    def test_rm_nonexistent_task(self):
        """Test removing a non-existent task."""
        import dopy.do
        from dopy.do import rm

        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=None)
        dopy.do.tasks = mock_tasks

        arguments = {'<id>': '999'}
        result = rm(arguments)

        assert 'not found' in result.lower()


class TestDoneFunction:
    """Test the done() function."""

    def test_done_existing_task(self):
        """Test marking an existing task as done."""
        import dopy.do
        from dopy.do import done

        mock_task = Mock()
        mock_task.update_record = Mock()

        mock_db = Mock()
        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=mock_task)

        dopy.do.db = mock_db
        dopy.do.tasks = mock_tasks

        arguments = {'<id>': '1'}
        result = done(arguments)

        mock_task.update_record.assert_called_once_with(status='done')
        mock_db.commit.assert_called_once()
        assert 'done' in result.lower()

    def test_done_nonexistent_task(self):
        """Test marking a non-existent task as done."""
        import dopy.do
        from dopy.do import done

        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=None)
        dopy.do.tasks = mock_tasks

        arguments = {'<id>': '999'}
        result = done(arguments)

        assert 'not found' in result.lower()


class TestMainFunction:
    """Test the main() function."""

    @patch('dopy.do.database')
    @patch('dopy.do.shell')
    def test_main_no_arguments_calls_shell(self, mock_shell, mock_database):
        """Test that main() with no arguments calls shell()."""
        from dopy.do import main

        mock_db = Mock()
        mock_tasks = Mock()
        mock_database.return_value = (mock_db, mock_tasks)

        arguments = dict.fromkeys([
            '--args', '--use', 'add', 'ls', 'rm', 'done', 'get', 'note', 'show'
        ], False)
        arguments['--use'] = None

        main(arguments)

        mock_shell.assert_called_once()

    @patch('dopy.do.database')
    @patch('dopy.do.add')
    @patch('builtins.print')
    def test_main_with_add_command(self, mock_print, mock_add, mock_database):
        """Test main() with add command."""
        from dopy.do import main

        mock_db = Mock()
        mock_tasks = Mock()
        mock_database.return_value = (mock_db, mock_tasks)
        mock_add.return_value = 'Task added'

        arguments = dict.fromkeys([
            '--args', '--use', 'ls', 'rm', 'done', 'get', 'note', 'show'
        ], False)
        arguments['add'] = True
        arguments['--use'] = None

        main(arguments)

        mock_add.assert_called_once_with(arguments)
        mock_print.assert_called_once_with('Task added')

    @patch('dopy.do.database')
    def test_main_with_custom_db(self, mock_database):
        """Test main() with custom database."""
        from dopy.do import main

        mock_db = Mock()
        mock_tasks = Mock()
        mock_database.return_value = (mock_db, mock_tasks)

        arguments = dict.fromkeys([
            '--args', 'add', 'ls', 'rm', 'done', 'get', 'note', 'show'
        ], False)
        arguments['--use'] = 'customdb'

        with patch('dopy.do.shell'):
            main(arguments)

        # Should have called database with modified URI
        assert mock_database.called
        called_uri = mock_database.call_args[0][0]
        assert 'customdb' in called_uri


class TestConfigurationHandling:
    """Test configuration file handling."""

    def test_basedir_exists(self):
        """Test that BASEDIR is defined."""
        from dopy.do import BASEDIR
        assert BASEDIR is not None
        assert isinstance(BASEDIR, str)

    def test_configfile_path(self):
        """Test that CONFIGFILE path is defined."""
        from dopy.do import CONFIGFILE
        assert CONFIGFILE is not None
        assert isinstance(CONFIGFILE, str)
        assert '.dopyrc' in CONFIGFILE

    def test_dburi_is_defined(self):
        """Test that DBURI is defined."""
        from dopy.do import DBURI
        assert DBURI is not None
        assert isinstance(DBURI, str)


class TestMainEntryPoint:
    """Test the main_entry() function."""

    @patch('dopy.do.docopt')
    @patch('dopy.do.main')
    def test_main_entry_parses_args(self, mock_main, mock_docopt):
        """Test that main_entry parses arguments and calls main."""
        from dopy.do import main_entry

        mock_args = {'test': 'args'}
        mock_docopt.return_value = mock_args

        main_entry()

        # Should call docopt to parse arguments
        assert mock_docopt.called
        # Should call main with parsed arguments
        mock_main.assert_called_once_with(mock_args)

    @patch('dopy.do.docopt')
    def test_main_entry_version(self, mock_docopt):
        """Test that main_entry uses correct version."""
        from dopy.do import main_entry

        mock_docopt.return_value = {}

        with patch('dopy.do.main'):
            main_entry()

        # Check version parameter
        call_kwargs = mock_docopt.call_args[1]
        assert 'version' in call_kwargs
        assert '0.3' in call_kwargs['version']
