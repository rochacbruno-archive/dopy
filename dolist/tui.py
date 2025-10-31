#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Textual TUI for DoList task management."""

from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import (
    Header,
    Footer,
    DataTable,
    Button,
    Input,
    Label,
    Static,
    Select,
    TextArea,
)
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.command import Hit, Provider
from .reminder_parser import parse_reminder, get_time_until
from functools import reduce


def parse_search(search_text: str) -> dict:
    """Parse search syntax into filter dict.

    Examples:
        /test → {'text': 'test'} (searches both name and notes)
        /name=test → {'name': 'test'} (searches only name)
        /note=test → {'note': 'test'} (searches only notes)
        /tag=work → {'tag': ['work']}
        /tag=work,personal → {'tag': ['work', 'personal']}
        /status=new,done → {'status': ['new', 'done']}
        /priority=5 → {'priority': '5'}
        /priority=>5 → {'priority': '>5'}
        /priority=>=3 → {'priority': '>=3'}
        /size=M → {'size': 'M'}
        /size=S,M → {'size': ['S', 'M']}
        /tag=work test → {'tag': ['work'], 'text': 'test'}
        /status=new tag=urgent bug → {'status': ['new'], 'tag': ['urgent'], 'text': 'bug'}
    """
    filters = {}
    remaining_text = []

    parts = search_text.strip().split()

    for part in parts:
        if "=" in part:
            key, value = part.split("=", 1)
            if key == "tag":
                filters["tag"] = value.split(",")
            elif key == "status":
                filters["status"] = value.split(",")
            elif key == "priority":
                # Store priority as-is to support range operators (>, >=, <, <=)
                filters["priority"] = value
            elif key == "size":
                # Support multiple sizes separated by comma
                sizes = value.split(",")
                if len(sizes) == 1:
                    filters["size"] = sizes[0]
                else:
                    filters["size"] = sizes
            elif key == "name":
                # Search only in task name
                filters["name"] = value
            elif key == "note":
                # Search only in task notes
                filters["note"] = value
        else:
            remaining_text.append(part)

    if remaining_text:
        # General text search (searches both name and notes)
        filters["text"] = " ".join(remaining_text)

    return filters


