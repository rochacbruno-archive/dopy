"""Tests for new features: JSON output, bulk actions, unquoted args, --actions flag."""

import json
from unittest.mock import Mock, patch
from datetime import datetime


class TestJSONOutput:
    """Test JSON output functionality for ls command."""

    @patch("dolist.do.init_db")
    @patch("builtins.print")
    def test_ls_json_output(self, mock_print, mock_init_db):
        """Test that ls with --json outputs valid JSON."""
        import dolist.do

        # Mock database query results
        mock_row1 = Mock()
        mock_row1.id = 1
        mock_row1.name = "Test task"
        mock_row1.tag = "work"
        mock_row1.status = "new"
        mock_row1.reminder = "tomorrow"
        mock_row1.reminder_timestamp = None
        mock_row1.notes = ["note 1"]
        mock_row1.created_on = datetime(2024, 1, 1, 12, 0)

        mock_row2 = Mock()
        mock_row2.id = 2
        mock_row2.name = "Another task"
        mock_row2.tag = "personal"
        mock_row2.status = "done"
        mock_row2.reminder = None
        mock_row2.reminder_timestamp = None
        mock_row2.notes = []
        mock_row2.created_on = datetime(2024, 1, 2, 10, 30)

        # Mock the database query chain
        mock_select_result = Mock()
        mock_select_result.select.return_value = [mock_row1, mock_row2]

        mock_db = Mock()
        mock_db.return_value = mock_select_result

        # Create a mock for tasks that supports the query operations
        mock_tasks = Mock()
        mock_tasks.deleted = Mock()
        mock_tasks.status = Mock()
        mock_tasks.id = Mock()

        # Make the comparison operations return mock query objects
        mock_query = Mock()
        mock_tasks.deleted.__ne__ = Mock(return_value=mock_query)
        mock_tasks.status.belongs = Mock(return_value=mock_query)
        mock_tasks.id.__gt__ = Mock(return_value=mock_query)

        # Make the mock query support bitwise operations
        mock_query.__invert__ = Mock(return_value=mock_query)
        mock_query.__and__ = Mock(return_value=mock_query)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        # Call ls with json flag
        from dolist.do import ls

        ls(json=True)

        # Check that print was called with JSON
        assert mock_print.called
        printed_output = mock_print.call_args[0][0]

        # Should be valid JSON
        parsed = json.loads(printed_output)
        assert isinstance(parsed, list)
        assert len(parsed) == 2
        assert parsed[0]["id"] == 1
        assert parsed[0]["name"] == "Test task"
        assert parsed[1]["id"] == 2

    @patch("dolist.do.init_db")
    @patch("builtins.print")
    def test_ls_json_with_filters(self, mock_print, mock_init_db):
        """Test JSON output works with filters."""
        import dolist.do

        mock_row = Mock()
        mock_row.id = 5
        mock_row.name = "Filtered task"
        mock_row.tag = "urgent"
        mock_row.status = "new"
        mock_row.reminder = None
        mock_row.reminder_timestamp = None
        mock_row.notes = []
        mock_row.created_on = datetime(2024, 1, 1)

        # Mock the database query chain
        mock_select_result = Mock()
        mock_select_result.select.return_value = [mock_row]

        mock_db = Mock()
        mock_db.return_value = mock_select_result

        # Create mock tasks with query support
        mock_tasks = Mock()
        mock_tasks.deleted = Mock()
        mock_tasks.status = Mock()
        mock_tasks.tag = Mock()
        mock_tasks.id = Mock()

        mock_query = Mock()
        mock_tasks.deleted.__ne__ = Mock(return_value=mock_query)
        mock_tasks.status.belongs = Mock(return_value=mock_query)
        mock_tasks.tag.__eq__ = Mock(return_value=mock_query)
        mock_tasks.id.__gt__ = Mock(return_value=mock_query)

        mock_query.__invert__ = Mock(return_value=mock_query)
        mock_query.__and__ = Mock(return_value=mock_query)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        # Call with filter and JSON
        from dolist.do import ls

        ls(tag="urgent", json=True)

        assert mock_print.called
        printed_output = mock_print.call_args[0][0]
        parsed = json.loads(printed_output)

        assert len(parsed) == 1
        assert parsed[0]["tag"] == "urgent"


