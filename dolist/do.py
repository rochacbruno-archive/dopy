#!/usr/bin/env python
#-*- coding:utf-8 -*-

r""" ____        _ _     _
|  _ \  ___ | (_)___| |_
| | | |/ _ \| | / __| __|
| |_| | (_) | | \__ \ |_
|____/ \___/|_|_|___/\__|

DoList - To-Do list on Command Line Interface
"""

from typing import Optional, Annotated
import cyclopts
from cyclopts import Parameter
from rich.console import Console
from rich import print as rprint
from .rich_table import print_table
from .database import Database, FieldDef
import os
import datetime
from .taskmodel import Task
from .colors import *
from .tui import run_tui
from pathlib import Path
import sys
import shutil
from .reminder_parser import parse_reminder, format_reminder, get_time_until
from .service import install_systemd_service, run_service_loop, trigger_reminder
import json

# tomllib is only available in Python 3.11+, use tomli for older versions
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        # Fallback if tomli is not installed
        tomllib = None

# XDG Base Directory support with backwards compatibility
def get_config_dir():
    """Get config directory with XDG support and backwards compatibility."""
    # Check for XDG_CONFIG_HOME first (Linux/Unix standard)
    xdg_config = os.getenv('XDG_CONFIG_HOME')
    if xdg_config:
        config_dir = Path(xdg_config) / 'dolist'
    else:
        # Default to ~/.config/dolist on Unix-like systems
        config_dir = Path.home() / '.config' / 'dolist'

    # Backwards compatibility: check if old ~/.dopy exists
    old_dir = Path.home() / '.dopy'
    if old_dir.exists() and not config_dir.exists():
        return old_dir

    return config_dir

def get_legacy_config_file():
    """Get legacy config file path for backwards compatibility."""
    return Path.home() / '.dopyrc'

BASEDIR = get_config_dir()

# Create config directory if it doesn't exist
if not BASEDIR.exists():
    BASEDIR.mkdir(parents=True, exist_ok=True)

# New TOML config file
CONFIGFILE = BASEDIR / 'config.toml'
LEGACY_CONFIGFILE = get_legacy_config_file()

# Migration and config loading
if LEGACY_CONFIGFILE.exists() and not CONFIGFILE.exists():
    # Migrate from legacy config
    try:
        legacy_config = eval(LEGACY_CONFIGFILE.read_text())
        # Create new TOML config
        toml_content = f'''# DoList Configuration File
# This file uses TOML format

[database]
# Database directory (default: ~/.config/dolist or $XDG_CONFIG_HOME/dolist)
dir = "{BASEDIR}"
# Database URI (default: sqlite://tasks.db)
uri = "sqlite://tasks.db"

[ui]
# TUI theme (default: textual-dark)
# Available themes: textual-dark, textual-light, nord, gruvbox, catppuccin, dracula, monokai, solarized-light, solarized-dark
theme = "textual-dark"
'''
        CONFIGFILE.write_text(toml_content)
        CONFIG = {'dbdir': str(BASEDIR), 'dburi': 'sqlite://tasks.db', 'theme': 'textual-dark'}
        print(f"Migrated legacy config from {LEGACY_CONFIGFILE} to {CONFIGFILE}")
    except Exception as e:
        print(f"Warning: Could not migrate legacy config: {e}")
        CONFIG = {'dbdir': str(BASEDIR), 'dburi': 'sqlite://tasks.db'}
elif CONFIGFILE.exists():
    # Load TOML config
    try:
        if tomllib is None:
            raise ImportError("TOML library not available")
        with open(CONFIGFILE, 'rb') as f:
            toml_config = tomllib.load(f)
        CONFIG = {
            'dbdir': toml_config.get('database', {}).get('dir', str(BASEDIR)),
            'dburi': toml_config.get('database', {}).get('uri', 'sqlite://tasks.db'),
            'theme': toml_config.get('ui', {}).get('theme', 'textual-dark'),
            'autorefresh_interval': toml_config.get('tui', {}).get('autorefresh_interval', 30),
            'reminder_cmd': toml_config.get('reminders', {}).get('reminder_cmd')
        }
    except Exception as e:
        print(f"Warning: Could not load config file: {e}")
        CONFIG = {'dbdir': str(BASEDIR), 'dburi': 'sqlite://tasks.db', 'theme': 'textual-dark', 'autorefresh_interval': 30}
