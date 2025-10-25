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
from rich.text import Text


class AddTaskScreen(ModalScreen):
    """Modal screen for adding a new task."""

    CSS = """
    AddTaskScreen {
        align: center middle;
    }

    #dialog {
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }

    #dialog Input {
        margin: 1 0;
    }

    #dialog Select {
        margin: 1 0;
    }

    #dialog Horizontal {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 1 0;
    }

    #dialog Button {
        margin: 0 1;
    }
    """

    def __init__(self, db, tasks_table):
        super().__init__()
        self.db = db
        self._tasks_table = tasks_table

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label("Add New Task")
            yield Input(placeholder="Task name", id="name_input")
            yield Input(placeholder="Tag (default: default)", id="tag_input")
            yield Select(
                [
                    ("New", "new"),
                    ("Working", "working"),
                    ("Done", "done"),
                    ("Cancel", "cancel"),
                    ("Post", "post"),
                ],
                value="new",
                id="status_select",
            )
            yield Input(placeholder="Reminder (optional)", id="reminder_input")
            with Horizontal():
                yield Button("Add", variant="primary", id="add_btn")
                yield Button("Cancel", variant="default", id="cancel_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_btn":
            self.app.pop_screen()
        elif event.button.id == "add_btn":
            name_input = self.query_one("#name_input", Input)
            tag_input = self.query_one("#tag_input", Input)
            status_select = self.query_one("#status_select", Select)
            reminder_input = self.query_one("#reminder_input", Input)

            name = name_input.value.strip()
            if not name:
                return

            tag = tag_input.value.strip() or "default"
            status = status_select.value or "new"
            reminder = reminder_input.value.strip() or None

            # Insert task
            created_on = datetime.now()
            self._tasks_table.insert(
                name=name,
                tag=tag,
                status=status,
                reminder=reminder,
                created_on=created_on,
            )
            self.db.commit()

            self.app.pop_screen()
            # Refresh the main screen
            if hasattr(self.app, "refresh_tasks"):
                self.app.refresh_tasks()


class EditTaskScreen(ModalScreen):
    """Modal screen for editing a task."""

    CSS = """
    EditTaskScreen {
        align: center middle;
    }

    #dialog {
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
        padding: 1 2;
    }

    #dialog Input {
        margin: 1 0;
    }

    #dialog Select {
        margin: 1 0;
    }

    #dialog TextArea {
        height: 6;
        margin: 1 0;
    }

    #dialog Horizontal {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 1 0;
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

    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Label(f"Edit Task #{self.task_row.id}")
            yield Input(value=self.task_row.name, placeholder="Task name", id="name_input")
            yield Input(value=self.task_row.tag, placeholder="Tag", id="tag_input")
            yield Select(
                [
                    ("New", "new"),
                    ("Working", "working"),
                    ("Done", "done"),
                    ("Cancel", "cancel"),
                    ("Post", "post"),
                ],
                value=self.task_row.status,
                id="status_select",
            )
            yield Input(
                value=self.task_row.reminder or "",
                placeholder="Reminder (optional)",
                id="reminder_input",
            )
            notes_text = "\n".join(self.task_row.notes or [])
            yield TextArea(notes_text, id="notes_textarea")
            with Horizontal():
                yield Button("Save", variant="primary", id="save_btn")
                yield Button("Delete", variant="error", id="delete_btn")
                yield Button("Cancel", variant="default", id="cancel_btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_btn":
            self.app.pop_screen()
        elif event.button.id == "delete_btn":
            self.task_row.update_record(deleted=True)
            self.db.commit()
            self.app.pop_screen()
            if hasattr(self.app, "refresh_tasks"):
                self.app.refresh_tasks()
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

            # Update task
            self.task_row.update_record(
                name=name,
                tag=tag,
                status=status,
                reminder=reminder,
                notes=notes,
            )
            self.db.commit()

            self.app.pop_screen()
            # Refresh the main screen
            if hasattr(self.app, "refresh_tasks"):
                self.app.refresh_tasks()


class DoListTUI(App):
    """A Textual TUI for DoList task management."""

    CSS = """
    Screen {
        background: $surface;
    }

    #main_container {
        width: 100%;
        height: 100%;
        padding: 1;
    }

    #tasks_table {
        width: 100%;
        height: 1fr;
    }

    #filter_container {
        width: 100%;
        height: auto;
        padding: 0 0 1 0;
    }

    #filter_container Horizontal {
        width: 100%;
        height: auto;
    }

    #filter_container Input {
        width: 1fr;
        margin: 0 1 0 0;
    }

    #filter_container Select {
        width: 20;
        margin: 0 1 0 0;
    }

    #button_container {
        width: 100%;
        height: auto;
        align: center middle;
        padding: 1 0 0 0;
    }

    #button_container Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", priority=True),
        Binding("escape", "quit", "Quit", priority=True),
        Binding("a", "add_task", "Add Task"),
        Binding("r", "refresh", "Refresh"),
        ("enter", "edit_task", "Edit"),
    ]

    def __init__(self, db, tasks_table):
        super().__init__()
        self.db = db
        self._tasks_table = tasks_table  # Use underscore prefix to avoid conflicts
        self.current_filter = {"tag": None, "status": None, "search": None, "show_all": False}

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main_container"):
            with Vertical(id="filter_container"):
                yield Label("Filters:")
                with Horizontal():
                    yield Input(placeholder="Search...", id="search_input")
                    yield Select(
                        [
                            ("All Tags", None),
                            ("default", "default"),
                        ],
                        value=None,
                        id="tag_filter",
                    )
                    yield Select(
                        [
                            ("Active Only", False),
                            ("All Statuses", True),
                        ],
                        value=False,
                        id="show_all_filter",
                    )
            yield DataTable(id="tasks_table", cursor_type="row")
            with Horizontal(id="button_container"):
                yield Button("Add Task (a)", variant="primary", id="add_task_btn")
                yield Button("Edit (Enter)", variant="default", id="edit_task_btn")
                yield Button("Refresh (r)", variant="default", id="refresh_btn")
                yield Button("Quit (Esc/Ctrl+Q)", variant="error", id="quit_btn")
        yield Footer()

    def on_mount(self) -> None:
        """Set up the table when the app starts."""
        table = self.query_one("#tasks_table", DataTable)
        table.add_columns("ID", "Name", "Tag", "Status", "Reminder", "Notes", "Created")
        self.refresh_tasks()

    def refresh_tasks(self) -> None:
        """Refresh the task list."""
        table = self.query_one("#tasks_table", DataTable)
        table.clear()

        # Build query
        query = self._tasks_table.deleted != True

        # Apply filters
        if not self.current_filter["show_all"]:
            query &= ~self._tasks_table.status.belongs(["done", "cancel", "post"])

        if self.current_filter["tag"]:
            query &= self._tasks_table.tag == self.current_filter["tag"]

        if self.current_filter["search"]:
            search = self.current_filter["search"].lower()
            query &= self._tasks_table.name.like(f"%{search}%")

        # Get rows
        rows = self.db(query).select()

        # Update tag filter options dynamically
        all_tags = set()
        for row in self.db(self._tasks_table.deleted != True).select():
            all_tags.add(row.tag)

        tag_filter = self.query_one("#tag_filter", Select)
        tag_options = [("All Tags", None)]
        for tag in sorted(all_tags):
            tag_options.append((tag, tag))
        # Note: Textual Select doesn't support dynamic options easily, skipping for now

        # Add rows to table
        for row in rows:
            # Color status
            status_text = row.status
            if row.status == "done":
                status_text = f"[green]{row.status}[/green]"
            elif row.status == "working":
                status_text = f"[yellow]{row.status}[/yellow]"
            elif row.status == "cancel":
                status_text = f"[red]{row.status}[/red]"
            elif row.status == "new":
                status_text = f"[blue]{row.status}[/blue]"

            table.add_row(
                str(row.id),
                row.name,
                row.tag,
                status_text,
                row.reminder or "",
                str(len(row.notes) if row.notes else 0),
                row.created_on.strftime("%d/%m-%H:%M"),
                key=str(row.id),
            )

    def action_quit(self) -> None:
        """Quit the application."""
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

    def action_refresh(self) -> None:
        """Refresh the task list."""
        self.refresh_tasks()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "quit_btn":
            self.action_quit()
        elif event.button.id == "add_task_btn":
            self.action_add_task()
        elif event.button.id == "edit_task_btn":
            self.action_edit_task()
        elif event.button.id == "refresh_btn":
            self.action_refresh()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes for filtering."""
        if event.input.id == "search_input":
            self.current_filter["search"] = event.value.strip() or None
            self.refresh_tasks()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes for filtering."""
        if event.select.id == "tag_filter":
            self.current_filter["tag"] = event.value
            self.refresh_tasks()
        elif event.select.id == "show_all_filter":
            self.current_filter["show_all"] = event.value
            self.refresh_tasks()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        self.action_edit_task()


def run_tui(db, tasks_table):
    """Run the Textual TUI."""
    app = DoListTUI(db, tasks_table)
    try:
        app.run()
    except Exception as e:
        # Ensure terminal is reset even if there's an error
        import sys
        print(f"\nError in TUI: {e}", file=sys.stderr)
        print("Terminal should be restored.", file=sys.stderr)
        raise
