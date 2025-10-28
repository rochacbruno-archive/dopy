#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Textual TUI for DoList task management."""

from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
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
from rich.text import Text
from .reminder_parser import parse_reminder, format_reminder, get_time_until
from functools import reduce


def parse_search(search_text: str) -> dict:
    """Parse search syntax into filter dict.

    Examples:
        /test → {'text': 'test'}
        /tag=work → {'tag': ['work']}
        /tag=work,personal → {'tag': ['work', 'personal']}
        /status=new,done → {'status': ['new', 'done']}
        /tag=work test → {'tag': ['work'], 'text': 'test'}
        /status=new tag=urgent bug → {'status': ['new'], 'tag': ['urgent'], 'text': 'bug'}
    """
    filters = {}
    remaining_text = []

    parts = search_text.strip().split()

    for part in parts:
        if '=' in part:
            key, value = part.split('=', 1)
            if key == 'tag':
                filters['tag'] = value.split(',')
            elif key == 'status':
                filters['status'] = value.split(',')
        else:
            remaining_text.append(part)

    if remaining_text:
        filters['text'] = ' '.join(remaining_text)

    return filters


class ConfirmDeleteScreen(ModalScreen):
    """Modal screen for confirming task deletion."""

    def __init__(self, task_name: str, on_confirm):
        super().__init__()
        self.task_name = task_name
        self.on_confirm = on_confirm

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
            yield Label(f"Delete task?")
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
            yield Input(placeholder="Search: text, tag=value, status=value", id="search_input")

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
            yield Input(placeholder="e.g., 2h, 30min, tomorrow, next week", id="reminder_input")
            yield Label("Notes:")
            yield TextArea("", id="notes_textarea")
            with Horizontal():
                yield Button("Add", variant="primary", classes="tight", id="add_btn")
                yield Button("Cancel", variant="default", classes="tight", id="cancel_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_btn":
            self.app.pop_screen()
        elif event.button.id == "add_btn":
            name_input = self.query_one("#name_input", Input)
            tag_input = self.query_one("#tag_input", Input)
            status_select = self.query_one("#status_select", Select)
            reminder_input = self.query_one("#reminder_input", Input)
            notes_textarea = self.query_one("#notes_textarea", TextArea)

            name = name_input.value.strip()
            if not name:
                return

            tag = tag_input.value.strip() or "default"
            status = status_select.value or "new"
            reminder = reminder_input.value.strip() or None
            notes_text = notes_textarea.text
            notes = [n.strip() for n in notes_text.split("\n") if n.strip()]

            # Parse and validate reminder
            reminder_timestamp = None
            if reminder:
                parsed_dt, error = parse_reminder(reminder)
                if error:
                    # Show validation error
                    self.app.notify(f"Invalid reminder format: {error}", severity="error")
                    return
                reminder_timestamp = parsed_dt

            # Insert task
            created_on = datetime.now()
            self._tasks_table.insert(
                name=name,
                tag=tag,
                status=status,
                reminder=reminder,
                reminder_timestamp=reminder_timestamp,
                notes=notes,
                created_on=created_on,
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
            yield Input(value=self.task_row.name, placeholder="Task name", id="name_input")
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
                placeholder="e.g., 2h, 30min, tomorrow, next week",
                id="reminder_input",
            )
            yield Label("Notes:")
            notes_text = "\n".join(self.task_row.notes or [])
            yield TextArea(notes_text, id="notes_textarea")
            with Horizontal():
                yield Button("Save", variant="primary", classes="tight", id="save_btn")
                yield Button("Cancel", variant="default", classes="tight", id="cancel_btn")
            with Horizontal():
                yield Button("Delay", variant="warning", classes="tight", id="delay_reminder_btn")
                yield Button("Delete", variant="error", classes="tight", id="delete_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_btn":
            self.app.pop_screen()
        elif event.button.id == "delay_reminder_btn":
            # Delay reminder by 10 minutes
            if not self.task_row.reminder_timestamp:
                self.app.notify("No active reminder to delay", severity="warning")
                return

            # Parse "10 minutes" to get new timestamp
            parsed_dt, error = parse_reminder("10 minutes")
            if error:
                self.app.notify(f"Error: {error}", severity="error")
                return

            # Update the reminder timestamp
            self.task_row.update_record(reminder="delayed: 10 minutes", reminder_timestamp=parsed_dt)
            self.db.commit()

            # Update the input field
            reminder_input = self.query_one("#reminder_input", Input)
            reminder_input.value = "delayed: 10 minutes"

            self.app.notify(f"Reminder delayed by 10 minutes", severity="information")
        elif event.button.id == "delete_btn":
            def confirm_delete():
                self.task_row.update_record(deleted=True)
                self.db.commit()
                self.app.pop_screen()
                if hasattr(self.app, "refresh_tasks"):
                    self.app.refresh_tasks()

            self.app.push_screen(ConfirmDeleteScreen(self.task_row.name, confirm_delete))
        elif event.button.id == "save_btn":
            name_input = self.query_one("#name_input", Input)
            tag_input = self.query_one("#tag_input", Input)
            status_select = self.query_one("#status_select", Select)
            reminder_input = self.query_one("#reminder_input", Input)
            notes_textarea = self.query_one("#notes_textarea", TextArea)

            name = name_input.value.strip()
            if not name:
                return

            tag = tag_input.value.strip() or "default"
            status = status_select.value or "new"
            reminder = reminder_input.value.strip() or None
            notes_text = notes_textarea.text
            notes = [n.strip() for n in notes_text.split("\n") if n.strip()]

            # Parse and validate reminder only if it changed
            reminder_timestamp = self.task_row.reminder_timestamp
            if reminder != self.task_row.reminder:
                # Reminder text changed, re-parse and validate it
                reminder_timestamp = None
                if reminder:
                    parsed_dt, error = parse_reminder(reminder)
                    if error:
                        # Show validation error
                        self.app.notify(f"Invalid reminder format: {error}", severity="error")
                        return
                    reminder_timestamp = parsed_dt

            # Update task
            self.task_row.update_record(
                name=name,
                tag=tag,
                status=status,
                reminder=reminder,
                reminder_timestamp=reminder_timestamp,
                notes=notes,
            )
            self.db.commit()

            self.app.pop_screen()
            # Refresh the main screen
            if hasattr(self.app, "refresh_tasks"):
                self.app.refresh_tasks()


class DoListCommandProvider(Provider):
    """Custom command provider for DoList TUI (Task 4)."""

    # Define available commands as a class constant for reuse
    COMMANDS = [
        ("Sort by Name (A-Z)", "sort-name-asc", "Sort tasks by name in ascending order"),
        ("Sort by Name (Z-A)", "sort-name-desc", "Sort tasks by name in descending order"),
        ("Sort by Created (Oldest)", "sort-created-asc", "Sort tasks by creation date (oldest first)"),
        ("Sort by Created (Newest)", "sort-created-desc", "Sort tasks by creation date (newest first)"),
        ("Sort by Status (A-Z)", "sort-status-asc", "Sort tasks by status in ascending order"),
        ("Sort by Status (Z-A)", "sort-status-desc", "Sort tasks by status in descending order"),
        ("Sort by Tag (A-Z)", "sort-tag-asc", "Sort tasks by tag in ascending order"),
        ("Sort by Tag (Z-A)", "sort-tag-desc", "Sort tasks by tag in descending order"),
        ("Sort by ID (Low-High)", "sort-id-asc", "Sort tasks by ID in ascending order"),
        ("Sort by ID (High-Low)", "sort-id-desc", "Sort tasks by ID in descending order"),
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
                help=help_text
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
                    help=help_text
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
        Binding("a", "add_task", "Add Task"),
        Binding("e", "edit_task", "Edit"),
        Binding("enter", "edit_task", "Edit", show=False),
        Binding("s", "cycle_status", "Cycle Status"),
        Binding("r", "refresh", "Refresh"),
        Binding("x", "toggle_autorefresh", "Auto-Refresh"),
        Binding("/", "open_search", "Search"),
        Binding(":", "command_palette", "Commands"),
        Binding("ctrl+q", "quit", "Quit", priority=True),
    ]

    def __init__(self, db, tasks_table, config=None):
        super().__init__()
        self.db = db
        self._tasks_table = tasks_table  # Use underscore prefix to avoid conflicts
        self.current_filter = {"tag": None, "status": None, "search": None, "show_all": False}
        self.config = config or {}
        self.config_file = config.get('config_file') if config else None
        self.selected_task_id = config.get('selected_task_id') if config else None

        # Task 2: State for status filters
        self.active_status_filters = set()  # Empty = show all active (not done/cancel)

        # All filter mode: 'active', 'inactive', or 'all'
        self.all_filter_mode = 'active'  # Default to showing active tasks

        # Task 3: State for search filters
        self.search_filter = {}  # Dict with 'tag', 'status', 'text' keys

        # Task 7: State for sorting and scroll preservation
        self.sort_column = None  # e.g., 'name', 'created', 'status'
        self.sort_direction = 'asc'  # 'asc' or 'desc'
        self.last_scroll_y = 0
        self.last_selected_task_id = None

        # Task 6: State for auto-refresh
        self.autorefresh_enabled = False
        self.autorefresh_timer = None
        self.autorefresh_interval = config.get('autorefresh_interval', 30) if config else 30

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main_container"):
            # Task 2: Status filter toggle buttons with keyboard shortcuts
            with Horizontal(id="status_buttons"):
                yield Button("^a All (active)", variant="primary", classes="tight", id="status_all")
                yield Button("^n New", variant="default", classes="tight", id="status_new")
                yield Button("^i In Progress", variant="default", classes="tight", id="status_in-progress")
                yield Button("^d Done", variant="default", classes="tight", id="status_done")
                yield Button("^c Cancel", variant="default", classes="tight", id="status_cancel")
                yield Button("^p Post", variant="default", classes="tight", id="status_post")

            # Main task table - this should get focus
            yield DataTable(id="tasks_table", cursor_type="row")
        yield Footer()

    def _update_all_button_label(self) -> None:
        """Update the All button label based on current all_filter_mode."""
        try:
            all_btn = self.query_one("#status_all", Button)
            if self.all_filter_mode == 'active':
                all_btn.label = "^a All (active)"
            elif self.all_filter_mode == 'inactive':
                all_btn.label = "^a All (inactive)"
            elif self.all_filter_mode == 'all':
                all_btn.label = "^a All (*)"
        except:
            pass

    def on_mount(self) -> None:
        """Set up the table when the app starts."""
        # Load theme from config
        theme = self.config.get('theme', 'textual-dark')
        self.theme = theme

        table = self.query_one("#tasks_table", DataTable)
        # Task 5: Add columns (they are clickable by default in Textual)
        table.add_columns("ID", "Name", "Tag", "Status", "Reminder", "Notes", "Created")
        self.refresh_tasks()

        # Focus the table by default (Task 1 requirement)
        table.focus()

        # If a specific task was requested, select it and open edit screen
        if self.selected_task_id is not None:
            self._select_and_edit_task(self.selected_task_id)

    def watch_theme(self, theme: str) -> None:
        """Watch for theme changes and persist to config."""
        if self.config_file and theme != self.config.get('theme'):
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
                lines = config_path.read_text().split('\n')

                # Update theme line
                updated = False
                for i, line in enumerate(lines):
                    if line.strip().startswith('theme ='):
                        lines[i] = f'theme = "{theme}"'
                        updated = True
                        break

                # If theme line not found, add it to [ui] section
                if not updated:
                    for i, line in enumerate(lines):
                        if line.strip() == '[ui]':
                            # Find the next section or end of file
                            j = i + 1
                            while j < len(lines) and not lines[j].strip().startswith('['):
                                j += 1
                            lines.insert(j, f'theme = "{theme}"')
                            updated = True
                            break

                if updated:
                    config_path.write_text('\n'.join(lines))
                    self.config['theme'] = theme
        except Exception as e:
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
            if row_data and str(row_data[0]) == str(task_id):
                # Move cursor to this row using the move_cursor method
                table.move_cursor(row=row_index)
                # Open edit screen
                task_row = self._tasks_table[task_id]
                if task_row:
                    self.push_screen(EditTaskScreen(self.db, self._tasks_table, task_row))
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

        reverse = self.sort_direction == 'desc'
        rows_list = list(rows)

        if self.sort_column == 'name':
            return sorted(rows_list, key=lambda r: r.name.lower(), reverse=reverse)
        elif self.sort_column == 'created':
            return sorted(rows_list, key=lambda r: r.created_on, reverse=reverse)
        elif self.sort_column == 'status':
            return sorted(rows_list, key=lambda r: r.status, reverse=reverse)
        elif self.sort_column == 'tag':
            return sorted(rows_list, key=lambda r: r.tag.lower(), reverse=reverse)
        elif self.sort_column == 'id':
            return sorted(rows_list, key=lambda r: r.id, reverse=reverse)

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
                    self.last_selected_task_id = int(row_data[0])
            except:
                self.last_selected_task_id = None

        # Clear table
        table.clear()

        # Build query
        query = self._tasks_table.deleted != True

        # Task 3: Apply search filters first (they can override status filters)
        if 'status' in self.search_filter and self.search_filter['status']:
            # Search filter specifies statuses - use those
            query &= self._tasks_table.status.belongs(self.search_filter['status'])
        elif self.active_status_filters:
            # Task 2: If specific statuses are selected, show only those
            query &= self._tasks_table.status.belongs(list(self.active_status_filters))
        else:
            # Use all_filter_mode to determine which tasks to show
            if self.all_filter_mode == 'active':
                # Show only active tasks (new, in-progress)
                query &= self._tasks_table.status.belongs(["new", "in-progress"])
            elif self.all_filter_mode == 'inactive':
                # Show only inactive tasks (done, cancel, post)
                query &= self._tasks_table.status.belongs(["done", "cancel", "post"])
            # If 'all' mode, don't apply any status filter (show everything)

        # Task 3: Apply text search filter
        if 'text' in self.search_filter and self.search_filter['text']:
            query &= self._tasks_table.name.like(f"%{self.search_filter['text']}%")

        # Task 3: Apply tag search filter (OR logic for multiple tags)
        if 'tag' in self.search_filter and self.search_filter['tag']:
            tag_conditions = [
                self._tasks_table.tag == tag
                for tag in self.search_filter['tag']
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
            reminder_display = ''
            if row.reminder_timestamp:
                # Check if reminder is in the past
                if row.reminder_timestamp < now:
                    # Auto-clear past reminders
                    row.update_record(reminder=None, reminder_timestamp=None)
                    self.db.commit()
                    reminder_display = ''
                else:
                    # Show time until reminder
                    reminder_display = get_time_until(row.reminder_timestamp)

            table.add_row(
                str(row.id),
                row.name,
                row.tag,
                status_text,
                reminder_display,
                str(len(row.notes) if row.notes else 0),
                row.created_on.strftime("%d/%m-%H:%M"),
                key=str(row.id),
            )

        # Task 7: Restore selection if the task is still visible
        if new_selection_index is not None:
            try:
                table.move_cursor(row=new_selection_index)
            except:
                pass

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
        if table.cursor_row is not None:
            row_key = table.get_row_at(table.cursor_row)[0]
            task_row = self._tasks_table[int(row_key)]
            if task_row:
                self.push_screen(EditTaskScreen(self.db, self._tasks_table, task_row))

    def action_cycle_status(self) -> None:
        """Cycle the status of the selected task through: new -> in-progress -> done -> post -> cancel."""
        table = self.query_one("#tasks_table", DataTable)
        if table.cursor_row is None:
            self.notify("No task selected", severity="warning")
            return

        # Get the selected task
        row_key = table.get_row_at(table.cursor_row)[0]
        task_row = self._tasks_table[int(row_key)]
        if not task_row:
            return

        # Define the status cycle
        status_cycle = ["new", "in-progress", "done", "post", "cancel"]

        # Get current status and find next status
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
        self.db.commit()

        # Show notification
        self.notify(f"Status changed: {current_status} → {next_status}", severity="information")

        # Refresh the task list to show the change
        self.refresh_tasks()

    def action_refresh(self) -> None:
        """Refresh the task list."""
        self.refresh_tasks()

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
                    self.autorefresh_interval,
                    self.refresh_tasks
                )
            self.notify(f"✓ Auto-refresh enabled ({self.autorefresh_interval}s)", severity="information")

    def action_open_search(self) -> None:
        """Open the search overlay (Task 3)."""
        self.push_screen(SearchOverlay())

    def action_filter_all(self) -> None:
        """Toggle 'All' status filter (Ctrl+A)."""
        try:
            btn = self.query_one("#status_all", Button)
            btn.press()
        except:
            pass

    def action_filter_new(self) -> None:
        """Toggle 'New' status filter (Ctrl+N)."""
        try:
            btn = self.query_one("#status_new", Button)
            btn.press()
        except:
            pass

    def action_filter_in_progress(self) -> None:
        """Toggle 'In Progress' status filter (Ctrl+I)."""
        try:
            btn = self.query_one("#status_in-progress", Button)
            btn.press()
        except:
            pass

    def action_filter_done(self) -> None:
        """Toggle 'Done' status filter (Ctrl+D)."""
        try:
            btn = self.query_one("#status_done", Button)
            btn.press()
        except:
            pass

    def action_filter_cancel(self) -> None:
        """Toggle 'Cancel' status filter (Ctrl+C)."""
        try:
            btn = self.query_one("#status_cancel", Button)
            btn.press()
        except:
            pass

    def action_filter_post(self) -> None:
        """Toggle 'Post' status filter (Ctrl+P)."""
        try:
            btn = self.query_one("#status_post", Button)
            btn.press()
        except:
            pass

    def apply_search_filter(self, filters: dict, live: bool = False) -> None:
        """Apply search filter and refresh tasks.

        Args:
            filters: Dict with 'tag', 'status', 'text' keys
            live: If True, this is live filtering (don't update status buttons)
        """
        self.search_filter = filters

        # Task 3: If search includes status filter, update status toggle buttons
        if not live and 'status' in filters and filters['status']:
            # Update active_status_filters to match search
            self.active_status_filters = set(filters['status'])

            # Update button variants
            for status in ["new", "in-progress", "done", "cancel", "post"]:
                btn_id = f"status_{status}"
                try:
                    btn = self.query_one(f"#{btn_id}", Button)
                    if status in self.active_status_filters:
                        btn.variant = "primary"
                    else:
                        btn.variant = "default"
                except:
                    pass

            # Update "All" button
            try:
                all_btn = self.query_one("#status_all", Button)
                all_btn.variant = "default"
            except:
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
                self.notify(f"Sorted by {column} ({direction_text})", severity="information")

                # Refresh with new sort
                self.refresh_tasks()

    def _restore_table_focus(self) -> None:
        """Restore focus to the tasks table (Task 9)."""
        try:
            table = self.query_one("#tasks_table", DataTable)
            table.focus()
        except:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        # Task 2: Handle status filter toggle buttons
        if event.button.id and event.button.id.startswith("status_"):
            status = event.button.id.replace("status_", "")

            # Handle "All" button - cycle through active/inactive/all modes
            if status == "all":
                # Cycle through: active -> inactive -> all -> active
                if self.all_filter_mode == 'active':
                    self.all_filter_mode = 'inactive'
                elif self.all_filter_mode == 'inactive':
                    self.all_filter_mode = 'all'
                else:  # 'all'
                    self.all_filter_mode = 'active'

                # Clear individual status filters when using All button
                self.active_status_filters.clear()

                # Reset all status buttons to default
                for btn_id in ["status_new", "status_in-progress", "status_done", "status_cancel", "status_post"]:
                    try:
                        btn = self.query_one(f"#{btn_id}", Button)
                        btn.variant = "default"
                    except:
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
            except:
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
        }

        # Get the column label from the event - use .label which is a Rich Text object
        column_label = str(event.label.plain) if hasattr(event.label, 'plain') else str(event.label)

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
            self.sort_direction = 'desc' if self.sort_direction == 'asc' else 'asc'
        else:
            self.sort_column = column_name
            self.sort_direction = 'asc'

        # Notify user of sort change
        direction_text = "ascending" if self.sort_direction == 'asc' else "descending"
        self.notify(f"Sorting by {column_name} ({direction_text})", severity="information")

        # Refresh with new sort
        self.refresh_tasks()

    def _update_column_headers(self) -> None:
        """Update column headers to show sort indicators (Task 5)."""
        # This method is no longer needed - we'll use a different approach
        # Instead of clearing and re-adding columns, we'll just refresh the table
        # The sort indicators will be shown in the status bar or via notifications
        pass


def run_tui(db, tasks_table, config=None):
    """Run the Textual TUI.

    Args:
        db: Database connection
        tasks_table: Tasks table object
        config: Configuration dict with 'theme' and 'config_file' keys
    """
    app = DoListTUI(db, tasks_table, config)
    try:
        app.run()
    except Exception as e:
        # Ensure terminal is reset even if there's an error
        import sys
        print(f"\nError in TUI: {e}", file=sys.stderr)
        print("Terminal should be restored.", file=sys.stderr)
        raise