else:
    # Create default TOML config
    default_config = f'''# DoList Configuration File
# This file uses TOML format

[database]
# Database directory (default: ~/.config/dolist or $XDG_CONFIG_HOME/dolist)
dir = "{BASEDIR}"
# Database URI (default: sqlite://tasks.db)
uri = "sqlite://tasks.db"

[ui]
# TUI theme (default: textual-dark)
# Available themes: textual-dark, textual-light, nord, gruvbox, catppuccin, dracula, monokai, solarized-light, solarized-dark
theme = "textual-dark"

[tui]
# Auto-refresh interval in seconds (default: 30)
# Set to 0 to disable auto-refresh
autorefresh_interval = 30

[reminders]
# Custom command to handle reminders (optional)
# If set, this command will be called with task JSON piped to stdin
# If not set, uses notify-send by default
# reminder_cmd = "/path/to/custom/reminder/handler"
'''
    CONFIGFILE.write_text(default_config)
    CONFIG = {'dbdir': str(BASEDIR), 'dburi': 'sqlite://tasks.db', 'theme': 'textual-dark', 'autorefresh_interval': 30}

# Support legacy database location (~/.dopy/dopy.db)
legacy_db_path = Path.home() / '.dopy' / 'dopy.db'
if legacy_db_path.exists() and 'dopy.db' in CONFIG['dburi']:
    # Use legacy database location
    CONFIG['dbdir'] = str(Path.home() / '.dopy')
    CONFIG['dburi'] = 'sqlite://dopy.db'

DBDIR = CONFIG['dbdir']
DBURI = CONFIG['dburi']

console = Console()

# Global database connection
db = None
tasks = None


SHELLDOC = r"""
     ____        _ _     _
    |  _ \  ___ | (_)___| |_
    | | | |/ _ \| | / __| __|
    | |_| | (_) | | \__ \ |_
    |____/ \___/|_|_|___/\__|

[Interactive Python REPL for DoList]

Available objects:
  • tasklist  - List of all active Task objects
  • db        - Database connection
  • tasks     - Tasks table

Quick examples:
  >>> tasklist                    # Show all tasks
  >>> tasklist[0].name            # Get first task name
  >>> tasklist[0].update_status('done')  # Update task status
  >>> [t.name for t in tasklist]  # List all task names

Task management:
  >>> task = tasklist[0]          # Get a task
  >>> task.name                   # View property
  >>> task.update_name("New")     # Update name
  >>> task.add_note("A note")     # Add a note
  >>> task.delete()               # Delete task

Tips:
  • Use Tab for auto-completion
  • Use F2 to toggle between Vi/Emacs mode
  • Use Ctrl+D or quit() to exit

"""


def database(DBURI):
    """Initialize database connection."""
    _db = Database(DBURI, folder=DBDIR)
    tasks = _db.define_table("dolist_tasks",
        FieldDef("name", "string"),
        FieldDef("tag", "string"),
        FieldDef("status", "string"),
        FieldDef("reminder", "string"),
        FieldDef("reminder_timestamp", "datetime"),
        FieldDef("notes", "list:string"),
        FieldDef("created_on", "datetime"),
        FieldDef("deleted", "boolean", default=False),
    )
    return _db, tasks


def init_db(use_db: Optional[str] = None):
    """Initialize global database connection."""
    global db, tasks
    dburi = DBURI
    if use_db:
        # Replace database name in URI
        dburi = dburi.replace('tasks', use_db).replace('dopy', use_db)
    db, tasks = database(dburi)


# Create the Cyclopts app
app = cyclopts.App(
    name="dolist",
    help="DoList - To-Do list on Command Line Interface",
    version="0.4.0",
)


