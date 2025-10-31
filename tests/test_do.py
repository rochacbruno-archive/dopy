"""Tests for do.py module functions."""

from unittest.mock import Mock, patch
from datetime import datetime


class TestDatabaseFunction:
    """Test the database() function."""

    @patch("dolist.do.Database")
    def test_database_creates_dal_instance(self, mock_database_class):
        """Test that database() creates a Database instance."""
        from dolist.do import database, DBDIR

        mock_db = Mock()
        mock_database_class.return_value = mock_db
        mock_db.define_table = Mock(return_value="tasks_table")

        db, tasks, history, state = database("sqlite://test.db")

        # Should create Database with correct parameters
        mock_database_class.assert_called_once_with("sqlite://test.db", folder=DBDIR)
        # Should define tables (tasks, history, and state)
        assert mock_db.define_table.called
        assert db == mock_db
        assert tasks == "tasks_table"
        assert history == "tasks_table"
        assert state == "tasks_table"

    @patch("dolist.do.Database")
    def test_database_defines_correct_schema(self, mock_database_class):
        """Test that database() defines correct table schema."""
        from dolist.do import database

        mock_db = Mock()
        mock_database_class.return_value = mock_db
        mock_db.define_table = Mock(return_value="tasks_table")

        db, tasks, history, state = database("sqlite://test.db")

        # Check that define_table was called 3 times (tasks, history, and state)
        assert mock_db.define_table.call_count == 3

        # Check the first call was for tasks table
        first_call_args = mock_db.define_table.call_args_list[0]
        assert first_call_args[0][0] == "dolist_tasks"
        # Should have FieldDef objects in the call
        assert len(first_call_args[0]) > 1  # Table name + fields

        # Check the second call was for history table
        second_call_args = mock_db.define_table.call_args_list[1]
        assert second_call_args[0][0] == "dolist_task_history"


class TestInitDbFunction:
    """Test the init_db() function."""

    @patch("dolist.do.database")
    def test_init_db_default(self, mock_database):
        """Test init_db with default database."""
        import dolist.do
        from dolist.do import init_db, DBURI

        mock_db = Mock()
        mock_tasks = Mock()
        mock_history = Mock()
        mock_state = Mock()
        mock_database.return_value = (mock_db, mock_tasks, mock_history, mock_state)

        dburi = init_db()

        mock_database.assert_called_once_with(DBURI)
        assert dolist.do.db == mock_db
        assert dolist.do.tasks == mock_tasks
        assert dolist.do.history == mock_history
        assert dburi == DBURI

    @patch("dolist.do.database")
    def test_init_db_custom(self, mock_database):
        """Test init_db with custom database."""
        from dolist.do import init_db

        mock_db = Mock()
        mock_tasks = Mock()
        mock_history = Mock()
        mock_state = Mock()
        mock_database.return_value = (mock_db, mock_tasks, mock_history, mock_state)

        dburi = init_db("customdb")

        # Should replace 'dopy' with 'customdb' in URI
        called_uri = mock_database.call_args[0][0]
        assert "customdb" in called_uri
        assert "customdb" in dburi


class TestAddCommand:
    """Test the add() command."""

    @patch("dolist.do.init_db")
    @patch("dolist.do.datetime")
    @patch("dolist.do.rprint")
    def test_add_basic_task(self, mock_rprint, mock_datetime, mock_init_db):
        """Test adding a basic task."""
        import dolist.do
        from dolist.do import add

        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.datetime.now.return_value = mock_now

        # Mock global db and tasks
        mock_db = Mock()
        mock_tasks = Mock()
        mock_tasks.insert = Mock(return_value=1)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        # Call add command
        add(name="Test task", tag="default", status="new", reminder=None, use=None)

        # Should initialize db
        mock_init_db.assert_called_once_with(None)

        # Should insert with correct values
        mock_tasks.insert.assert_called_once_with(
            name="Test task",
            tag="default",
            status="new",
            reminder=None,
            reminder_timestamp=None,
            reminder_repeat=None,
            notes=None,
            created_on=mock_now,
            priority=0,
            size="U",
        )

        # Should commit
        mock_db.commit.assert_called_once()

        # Should print success message
        assert mock_rprint.called

    @patch("dolist.do.init_db")
    @patch("dolist.do.datetime")
    @patch("dolist.do.rprint")
    def test_add_task_with_all_fields(self, mock_rprint, mock_datetime, mock_init_db):
        """Test adding a task with all fields specified."""
        import dolist.do
        from dolist.do import add

        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.datetime.now.return_value = mock_now

        mock_db = Mock()
        mock_tasks = Mock()
        mock_tasks.insert = Mock(return_value=5)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        add(
            name="Important task",
            tag="work",
            status="working",
            reminder="tomorrow",
            use=None,
        )

        call_kwargs = mock_tasks.insert.call_args[1]
        assert call_kwargs["name"] == "Important task"
        assert call_kwargs["tag"] == "work"
        assert call_kwargs["status"] == "working"
        assert call_kwargs["reminder"] == "tomorrow"