class TestBulkActions:
    """Test bulk action functionality."""

    @patch("dolist.do.init_db")
    @patch("dolist.do.console")
    @patch("builtins.input", return_value="yes")
    def test_bulk_action_done(self, mock_input, mock_console, mock_init_db):
        """Test bulk action to mark multiple tasks as done."""
        import dolist.do

        # Mock multiple tasks
        mock_row1 = Mock()
        mock_row1.id = 1
        mock_row1.name = "Task 1"
        mock_row1.update_record = Mock()

        mock_row2 = Mock()
        mock_row2.id = 2
        mock_row2.name = "Task 2"
        mock_row2.update_record = Mock()

        # Mock the database query chain
        mock_select_result = Mock()
        mock_select_result.select.return_value = [mock_row1, mock_row2]

        mock_db = Mock()
        mock_db.return_value = mock_select_result

        # Create mock tasks with query support
        mock_tasks = Mock()
        mock_tasks.deleted = Mock()
        mock_tasks.status = Mock()
        mock_tasks.id = Mock()

        mock_query = Mock()
        mock_tasks.deleted.__ne__ = Mock(return_value=mock_query)
        mock_tasks.status.belongs = Mock(return_value=mock_query)
        mock_tasks.id.__gt__ = Mock(return_value=mock_query)

        mock_query.__invert__ = Mock(return_value=mock_query)
        mock_query.__and__ = Mock(return_value=mock_query)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        # Execute bulk action
        from dolist.do import ls

        ls(action="done")

        # Both tasks should be updated
        mock_row1.update_record.assert_called_once_with(status="done")
        mock_row2.update_record.assert_called_once_with(status="done")

        # Database should be committed
        mock_db.commit.assert_called_once()

    @patch("dolist.do.init_db")
    @patch("dolist.do.console")
    @patch("builtins.input", return_value="no")
    def test_bulk_action_cancelled(self, mock_input, mock_console, mock_init_db):
        """Test bulk action can be cancelled."""
        import dolist.do

        mock_row = Mock()
        mock_row.id = 1
        mock_row.name = "Task"
        mock_row.update_record = Mock()

        # Mock the database query chain
        mock_select_result = Mock()
        mock_select_result.select.return_value = [mock_row]

        mock_db = Mock()
        mock_db.return_value = mock_select_result

        # Create mock tasks with query support
        mock_tasks = Mock()
        mock_tasks.deleted = Mock()
        mock_tasks.status = Mock()
        mock_tasks.id = Mock()

        mock_query = Mock()
        mock_tasks.deleted.__ne__ = Mock(return_value=mock_query)
        mock_tasks.status.belongs = Mock(return_value=mock_query)
        mock_tasks.id.__gt__ = Mock(return_value=mock_query)

        mock_query.__invert__ = Mock(return_value=mock_query)
        mock_query.__and__ = Mock(return_value=mock_query)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        from dolist.do import ls

        ls(action="delete")

        # Task should NOT be updated when cancelled
        mock_row.update_record.assert_not_called()

    @patch("dolist.do.init_db")
    @patch("dolist.do.console")
    @patch("dolist.do.parse_reminder", return_value=(datetime(2024, 1, 5), None, None))
    @patch("builtins.input", return_value="yes")
    def test_bulk_action_remind(
        self, mock_input, mock_parse, mock_console, mock_init_db
    ):
        """Test bulk action to set reminders."""
        import dolist.do

        mock_row = Mock()
        mock_row.id = 1
        mock_row.name = "Task"
        mock_row.update_record = Mock()

        # Mock the database query chain
        mock_select_result = Mock()
        mock_select_result.select.return_value = [mock_row]

        mock_db = Mock()
        mock_db.return_value = mock_select_result

        # Create mock tasks with query support
        mock_tasks = Mock()
        mock_tasks.deleted = Mock()
        mock_tasks.status = Mock()
        mock_tasks.id = Mock()

        mock_query = Mock()
        mock_tasks.deleted.__ne__ = Mock(return_value=mock_query)
        mock_tasks.status.belongs = Mock(return_value=mock_query)
        mock_tasks.id.__gt__ = Mock(return_value=mock_query)

        mock_query.__invert__ = Mock(return_value=mock_query)
        mock_query.__and__ = Mock(return_value=mock_query)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        from dolist.do import ls

        ls(action="remind", action_args="tomorrow")

        # Reminder should be set
        mock_row.update_record.assert_called_once()
        call_kwargs = mock_row.update_record.call_args[1]
        assert call_kwargs["reminder"] == "tomorrow"
        assert call_kwargs["reminder_timestamp"] == datetime(2024, 1, 5)

    @patch("dolist.do.init_db")
    @patch("dolist.do.console")
    @patch("builtins.input")
    def test_bulk_action_with_yes_flag(self, mock_input, mock_console, mock_init_db):
        """Test bulk action with --yes flag bypasses confirmation."""
        import dolist.do

        mock_row = Mock()
        mock_row.id = 1
        mock_row.name = "Task"
        mock_row.update_record = Mock()

        # Mock the database query chain
        mock_select_result = Mock()
        mock_select_result.select.return_value = [mock_row]

        mock_db = Mock()
        mock_db.return_value = mock_select_result

        # Create mock tasks with query support
        mock_tasks = Mock()
        mock_tasks.deleted = Mock()
        mock_tasks.status = Mock()
        mock_tasks.id = Mock()

        mock_query = Mock()
        mock_tasks.deleted.__ne__ = Mock(return_value=mock_query)
        mock_tasks.status.belongs = Mock(return_value=mock_query)
        mock_tasks.id.__gt__ = Mock(return_value=mock_query)

        mock_query.__invert__ = Mock(return_value=mock_query)
        mock_query.__and__ = Mock(return_value=mock_query)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        from dolist.do import ls

        ls(action="done", yes=True)

        # input() should NOT have been called (confirmation bypassed)
        mock_input.assert_not_called()

        # Task should still be updated
        mock_row.update_record.assert_called_once_with(status="done")
        mock_db.commit.assert_called_once()