@app.default
def default_action(
    *tokens,
    rm: Optional[int] = None,
    use: Optional[str] = None,
    actions: bool = False,
):
    """Default action - Launch TUI or perform task action.

    When called without arguments, launches the TUI.
    When called with an ID and optional action, performs the task action.

    Args:
        tokens: Task ID and action with optional arguments.
        rm: Index of note to remove (for 'note' action with --rm flag).
        use: Database name to use (optional).
        actions: Show list of available actions.

    Examples:
        dolist                   # Launch TUI
        dolist --actions         # List available actions
        dolist 1                 # Edit task 1 interactively
        dolist 1 done            # Mark task 1 as done
        dolist 2 remind tomorrow # Set reminder on task 2
        dolist 3 delay 1 hour    # Delay reminder by 1 hour (unquoted)
        dolist 4 start           # Start working on task 4
        dolist 5 note This is a note  # Add note (unquoted)
    """
    global db, tasks
    init_db(use)

    # Show available actions if --actions flag is set
    if actions:
        console.print("[bold cyan]Available Actions for Tasks:[/bold cyan]\n")
        console.print("[yellow]Status Management:[/yellow]")
        console.print("  • [green]start, in-progress[/green]  - Mark task as in-progress")
        console.print("  • [green]done[/green]                 - Mark task as done")
        console.print("  • [green]cancel[/green]               - Mark task as cancelled")
        console.print("  • [green]new[/green]                  - Mark task as new")
        console.print("  • [green]post[/green]                 - Mark task as postponed")
        console.print()
        console.print("[yellow]Reminder Management:[/yellow]")
        console.print("  • [green]remind <time>[/green]        - Set a reminder (e.g., 'tomorrow', '2 hours')")
        console.print("  • [green]delay [time][/green]         - Delay reminder (default: 10 minutes)")
        console.print("  • [green]clear-reminder[/green]       - Clear reminder from task")
        console.print()
        console.print("[yellow]Note Management:[/yellow]")
        console.print("  • [green]note <text>[/green]          - Add a note to task")
        console.print("  • [green]note --rm <index>[/green]    - Remove note by index")
        console.print()
        console.print("[yellow]Task Operations:[/yellow]")
        console.print("  • [green]show[/green]                 - Show task details with notes")
        console.print("  • [green]edit[/green]                 - Open TUI with task selected for editing")
        console.print("  • [green]get[/green]                  - Open interactive Python shell for task")
        console.print("  • [green]delete, rm[/green]           - Delete task (soft delete)")
        console.print()
        console.print("[yellow]Usage Examples:[/yellow]")
        console.print("  dolist 1            # Show task 1 details")
        console.print("  dolist 1 done       # Mark task 1 as done")
        console.print("  dolist 2 remind tomorrow")
        console.print("  dolist 3 note This is a note")
        console.print("  dolist 4 delay 1 hour")
        console.print("  dolist 5 edit       # Open TUI and edit task 5")
        return

    # Parse tokens
    if not tokens:
        # No arguments - launch TUI
        tui_config = {
            'theme': CONFIG.get('theme', 'textual-dark'),
            'config_file': str(CONFIGFILE)
        }
        try:
            run_tui(db, tasks, tui_config)
        except KeyboardInterrupt:
            console.print("\n[yellow]TUI interrupted by user[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error running TUI: {e}[/red]")
            console.print("[yellow]Your terminal should be restored.[/yellow]")
            raise
        return

    # First token should be the task ID
    try:
        id = int(tokens[0])
    except (ValueError, IndexError):
        console.print("[red]First argument must be a task ID (number)[/red]")
        return

    # Task action mode
    row = tasks[id]
    if not row:
        rprint("[red]Task not found[/red]")
        return

    # If no action provided, show the task
    if len(tokens) == 1:
        _show_task(row)
        return

    # Extract action and remaining arguments
    action = tokens[1].lower()
    action_args = list(tokens[2:]) if len(tokens) > 2 else []

    # Handle different actions
    if action in ['start', 'in-progress']:
        row.update_record(status='in-progress')
        db.commit()
        console.print(f"[green]✓ Task {id} marked as in-progress[/green]")
        console.print(f"[cyan]  {row.name}[/cyan]")

    elif action == 'done':
        row.update_record(status='done')
        db.commit()
        console.print(f"[green]✓ Task {id} marked as done[/green]")
        console.print(f"[cyan]  {row.name}[/cyan]")

    elif action == 'cancel':
        row.update_record(status='cancel')
        db.commit()
        console.print(f"[green]✓ Task {id} marked as cancelled[/green]")
        console.print(f"[cyan]  {row.name}[/cyan]")

    elif action == 'new':
        row.update_record(status='new')
        db.commit()
        console.print(f"[green]✓ Task {id} marked as new[/green]")
        console.print(f"[cyan]  {row.name}[/cyan]")

    elif action == 'post':
        row.update_record(status='post')
        db.commit()
        console.print(f"[green]✓ Task {id} marked as postponed[/green]")
        console.print(f"[cyan]  {row.name}[/cyan]")

    elif action in ['rm', 'delete']:
        row.update_record(deleted=True)
        db.commit()
        console.print(f"[green]✓ Task {id} deleted[/green]")
        console.print(f"[cyan]  {row.name}[/cyan]")

    elif action == 'clear-reminder':
        row.update_record(reminder=None, reminder_timestamp=None)
        db.commit()
        console.print(f"[green]✓ Reminder cleared from task {id}[/green]")
        console.print(f"[cyan]  {row.name}[/cyan]")

    elif action == 'remind':
        if not action_args:
            console.print("[red]Error: remind requires a time argument[/red]")
            console.print("Usage: dolist <id> remind <time>")
            console.print("Example: dolist 1 remind 2 hours")
            return

        reminder_time = ' '.join(action_args)
        parsed_dt, error = parse_reminder(reminder_time)
        if error:
            console.print(f"[red]Error parsing reminder: {error}[/red]")
            return

        row.update_record(reminder=reminder_time, reminder_timestamp=parsed_dt)
        db.commit()
        console.print(f"[green]✓ Reminder set for task {id}[/green]")
        console.print(f"[cyan]  {row.name}[/cyan]")
        console.print(f"[yellow]  Due: {format_reminder(parsed_dt)}[/yellow]")

    elif action == 'delay':
        # Check if task has a reminder
        if not row.reminder_timestamp:
            console.print(f"[red]Task {id} has no active reminder[/red]")
            console.print("[yellow]Set a reminder first using: dolist {id} remind <time>[/yellow]".replace('{id}', str(id)))
            return

        # Default to 10 minutes if no time specified
        delay_time = ' '.join(action_args) if action_args else "10 minutes"

        parsed_dt, error = parse_reminder(delay_time)
        if error:
            console.print(f"[red]Error parsing delay time: {error}[/red]")
            return

        row.update_record(reminder=f"delayed: {delay_time}", reminder_timestamp=parsed_dt)
        db.commit()
        console.print(f"[green]✓ Reminder delayed for task {id}[/green]")
        console.print(f"[cyan]  {row.name}[/cyan]")
        console.print(f"[yellow]  New due time: {format_reminder(parsed_dt)}[/yellow]")

    elif action == 'note':
        row.notes = row.notes or []

        # Handle note addition (from args or stdin)
        if action_args:
            note_text = ' '.join(action_args)
            row.update_record(notes=row.notes + [note_text])
            db.commit()
            console.print(f"[green]✓ Note added to task {id}[/green]")
            console.print(f"[cyan]  {row.name}[/cyan]")
        elif rm is None and not sys.stdin.isatty():
            # Read note from stdin (but only if not removing a note)
            stdin_content = sys.stdin.read().strip()
            if stdin_content:
                row.update_record(notes=row.notes + [stdin_content])
                db.commit()
                console.print(f"[green]✓ Note added to task {id} from stdin[/green]")
                console.print(f"[cyan]  {row.name}[/cyan]")

        # Handle note removal
        if rm is not None:
            try:
                del row.notes[rm]
                row.update_record(notes=row.notes)
                db.commit()
                console.print(f"[green]✓ Note {rm} removed from task {id}[/green]")
                console.print(f"[cyan]  {row.name}[/cyan]")
            except (IndexError, TypeError):
                console.print("[bold red]Note not found[/bold red]")
                return

        # Show task with notes
        _show_task(row)

    elif action == 'show':
        _show_task(row)

    elif action == 'get':
        _get_task_shell(row)

    elif action == 'edit':
        # Open TUI with this task selected
        tui_config = {
            'theme': CONFIG.get('theme', 'textual-dark'),
            'config_file': str(CONFIGFILE),
            'selected_task_id': id
        }
        try:
            run_tui(db, tasks, tui_config)
        except KeyboardInterrupt:
            console.print("\n[yellow]TUI interrupted by user[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error running TUI: {e}[/red]")
            console.print("[yellow]Your terminal should be restored.[/yellow]")
            raise

    else:
        rprint(f"[red]Unknown action: {action}[/red]")
        rprint("[yellow]Valid actions: start, done, cancel, new, post, show, rm, delete, remind, delay, clear-reminder, note, get, edit[/yellow]")