class ConfirmDeleteScreen(ModalScreen):
    """Modal screen for confirming task deletion."""

    BINDINGS = [
        ("escape", "dismiss", "Cancel"),
    ]

    def __init__(self, task_name: str, on_confirm, task_count: int = 1):
        super().__init__()
        self.task_name = task_name
        self.on_confirm = on_confirm
        self.task_count = task_count

    def action_dismiss(self) -> None:
        """Cancel and return to home screen."""
        self.app.pop_screen()

    CSS = """
    ConfirmDeleteScreen {
        align: center middle;
    }

    #confirm_dialog {
        width: 60%;
        max-width: 60;
        height: auto;
        border: thick $error;
        background: $surface;
        padding: 1;
    }

    #confirm_dialog Label {
        width: 100%;
        text-align: center;
        margin: 1 0;
    }

    #confirm_dialog Horizontal {
        width: 100%;
        align: center middle;
    }

    #confirm_dialog Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="confirm_dialog"):
            if self.task_count > 1:
                yield Label(f"Delete {self.task_count} tasks?")
                yield Label("This cannot be undone!")
            else:
                yield Label("Delete task?")
                yield Label(f'"{self.task_name}"')
                yield Label("This cannot be undone!")
            with Horizontal():
                yield Button("Delete", variant="error", id="confirm_delete_btn")
                yield Button("Cancel", variant="default", id="cancel_delete_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm_delete_btn":
            self.on_confirm()
            self.app.pop_screen()
        elif event.button.id == "cancel_delete_btn":
            self.app.pop_screen()


class SearchOverlay(ModalScreen):
    """Vim-like search overlay at the bottom of screen."""

    BINDINGS = [
        ("escape", "cancel_search", "Cancel search"),
        ("enter", "apply_search", "Apply search"),
    ]

    CSS = """
    SearchOverlay {
        align: center bottom;
        background: transparent;
    }

    #search_container {
        width: 100%;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    #search_container Label {
        width: auto;
        margin: 0 1 0 0;
    }

    #search_container Input {
        width: 1fr;
    }
    """

    def __init__(self):
        super().__init__()
        self.search_text = ""

    def compose(self) -> ComposeResult:
        with Horizontal(id="search_container"):
            yield Label("/")
            yield Input(
                placeholder="Search: text, tag=value, status=value", id="search_input"
            )

    def on_mount(self) -> None:
        """Focus the input when overlay appears."""
        search_input = self.query_one("#search_input", Input)
        search_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Live filtering as user types."""
        if event.input.id == "search_input":
            self.search_text = event.value
            # Apply live filtering
            if hasattr(self.app, "apply_search_filter"):
                filters = parse_search(self.search_text)
                self.app.apply_search_filter(filters, live=True)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in search input."""
        if event.input.id == "search_input":
            self.action_apply_search()

    def action_cancel_search(self) -> None:
        """ESC: Close overlay and clear search."""
        if hasattr(self.app, "clear_search_filter"):
            self.app.clear_search_filter()
        self.app.pop_screen()
        # Task 9: Restore focus to table
        if hasattr(self.app, "_restore_table_focus"):
            self.app._restore_table_focus()

    def action_apply_search(self) -> None:
        """Enter: Close overlay and keep search active."""
        if hasattr(self.app, "apply_search_filter"):
            filters = parse_search(self.search_text)
            self.app.apply_search_filter(filters, live=False)
        self.app.pop_screen()
        # Task 9: Restore focus to table
        if hasattr(self.app, "_restore_table_focus"):
            self.app._restore_table_focus()


class AddTaskScreen(ModalScreen):
    """Modal screen for adding a new task."""

    BINDINGS = [
        ("escape", "dismiss", "Return to home"),
    ]

    CSS = """
    AddTaskScreen {
        align: center middle;
    }

    #dialog {
        width: 70%;
        max-width: 80;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    #dialog Horizontal {
        width: 100%;
        align: center middle;
    }

    #dialog Button {
        margin: 0 1;
    }
    """

    def __init__(self, db, tasks_table):
        super().__init__()
        self.db = db
        self._tasks_table = tasks_table

    def action_dismiss(self) -> None:
        """Return to home screen."""
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Add New Task")
            yield Label("Name:")
            yield Input(placeholder="Task name", id="name_input")
            yield Label("Tag:")
            yield Input(placeholder="Tag (default: default)", id="tag_input")
            yield Label("Status:")
            yield Select(
                [
                    ("New", "new"),
                    ("In Progress", "in-progress"),
                    ("Done", "done"),
                    ("Cancelled", "cancel"),
                    ("Postponed", "post"),
                ],
                value="new",
                allow_blank=False,
                prompt="Select status",
                id="status_select",
            )
            yield Label("Reminder:")
            yield Input(
                placeholder="e.g., 2h, 30min, tomorrow, 2h repeat", id="reminder_input"
            )
            yield Label("Priority:")
            yield Input(
                placeholder="Priority (number, default: 0)", id="priority_input"
            )
            yield Label("Size:")
            yield Select(
                [
                    ("Undefined", "U"),
                    ("Small", "S"),
                    ("Medium", "M"),
                    ("Large", "L"),
                ],
                value="U",
                allow_blank=False,
                prompt="Select size",
                id="size_select",
            )
            yield Label("Notes:")
            yield TextArea("", id="notes_textarea")
            with Horizontal():
                yield Button("Add", variant="primary", classes="tight", id="add_btn")
                yield Button(
                    "Cancel", variant="default", classes="tight", id="cancel_btn"
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_btn":
            self.app.pop_screen()
        elif event.button.id == "add_btn":
            name_input = self.query_one("#name_input", Input)
            tag_input = self.query_one("#tag_input", Input)
            status_select = self.query_one("#status_select", Select)
            reminder_input = self.query_one("#reminder_input", Input)
            priority_input = self.query_one("#priority_input", Input)
            size_select = self.query_one("#size_select", Select)
            notes_textarea = self.query_one("#notes_textarea", TextArea)

            name = name_input.value.strip()
            if not name:
                return

            tag = tag_input.value.strip() or "default"
            status = status_select.value or "new"
            reminder = reminder_input.value.strip() or None
            notes_text = notes_textarea.text
            notes = [n.strip() for n in notes_text.split("\n") if n.strip()]

            # Parse priority
            try:
                priority = int(priority_input.value.strip() or "0")
            except ValueError:
                self.app.notify("Invalid priority: must be a number", severity="error")
                return

            # Get size
            size = size_select.value or "U"

            # Parse and validate reminder
            reminder_timestamp = None
            reminder_repeat = None
            if reminder:
                parsed_dt, error, repeat_interval = parse_reminder(reminder)
                if error:
                    # Show validation error
                    self.app.notify(
                        f"Invalid reminder format: {error}", severity="error"
                    )
                    return
                reminder_timestamp = parsed_dt
                reminder_repeat = repeat_interval

            # Insert task
            created_on = datetime.now()
            self._tasks_table.insert(
                name=name,
                tag=tag,
                status=status,
                reminder=reminder,
                reminder_timestamp=reminder_timestamp,
                reminder_repeat=reminder_repeat,
                notes=notes,
                created_on=created_on,
                priority=priority,
                size=size,
            )
            self.db.commit()

            self.app.pop_screen()
            # Refresh the main screen
            if hasattr(self.app, "refresh_tasks"):
                self.app.refresh_tasks()


class EditTaskScreen(ModalScreen):
    """Modal screen for editing a task."""

    BINDINGS = [
        ("escape", "dismiss", "Return to home"),
    ]

    CSS = """
    EditTaskScreen {
        align: center middle;
    }

    #dialog {
        width: 90%;
        max-width: 100;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    #dialog Horizontal {
        width: 100%;
        align: center middle;
    }

    #dialog Button {
        margin: 0 1;
    }
    """

    def __init__(self, db, tasks_table, task_row):
        super().__init__()
        self.db = db
        self._tasks_table = tasks_table
        self.task_row = task_row

    def action_dismiss(self) -> None:
        """Return to home screen."""
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(f"Edit Task #{self.task_row.id}")
            yield Label("Name:")
            yield Input(
                value=self.task_row.name, placeholder="Task name", id="name_input"
            )
            yield Label("Tag:")
            yield Input(value=self.task_row.tag, placeholder="Tag", id="tag_input")
            yield Label("Status:")
            yield Select(
                [
                    ("New", "new"),
                    ("In Progress", "in-progress"),
                    ("Done", "done"),
                    ("Cancelled", "cancel"),
                    ("Postponed", "post"),
                ],
                value=self.task_row.status,
                allow_blank=False,
                prompt="Select status",
                id="status_select",
            )
            yield Label("Reminder:")
            yield Input(
                value=self.task_row.reminder or "",
                placeholder="e.g., 2h, 30min, tomorrow, 2h repeat",
                id="reminder_input",
            )
            yield Label("Priority:")
            yield Input(
                value=str(self.task_row.get("priority", 0)),
                placeholder="Priority (number, default: 0)",
                id="priority_input",
            )
            yield Label("Size:")
            yield Select(
                [
                    ("Undefined", "U"),
                    ("Small", "S"),
                    ("Medium", "M"),
                    ("Large", "L"),
                ],
                value=self.task_row.get("size", "U"),
                allow_blank=False,
                prompt="Select size",
                id="size_select",
            )
            yield Label("Notes:")
            notes_text = "\n".join(self.task_row.notes or [])
            yield TextArea(notes_text, id="notes_textarea")
            with Horizontal():
                yield Button("Save", variant="primary", classes="tight", id="save_btn")
                yield Button(
                    "Cancel", variant="default", classes="tight", id="cancel_btn"
                )
            with Horizontal():
                yield Button(
                    "Delay", variant="warning", classes="tight", id="delay_reminder_btn"
                )
                yield Button(
                    "Delete", variant="error", classes="tight", id="delete_btn"
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_btn":
            self.app.pop_screen()
        elif event.button.id == "delay_reminder_btn":
            # Delay reminder by 10 minutes
            if not self.task_row.reminder_timestamp:
                self.app.notify("No active reminder to delay", severity="warning")
                return

            # Parse "10 minutes" to get new timestamp
            parsed_dt, error, _ = parse_reminder("10 minutes")
            if error:
                self.app.notify(f"Error: {error}", severity="error")
                return

            # Update the reminder timestamp (keep existing reminder_repeat)
            self.task_row.update_record(
                reminder="delayed: 10 minutes", reminder_timestamp=parsed_dt
            )
            self.db.commit()

            # Record history
            if hasattr(self.app, "_record_task_history"):
                self.app._record_task_history(self.task_row)

            # Update the input field
            reminder_input = self.query_one("#reminder_input", Input)
            reminder_input.value = "delayed: 10 minutes"

            self.app.notify("Reminder delayed by 10 minutes", severity="information")
        elif event.button.id == "delete_btn":

            def confirm_delete():
                self.task_row.update_record(deleted=True)
                self.db.commit()
                # Record history
                if hasattr(self.app, "_record_task_history"):
                    self.app._record_task_history(self.task_row)
                self.app.pop_screen()
                if hasattr(self.app, "refresh_tasks"):
                    self.app.refresh_tasks()

            self.app.push_screen(
                ConfirmDeleteScreen(self.task_row.name, confirm_delete)
            )
        elif event.button.id == "save_btn":
            name_input = self.query_one("#name_input", Input)
            tag_input = self.query_one("#tag_input", Input)
            status_select = self.query_one("#status_select", Select)
            reminder_input = self.query_one("#reminder_input", Input)
            priority_input = self.query_one("#priority_input", Input)
            size_select = self.query_one("#size_select", Select)
            notes_textarea = self.query_one("#notes_textarea", TextArea)

            name = name_input.value.strip()
            if not name:
                return

            tag = tag_input.value.strip() or "default"
            reminder = reminder_input.value.strip() or None
            notes_text = notes_textarea.text
            notes = [n.strip() for n in notes_text.split("\n") if n.strip()]

            # Check if task is blocked (cannot change status)
            from dolist.dependency import parse_dependencies

            depends_on, _ = parse_dependencies(self.task_row.notes or [])
            if depends_on is not None:
                # Task is blocked - use original status
                status = self.task_row.status
            else:
                # Allow status change
                status = status_select.value or "new"

            # Parse priority
            try:
                priority = int(priority_input.value.strip() or "0")
            except ValueError:
                self.app.notify("Invalid priority: must be a number", severity="error")
                return

            # Get size
            size = size_select.value or "U"

            # Parse and validate reminder only if it changed
            reminder_timestamp = self.task_row.reminder_timestamp
            reminder_repeat = getattr(self.task_row, "reminder_repeat", None)
            if reminder != self.task_row.reminder:
                # Reminder text changed, re-parse and validate it
                reminder_timestamp = None
                reminder_repeat = None
                if reminder:
                    parsed_dt, error, repeat_interval = parse_reminder(reminder)
                    if error:
                        # Show validation error
                        self.app.notify(
                            f"Invalid reminder format: {error}", severity="error"
                        )
                        return
                    reminder_timestamp = parsed_dt
                    reminder_repeat = repeat_interval

            # Update task
            self.task_row.update_record(
                name=name,
                tag=tag,
                status=status,
                reminder=reminder,
                reminder_timestamp=reminder_timestamp,
                reminder_repeat=reminder_repeat,
                notes=notes,
                priority=priority,
                size=size,
            )
            self.db.commit()

            # Record history
            if hasattr(self.app, "_record_task_history"):
                self.app._record_task_history(self.task_row)

            self.app.pop_screen()
            # Refresh the main screen
            if hasattr(self.app, "refresh_tasks"):
                self.app.refresh_tasks()


class TaskHistoryScreen(ModalScreen):
    """Modal screen for viewing task history."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
    ]

    CSS = """
    TaskHistoryScreen {
        align: center middle;
    }

    #history_dialog {
        width: 90%;
        max-width: 120;
        height: 80%;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    #history_dialog Label {
        width: 100%;
        margin: 1 0;
    }

    #history_dialog DataTable {
        width: 100%;
        height: 1fr;
    }

    #history_dialog Button {
        margin: 1 0;
        width: 100%;
    }
    """

    def __init__(self, task_row, history_table, db):
        super().__init__()
        self.task_row = task_row
        self.history_table = history_table
        self.db = db

    def action_dismiss(self) -> None:
        """Close and return to home screen."""
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        with Container(id="history_dialog"):
            yield Label(f"History for Task #{self.task_row.id}: {self.task_row.name}")
            yield DataTable(id="history_table", cursor_type="row")
            yield Button("Close", variant="default", id="close_btn")

    def on_mount(self) -> None:
        """Populate the history table when screen mounts."""
        table = self.query_one("#history_table", DataTable)
        table.add_columns(
            "Changed At",
            "Name",
            "Tag",
            "Status",
            "Priority",
            "Size",
            "Reminder",
            "Notes",
        )

        if self.history_table is None:
            table.add_row("No history available", "", "", "", "", "", "", "")
            return

        # Query history for this task
        try:
            query = self.history_table.task_id == self.task_row.id
            rows = self.db(query).select()

            # Sort by changed_at descending (most recent first)
            rows = sorted(rows, key=lambda r: r.changed_at, reverse=True)

            if not rows:
                table.add_row("No history recorded yet", "", "", "", "", "", "", "")
                return

            for row in rows:
                # Format timestamp
                changed_str = row.changed_at.strftime("%Y-%m-%d %H:%M:%S")

                # Color status
                status_text = row.status or ""
                if row.status == "done":
                    status_text = f"[green]{row.status}[/green]"
                elif row.status == "in-progress":
                    status_text = f"[yellow]{row.status}[/yellow]"
                elif row.status == "cancel":
                    status_text = f"[red]{row.status}[/red]"
                elif row.status == "new":
                    status_text = f"[blue]{row.status}[/blue]"
                elif row.status == "post":
                    status_text = f"[magenta]{row.status}[/magenta]"

                # Get priority and size
                priority = row.get("priority", 0)
                size = row.get("size", "U")

                # Format reminder
                reminder_text = row.reminder or ""

                # Format notes count
                notes_count = len(row.notes) if row.notes else 0

                table.add_row(
                    changed_str,
                    row.name or "",
                    row.tag or "",
                    status_text,
                    str(priority),
                    size,
                    reminder_text,
                    str(notes_count),
                )
        except Exception as e:
            table.add_row(f"Error loading history: {e}", "", "", "", "", "", "", "")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close_btn":
            self.app.pop_screen()