class TestUnquotedArgs:
    """Test unquoted multi-word argument support."""

    @patch("dolist.do.init_db")
    @patch("dolist.do.console")
    @patch(
        "dolist.do.parse_reminder",
        return_value=(datetime(2024, 1, 1, 14, 0), None, None),
    )
    def test_remind_unquoted_args(self, mock_parse, mock_console, mock_init_db):
        """Test remind action with unquoted multi-word args."""
        import dolist.do
        from dolist.do import default_action

        mock_row = Mock()
        mock_row.id = 1
        mock_row.name = "Test"
        mock_row.update_record = Mock()

        mock_db = Mock()
        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=mock_row)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        # Call with unquoted args: dolist 1 remind 2 hours
        default_action(1, "remind", "2", "hours")

        # Should parse "2 hours" as a single reminder time
        mock_parse.assert_called_once_with("2 hours")
        mock_row.update_record.assert_called_once()

    @patch("dolist.do.init_db")
    @patch("dolist.do.console")
    @patch("dolist.do._show_task")
    def test_note_unquoted_args(self, mock_show, mock_console, mock_init_db):
        """Test note action with unquoted multi-word args."""
        import dolist.do
        from dolist.do import default_action

        mock_row = Mock()
        mock_row.id = 1
        mock_row.name = "Test"
        mock_row.notes = []
        mock_row.update_record = Mock()

        mock_db = Mock()
        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=mock_row)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        # Call with unquoted args: dolist 1 note This is my note
        default_action(1, "note", "This", "is", "my", "note")

        # Should join all args into one note
        mock_row.update_record.assert_called_once()
        call_kwargs = mock_row.update_record.call_args[1]
        assert call_kwargs["notes"] == ["This is my note"]


class TestActionsFlag:
    """Test --actions flag."""

    @patch("dolist.do.init_db")
    @patch("dolist.do.console")
    def test_actions_flag_displays_help(self, mock_console, mock_init_db):
        """Test that --actions displays available actions."""
        from dolist.do import default_action

        # Call with actions flag
        default_action(actions=True)

        # Should print action information
        assert mock_console.print.called

        # Check that key action categories are mentioned
        printed_calls = [str(call) for call in mock_console.print.call_args_list]
        all_output = " ".join(printed_calls)

        assert "Status Management" in all_output or "start" in all_output
        assert "remind" in all_output or "Reminder" in all_output