@app.command
def shell(use: Optional[str] = None):
    """Start interactive Python REPL with access to task list.

    Args:
        use: Database name to use (optional).
    """
    init_db(use)

    global tasklist
    tasklist = []
    for task in db(tasks.deleted != True).select():
        tasklist.append(Task.from_row(db, task))

    # Try to use ptpython for a better REPL experience
    try:
        from ptpython.repl import embed
        from ptpython.prompt_style import PromptStyle
        from prompt_toolkit.formatted_text import HTML

        # Custom prompt style
        class DopyPromptStyle(PromptStyle):
            def in_prompt(self):
                return HTML('<ansigreen><b>dopy</b></ansigreen> <ansicyan>&gt;&gt;&gt;</ansicyan> ')

            def in2_prompt(self, width):
                return HTML('<ansigreen>...</ansigreen> ')

            def out_prompt(self):
                return HTML('<ansiyellow>Out</ansiyellow> <ansicyan>&gt;&gt;&gt;</ansicyan> ')

        def configure(repl):
            """Configure the ptpython REPL."""
            # Enable syntax highlighting
            repl.highlight_matching_parenthesis = True
            repl.show_signature = True
            repl.show_docstring = True
            repl.show_meta_enter_message = True
            repl.completion_visualisation = 'MULTI_COLUMN'
            repl.enable_history_search = True
            repl.enable_auto_suggest = True
            repl.show_status_bar = True
            repl.show_sidebar_help = True
            repl.swap_light_and_dark = False

            # Set custom prompt style
            repl.all_prompt_styles['dopy'] = DopyPromptStyle()
            repl.prompt_style = 'dopy'

        # Print banner with Rich
        console.print(SHELLDOC, style="cyan")
        console.print(f"[green]Loaded {len(tasklist)} tasks[/green]\n")

        # Start ptpython REPL
        embed(globals(), locals(), configure=configure)

    except ImportError:
        # Fallback to standard REPL if ptpython is not available
        import code
        console.print(SHELLDOC, style="cyan")
        console.print(f"[yellow]Note: Install ptpython for a better REPL experience[/yellow]\n")
        code.interact(local=globals(), banner="")