class DatabaseSwitchScreen(ModalScreen):
    """Modal screen for switching databases."""

    BINDINGS = [
        ("escape", "dismiss", "Cancel"),
    ]

    CSS = """
    DatabaseSwitchScreen {
        align: center middle;
    }

    #db_dialog {
        width: 70%;
        max-width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    #db_dialog Label {
        width: 100%;
        margin: 1 0;
    }

    #db_dialog Select {
        width: 100%;
        margin: 1 0;
    }

    #db_dialog Input {
        width: 100%;
        margin: 1 0;
    }

    #db_dialog Horizontal {
        width: 100%;
        align: center middle;
    }

    #db_dialog Button {
        margin: 0 1;
    }
    """

    def __init__(self, config_dir: str, current_db_path: str):
        super().__init__()
        self.config_dir = config_dir
        self.current_db_path = current_db_path

    def action_dismiss(self) -> None:
        """Cancel and return to home screen."""
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        from pathlib import Path

        # Find all .db files in config directory
        config_path = Path(self.config_dir)
        db_files = list(config_path.glob("*.db"))

        # Build options list: (label, value)
        options = [("+ Create New Database", "new")]
        for db_file in sorted(db_files):
            db_name = db_file.name
            if str(db_file) == self.current_db_path:
                options.append((f"{db_name} (current)", str(db_file)))
            else:
                options.append((db_name, str(db_file)))

        with Container(id="db_dialog"):
            yield Label(f"Current: {Path(self.current_db_path).name}")
            yield Label("Select Database:")
            yield Select(
                options=options,
                prompt="Choose a database",
                id="db_select",
                allow_blank=False,
            )
            yield Label("Or create new (enter name):")
            yield Input(placeholder="e.g., work, project", id="new_db_input")
            with Horizontal():
                yield Button("Switch", variant="primary", id="switch_btn")
                yield Button("Cancel", variant="default", id="cancel_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_btn":
            self.app.pop_screen()
        elif event.button.id == "switch_btn":
            from pathlib import Path

            db_select = self.query_one("#db_select", Select)
            new_db_input = self.query_one("#new_db_input", Input)

            # Check if user wants to create a new database
            if new_db_input.value.strip():
                # Create new database
                db_name = new_db_input.value.strip()
                if not db_name.endswith(".db"):
                    db_name += ".db"
                new_db_path = Path(self.config_dir) / db_name

                # Switch to new database
                if hasattr(self.app, "switch_database"):
                    self.app.switch_database(str(new_db_path))
                self.app.pop_screen()
            elif db_select.value and db_select.value != "new":
                # Switch to selected database
                if hasattr(self.app, "switch_database"):
                    self.app.switch_database(db_select.value)
                self.app.pop_screen()
            else:
                self.app.notify(
                    "Please select a database or enter a new name", severity="warning"
                )


class KeyBindingsHelpScreen(ModalScreen):
    """Modal screen showing all available key bindings."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
    ]

    CSS = """
    KeyBindingsHelpScreen {
        align: center middle;
    }

    #help_dialog {
        width: 90%;
        max-width: 100;
        height: 85%;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    #help_dialog Label {
        width: 100%;
        margin: 0 0 1 0;
    }

    #help_title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin: 0 0 1 0;
    }

    #help_dialog DataTable {
        width: 100%;
        height: 1fr;
    }

    #help_dialog Button {
        margin: 1 0 0 0;
        width: 100%;
    }
    """

    def action_dismiss(self) -> None:
        """Close and return to home screen."""
        self.app.pop_screen()

    def compose(self) -> ComposeResult:
        with Container(id="help_dialog"):
            yield Label("DoList TUI - Keyboard Shortcuts", id="help_title")
            yield DataTable(id="help_table", cursor_type="none", zebra_stripes=True)
            yield Button("Close (Esc)", variant="primary", id="close_btn")

    def on_mount(self) -> None:
        """Populate the help table when screen mounts."""
        table = self.query_one("#help_table", DataTable)
        table.add_columns("Key", "Description")

        # Define all keybindings with descriptions
        keybindings = [
            ("Task Management", ""),
            ("a", "Add new task"),
            ("Enter / e", "Edit selected task"),
            ("d", "Delete selected task(s)"),
            ("s", "Cycle task status (new → in-progress → done → post → cancel)"),
            ("Space", "Toggle task selection (for bulk operations)"),
            ("", ""),
            ("Navigation & Search", ""),
            ("/", "Open search overlay (vim-style)"),
            (":", "Open command palette"),
            ("?", "Show this help screen"),
            ("p", "Go to parent task (if task has dependency)"),
            ("c", "Show children tasks"),
            ("", ""),
            ("View & Filters", ""),
            ("r", "Show metrics report"),
            ("F5", "Refresh task list"),
            ("x", "Toggle auto-refresh"),
            ("u", "Switch database"),
            ("h", "View task history"),
            ("Ctrl+a", "Filter: All tasks (cycles: active/inactive/all)"),
            ("Ctrl+n", "Filter: New tasks"),
            ("Ctrl+i", "Filter: In-progress tasks"),
            ("Ctrl+d", "Filter: Done tasks"),
            ("Ctrl+c", "Filter: Cancelled tasks"),
            ("Ctrl+p", "Filter: Postponed tasks"),
            ("", ""),
            ("General", ""),
            ("Esc", "Close modals/overlays/clear search"),
            ("Ctrl+Q", "Quit the TUI"),
        ]

        # Add rows to table with styling
        for key, description in keybindings:
            if not description:
                # Section header
                if key:
                    table.add_row(f"[bold cyan]{key}[/bold cyan]", "")
                else:
                    # Empty row for spacing
                    table.add_row("", "")
            else:
                # Regular keybinding
                table.add_row(f"[yellow]{key}[/yellow]", description)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close_btn":
            self.app.pop_screen()


class ReportScreen(ModalScreen):
    """Modal screen showing task metrics and charts."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("d", "change_period_day", "Day", show=False),
        Binding("w", "change_period_week", "Week", show=False),
        Binding("m", "change_period_month", "Month", show=False),
        Binding("y", "change_period_year", "Year", show=False),
    ]

    CSS = """
    ReportScreen {
        align: center middle;
    }

    #report_dialog {
        width: 95%;
        max-width: 120;
        height: 90%;
        border: thick $primary;
        background: $surface;
        padding: 1;
    }

    #report_title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin: 0 0 1 0;
    }

    #period_selector {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
    }

    #period_buttons {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
    }

    #period_buttons Button {
        margin: 0 1 0 0;
        min-width: 10;
    }

    #report_content {
        width: 100%;
        height: 1fr;
        overflow-y: auto;
    }

    #close_button {
        margin: 1 0 0 0;
        width: 100%;
    }
    """

    def __init__(self, db, tasks_table, filtered_rows=None):
        super().__init__()
        self.db = db
        self.tasks_table = tasks_table
        self.filtered_rows = filtered_rows or []
        self.period = "month"

    def action_dismiss(self) -> None:
        """Close and return to home screen."""
        self.app.pop_screen()

    def action_change_period_day(self) -> None:
        """Change period to day."""
        self.period = "day"
        self.refresh_report()

    def action_change_period_week(self) -> None:
        """Change period to week."""
        self.period = "week"
        self.refresh_report()

    def action_change_period_month(self) -> None:
        """Change period to month."""
        self.period = "month"
        self.refresh_report()

    def action_change_period_year(self) -> None:
        """Change period to year."""
        self.period = "year"
        self.refresh_report()

    def compose(self) -> ComposeResult:
        with Container(id="report_dialog"):
            yield Label("Task Metrics Report", id="report_title")
            with Horizontal(id="period_buttons"):
                yield Button("Day (d)", id="period_day", variant="default")
                yield Button("Week (w)", id="period_week", variant="default")
                yield Button("Month (m)", id="period_month", variant="primary")
                yield Button("Year (y)", id="period_year", variant="default")
            yield Container(id="report_content")
            yield Button("Close (Esc)", variant="primary", id="close_button")

    def on_mount(self) -> None:
        """Generate and display the report when screen mounts."""
        self.refresh_report()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close_button":
            self.app.pop_screen()
        elif event.button.id == "period_day":
            self.period = "day"
            self.refresh_report()
        elif event.button.id == "period_week":
            self.period = "week"
            self.refresh_report()
        elif event.button.id == "period_month":
            self.period = "month"
            self.refresh_report()
        elif event.button.id == "period_year":
            self.period = "year"
            self.refresh_report()

        # Update button variants to show active period
        for button_id in ["period_day", "period_week", "period_month", "period_year"]:
            button = self.query_one(f"#{button_id}", Button)
            if button_id == f"period_{self.period}":
                button.variant = "primary"
            else:
                button.variant = "default"

    def refresh_report(self) -> None:
        """Refresh the report with current period."""
        from .reports import calculate_metrics
        from .taskmodel import Task

        # Convert rows to Task objects
        task_objects = [Task.from_row(self.db, row) for row in self.filtered_rows]

        # Calculate metrics
        metrics = calculate_metrics(task_objects, period=self.period)

        # Generate report content with charts
        from textual_plotext import PlotextPlot

        content_container = self.query_one("#report_content", Container)
        content_container.remove_children()

        # Summary statistics
        summary = Static(
            f"[bold cyan]Total Tasks:[/bold cyan] {metrics['total_tasks']}\n"
            f"[bold cyan]Period:[/bold cyan] {self.period.title()}\n"
        )
        content_container.mount(summary)

        # Status distribution chart
        if metrics["status_totals"]:
            status_label = Static("[bold yellow]Tasks by Status:[/bold yellow]")
            content_container.mount(status_label)

            # Create bar chart data
            statuses = list(metrics["status_totals"].keys())
            counts = list(metrics["status_totals"].values())

            # Define colors for each status
            status_colors = {
                "new": "cyan",
                "in-progress": "yellow",
                "done": "green",
                "cancel": "red",
                "post": "magenta",
            }

            # Create a custom text-based horizontal bar chart with colors
            max_count = max(counts) if counts else 1
            bar_width = 60  # Maximum bar width in characters

            chart_lines = ["[bold white]Tasks by Status[/bold white]", ""]
            for i, (status, count) in enumerate(zip(statuses, counts)):
                color = status_colors.get(status, "white")
                pct = metrics["status_percentages"][status]

                # Calculate bar length
                bar_length = (
                    int((count / max_count) * bar_width) if max_count > 0 else 0
                )
                bar = "█" * bar_length

                # Alternate background for row
                if i % 2 == 0:
                    # With background
                    chart_lines.append(
                        f"[on grey11]{status:12s}[/] [{color}]{bar}[/] [{color} bold]{count:3d}[/] [dim]({pct:.1f}%)[/]"
                    )
                else:
                    # Without background
                    chart_lines.append(
                        f"{status:12s} [{color}]{bar}[/] [{color} bold]{count:3d}[/] [dim]({pct:.1f}%)[/]"
                    )

            content_container.mount(Static("\n".join(chart_lines) + "\n"))

        # Tag distribution chart
        if metrics["tag_totals"]:
            tag_label = Static("[bold yellow]Tasks by Tag:[/bold yellow]")
            content_container.mount(tag_label)

            tags = list(metrics["tag_totals"].keys())
            tag_counts = list(metrics["tag_totals"].values())

            # Use a variety of colors for tags
            tag_colors = ["cyan", "yellow", "green", "magenta", "blue", "red"]

            # Create a custom text-based horizontal bar chart with colors
            max_count = max(tag_counts) if tag_counts else 1
            bar_width = 60  # Maximum bar width in characters

            chart_lines = ["[bold white]Tasks by Tag[/bold white]", ""]
            for i, (tag, count) in enumerate(zip(tags, tag_counts)):
                color = tag_colors[i % len(tag_colors)]
                pct = metrics["tag_percentages"][tag]

                # Calculate bar length
                bar_length = (
                    int((count / max_count) * bar_width) if max_count > 0 else 0
                )
                bar = "█" * bar_length

                # Alternate background for row
                if i % 2 == 0:
                    # With background
                    chart_lines.append(
                        f"[on grey11]{tag:12s}[/] [{color}]{bar}[/] [{color} bold]{count:3d}[/] [dim]({pct:.1f}%)[/]"
                    )
                else:
                    # Without background
                    chart_lines.append(
                        f"{tag:12s} [{color}]{bar}[/] [{color} bold]{count:3d}[/] [dim]({pct:.1f}%)[/]"
                    )

            content_container.mount(Static("\n".join(chart_lines) + "\n"))

        # Tasks over time
        if metrics["total_by_period"] and len(metrics["total_by_period"]) > 1:
            period_label = Static("[bold yellow]Tasks by Period:[/bold yellow]")
            content_container.mount(period_label)

            periods = sorted(metrics["total_by_period"].keys())
            period_counts = [metrics["total_by_period"][p] for p in periods]

            # Use PlotextPlot for line chart
            plot3 = PlotextPlot()
            content_container.mount(plot3)

            # Access plt and create the plot
            plt3 = plot3.plt
            plt3.plot(
                list(range(len(periods))), period_counts, marker="dot", color="cyan"
            )
            plt3.title(f"Tasks Created by {self.period.title()}")

            # Add period breakdown
            breakdown = "\n".join(
                f"  {period}: {count}" for period, count in zip(periods, period_counts)
            )
            content_container.mount(Static(breakdown))