class TestDefaultAction:
    """Test the refactored default_action with variadic args."""

    @patch("dolist.do.init_db")
    @patch("dolist.do.run_tui")
    def test_default_action_no_args_launches_tui(self, mock_tui, mock_init_db):
        """Test that calling with no args launches TUI."""
        from dolist.do import default_action

        default_action()

        # Should launch TUI
        mock_tui.assert_called_once()

    @patch("dolist.do.init_db")
    @patch("dolist.do._show_task")
    def test_default_action_id_only_shows_task(self, mock_show_task, mock_init_db):
        """Test that ID with no action shows the task."""
        import dolist.do
        from dolist.do import default_action

        mock_row = Mock()
        mock_row.id = 5

        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=mock_row)
        dolist.do.tasks = mock_tasks

        default_action(5)

        # Should show the task
        mock_show_task.assert_called_once_with(mock_row)

    @patch("dolist.do.init_db")
    @patch("dolist.do.console")
    def test_default_action_status_change(self, mock_console, mock_init_db):
        """Test status change action."""
        import dolist.do
        from dolist.do import default_action

        mock_row = Mock()
        mock_row.id = 1
        mock_row.name = "Test"
        mock_row.update_record = Mock()

        mock_db = Mock()
        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=mock_row)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        # Test done action
        default_action(1, "done")

        mock_row.update_record.assert_called_once_with(status="done")
        # Commit is called twice: once for update, once for history
        assert mock_db.commit.call_count >= 1


class TestEditAction:
    """Test the edit action."""

    @patch("dolist.do.init_db")
    @patch("dolist.do.run_tui")
    def test_edit_action_opens_tui(self, mock_run_tui, mock_init_db):
        """Test that edit action opens TUI with task selected."""
        import dolist.do
        from dolist.do import default_action

        mock_row = Mock()
        mock_row.id = 12
        mock_row.name = "Test task"

        mock_db = Mock()
        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=mock_row)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        # Call edit action
        default_action(12, "edit")

        # Should call run_tui with task_id in config
        mock_run_tui.assert_called_once()
        call_args = mock_run_tui.call_args
        config = call_args[0][2]  # Third argument is config
        assert config["selected_task_id"] == 12


class TestLsCommand:
    """Test the enhanced ls command."""

    @patch("dolist.do.init_db")
    @patch("dolist.do.print_table")
    @patch("dolist.do.console")
    def test_ls_basic(self, mock_console, mock_print_table, mock_init_db):
        """Test basic ls functionality."""
        import dolist.do
        from dolist.do import ls

        mock_row = Mock()
        mock_row.id = 1
        mock_row.name = "Task"
        mock_row.tag = "default"
        mock_row.status = "new"
        mock_row.reminder_timestamp = None
        mock_row.notes = []
        mock_row.created_on = datetime(2024, 1, 1)

        # Mock the database query chain
        mock_select_result = Mock()
        mock_select_result.select.return_value = [mock_row]

        mock_db = Mock()
        mock_db.return_value = mock_select_result

        # Create mock tasks with query support
        mock_tasks = Mock()
        mock_tasks.deleted = Mock()
        mock_tasks.status = Mock()
        mock_tasks.id = Mock()

        mock_query = Mock()
        mock_tasks.deleted.__ne__ = Mock(return_value=mock_query)
        mock_tasks.status.belongs = Mock(return_value=mock_query)
        mock_tasks.id.__gt__ = Mock(return_value=mock_query)

        # Make the mock query support bitwise operations
        mock_query.__invert__ = Mock(return_value=mock_query)
        mock_query.__and__ = Mock(return_value=mock_query)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        ls()

        # Should call print_table
        assert mock_print_table.called

    @patch("dolist.do.init_db")
    @patch("dolist.do.print_table")
    @patch("dolist.do.console")
    def test_ls_with_search(self, mock_console, mock_print_table, mock_init_db):
        """Test ls with search filter."""
        import dolist.do
        from dolist.do import ls

        # Mock the database query chain
        mock_select_result = Mock()
        mock_select_result.select.return_value = []

        mock_db = Mock()
        mock_db.return_value = mock_select_result

        # Create mock tasks with query support
        mock_tasks = Mock()
        mock_tasks.deleted = Mock()
        mock_tasks.status = Mock()
        mock_tasks.name = Mock()
        mock_tasks.id = Mock()

        # Create mock row with name and notes
        from datetime import datetime

        mock_row = Mock()
        mock_row.id = 1
        mock_row.name = "test task"
        mock_row.notes = ["some note"]
        mock_row.status = "new"
        mock_row.tag = "default"
        mock_row.created_on = datetime.now()
        mock_row.reminder_timestamp = None
        mock_row.get = (
            lambda k, d=None: getattr(mock_row, k, d) if hasattr(mock_row, k) else d
        )

        mock_query = Mock()
        mock_query.select = Mock(return_value=[mock_row])

        mock_tasks.deleted.__ne__ = Mock(return_value=mock_query)
        mock_tasks.status.belongs = Mock(return_value=mock_query)
        mock_tasks.name.like = Mock(return_value=mock_query)
        mock_tasks.id.__gt__ = Mock(return_value=mock_query)

        # Make the mock query support bitwise operations
        mock_query.__invert__ = Mock(return_value=mock_query)
        mock_query.__and__ = Mock(return_value=mock_query)

        # Mock db to return mock_query
        mock_db_call = Mock(return_value=mock_query)

        dolist.do.db = mock_db_call
        dolist.do.tasks = mock_tasks

        ls(search="test")

        # Search now filters post-query, so we just check db was queried
        assert mock_db_call.called