@app.command
def add(
    name: Optional[str] = None,
    tag: str = "default",
    status: str = "new",
    reminder: Optional[str] = None,
    use: Optional[str] = None,
):
    """Add a new task.

    Args:
        name: Task name/description. If not provided, reads from stdin (first line as name, rest as notes).
        tag: Task tag/category (default: "default").
        status: Task status (default: "new").
        reminder: Optional reminder text (e.g., "today", "2 hours", "next week").
        use: Database name to use (optional).
    """
    init_db(use)

    notes = []

    # Check if we should read from stdin
    if name is None or name == "-":
        # Read from stdin
        if sys.stdin.isatty():
            console.print("[red]Error: No task name provided and stdin is not available[/red]")
            console.print("Usage: dolist add <name> or echo 'task' | dolist add")
            return

        stdin_lines = sys.stdin.read().strip().split('\n')
        if not stdin_lines or not stdin_lines[0]:
            console.print("[red]Error: Empty input from stdin[/red]")
            return

        # First line is the task name
        name = stdin_lines[0].strip()

        # Rest of the lines become notes
        if len(stdin_lines) > 1:
            notes = [line.strip() for line in stdin_lines[1:] if line.strip()]

    if not name:
        console.print("[red]Error: Task name cannot be empty[/red]")
        return

    created_on = datetime.datetime.now()
    reminder_timestamp = None

    # Parse reminder if provided
    if reminder:
        parsed_dt, error = parse_reminder(reminder)
        if error:
            rprint(f"[yellow]Warning: Could not parse reminder '{reminder}': {error}[/yellow]")
            rprint("[yellow]Task will be created without a reminder timestamp.[/yellow]")
        else:
            reminder_timestamp = parsed_dt
            rprint(f"[cyan]Reminder set for: {format_reminder(parsed_dt)}[/cyan]")

    task_id = tasks.insert(
        name=name,
        tag=tag or 'default',
        status=status or 'new',
        reminder=reminder,
        reminder_timestamp=reminder_timestamp,
        notes=notes if notes else None,
        created_on=created_on
    )
    db.commit()
    rprint(f"[green]Task {task_id} inserted[/green]")
    if notes:
        rprint(f"[cyan]Added {len(notes)} note(s)[/cyan]")