class DoListCommandProvider(Provider):
    """Custom command provider for DoList TUI (Task 4)."""

    # Define available commands as a class constant for reuse
    COMMANDS = [
        (
            "Sort by Name (A-Z)",
            "sort-name-asc",
            "Sort tasks by name in ascending order",
        ),
        (
            "Sort by Name (Z-A)",
            "sort-name-desc",
            "Sort tasks by name in descending order",
        ),
        (
            "Sort by Created (Oldest)",
            "sort-created-asc",
            "Sort tasks by creation date (oldest first)",
        ),
        (
            "Sort by Created (Newest)",
            "sort-created-desc",
            "Sort tasks by creation date (newest first)",
        ),
        (
            "Sort by Status (A-Z)",
            "sort-status-asc",
            "Sort tasks by status in ascending order",
        ),
        (
            "Sort by Status (Z-A)",
            "sort-status-desc",
            "Sort tasks by status in descending order",
        ),
        ("Sort by Tag (A-Z)", "sort-tag-asc", "Sort tasks by tag in ascending order"),
        ("Sort by Tag (Z-A)", "sort-tag-desc", "Sort tasks by tag in descending order"),
        ("Sort by ID (Low-High)", "sort-id-asc", "Sort tasks by ID in ascending order"),
        (
            "Sort by ID (High-Low)",
            "sort-id-desc",
            "Sort tasks by ID in descending order",
        ),
        ("Refresh", "refresh", "Manually refresh the task list"),
        ("Quit", "quit", "Exit the TUI"),
    ]

    def _make_callback(self, command_name: str):
        """Create a callback function for a command.

        This is a separate method to avoid closure issues with lambdas.
        """

        def callback():
            self.app.run_command(command_name)

        return callback

    async def discover(self):
        """Discover commands when palette first opens (improves discoverability)."""
        # Yield all commands when palette opens
        for label, command_name, help_text in self.COMMANDS:
            yield Hit(
                score=1.0,
                match_display=label,
                command=self._make_callback(command_name),
                help=help_text,
            )

    async def search(self, query: str):
        """Search for commands matching the query."""
        matcher = self.matcher(query)

        # Yield Hit objects for each command
        for label, command_name, help_text in self.COMMANDS:
            # Calculate match score
            match_score = matcher.match(label)

            if match_score > 0:
                yield Hit(
                    score=match_score,
                    match_display=label,
                    command=self._make_callback(command_name),
                    help=help_text,
                )


