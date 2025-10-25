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
'''
        CONFIGFILE.write_text(toml_content)
        CONFIG = {'dbdir': str(BASEDIR), 'dburi': 'sqlite://tasks.db'}
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
            'dburi': toml_config.get('database', {}).get('uri', 'sqlite://tasks.db')
        }
    except Exception as e:
        print(f"Warning: Could not load config file: {e}")
        CONFIG = {'dbdir': str(BASEDIR), 'dburi': 'sqlite://tasks.db'}
else:
    # Create default TOML config
    default_config = f'''# DoList Configuration File
# This file uses TOML format

[database]
# Database directory (default: ~/.config/dolist or $XDG_CONFIG_HOME/dolist)
dir = "{BASEDIR}"
# Database URI (default: sqlite://tasks.db)
uri = "sqlite://tasks.db"
'''
    CONFIGFILE.write_text(default_config)
    CONFIG = {'dbdir': str(BASEDIR), 'dburi': 'sqlite://tasks.db'}

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
    # Pass the initialized db and tasks to the TUI
    try:
        run_tui(db, tasks)
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
        reminder: Optional reminder text.
        use: Database name to use (optional).
    """
    init_db(use)

    created_on = datetime.datetime.now()
    task_id = tasks.insert(
        name=name,
        tag=tag or 'default',
        status=status or 'new',
        reminder=reminder,
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

    for row in rows:
        fields = [
            ID(str(row.id)),
            NAME(str(row.name)),
            TAG(str(row.tag)),
            STATUS(str(row.status)),
            str(row.reminder or ''),
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
        task_banner = f"""
     ____                     _
    |  _ \  ___   _ __  _   _| |
    | | | |/ _ \ | '_ \| | | | |
    | |_| | (_) || |_) | |_| |_|
    |____/ \___(_) .__/ \__, (_)
                 |_|    |___/

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


def main_entry():
    """Entry point for console script."""
    app()


if __name__ == '__main__':
    main_entry()