@app.command
def ls(
    all: bool = False,
    tag: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    date: Optional[str] = None,
    month: Optional[str] = None,
    day: Optional[str] = None,
    year: Optional[str] = None,
    json: bool = False,
    action: Optional[str] = None,
    action_args: Optional[str] = None,
    yes: Annotated[bool, Parameter(name=["--yes", "-y"])] = False,
    use: Optional[str] = None,
):
    """List tasks.

    Args:
        all: Show all tasks including done/cancelled.
        tag: Filter by tag.
        status: Filter by status.
        search: Search in task names.
        date: Filter by date.
        month: Filter by month.
        day: Filter by day.
        year: Filter by year.
        json: Output in JSON format.
        action: Bulk action to perform on all matching tasks (done, start, cancel, new, post, delete, rm, remind).
        action_args: Arguments for the bulk action (e.g., reminder time).
        yes: Skip confirmation prompt for bulk actions.
        use: Database name to use (optional).
    """
    init_db(use)

    query = tasks.deleted != True
    query &= ~tasks.status.belongs(['done', 'cancel', 'post']) if not all and not status else tasks.id > 0

    if tag:
        query &= tasks.tag == tag
    if status:
        query &= tasks.status == status
    if search:
        query &= tasks.name.like('%%%s%%' % search.lower())

    rows = db(query).select()

    # Apply date filters (post-query filtering)
    if date or month or day or year:
        filtered_rows = []
        for row in rows:
            if not row.created_on:
                continue

            include_row = True

            # Check specific date
            if date and include_row:
                try:
                    filter_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
                    if row.created_on.date() != filter_date:
                        include_row = False
                except ValueError:
                    console.print(f"[red]Invalid date format. Use YYYY-MM-DD[/red]")
                    return

            # Check month
            if month and include_row:
                try:
                    month_num = int(month)
                    if not 1 <= month_num <= 12:
                        raise ValueError
                    if row.created_on.month != month_num:
                        include_row = False
                except ValueError:
                    console.print(f"[red]Invalid month. Use 1-12[/red]")
                    return

            # Check day
            if day and include_row:
                try:
                    day_num = int(day)
                    if not 1 <= day_num <= 31:
                        raise ValueError
                    if row.created_on.day != day_num:
                        include_row = False
                except ValueError:
                    console.print(f"[red]Invalid day. Use 1-31[/red]")
                    return

            # Check year
            if year and include_row:
                try:
                    year_num = int(year)
                    if row.created_on.year != year_num:
                        include_row = False
                except ValueError:
                    console.print(f"[red]Invalid year[/red]")
                    return

            if include_row:
                filtered_rows.append(row)

        rows = filtered_rows

    # Handle bulk actions
    if action:
        if not rows:
            console.print("[yellow]No tasks match the filters[/yellow]")
            return

        # Confirm bulk action (unless --yes flag is set)
        if not yes:
            console.print(f"[yellow]About to perform action '{action}' on {len(rows)} task(s)[/yellow]")
            for row in rows:
                console.print(f"  - [{row.id}] {row.name}")

            confirmation = input("\nType 'yes' to confirm: ").strip().lower()
            if confirmation != 'yes':
                console.print("[green]Bulk action cancelled.[/green]")
                return

        # Perform action on each task
        for row in rows:
            if action in ['start', 'in-progress']:
                row.update_record(status='in-progress')
            elif action == 'done':
                row.update_record(status='done')
            elif action == 'cancel':
                row.update_record(status='cancel')
            elif action == 'new':
                row.update_record(status='new')
            elif action == 'post':
                row.update_record(status='post')
            elif action in ['rm', 'delete']:
                row.update_record(deleted=True)
            elif action == 'remind':
                if not action_args:
                    console.print("[red]Error: remind action requires time argument[/red]")
                    console.print("Usage: dolist ls ... --action remind --action-args '2 hours'")
                    return
                parsed_dt, error = parse_reminder(action_args)
                if error:
                    console.print(f"[red]Error parsing reminder: {error}[/red]")
                    return
                row.update_record(reminder=action_args, reminder_timestamp=parsed_dt)
            else:
                console.print(f"[red]Unknown action: {action}[/red]")
                return

        db.commit()
        console.print(f"[green]✓ Action '{action}' applied to {len(rows)} task(s)[/green]")
        return

    # Handle JSON output
    if json:
        import json as json_module
        tasks_data = []
        now = datetime.datetime.now()
        for row in rows:
            # Format reminder display
            reminder_display = ''
            if row.reminder_timestamp:
                # Check if reminder is in the past
                if row.reminder_timestamp < now:
                    reminder_display = ''
                else:
                    reminder_display = get_time_until(row.reminder_timestamp)

            task_data = {
                'id': row.id,
                'name': row.name,
                'tag': row.tag,
                'status': row.status,
                'reminder': row.reminder,
                'reminder_display': reminder_display,
                'reminder_timestamp': row.reminder_timestamp.isoformat() if row.reminder_timestamp else None,
                'notes': row.notes or [],
                'created_on': row.created_on.isoformat() if row.created_on else None,
            }
            tasks_data.append(task_data)

        print(json_module.dumps(tasks_data, indent=2))
        return

    # Handle table output
    headers = [HEAD(s) for s in ['ID','Name','Tag','Status','Reminder','Notes','Created']]
    table = [headers]

    now = datetime.datetime.now()
    for row in rows:
        # Format reminder display
        reminder_display = ''
        if row.reminder_timestamp:
            # Check if reminder is in the past
            if row.reminder_timestamp < now:
                # Auto-clear past reminders
                row.update_record(reminder=None, reminder_timestamp=None)
                db.commit()
                reminder_display = ''
            else:
                # Show time until reminder
                reminder_display = get_time_until(row.reminder_timestamp)

        fields = [
            ID(str(row.id)),
            NAME(str(row.name)),
            TAG(str(row.tag)),
            STATUS(str(row.status)),
            reminder_display,
            str(len(row.notes) if row.notes else 0),
            str(row.created_on.strftime("%d/%m-%H:%M"))
        ]
        table.append(fields)

    print_table(table)

    if rows:
        console.print(f"[green]TOTAL: {len(rows)} tasks[/green]")
    else:
        console.print("[yellow]NO TASKS FOUND[/yellow]")
        console.print("Use --help to see the usage tips")