class DoListTUI(App):
    """A Textual TUI for DoList task management."""

    # Task 4: Register command provider
    COMMANDS = App.COMMANDS | {DoListCommandProvider}
    # Note: COMMAND_PALETTE_BINDING sets the key, but we also need explicit binding below
    COMMAND_PALETTE_BINDING = ":"
    # Ensure command palette is enabled
    ENABLE_COMMAND_PALETTE = True
    CSS = """
    Screen {
        background: $surface;
    }

    #main_container {
        width: 100%;
        height: 100%;
        padding: 0;
    }

    #db_path {
        width: 100%;
        height: auto;
        padding: 0 1;
        background: $panel;
        color: $text-muted;
    }

    #search_status {
        width: 100%;
        height: auto;
        padding: 0 1;
        background: $boost;
        color: $text;
    }

    #status_buttons {
        width: 100%;
        height: 1;
        padding: 0;
    }

    #status_buttons Button {
        margin: 0 1 0 0;
        min-width: 8;
        height: 1;
        border: none;
    }

    #tasks_table {
        width: 100%;
        height: 1fr;
    }
    """

    BINDINGS = [
        # Status filter keyboard shortcuts (hidden from footer)
        Binding("ctrl+a", "filter_all", "", show=False),
        Binding("ctrl+n", "filter_new", "", show=False),
        Binding("ctrl+i", "filter_in_progress", "", show=False),
        Binding("ctrl+d", "filter_done", "", show=False),
        Binding("ctrl+c", "filter_cancel", "", show=False),
        Binding("ctrl+p", "filter_post", "", show=False),
        # Visible bindings in footer
        Binding("a", "add_task", "Add"),
        Binding("d", "delete_task", "Del"),
        Binding("e", "edit_task", "Edit"),
        Binding("enter", "edit_task", "Edit", show=False),
        Binding("s", "cycle_status", "Status"),
        Binding("space", "toggle_selection", "Sel", show=False),
        Binding("r", "show_report", "Report"),
        Binding("f5", "refresh", "Refresh", show=False),
        Binding("x", "toggle_autorefresh", "Auto-Refresh", show=False),
        Binding("/", "open_search", "Search"),
        Binding(":", "command_palette", "Commands"),
        Binding("question_mark", "show_help", "Help"),
        Binding("u", "switch_db", "Switch DB", show=False),
        Binding("h", "view_history", "History", show=False),
        Binding("p", "goto_parent", "Parent", show=False),
        Binding("c", "show_children", "Children", show=False),
        Binding("ctrl+q", "quit", "Quit", priority=True),
    ]

    def __init__(self, db, tasks_table, config=None, history_table=None):
        super().__init__()
        self.db = db
        self._tasks_table = tasks_table  # Use underscore prefix to avoid conflicts
        self._history_table = history_table  # History table for tracking changes
        self.current_filter = {
            "tag": None,
            "status": None,
            "search": None,
            "show_all": False,
        }
        self.config = config or {}
        self.config_file = config.get("config_file") if config else None
        self.selected_task_id = config.get("selected_task_id") if config else None
        self.db_path = config.get("db_path", "Unknown") if config else "Unknown"
        self.config_dir = config.get("config_dir", "") if config else ""

        # Task 2: State for status filters
        self.active_status_filters = set()  # Empty = show all active (not done/cancel)

        # All filter mode: 'active', 'inactive', or 'all'
        self.all_filter_mode = "active"  # Default to showing active tasks

        # Task 3: State for search filters
        self.search_filter = {}  # Dict with 'tag', 'status', 'text' keys

        # Task 7: State for sorting and scroll preservation
        self.sort_column = "priority"  # Default sort by priority (as per requirements)
        self.sort_direction = (
            "desc"  # 'asc' or 'desc' - desc for priority to show high priority first
        )
        self.last_scroll_y = 0
        self.last_selected_task_id = None

        # Task 6: State for auto-refresh
        self.autorefresh_enabled = False
        self.autorefresh_timer = None
        self.autorefresh_interval = (
            config.get("autorefresh_interval", 30) if config else 30
        )

        # Multi-selection state
        self.selected_task_ids = set()  # Set of task IDs that are currently selected

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main_container"):
            # Database path display
            yield Static(f"[dim]Database: {self.db_path}[/dim]", id="db_path")

            # Search status display
            yield Static("", id="search_status")

            # Task 2: Status filter toggle buttons with keyboard shortcuts
            with Horizontal(id="status_buttons"):
                yield Button(
                    "^a All (active)",
                    variant="primary",
                    classes="tight",
                    id="status_all",
                )
                yield Button(
                    "^n New", variant="default", classes="tight", id="status_new"
                )
                yield Button(
                    "^i In Progress",
                    variant="default",
                    classes="tight",
                    id="status_in-progress",
                )
                yield Button(
                    "^d Done", variant="default", classes="tight", id="status_done"
                )
                yield Button(
                    "^c Cancel", variant="default", classes="tight", id="status_cancel"
                )
                yield Button(
                    "^p Post", variant="default", classes="tight", id="status_post"
                )

            # Main task table - this should get focus
            yield DataTable(id="tasks_table", cursor_type="row")
        yield Footer()

    def _update_all_button_label(self) -> None:
        """Update the All button label based on current all_filter_mode."""
        try:
            all_btn = self.query_one("#status_all", Button)
            if self.all_filter_mode == "active":
                all_btn.label = "^a All (active)"
            elif self.all_filter_mode == "inactive":
                all_btn.label = "^a All (inactive)"
            elif self.all_filter_mode == "all":
                all_btn.label = "^a All (*)"
        except Exception:
            pass

    def _record_task_history(self, task_row):
        """Record a snapshot of the task to the history table.

        Args:
            task_row: The task row to record
        """
        if self._history_table is None:
            return

        try:
            from datetime import datetime

            self._history_table.insert(
                changed_at=datetime.now(),
                task_id=task_row.id,
                name=task_row.name,
                tag=task_row.tag,
                status=task_row.status,
                reminder=task_row.reminder,
                reminder_timestamp=task_row.reminder_timestamp,
                notes=task_row.notes,
                created_on=task_row.created_on,
                deleted=task_row.deleted,
            )
            self.db.commit()
        except Exception:
            # Don't fail if history recording fails
            pass

    def _update_search_status(self, result_count: int) -> None:
        """Update the search status display based on current filters.

        Args:
            result_count: Number of results shown
        """
        try:
            search_status = self.query_one("#search_status", Static)

            # Build the search filter description
            filter_parts = []

            if "text" in self.search_filter and self.search_filter["text"]:
                filter_parts.append(f"text: '{self.search_filter['text']}'")

            if "name" in self.search_filter and self.search_filter["name"]:
                filter_parts.append(f"name: '{self.search_filter['name']}'")

            if "note" in self.search_filter and self.search_filter["note"]:
                filter_parts.append(f"note: '{self.search_filter['note']}'")

            if "tag" in self.search_filter and self.search_filter["tag"]:
                tags = ", ".join(self.search_filter["tag"])
                filter_parts.append(f"tag: {tags}")

            if "status" in self.search_filter and self.search_filter["status"]:
                statuses = ", ".join(self.search_filter["status"])
                filter_parts.append(f"status: {statuses}")

            if "priority" in self.search_filter and self.search_filter["priority"]:
                filter_parts.append(f"priority: {self.search_filter['priority']}")

            if "size" in self.search_filter and self.search_filter["size"]:
                if isinstance(self.search_filter["size"], list):
                    sizes = ", ".join(self.search_filter["size"])
                    filter_parts.append(f"size: {sizes}")
                else:
                    filter_parts.append(f"size: {self.search_filter['size']}")

            if "under" in self.search_filter and self.search_filter["under"]:
                filter_parts.append(f"under: #{self.search_filter['under']}")

            if filter_parts:
                filter_desc = " | ".join(filter_parts)
                search_status.update(
                    f"[bold cyan]{result_count} results for /{filter_desc}[/bold cyan]"
                )
            else:
                # No active search filter
                search_status.update("")
        except Exception:
            pass

    def on_mount(self) -> None:
        """Set up the table when the app starts."""
        # Load theme from config
        theme = self.config.get("theme", "textual-dark")
        self.theme = theme

        table = self.query_one("#tasks_table", DataTable)
        # Task 5: Add columns (they are clickable by default in Textual)
        # Get columns from config with default fallback
        columns_config = self.config.get(
            "columns",
            [
                "id",
                "name",
                "tag",
                "status",
                "reminder",
                "notes",
                "created",
                "priority",
                "size",
            ],
        )

        # Map column names to display names
        column_display_map = {
            "id": "ID",
            "name": "Name",
            "tag": "Tag",
            "status": "Status",
            "reminder": "Reminder",
            "notes": "Notes",
            "created": "Created",
            "priority": "Priority",
            "size": "Size",
        }

        # Add columns based on configuration
        display_columns = [
            column_display_map.get(col, col.title()) for col in columns_config
        ]
        table.add_columns(*display_columns)

        # Store column configuration for row building
        self.columns_config = columns_config

        self.refresh_tasks()

        # Focus the table by default (Task 1 requirement)
        table.focus()

        # If a specific task was requested, select it and open edit screen
        if self.selected_task_id is not None:
            self._select_and_edit_task(self.selected_task_id)

    def watch_theme(self, theme: str) -> None:
        """Watch for theme changes and persist to config."""
        if self.config_file and theme != self.config.get("theme"):
            self._save_theme(theme)

    def _save_theme(self, theme: str) -> None:
        """Save the current theme to the config file."""
        if not self.config_file:
            return

        try:
            from pathlib import Path

            config_path = Path(self.config_file)

            if config_path.exists():
                # Read current config
                lines = config_path.read_text().split("\n")

                # Update theme line
                updated = False
                for i, line in enumerate(lines):
                    if line.strip().startswith("theme ="):
                        lines[i] = f'theme = "{theme}"'
                        updated = True
                        break

                # If theme line not found, add it to [ui] section
                if not updated:
                    for i, line in enumerate(lines):
                        if line.strip() == "[ui]":
                            # Find the next section or end of file
                            j = i + 1
                            while j < len(lines) and not lines[j].strip().startswith(
                                "["
                            ):
                                j += 1
                            lines.insert(j, f'theme = "{theme}"')
                            updated = True
                            break

                if updated:
                    config_path.write_text("\n".join(lines))
                    self.config["theme"] = theme
        except Exception:
            # Silently fail - don't interrupt the user experience
            pass

    def _select_and_edit_task(self, task_id: int) -> None:
        """Select a specific task in the table and open edit screen.

        Args:
            task_id: The ID of the task to select and edit.
        """
        table = self.query_one("#tasks_table", DataTable)

        # Find the row with this task ID
        for row_index, row_key in enumerate(table.rows):
            row_data = table.get_row_at(row_index)
            if row_data:
                # Extract numeric ID from display (might be "✓ 123" or just "123")
                display_id = str(row_data[0])
                actual_id = int(
                    display_id.split()[-1] if "✓" in display_id else display_id
                )
                if actual_id == task_id:
                    # Move cursor to this row using the move_cursor method
                    table.move_cursor(row=row_index)
                    # Open edit screen
                    task_row = self._tasks_table[task_id]
                    if task_row:
                        self.push_screen(
                            EditTaskScreen(self.db, self._tasks_table, task_row)
                        )
                    break

    def apply_sort(self, rows):
        """Apply current sort to rows (Task 7).

        Args:
            rows: List of database rows to sort

        Returns:
            Sorted list of rows
        """
        if not self.sort_column:
            return list(rows)

        reverse = self.sort_direction == "desc"
        rows_list = list(rows)

        if self.sort_column == "name":
            return sorted(rows_list, key=lambda r: r.name.lower(), reverse=reverse)
        elif self.sort_column == "created":
            return sorted(rows_list, key=lambda r: r.created_on, reverse=reverse)
        elif self.sort_column == "status":
            return sorted(rows_list, key=lambda r: r.status, reverse=reverse)
        elif self.sort_column == "tag":
            return sorted(rows_list, key=lambda r: r.tag.lower(), reverse=reverse)
        elif self.sort_column == "id":
            return sorted(rows_list, key=lambda r: r.id, reverse=reverse)
        elif self.sort_column == "priority":
            # Sort by priority first, then by created_on as secondary sort (newest first)
            return sorted(
                rows_list,
                key=lambda r: (r.get("priority", 0), r.created_on),
                reverse=reverse,
            )
        elif self.sort_column == "size":
            # Sort by size with order: U, S, M, L
            size_order = {"U": 0, "S": 1, "M": 2, "L": 3}
            return sorted(
                rows_list,
                key=lambda r: size_order.get(r.get("size", "U"), 0),
                reverse=reverse,
            )

        return rows_list

    def refresh_tasks(self) -> None:
        """Refresh the task list with state preservation (Task 7)."""
        table = self.query_one("#tasks_table", DataTable)

        # Task 7: Store current state before refresh
        current_cursor_row = table.cursor_row
        if current_cursor_row is not None and current_cursor_row < len(table.rows):
            try:
                row_data = table.get_row_at(current_cursor_row)
                if row_data:
                    # Extract numeric ID from display (might be "✓ 123" or just "123")
                    display_id = str(row_data[0])
                    self.last_selected_task_id = int(
                        display_id.split()[-1] if "✓" in display_id else display_id
                    )
            except Exception:
                self.last_selected_task_id = None

        # Clear table
        table.clear()

        # Build query
        query = self._tasks_table.deleted != True  # noqa: E712

        # Task 3: Apply search filters first (they can override status filters)
        if "status" in self.search_filter and self.search_filter["status"]:
            # Search filter specifies statuses - use those
            query &= self._tasks_table.status.belongs(self.search_filter["status"])
        elif self.active_status_filters:
            # Task 2: If specific statuses are selected, show only those
            query &= self._tasks_table.status.belongs(list(self.active_status_filters))
        else:
            # Use all_filter_mode to determine which tasks to show
            if self.all_filter_mode == "active":
                # Show only active tasks (new, in-progress)
                query &= self._tasks_table.status.belongs(["new", "in-progress"])
            elif self.all_filter_mode == "inactive":
                # Show only inactive tasks (done, cancel, post)
                query &= self._tasks_table.status.belongs(["done", "cancel", "post"])
            # If 'all' mode, don't apply any status filter (show everything)

        # Task 3: Apply specific name search filter
        if "name" in self.search_filter and self.search_filter["name"]:
            query &= self._tasks_table.name.like(f"%{self.search_filter['name']}%")

        # Task 3: Apply tag search filter (OR logic for multiple tags)
        if "tag" in self.search_filter and self.search_filter["tag"]:
            tag_conditions = [
                self._tasks_table.tag == tag for tag in self.search_filter["tag"]
            ]
            query &= reduce(lambda a, b: a | b, tag_conditions)

        # Legacy filter support (will be removed later)
        if self.current_filter.get("tag"):
            query &= self._tasks_table.tag == self.current_filter["tag"]

        if self.current_filter.get("search"):
            search = self.current_filter["search"].lower()
            query &= self._tasks_table.name.like(f"%{search}%")

        # Get rows
        rows = self.db(query).select()

        # Handle general text search (searches both name and notes, with name matches first)
        if "text" in self.search_filter and self.search_filter["text"]:
            name_matches = []
            note_matches = []
            search_text = self.search_filter["text"].lower()

            for row in rows:
                # Check if search term is in name
                if search_text in row.name.lower():
                    name_matches.append(row)
                # Check if search term is in any note
                elif row.notes:
                    for note in row.notes:
                        if search_text in note.lower():
                            note_matches.append(row)
                            break  # Only add once even if multiple notes match

            # Combine with name matches first
            rows = name_matches + note_matches

        # Handle specific note search
        elif "note" in self.search_filter and self.search_filter["note"]:
            note_matches = []
            note_text = self.search_filter["note"].lower()

            for row in rows:
                if row.notes:
                    for task_note in row.notes:
                        if note_text in task_note.lower():
                            note_matches.append(row)
                            break  # Only add once even if multiple notes match

            rows = note_matches

        # Apply priority filter (post-query filtering to support range operators)
        if "priority" in self.search_filter and self.search_filter["priority"]:
            priority_filter = self.search_filter["priority"]
            filtered_rows = []
            for row in rows:
                task_priority = row.get("priority", 0)
                include = False

                # Check for range operators
                if priority_filter.startswith(">="):
                    try:
                        val = int(priority_filter[2:])
                        include = task_priority >= val
                    except ValueError:
                        pass
                elif priority_filter.startswith(">"):
                    try:
                        val = int(priority_filter[1:])
                        include = task_priority > val
                    except ValueError:
                        pass
                elif priority_filter.startswith("<="):
                    try:
                        val = int(priority_filter[2:])
                        include = task_priority <= val
                    except ValueError:
                        pass
                elif priority_filter.startswith("<"):
                    try:
                        val = int(priority_filter[1:])
                        include = task_priority < val
                    except ValueError:
                        pass
                elif priority_filter.startswith("="):
                    try:
                        val = int(priority_filter[1:])
                        include = task_priority == val
                    except ValueError:
                        pass
                else:
                    # Exact match
                    try:
                        val = int(priority_filter)
                        include = task_priority == val
                    except ValueError:
                        pass

                if include:
                    filtered_rows.append(row)

            rows = filtered_rows

        # Apply size filter (post-query filtering)
        if "size" in self.search_filter and self.search_filter["size"]:
            size_filter = self.search_filter["size"]
            filtered_rows = []

            # Handle multiple sizes (list) or single size (string)
            if isinstance(size_filter, list):
                # Normalize sizes
                normalized_sizes = []
                for s in size_filter:
                    s_upper = s.upper()
                    if s_upper in ("SMALL", "MEDIUM", "LARGE", "UNDEFINED"):
                        size_map = {
                            "SMALL": "S",
                            "MEDIUM": "M",
                            "LARGE": "L",
                            "UNDEFINED": "U",
                        }
                        normalized_sizes.append(size_map[s_upper])
                    elif s_upper in ("U", "S", "M", "L"):
                        normalized_sizes.append(s_upper)

                for row in rows:
                    task_size = row.get("size", "U")
                    if task_size in normalized_sizes:
                        filtered_rows.append(row)
            else:
                # Single size
                size_upper = size_filter.upper()
                if size_upper in ("SMALL", "MEDIUM", "LARGE", "UNDEFINED"):
                    size_map = {
                        "SMALL": "S",
                        "MEDIUM": "M",
                        "LARGE": "L",
                        "UNDEFINED": "U",
                    }
                    size_upper = size_map[size_upper]

                if size_upper in ("U", "S", "M", "L"):
                    for row in rows:
                        task_size = row.get("size", "U")
                        if task_size == size_upper:
                            filtered_rows.append(row)

            rows = filtered_rows

        # Apply 'under' filter (for task dependencies)
        if "under" in self.search_filter and self.search_filter["under"]:
            from dolist.dependency import parse_dependencies

            filtered_rows = []
            parent_id = self.search_filter["under"]
            for row in rows:
                row_notes = row.notes or []
                depends_on, under_ids = parse_dependencies(row_notes)
                # Check if this task depends on or is under the specified parent
                if depends_on == parent_id or parent_id in under_ids:
                    filtered_rows.append(row)

            rows = filtered_rows

        # Task 7: Apply current sort
        rows = self.apply_sort(rows)

        # Add rows to table
        now = datetime.now()
        new_selection_index = None
        for idx, row in enumerate(rows):
            # Task 7: Track where the previously selected task appears
            if self.last_selected_task_id and row.id == self.last_selected_task_id:
                new_selection_index = idx

            # Color status
            status_text = row.status
            if row.status == "done":
                status_text = f"[green]{row.status}[/green]"
            elif row.status == "in-progress":
                status_text = f"[yellow]{row.status}[/yellow]"
            elif row.status == "cancel":
                status_text = f"[red]{row.status}[/red]"
            elif row.status == "new":
                status_text = f"[blue]{row.status}[/blue]"
            elif row.status == "post":
                status_text = f"[magenta]{row.status}[/magenta]"

            # Format reminder display
            reminder_display = ""

            # Safeguard: If reminder text exists but timestamp is NULL, try to recalculate
            if row.reminder and not row.reminder_timestamp:
                from dolist.reminder_parser import parse_reminder

                parsed_dt, error, repeat_interval = parse_reminder(row.reminder)
                if not error and parsed_dt:
                    row.update_record(
                        reminder_timestamp=parsed_dt,
                        reminder_repeat=repeat_interval or row.get("reminder_repeat"),
                    )
                    self.db.commit()
                    row._data["reminder_timestamp"] = parsed_dt

            if row.reminder_timestamp:
                # Check if reminder is in the past
                if row.reminder_timestamp < now:
                    # Auto-clear past reminders
                    row.update_record(reminder=None, reminder_timestamp=None)
                    self.db.commit()
                    reminder_display = ""
                else:
                    # Show time until reminder
                    reminder_display = get_time_until(row.reminder_timestamp)
                    # Add (r) indicator for repeating reminders
                    if row.get("reminder_repeat"):
                        reminder_display = f"{reminder_display} (r)"

            # Build row data based on column configuration
            row_data = {}
            row_data["id"] = str(row.id)
            if row.id in self.selected_task_ids:
                row_data["id"] = f"[bold cyan]✓ {row.id}[/bold cyan]"

            row_data["priority"] = str(row.get("priority", 0))
            row_data["size"] = row.get("size", "U")

            # Handle dependency indicators
            from dolist.dependency import get_dependency_display_info, count_children

            dep_info = get_dependency_display_info(row.id, row.notes or [])

            # Build name with dependency prefix
            name_text = row.name
            if dep_info["display_prefix"]:
                name_text = f"{dep_info['display_prefix']} {name_text}"

            # Count children to add suffix
            child_count = count_children(row.id, rows)
            if child_count > 0:
                name_text = f"{name_text} ({child_count})"

            # Apply color based on dependency type
            if dep_info["prefix_type"] == "blocked":
                # Red-ish for blocked tasks
                row_data["name"] = f"[red]{name_text}[/red]"
                status_text = "[red]blocked[/red]"
            elif dep_info["prefix_type"] == "under":
                # Yellow-ish for under tasks
                row_data["name"] = f"[yellow]{name_text}[/yellow]"
            else:
                row_data["name"] = name_text

            row_data["tag"] = row.tag
            row_data["status"] = status_text
            row_data["reminder"] = reminder_display
            row_data["notes"] = str(len(row.notes) if row.notes else 0)
            row_data["created"] = row.created_on.strftime("%d/%m-%H:%M")

            # Build row in configured column order
            ordered_row = [row_data.get(col, "") for col in self.columns_config]

            table.add_row(
                *ordered_row,
                key=str(row.id),
            )

        # Task 7: Restore selection if the task is still visible
        if new_selection_index is not None:
            try:
                table.move_cursor(row=new_selection_index)
            except Exception:
                pass

        # Update search status display with result count
        self._update_search_status(len(rows))

    def action_quit(self) -> None:
        """Quit the application (Task 9: cleanup timers)."""
        # Stop auto-refresh timer if running
        if self.autorefresh_timer:
            self.autorefresh_timer.stop()
            self.autorefresh_timer = None
        self.exit()

    def action_add_task(self) -> None:
        """Show the add task screen."""
        self.push_screen(AddTaskScreen(self.db, self._tasks_table))

    def action_edit_task(self) -> None:
        """Edit the selected task."""
        table = self.query_one("#tasks_table", DataTable)
        if table.cursor_row is not None and table.row_count > 0:
            row_key = table.get_row_at(table.cursor_row)[0]
            # Extract numeric ID from display (might be "✓ 123" or just "123")
            task_id = int(row_key.split()[-1] if "✓" in row_key else row_key)
            task_row = self._tasks_table[task_id]
            if task_row:
                self.push_screen(EditTaskScreen(self.db, self._tasks_table, task_row))

    def action_delete_task(self) -> None:
        """Delete the selected task(s) with confirmation."""
        table = self.query_one("#tasks_table", DataTable)

        # Determine which tasks to delete
        tasks_to_delete = []

        if self.selected_task_ids:
            # Use selected tasks
            for task_id in self.selected_task_ids:
                task_row = self._tasks_table[task_id]
                if task_row:
                    tasks_to_delete.append(task_row)
        else:
            # Use current cursor task
            if table.cursor_row is None or table.row_count == 0:
                self.notify("No task selected", severity="warning")
                return

            row_key = table.get_row_at(table.cursor_row)[0]
            # Extract numeric ID from display (might be "✓ 123" or just "123")
            task_id = int(row_key.split()[-1] if "✓" in row_key else row_key)
            task_row = self._tasks_table[task_id]
            if task_row:
                tasks_to_delete.append(task_row)

        if not tasks_to_delete:
            return

        # Define the confirmation callback
        def confirm_delete():
            for task_row in tasks_to_delete:
                task_row.update_record(deleted=True)
                # Record history
                self._record_task_history(task_row)
            self.db.commit()

            if len(tasks_to_delete) == 1:
                self.notify(
                    f"Task deleted: {tasks_to_delete[0].name}", severity="information"
                )
            else:
                self.notify(
                    f"{len(tasks_to_delete)} tasks deleted", severity="information"
                )

            # Clear selection after bulk delete
            if self.selected_task_ids:
                self.selected_task_ids.clear()

            self.refresh_tasks()

        # Show confirmation dialog
        task_name = tasks_to_delete[0].name if len(tasks_to_delete) == 1 else ""
        self.push_screen(
            ConfirmDeleteScreen(task_name, confirm_delete, len(tasks_to_delete))
        )

    def action_cycle_status(self) -> None:
        """Cycle the status of selected task(s) through: new -> in-progress -> done -> post -> cancel."""
        table = self.query_one("#tasks_table", DataTable)

        # Define the status cycle
        status_cycle = ["new", "in-progress", "done", "post", "cancel"]

        # Determine which tasks to cycle
        tasks_to_cycle = []

        if self.selected_task_ids:
            # Use selected tasks
            for task_id in self.selected_task_ids:
                task_row = self._tasks_table[task_id]
                if task_row:
                    tasks_to_cycle.append(task_row)
        else:
            # Use current cursor task
            if table.cursor_row is None or table.row_count == 0:
                self.notify("No task selected", severity="warning")
                return

            row_key = table.get_row_at(table.cursor_row)[0]
            # Extract numeric ID from display (might be "✓ 123" or just "123")
            task_id = int(row_key.split()[-1] if "✓" in row_key else row_key)
            task_row = self._tasks_table[task_id]
            if task_row:
                tasks_to_cycle.append(task_row)

        if not tasks_to_cycle:
            return

        # Cycle status for all tasks
        status_changes = []
        for task_row in tasks_to_cycle:
            # Check if task is blocked
            from dolist.dependency import parse_dependencies

            depends_on, _ = parse_dependencies(task_row.notes or [])
            if depends_on is not None:
                self.notify(
                    f"Cannot change status of blocked task #{task_row.id}",
                    severity="error",
                )
                continue

            current_status = task_row.status
            try:
                current_index = status_cycle.index(current_status)
                next_index = (current_index + 1) % len(status_cycle)
                next_status = status_cycle[next_index]
            except ValueError:
                # If current status is not in cycle, default to first status
                next_status = status_cycle[0]

            # Update the task status
            task_row.update_record(status=next_status)
            status_changes.append((current_status, next_status))

            # Record history
            self._record_task_history(task_row)

        self.db.commit()

        # Show notification only if changes were made
        if status_changes:
            if len(status_changes) == 1:
                self.notify(
                    f"Status changed: {status_changes[0][0]} → {status_changes[0][1]}",
                    severity="information",
                )
            else:
                self.notify(
                    f"Status cycled for {len(status_changes)} task(s)",
                    severity="information",
                )

            # Clear selection after bulk operation
            if self.selected_task_ids:
                self.selected_task_ids.clear()

            # Refresh the task list to show the change
            self.refresh_tasks()

    def action_toggle_selection(self) -> None:
        """Toggle selection of the current task using space bar."""
        table = self.query_one("#tasks_table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            return

        # Get the task ID from the row key (not the displayed value)
        # The key is set when we add_row() and should be the plain task ID as string
        current_row = table.cursor_row
        row_key = list(table.rows)[current_row]
        task_id = int(row_key.value)

        # Toggle selection
        was_selected = task_id in self.selected_task_ids
        if was_selected:
            self.selected_task_ids.remove(task_id)
        else:
            self.selected_task_ids.add(task_id)

        # Refresh to show the selection change
        self.refresh_tasks()

        # Move cursor: down if selecting, up if deselecting
        total_rows = table.row_count
        if not was_selected:
            # Just selected - move cursor down to next row if available
            if current_row < total_rows - 1:
                table.move_cursor(row=current_row + 1)
        else:
            # Just deselected - move cursor up to previous row if available
            if current_row > 0:
                table.move_cursor(row=current_row - 1)

        # Show status in notification
        count = len(self.selected_task_ids)
        if count > 0:
            self.notify(f"{count} task(s) selected", severity="information")

    def action_refresh(self) -> None:
        """Refresh the task list."""
        self.refresh_tasks()

    def action_show_report(self) -> None:
        """Show the report screen with metrics and charts."""
        # Get all currently visible rows from the table
        table = self.query_one("#tasks_table", DataTable)
        visible_rows = []

        for row_key in table.rows:
            task_id = int(row_key.value)
            task_row = self._tasks_table[task_id]
            if task_row:
                visible_rows.append(task_row)

        # Show the report screen with filtered data
        self.push_screen(ReportScreen(self.db, self._tasks_table, visible_rows))

    def action_toggle_autorefresh(self) -> None:
        """Toggle auto-refresh on/off (Task 6)."""
        if self.autorefresh_enabled:
            # Disable auto-refresh
            self.autorefresh_enabled = False
            if self.autorefresh_timer:
                self.autorefresh_timer.stop()
                self.autorefresh_timer = None
            self.notify("✓ Auto-refresh disabled", severity="warning")
        else:
            # Enable auto-refresh
            self.autorefresh_enabled = True
            if self.autorefresh_interval > 0:
                self.autorefresh_timer = self.set_interval(
                    self.autorefresh_interval, self.refresh_tasks
                )
            self.notify(
                f"✓ Auto-refresh enabled ({self.autorefresh_interval}s)",
                severity="information",
            )

    def action_open_search(self) -> None:
        """Open the search overlay (Task 3)."""
        self.push_screen(SearchOverlay())

    def action_switch_db(self) -> None:
        """Open the database switch screen."""
        if not self.config_dir:
            self.notify("Config directory not set", severity="error")
            return
        self.push_screen(DatabaseSwitchScreen(self.config_dir, self.db_path))

    def action_view_history(self) -> None:
        """View history for the selected task."""
        table = self.query_one("#tasks_table", DataTable)
        if table.cursor_row is None or not table.rows:
            self.notify("No task selected", severity="warning")
            return

        # Get the task ID from the row key
        row_key = list(table.rows)[table.cursor_row]
        task_id = int(row_key.value)
        task_row = self._tasks_table[task_id]

        if not task_row:
            self.notify("Task not found", severity="error")
            return

        self.push_screen(TaskHistoryScreen(task_row, self._history_table, self.db))

    def action_show_help(self) -> None:
        """Show the help screen with all key bindings."""
        self.push_screen(KeyBindingsHelpScreen())

    def action_goto_parent(self) -> None:
        """Navigate to parent task (if current task has dependency)."""
        table = self.query_one("#tasks_table", DataTable)
        if table.cursor_row is None or not table.rows:
            self.notify("No task selected", severity="warning")
            return

        # Get the task ID from the row key
        row_key = list(table.rows)[table.cursor_row]
        task_id = int(row_key.value)
        task_row = self._tasks_table[task_id]

        if not task_row:
            self.notify("Task not found", severity="error")
            return

        # Check for parent task in notes
        from dolist.dependency import parse_dependencies

        depends_on, under_ids = parse_dependencies(task_row.notes or [])

        parent_id = (
            depends_on
            if depends_on is not None
            else (min(under_ids) if under_ids else None)
        )

        if parent_id is None:
            self.notify("Task has no parent", severity="warning")
            return

        # Find parent task in current view
        for idx, row in enumerate(table.rows):
            if int(row.value) == parent_id:
                table.move_cursor(row=idx)
                self.notify(
                    f"Navigated to parent task #{parent_id}", severity="information"
                )
                return

        self.notify(f"Parent task #{parent_id} not in current view", severity="warning")

    def action_show_children(self) -> None:
        """Show children tasks (tasks that depend on or are under current task)."""
        table = self.query_one("#tasks_table", DataTable)
        if table.cursor_row is None or not table.rows:
            self.notify("No task selected", severity="warning")
            return

        # Get the task ID from the row key
        row_key = list(table.rows)[table.cursor_row]
        task_id = int(row_key.value)

        # Apply filter to show only children
        self.search_filter = {"under": task_id}
        self.refresh_tasks()
        self.notify(f"Showing children of task #{task_id}", severity="information")

    def switch_database(self, new_db_path: str) -> None:
        """Switch to a different database.

        Args:
            new_db_path: Full path to the new database file
        """
        from pathlib import Path
        from .database import Database
        from .database import FieldDef

        try:
            # Create database URI from path
            db_filename = Path(new_db_path).name
            db_uri = f"sqlite://{db_filename}"
            config_dir = str(Path(new_db_path).parent)

            # Initialize new database connection
            new_db = Database(db_uri, folder=config_dir)
            new_tasks_table = new_db.define_table(
                "dolist_tasks",
                FieldDef("name", "string"),
                FieldDef("tag", "string"),
                FieldDef("status", "string"),
                FieldDef("reminder", "string"),
                FieldDef("reminder_timestamp", "datetime"),
                FieldDef("reminder_repeat", "string"),
                FieldDef("notes", "list:string"),
                FieldDef("created_on", "datetime"),
                FieldDef("deleted", "boolean", default=False),
                FieldDef("priority", "integer", default=0),
                FieldDef("size", "string", default="U"),
            )

            # Also initialize history table
            _new_history_table = new_db.define_table(
                "dolist_task_history",
                FieldDef("changed_at", "datetime"),
                FieldDef("task_id", "integer"),
                FieldDef("name", "string"),
                FieldDef("tag", "string"),
                FieldDef("status", "string"),
                FieldDef("reminder", "string"),
                FieldDef("reminder_timestamp", "datetime"),
                FieldDef("reminder_repeat", "string"),
                FieldDef("notes", "list:string"),
                FieldDef("created_on", "datetime"),
                FieldDef("deleted", "boolean", default=False),
                FieldDef("priority", "integer", default=0),
                FieldDef("size", "string", default="U"),
            )

            # Switch to new database
            self.db = new_db
            self._tasks_table = new_tasks_table
            self.db_path = new_db_path

            # Update database path display
            try:
                db_path_widget = self.query_one("#db_path", Static)
                db_path_widget.update(f"[dim]Database: {self.db_path}[/dim]")
            except Exception:
                pass

            # Clear selections and filters
            self.selected_task_ids.clear()
            self.search_filter = {}
            self.active_status_filters.clear()
            self.all_filter_mode = "active"

            # Refresh task list
            self.refresh_tasks()

            self.notify(
                f"Switched to: {Path(new_db_path).name}", severity="information"
            )
        except Exception as e:
            self.notify(f"Error switching database: {e}", severity="error")

    def action_filter_all(self) -> None:
        """Toggle 'All' status filter (Ctrl+A)."""
        try:
            btn = self.query_one("#status_all", Button)
            btn.press()
        except Exception:
            pass

    def action_filter_new(self) -> None:
        """Toggle 'New' status filter (Ctrl+N)."""
        try:
            btn = self.query_one("#status_new", Button)
            btn.press()
        except Exception:
            pass

    def action_filter_in_progress(self) -> None:
        """Toggle 'In Progress' status filter (Ctrl+I)."""
        try:
            btn = self.query_one("#status_in-progress", Button)
            btn.press()
        except Exception:
            pass

    def action_filter_done(self) -> None:
        """Toggle 'Done' status filter (Ctrl+D)."""
        try:
            btn = self.query_one("#status_done", Button)
            btn.press()
        except Exception:
            pass

    def action_filter_cancel(self) -> None:
        """Toggle 'Cancel' status filter (Ctrl+C)."""
        try:
            btn = self.query_one("#status_cancel", Button)
            btn.press()
        except Exception:
            pass

    def action_filter_post(self) -> None:
        """Toggle 'Post' status filter (Ctrl+P)."""
        try:
            btn = self.query_one("#status_post", Button)
            btn.press()
        except Exception:
            pass

    def apply_search_filter(self, filters: dict, live: bool = False) -> None:
        """Apply search filter and refresh tasks.

        Args:
            filters: Dict with 'tag', 'status', 'text' keys
            live: If True, this is live filtering (don't update status buttons)
        """
        self.search_filter = filters

        # Task 3: If search includes status filter, update status toggle buttons
        if not live and "status" in filters and filters["status"]:
            # Update active_status_filters to match search
            self.active_status_filters = set(filters["status"])

            # Update button variants
            for status in ["new", "in-progress", "done", "cancel", "post"]:
                btn_id = f"status_{status}"
                try:
                    btn = self.query_one(f"#{btn_id}", Button)
                    if status in self.active_status_filters:
                        btn.variant = "primary"
                    else:
                        btn.variant = "default"
                except Exception:
                    pass

            # Update "All" button
            try:
                all_btn = self.query_one("#status_all", Button)
                all_btn.variant = "default"
            except Exception:
                pass

        self.refresh_tasks()

    def clear_search_filter(self) -> None:
        """Clear search filter and refresh tasks."""
        self.search_filter = {}
        self.refresh_tasks()

    def run_command(self, command: str) -> None:
        """Execute a custom command (Task 4).

        Args:
            command: The command name to execute
        """
        if command == "refresh":
            self.action_refresh()
        elif command == "quit":
            self.action_quit()
        elif command.startswith("sort-"):
            # Parse sort command: sort-{column}-{direction}
            parts = command.split("-")
            if len(parts) == 3:
                _, column, direction = parts
                self.sort_column = column
                self.sort_direction = direction

                # Notify user of sort change
                direction_text = "ascending" if direction == "asc" else "descending"
                self.notify(
                    f"Sorted by {column} ({direction_text})", severity="information"
                )

                # Refresh with new sort
                self.refresh_tasks()

    def _restore_table_focus(self) -> None:
        """Restore focus to the tasks table (Task 9)."""
        try:
            table = self.query_one("#tasks_table", DataTable)
            table.focus()
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        # Task 2: Handle status filter toggle buttons
        if event.button.id and event.button.id.startswith("status_"):
            status = event.button.id.replace("status_", "")

            # Handle "All" button - cycle through active/inactive/all modes
            if status == "all":
                # Cycle through: active -> inactive -> all -> active
                if self.all_filter_mode == "active":
                    self.all_filter_mode = "inactive"
                elif self.all_filter_mode == "inactive":
                    self.all_filter_mode = "all"
                else:  # 'all'
                    self.all_filter_mode = "active"

                # Clear individual status filters when using All button
                self.active_status_filters.clear()

                # Reset all status buttons to default
                for btn_id in [
                    "status_new",
                    "status_in-progress",
                    "status_done",
                    "status_cancel",
                    "status_post",
                ]:
                    try:
                        btn = self.query_one(f"#{btn_id}", Button)
                        btn.variant = "default"
                    except Exception:
                        pass

                # Set "All" button to primary
                event.button.variant = "primary"

                # Update the button label
                self._update_all_button_label()

                self.refresh_tasks()
                return

            # Handle individual status buttons
            if status in self.active_status_filters:
                # Remove from filter
                self.active_status_filters.remove(status)
                event.button.variant = "default"
            else:
                # Add to filter
                self.active_status_filters.add(status)
                event.button.variant = "primary"

            # Update "All" button state
            try:
                all_btn = self.query_one("#status_all", Button)
                if self.active_status_filters:
                    # Individual filters are active, deactivate All button
                    all_btn.variant = "default"
                else:
                    # No individual filters, revert to All button with current mode
                    all_btn.variant = "primary"
                    self._update_all_button_label()
            except Exception:
                pass

            self.refresh_tasks()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        self.action_edit_task()

    def on_data_table_header_selected(self, event: DataTable.HeaderSelected) -> None:
        """Handle column header click for sorting (Task 5)."""
        # Map column labels to internal column names
        column_map = {
            "ID": "id",
            "Name": "name",
            "Tag": "tag",
            "Status": "status",
            "Created": "created",
            "Priority": "priority",
            "Size": "size",
            "Reminder": "reminder",
            "Notes": "notes",
        }

        # Get the column label from the event - use .label which is a Rich Text object
        column_label = (
            str(event.label.plain)
            if hasattr(event.label, "plain")
            else str(event.label)
        )

        # Debug: notify that event was received
        # self.notify(f"Header clicked: {column_label}", severity="information")

        # Don't sort by Reminder or Notes columns
        if column_label in ["Reminder", "Notes"]:
            self.notify("Cannot sort by this column", severity="warning")
            return

        column_name = column_map.get(column_label)
        if not column_name:
            self.notify(f"Unknown column: {column_label}", severity="error")
            return

        # Toggle sort: if same column, toggle direction; if new column, start with asc
        if self.sort_column == column_name:
            self.sort_direction = "desc" if self.sort_direction == "asc" else "asc"
        else:
            self.sort_column = column_name
            self.sort_direction = "asc"

        # Notify user of sort change
        direction_text = "ascending" if self.sort_direction == "asc" else "descending"
        self.notify(
            f"Sorting by {column_name} ({direction_text})", severity="information"
        )

        # Refresh with new sort
        self.refresh_tasks()

    def _update_column_headers(self) -> None:
        """Update column headers to show sort indicators (Task 5)."""
        # This method is no longer needed - we'll use a different approach
        # Instead of clearing and re-adding columns, we'll just refresh the table
        # The sort indicators will be shown in the status bar or via notifications
        pass


def run_tui(db, tasks_table, config=None, history_table=None):
    """Run the Textual TUI.

    Args:
        db: Database connection
        tasks_table: Tasks table object
        config: Configuration dict with 'theme' and 'config_file' keys
        history_table: TaskHistory table object (optional)
    """
    app = DoListTUI(db, tasks_table, config, history_table)
    try:
        app.run()
    except Exception as e:
        # Ensure terminal is reset even if there's an error
        import sys

        print(f"\nError in TUI: {e}", file=sys.stderr)
        print("Terminal should be restored.", file=sys.stderr)
        raise