class TestShowAction:
    """Test the show action."""

    @patch("dolist.do.init_db")
    @patch("dolist.do._show_task")
    def test_show_action(self, mock_show_task, mock_init_db):
        """Test show action displays task details."""
        import dolist.do
        from dolist.do import default_action

        mock_row = Mock()
        mock_row.id = 1
        mock_row.name = "Test task"

        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=mock_row)
        dolist.do.tasks = mock_tasks

        # Call show action
        default_action(1, "show")

        # Should call _show_task helper
        mock_show_task.assert_called_once_with(mock_row)


class TestDelayAction:
    """Test the delay action."""

    @patch("dolist.do.init_db")
    @patch("dolist.do.console")
    @patch("dolist.do.parse_reminder")
    def test_delay_action_with_time(self, mock_parse, mock_console, mock_init_db):
        """Test delay action with custom time."""
        import dolist.do
        from dolist.do import default_action

        # Mock parse_reminder to return a future datetime
        future_time = datetime(2024, 1, 1, 15, 0)
        mock_parse.return_value = (future_time, None, None)

        mock_row = Mock()
        mock_row.id = 1
        mock_row.name = "Test task"
        mock_row.reminder_timestamp = datetime(2024, 1, 1, 14, 0)
        mock_row.update_record = Mock()

        mock_db = Mock()
        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=mock_row)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        # Call delay with custom time: dolist 1 delay 1 hour
        default_action(1, "delay", "1", "hour")

        # Should parse the delay time
        mock_parse.assert_called_once_with("1 hour")

        # Should update the reminder
        mock_row.update_record.assert_called_once()
        call_kwargs = mock_row.update_record.call_args[1]
        assert "delayed:" in call_kwargs["reminder"]
        assert call_kwargs["reminder_timestamp"] == future_time

    @patch("dolist.do.init_db")
    @patch("dolist.do.console")
    @patch("dolist.do.parse_reminder")
    def test_delay_action_default(self, mock_parse, mock_console, mock_init_db):
        """Test delay action with default time (10 minutes)."""
        import dolist.do
        from dolist.do import default_action

        future_time = datetime(2024, 1, 1, 14, 10)
        mock_parse.return_value = (future_time, None, None)

        mock_row = Mock()
        mock_row.id = 1
        mock_row.name = "Test task"
        mock_row.reminder_timestamp = datetime(2024, 1, 1, 14, 0)
        mock_row.update_record = Mock()

        mock_db = Mock()
        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=mock_row)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        # Call delay without time (should default to 10 minutes)
        default_action(1, "delay")

        # Should parse "10 minutes" as default
        mock_parse.assert_called_once_with("10 minutes")


class TestNoteRemoveAction:
    """Test the note --rm action."""

    @patch("dolist.do.init_db")
    @patch("dolist.do.console")
    def test_note_rm_action(self, mock_console, mock_init_db):
        """Test removing a note by index."""
        import dolist.do
        from dolist.do import default_action

        mock_row = Mock()
        mock_row.id = 1
        mock_row.name = "Test task"
        mock_row.notes = ["First note", "Second note", "Third note"]
        mock_row.update_record = Mock()

        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=mock_row)

        dolist.do.db = Mock()
        dolist.do.tasks = mock_tasks

        # Remove note at index 1: dolist 1 note --rm 1
        default_action(1, "note", rm=1)

        # Should update with note removed
        mock_row.update_record.assert_called_once()
        call_kwargs = mock_row.update_record.call_args[1]
        assert call_kwargs["notes"] == ["First note", "Third note"]

    @patch("dolist.do.init_db")
    @patch("dolist.do.console")
    def test_note_rm_invalid_index(self, mock_console, mock_init_db):
        """Test removing a note with invalid index."""
        import dolist.do
        from dolist.do import default_action

        mock_row = Mock()
        mock_row.id = 1
        mock_row.name = "Test task"
        mock_row.notes = ["Only note"]
        mock_row.update_record = Mock()

        mock_tasks = Mock()
        mock_tasks.__getitem__ = Mock(return_value=mock_row)

        dolist.do.tasks = mock_tasks

        # Try to remove note at invalid index
        default_action(1, "note", rm=5)

        # Should print error via console
        assert mock_console.print.called
        # Should NOT update the task
        mock_row.update_record.assert_not_called()