def _show_task(task_row):
    """Helper function to show a task with all its notes."""
    headers = [HEAD(s) for s in ['ID','Name','Tag','Status','Reminder','Created']]
    fields = [
        ID(str(task_row.id)),
        NAME(str(task_row.name)),
        TAG(str(task_row.tag)),
        STATUS(str(task_row.status)),
        str(task_row.reminder or ''),
        str(task_row.created_on.strftime("%d/%m-%H:%M"))
    ]
    print_table([headers, fields])

    if task_row.notes:
        console.print("\n[bold cyan]NOTES:[/bold cyan]")
        for i, note in enumerate(task_row.notes):
            # Alternate colors for readability
            color = "blue" if i % 2 == 0 else "cyan"
            console.print(f"  [{color}][{i}][/{color}] {note}")
        console.print(f"\n[green]Total: {len(task_row.notes)} note(s)[/green]")
    else:
        console.print("\n[dim]No notes[/dim]")


def _get_task_shell(task_row):
    """Helper function to open interactive shell for a task."""
    task = Task.from_row(db, task_row)

    # Create a nice banner for single task editing
    task_banner = rf"""
     ____        _ _     _
    |  _ \  ___ | (_)___| |_
    | | | |/ _ \| | / __| __|
    | |_| | (_) | | \__ \ |_
    |____/ \___/|_|_|___/\__|

[Interactive Task Editor - Task #{task.id}]

Current task: {task.name}
Tag: {task.tag} | Status: {task.status}

Available methods:
  • task.update_name("new name")     - Update task name
  • task.update_status("done")       - Update status
  • task.update_tag("work")          - Update tag
  • task.add_note("note text")       - Add a note
  • task.delete()                    - Delete this task

Properties:
  • task.name, task.tag, task.status, task.reminder, task.notes

Tips:
  • Use Tab for auto-completion
  • Use Ctrl+D or quit() to exit
"""

    # Try to use ptpython for better experience
    try:
        from ptpython.repl import embed
        from ptpython.prompt_style import PromptStyle
        from prompt_toolkit.formatted_text import HTML

        class DopyPromptStyle(PromptStyle):
            def in_prompt(self):
                return HTML(f'<ansigreen><b>task[{task.id}]</b></ansigreen> <ansicyan>&gt;&gt;&gt;</ansicyan> ')

            def in2_prompt(self, width):
                return HTML('<ansigreen>...</ansigreen> ')

            def out_prompt(self):
                return HTML('<ansiyellow>Out</ansiyellow> <ansicyan>&gt;&gt;&gt;</ansicyan> ')

        def configure(repl):
            repl.highlight_matching_parenthesis = True
            repl.show_signature = True
            repl.show_docstring = True
            repl.completion_visualisation = 'MULTI_COLUMN'
            repl.enable_history_search = True
            repl.enable_auto_suggest = True
            repl.show_status_bar = True
            repl.all_prompt_styles['dopy'] = DopyPromptStyle()
            repl.prompt_style = 'dopy'

        console.print(task_banner, style="cyan")
        embed(globals(), locals(), configure=configure)

    except ImportError:
        import code
        console.print(task_banner, style="cyan")
        code.interact(local=dict(task=task), banner="")


