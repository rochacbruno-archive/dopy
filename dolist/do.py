#!/usr/bin/env python
#-*- coding:utf-8 -*-

r""" ____        _ _     _
|  _ \  ___ | (_)___| |_
| | | |/ _ \| | / __| __|
| |_| | (_) | | \__ \ |_
|____/ \___/|_|_|___/\__|

DoList - To-Do list on Command Line Interface
"""

from typing import Optional
import cyclopts
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
            'reminder_cmd': toml_config.get('reminders', {}).get('reminder_cmd')
        }
    except Exception as e:
        print(f"Warning: Could not load config file: {e}")
        CONFIG = {'dbdir': str(BASEDIR), 'dburi': 'sqlite://tasks.db', 'theme': 'textual-dark'}
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

[reminders]
# Custom command to handle reminders (optional)
# If set, this command will be called with task JSON piped to stdin
# If not set, uses notify-send by default
# reminder_cmd = "/path/to/custom/reminder/handler"
'''
    CONFIGFILE.write_text(default_config)
    CONFIG = {'dbdir': str(BASEDIR), 'dburi': 'sqlite://tasks.db', 'theme': 'textual-dark'}

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
def tui_mode(use: Optional[str] = None):
    """Launch the Textual TUI interface (default).

    Args:
        use: Database name to use (optional).
    """
    global db, tasks
    init_db(use)
    # Pass the initialized db, tasks, and config to the TUI
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
    name: str,
    tag: str = "default",
    status: str = "new",
    reminder: Optional[str] = None,
    use: Optional[str] = None,
):
    """Add a new task.

    Args:
        name: Task name/description.
        tag: Task tag/category (default: "default").
        status: Task status (default: "new").
        reminder: Optional reminder text (e.g., "today", "2 hours", "next week").
        use: Database name to use (optional).
    """
    init_db(use)

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
        created_on=created_on
    )
    db.commit()
    rprint(f"[green]Task {task_id} inserted[/green]")


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


@app.command
def rm(
    id: int,
    use: Optional[str] = None,
):
    """Remove (soft delete) a task.

    Args:
        id: Task ID to remove.
        use: Database name to use (optional).
    """
    init_db(use)

    task = tasks[id]
    if task:
        task.update_record(deleted=True)
        db.commit()
        rprint(f"[green]Task {id} deleted[/green]")
    else:
        rprint("[red]Task not found[/red]")


@app.command
def done(
    id: int,
    use: Optional[str] = None,
):
    """Mark a task as done.

    Args:
        id: Task ID to mark as done.
        use: Database name to use (optional).
    """
    init_db(use)

    task = tasks[id]
    if task:
        task.update_record(status='done')
        db.commit()
        rprint(f"[green]Task {id} marked as done[/green]")
    else:
        rprint("[red]Task not found[/red]")


@app.command
def cancel(
    id: int,
    use: Optional[str] = None,
):
    """Mark a task as cancelled.

    Args:
        id: Task ID to mark as cancelled.
        use: Database name to use (optional).
    """
    init_db(use)

    task = tasks[id]
    if task:
        task.update_record(status='cancel')
        db.commit()
        rprint(f"[yellow]Task {id} marked as cancelled[/yellow]")
    else:
        rprint("[red]Task not found[/red]")


@app.command
def start(
    id: int,
    use: Optional[str] = None,
):
    """Mark a task as in-progress (start working on it).

    Args:
        id: Task ID to mark as in-progress.
        use: Database name to use (optional).
    """
    init_db(use)

    task = tasks[id]
    if task:
        task.update_record(status='in-progress')
        db.commit()
        rprint(f"[cyan]Task {id} marked as in-progress[/cyan]")
    else:
        rprint("[red]Task not found[/red]")


@app.command(name="in-progress")
def in_progress(
    id: int,
    use: Optional[str] = None,
):
    """Mark a task as in-progress (alias for start).

    Args:
        id: Task ID to mark as in-progress.
        use: Database name to use (optional).
    """
    init_db(use)

    task = tasks[id]
    if task:
        task.update_record(status='in-progress')
        db.commit()
        rprint(f"[cyan]Task {id} marked as in-progress[/cyan]")
    else:
        rprint("[red]Task not found[/red]")


@app.command
def new(
    id: int,
    use: Optional[str] = None,
):
    """Mark a task as new (reset to initial state).

    Args:
        id: Task ID to mark as new.
        use: Database name to use (optional).
    """
    init_db(use)

    task = tasks[id]
    if task:
        task.update_record(status='new')
        db.commit()
        rprint(f"[green]Task {id} marked as new[/green]")
    else:
        rprint("[red]Task not found[/red]")


@app.command
def post(
    id: int,
    use: Optional[str] = None,
):
    """Mark a task as postponed/delayed.

    Args:
        id: Task ID to mark as postponed.
        use: Database name to use (optional).
    """
    init_db(use)

    task = tasks[id]
    if task:
        task.update_record(status='post')
        db.commit()
        rprint(f"[blue]Task {id} marked as postponed[/blue]")
    else:
        rprint("[red]Task not found[/red]")


@app.command
def get(
    id: int,
    use: Optional[str] = None,
):
    """Interactive shell for a specific task.

    Args:
        id: Task ID to interact with.
        use: Database name to use (optional).
    """
    init_db(use)

    row = tasks[id]
    if row:
        task = Task.from_row(db, row)

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
    else:
        rprint("[red]Task not found[/red]")


@app.command
def note(
    id: int,
    note: Optional[str] = None,
    rm_index: Optional[int] = None,
    use: Optional[str] = None,
):
    """Add or manage notes for a task.

    Args:
        id: Task ID.
        note: Note text to add (optional).
        rm_index: Index of note to remove (optional).
        use: Database name to use (optional).
    """
    init_db(use)

    task = tasks[id]
    if task:
        task.notes = task.notes or []

        if note:
            task.update_record(notes=task.notes + [note])
            db.commit()

        if rm_index is not None:
            try:
                del task.notes[rm_index]
                task.update_record(notes=task.notes)
                db.commit()
            except Exception:
                console.print("[bold red]Note not found[/bold red]")

        # Show task with notes
        show(id, use)
    else:
        console.print("[red]Task not found[/red]")


@app.command
def show(
    id: int,
    use: Optional[str] = None,
):
    """Show a task with all its notes.

    Args:
        id: Task ID to show.
        use: Database name to use (optional).
    """
    init_db(use)

    task = tasks[id]
    if task:
        lenmax = max([len(note) for note in task.notes]) if task.notes else 20
        out = "+----" + "-" * lenmax + "-----+"

        headers = [HEAD(s) for s in ['ID','Name','Tag','Status','Reminder','Created']]
        fields = [
            ID(str(task.id)),
            NAME(str(task.name)),
            TAG(str(task.tag)),
            STATUS(str(task.status)),
            str(task.reminder or ''),
            str(task.created_on.strftime("%d/%m-%H:%M"))
        ]
        print_table([headers, fields])

        if task.notes:
            console.print("[bold cyan]NOTES:[/bold cyan]")
            console.print(out)
            from termcolor import cprint
            cprint("\n".join([ID(str(i)) + " " + NOTE(note, i) for i, note in enumerate(task.notes)]), 'blue', attrs=['bold'])
            console.print(f"[green]{len(task.notes)} notes[/green]")
        else:
            console.print("")
    else:
        console.print("[red]Task not found[/red]")


@app.command
def clear_reminder(
    id: int,
    use: Optional[str] = None,
):
    """Clear the reminder from a task.

    Args:
        id: Task ID to clear reminder from.
        use: Database name to use (optional).
    """
    init_db(use)

    task = tasks[id]
    if task:
        task.update_record(reminder=None, reminder_timestamp=None)
        db.commit()
        rprint(f"[green]Reminder cleared from task {id}[/green]")
    else:
        rprint("[red]Task not found[/red]")


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
    yes: bool = False,
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


def handle_id_command(args):
    """Handle ID-based shortcut commands like: dolist 1 done, dolist 2 remind today.

    Args:
        args: Command line arguments

    Returns:
        True if handled, False otherwise
    """
    if len(args) < 2:
        return False

    # Check if first arg is a number (task ID)
    try:
        task_id = int(args[1])
    except ValueError:
        return False

    # If only ID provided, default to 'get'
    if len(args) == 2:
        init_db(None)
        from .do import get
        get(task_id, None)
        return True

    # Get the action
    action = args[2].lower()

    # Initialize database
    init_db(None)

    # Handle different actions
    if action == 'remind':
        # dolist 1 remind 2 hours
        if len(args) < 4:
            console.print("[red]Error: remind requires a time argument[/red]")
            console.print("Usage: dolist <id> remind <time>")
            console.print("Example: dolist 1 remind 2 hours")
            sys.exit(1)

        reminder_text = ' '.join(args[3:])
        task = tasks[task_id]

        if not task:
            console.print(f"[red]Task {task_id} not found[/red]")
            sys.exit(1)

        # Parse reminder
        parsed_dt, error = parse_reminder(reminder_text)
        if error:
            console.print(f"[red]Error parsing reminder: {error}[/red]")
            sys.exit(1)

        # Update task
        task.update_record(reminder=reminder_text, reminder_timestamp=parsed_dt)
        db.commit()

        console.print(f"[green]✓ Reminder set for task {task_id}[/green]")
        console.print(f"[cyan]  {task.name}[/cyan]")
        console.print(f"[yellow]  Due: {format_reminder(parsed_dt)}[/yellow]")
        return True

    elif action in ['done', 'cancel', 'start', 'new', 'post', 'in-progress']:
        # dolist 1 done
        task = tasks[task_id]

        if not task:
            console.print(f"[red]Task {task_id} not found[/red]")
            sys.exit(1)

        # Map action to status
        status_map = {
            'done': 'done',
            'cancel': 'cancel',
            'cancelled': 'cancel',
            'start': 'in-progress',
            'in-progress': 'in-progress',
            'new': 'new',
            'post': 'post',
            'postpone': 'post',
            'postponed': 'post',
        }

        new_status = status_map.get(action)
        if not new_status:
            console.print(f"[red]Unknown action: {action}[/red]")
            return False

        task.update_record(status=new_status)
        db.commit()

        console.print(f"[green]✓ Task {task_id} marked as {new_status}[/green]")
        console.print(f"[cyan]  {task.name}[/cyan]")
        return True

    elif action == 'clear-reminder':
        # dolist 1 clear-reminder
        task = tasks[task_id]

        if not task:
            console.print(f"[red]Task {task_id} not found[/red]")
            sys.exit(1)

        task.update_record(reminder=None, reminder_timestamp=None)
        db.commit()

        console.print(f"[green]✓ Reminder cleared from task {task_id}[/green]")
        console.print(f"[cyan]  {task.name}[/cyan]")
        return True

    elif action == 'delete' or action == 'rm':
        # dolist 1 delete
        task = tasks[task_id]

        if not task:
            console.print(f"[red]Task {task_id} not found[/red]")
            sys.exit(1)

        task.update_record(deleted=True)
        db.commit()

        console.print(f"[green]✓ Task {task_id} deleted[/green]")
        console.print(f"[cyan]  {task.name}[/cyan]")
        return True

    elif action == 'delay':
        # dolist 1 delay [time]
        task = tasks[task_id]

        if not task:
            console.print(f"[red]Task {task_id} not found[/red]")
            sys.exit(1)

        # Check if task has a reminder
        if not task.reminder_timestamp:
            console.print(f"[yellow]Task {task_id} has no active reminder[/yellow]")
            console.print("[yellow]Set a reminder first using: dolist {task_id} remind <time>[/yellow]")
            sys.exit(1)

        # Default delay is 10 minutes if not specified
        if len(args) < 4:
            delay_text = "10 minutes"
        else:
            delay_text = ' '.join(args[3:])

        # Parse the delay time
        parsed_dt, error = parse_reminder(delay_text)
        if error:
            console.print(f"[red]Error parsing delay time: {error}[/red]")
            sys.exit(1)

        # Update the reminder timestamp
        task.update_record(reminder=f"delayed: {delay_text}", reminder_timestamp=parsed_dt)
        db.commit()

        console.print(f"[green]✓ Reminder delayed for task {task_id}[/green]")
        console.print(f"[cyan]  {task.name}[/cyan]")
        console.print(f"[yellow]  New due time: {format_reminder(parsed_dt)}[/yellow]")
        return True

    elif action == 'show':
        # dolist 1 show
        from .do import show
        show(task_id, None)
        return True

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("\n[yellow]Available actions:[/yellow]")
        console.print("  remind <time>     - Set a reminder")
        console.print("  delay [time]      - Delay reminder (default: 10 minutes)")
        console.print("  done              - Mark as done")
        console.print("  cancel            - Mark as cancelled")
        console.print("  start             - Mark as in-progress")
        console.print("  new               - Mark as new")
        console.print("  post              - Mark as postponed")
        console.print("  clear-reminder    - Clear reminder")
        console.print("  delete, rm        - Delete task")
        console.print("  show              - Show task details")
        console.print("  (no action)       - Interactive edit")
        return False

    return False


def main_entry():
    """Entry point for console script."""
    import sys

    # Check if this is an ID-based command
    if handle_id_command(sys.argv):
        return

    # Otherwise, use normal command parsing
    app()


if __name__ == '__main__':
    main_entry()