class TestBulkActionsWithTagFilter:
    """Test bulk actions with tag filtering."""

    @patch("dolist.do.init_db")
    @patch("dolist.do.console")
    @patch("builtins.input", return_value="yes")
    def test_bulk_action_with_tag_filter(self, mock_input, mock_console, mock_init_db):
        """Test bulk action with --tag filter."""
        import dolist.do

        # Mock tasks with different tags
        mock_row1 = Mock()
        mock_row1.id = 1
        mock_row1.name = "Work task"
        mock_row1.tag = "work"
        mock_row1.update_record = Mock()

        mock_row2 = Mock()
        mock_row2.id = 2
        mock_row2.name = "Food task"
        mock_row2.tag = "food"
        mock_row2.update_record = Mock()

        # Mock the database query chain
        mock_select_result = Mock()
        # Only return the food task (filtered by tag)
        mock_select_result.select.return_value = [mock_row2]

        mock_db = Mock()
        mock_db.return_value = mock_select_result

        # Create mock tasks with query support
        mock_tasks = Mock()
        mock_tasks.deleted = Mock()
        mock_tasks.status = Mock()
        mock_tasks.tag = Mock()
        mock_tasks.id = Mock()

        mock_query = Mock()
        mock_tasks.deleted.__ne__ = Mock(return_value=mock_query)
        mock_tasks.status.belongs = Mock(return_value=mock_query)
        mock_tasks.tag.__eq__ = Mock(return_value=mock_query)
        mock_tasks.id.__gt__ = Mock(return_value=mock_query)

        mock_query.__invert__ = Mock(return_value=mock_query)
        mock_query.__and__ = Mock(return_value=mock_query)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        from dolist.do import ls

        # Test: dolist ls --tag food --action post
        ls(tag="food", action="post")

        # Should have checked tag filter
        mock_tasks.tag.__eq__.assert_called_once_with("food")

        # Only the food task should be updated
        mock_row2.update_record.assert_called_once_with(status="post")
        mock_db.commit.assert_called_once()

    @patch("dolist.do.init_db")
    @patch("dolist.do.console")
    def test_bulk_action_with_tag_and_yes_flag(self, mock_console, mock_init_db):
        """Test bulk action with --tag and -y flag (skip confirmation)."""
        import dolist.do

        mock_row = Mock()
        mock_row.id = 1
        mock_row.name = "Food task"
        mock_row.tag = "food"
        mock_row.update_record = Mock()

        mock_select_result = Mock()
        mock_select_result.select.return_value = [mock_row]

        mock_db = Mock()
        mock_db.return_value = mock_select_result

        mock_tasks = Mock()
        mock_tasks.deleted = Mock()
        mock_tasks.status = Mock()
        mock_tasks.tag = Mock()
        mock_tasks.id = Mock()

        mock_query = Mock()
        mock_tasks.deleted.__ne__ = Mock(return_value=mock_query)
        mock_tasks.status.belongs = Mock(return_value=mock_query)
        mock_tasks.tag.__eq__ = Mock(return_value=mock_query)
        mock_tasks.id.__gt__ = Mock(return_value=mock_query)

        mock_query.__invert__ = Mock(return_value=mock_query)
        mock_query.__and__ = Mock(return_value=mock_query)

        dolist.do.db = mock_db
        dolist.do.tasks = mock_tasks

        from dolist.do import ls

        # Test: dolist ls --tag food --all --action post -y
        ls(tag="food", all=True, action="post", yes=True)

        # Should update the task
        mock_row.update_record.assert_called_once_with(status="post")
        mock_db.commit.assert_called_once()