@app.command
def service(
    enable: bool = False,
    remind: bool = False,
    use: Optional[str] = None,
):
    """Run or manage the reminder service.

    Args:
        enable: Install and enable as systemd service.
        remind: Process a reminder (reads task JSON from stdin).
        use: Database name to use (optional).
    """
    if enable:
        # Install systemd service
        console.print("[bold cyan]Installing DoList Reminder Service[/bold cyan]")
        if install_systemd_service():
            console.print("[green]Service installed successfully![/green]")
        else:
            console.print("[red]Service installation failed[/red]")
            sys.exit(1)
        return

    if remind:
        # Process reminder from stdin
        try:
            task_json = sys.stdin.read()
            task_data = json.loads(task_json)
            trigger_reminder(task_data, CONFIG)
        except json.JSONDecodeError as e:
            console.print(f"[red]Invalid JSON input: {e}[/red]")
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Error processing reminder: {e}[/red]")
            sys.exit(1)
        return

    # Default: run service loop
    init_db(use)
    console.print("[bold green]Starting DoList Reminder Service[/bold green]")
    console.print(f"[cyan]Using database: {DBURI}[/cyan]")
    run_service_loop(db, tasks, CONFIG)


@app.command
def reset(
    use: Optional[str] = None,
    yes: Annotated[bool, Parameter(name=["--yes", "-y"])] = False,
):
    """Reset the database (WARNING: deletes all tasks after creating a backup).

    Args:
        use: Database name to use (optional).
        yes: Skip confirmation prompt (use with caution).
    """
    init_db(use)

    # Get the database file path
    dburi = DBURI
    if use:
        dburi = dburi.replace('tasks', use).replace('dopy', use)

    # Extract database filename from URI (e.g., sqlite://tasks.db -> tasks.db)
    db_filename = dburi.replace('sqlite://', '')
    db_path = Path(DBDIR) / db_filename

    if not db_path.exists():
        console.print(f"[yellow]Database file not found: {db_path}[/yellow]")
        console.print("[yellow]Nothing to reset.[/yellow]")
        return

    # Confirmation
    if not yes:
        console.print(f"[bold red]WARNING: This will delete all tasks from {db_path}[/bold red]")
        console.print("[yellow]A timestamped backup will be created before deletion.[/yellow]")
        confirmation = input("\nType 'yes' to confirm: ").strip().lower()
        if confirmation != 'yes':
            console.print("[green]Reset cancelled.[/green]")
            return

    # Create timestamped backup
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(DBDIR) / f"{db_filename}.backup_{timestamp}"

    try:
        shutil.copy2(db_path, backup_path)
        console.print(f"[green]Backup created: {backup_path}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create backup: {e}[/red]")
        console.print("[red]Reset aborted for safety.[/red]")
        return

    # Delete the database file
    try:
        db_path.unlink()
        console.print(f"[green]Database reset successfully: {db_path}[/green]")
        console.print("[yellow]A new database will be created on next use.[/yellow]")
    except Exception as e:
        console.print(f"[red]Failed to delete database: {e}[/red]")
        console.print(f"[yellow]Backup is still available at: {backup_path}[/yellow]")


def main_entry():
    """Entry point for console script."""
    app()


if __name__ == '__main__':
    main_entry()