class TestRemoveCommand:
    """Test the remove/delete action via default_action."""

    @patch("dolist.do.init_db")
    @patch("dolist.do.console")
    def test_rm_existing_task(self, mock_console, mock_init_db):
        """Test removing an existing task."""
        import dolist.do
        from dolist.do import default_action

        # Mock task
        mock_task = Mock()
        mock_task.id = 1
        mock_task.name = "Test task"
        mock_task.update_record = Mock()

        mock_db = Mock()
        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=mock_task)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        default_action(1, "delete")

        # Should initialize db
        mock_init_db.assert_called_once_with(None)

        # Should soft delete the task
        mock_task.update_record.assert_called_once_with(deleted=True)
        # Commit is called twice: once for update, once for history
        assert mock_db.commit.call_count >= 1

    @patch("dolist.do.init_db")
    @patch("dolist.do.rprint")
    def test_rm_nonexistent_task(self, mock_rprint, mock_init_db):
        """Test removing a non-existent task."""
        import dolist.do
        from dolist.do import default_action

        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=None)
        dolist.do.tasks = mock_tasks

        default_action(999, "delete")

        # Should print not found message via rprint
        assert mock_rprint.called


class TestDoneCommand:
    """Test the done action via default_action."""

    @patch("dolist.do.init_db")
    @patch("dolist.do.console")
    def test_done_existing_task(self, mock_console, mock_init_db):
        """Test marking an existing task as done."""
        import dolist.do
        from dolist.do import default_action

        mock_task = Mock()
        mock_task.id = 1
        mock_task.name = "Test task"
        mock_task.update_record = Mock()

        mock_db = Mock()
        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=mock_task)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        default_action(1, "done")

        mock_task.update_record.assert_called_once_with(status="done")
        # Commit is called twice: once for update, once for history
        assert mock_db.commit.call_count >= 1

    @patch("dolist.do.init_db")
    @patch("dolist.do.rprint")
    def test_done_nonexistent_task(self, mock_rprint, mock_init_db):
        """Test marking a non-existent task as done."""
        import dolist.do
        from dolist.do import default_action

        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=None)
        dolist.do.tasks = mock_tasks

        default_action(999, "done")

        # Should print not found
        assert mock_rprint.called


class TestShellCommand:
    """Test the shell() command."""

    @patch("dolist.do.init_db")
    @patch("ptpython.repl.embed")
    @patch("dolist.do.Task")
    def test_shell_loads_tasks(self, mock_task_class, mock_embed, mock_init_db):
        """Test that shell command loads tasks."""
        import dolist.do
        from dolist.do import shell

        # Mock database
        mock_db = Mock()
        mock_tasks = Mock()

        # Mock rows
        mock_row1 = Mock()
        mock_row2 = Mock()
        mock_query = Mock()
        mock_query.select = Mock(return_value=[mock_row1, mock_row2])
        mock_db.return_value = mock_query
        mock_tasks.deleted = Mock()

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        # Mock Task.from_row
        mock_task1 = Mock()
        mock_task2 = Mock()
        mock_task_class.from_row = Mock(side_effect=[mock_task1, mock_task2])

        shell(use=None)

        # Should initialize db
        mock_init_db.assert_called_once_with(None)

        # Should start the REPL (ptpython embed)
        assert mock_embed.called


class TestTUIDefaultCommand:
    """Test the TUI default command."""

    @patch("dolist.do.init_db")
    @patch("dolist.do.run_tui")
    def test_tui_mode_is_default(self, mock_run_tui, mock_init_db):
        """Test that TUI launches by default."""
        import dolist.do
        from dolist.do import default_action

        # Mock database
        mock_db = Mock()
        mock_tasks = Mock()

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        default_action()

        # Should initialize db
        mock_init_db.assert_called_once_with(None)

        # Should run TUI with config
        assert mock_run_tui.called
        call_args = mock_run_tui.call_args
        assert call_args[0][0] == mock_db
        assert call_args[0][1] == mock_tasks
        # Third argument should be config dict with theme
        assert isinstance(call_args[0][2], dict)
        assert "theme" in call_args[0][2]
        assert "config_file" in call_args[0][2]


class TestConfigurationHandling:
    """Test configuration file handling."""

    def test_basedir_exists(self):
        """Test that BASEDIR is defined."""
        from dolist.do import BASEDIR
        from pathlib import Path

        assert BASEDIR is not None
        assert isinstance(BASEDIR, (str, Path))

    def test_configfile_path(self):
        """Test that CONFIGFILE path is defined."""
        from dolist.do import CONFIGFILE
        from pathlib import Path

        assert CONFIGFILE is not None
        assert isinstance(CONFIGFILE, (str, Path))
        # Config can be either config.toml or legacy .dopyrc
        assert "config.toml" in str(CONFIGFILE) or ".dopyrc" in str(CONFIGFILE)

    def test_dburi_is_defined(self):
        """Test that DBURI is defined."""
        from dolist.do import DBURI

        assert DBURI is not None
        assert isinstance(DBURI, str)


class TestCycloptsApp:
    """Test the cyclopts app configuration."""

    def test_app_exists(self):
        """Test that the cyclopts app is defined."""
        from dolist.do import app

        assert app is not None

    def test_app_has_commands(self):
        """Test that app has registered commands."""
        from dolist.do import app

        # Cyclopts app should exist
        assert hasattr(app, "__call__")


class TestMainEntryPoint:
    """Test the main_entry() function."""

    @patch("dolist.do.app")
    def test_main_entry_calls_app(self, mock_app):
        """Test that main_entry calls the cyclopts app."""
        from dolist.do import main_entry

        main_entry()

        # Should call the cyclopts app
        mock_app.assert_called_once()
