DoList
======

     ██████████            ████   ███           █████   
    ░░███░░░░███          ░░███  ░░░           ░░███    
     ░███   ░░███  ██████  ░███  ████   █████  ███████  
     ░███    ░███ ███░░███ ░███ ░░███  ███░░  ░░░███░   
     ░███    ░███░███ ░███ ░███  ░███ ░░█████   ░███    
     ░███    ███ ░███ ░███ ░███  ░███  ░░░░███  ░███ ███
     ██████████  ░░██████  █████ █████ ██████   ░░█████ 
    ░░░░░░░░░░    ░░░░░░  ░░░░░ ░░░░░ ░░░░░░     ░░░░░  

To Do list on Command Line Interface

Manage to-do list on a shell-based interface with beautiful tables and optional TUI mode. Stores your to-do locally in a SQLite database.

optionally use your Dropbox to store the database

![image](https://raw.github.com/rochacbruno/dolist/master/dolist.png)

## ✨ Features

- 🎨 **Modern CLI** powered by [Cyclopts](https://github.com/BrianPugh/cyclopts) with type hints
- 📊 **Beautiful Tables** using [Rich](https://github.com/Textualize/rich) library
- 🖥️ **Interactive TUI Mode** with [Textual](https://github.com/Textualize/textual) for graphical terminal interface
- 🐍 **Enhanced Python REPL** with [ptpython](https://github.com/prompt-toolkit/ptpython) featuring syntax highlighting and auto-completion
- ✅ **Data Validation** with [Pydantic](https://github.com/pydantic/pydantic) models
- 🗄️ **SQLite Database** for local task storage
- 🏷️ **Tag Support** to organize tasks
- 📝 **Notes** on tasks
- ⏰ **Reminders** for tasks
- 💾 **Multiple Databases** support

## Requirements

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) package manager (recommended)

## Installation

### Option 1: Using uvx from PyPI (⭐ Recommended)

The easiest way to use DoList is with `uvx` - no installation or cloning needed:

```bash
# Run dolist commands directly from PyPI
uvx dolist --help
uvx dolist add "My first task"
uvx dolist ls

# Launch the interactive TUI
uvx dolist
```

This will automatically download and run the latest version from PyPI each time.

### Option 2: Using uvx from GitHub

Run the latest development version directly from GitHub:

```bash
# Run dolist commands from GitHub
uvx --from git+https://github.com/rochacbruno/dolist dolist --help
uvx --from git+https://github.com/rochacbruno/dolist dolist add "My first task"
uvx --from git+https://github.com/rochacbruno/dolist dolist ls
```

### Option 3: Install with uv/pip

For permanent installation:

```bash
# Install from PyPI
uv pip install dolist

# Or install from GitHub for latest development version
uv pip install git+https://github.com/rochacbruno/dolist

# Now dolist is available as a command
dolist --help
dolist add "My task"
dolist ls
```

### Option 4: Development installation

```bash
# Clone the repository
git clone https://github.com/rochacbruno/dolist
cd dolist

# Install dependencies and set up the project
uv sync

# Run dolist
dolist --help

# Or install in development mode
uv pip install -e .
dolist --help
```

## Usage

```
     ____        _ _     _
    |  _ \  ___ | (_)___| |_
    | | | |/ _ \| | / __| __|
    | |_| | (_) | | \__ \ |_
    |____/ \___/|_|_|___/\__|
```

### Command Reference

```bash
Usage: dolist COMMAND [ARGS]

DoList - To-Do list on Command Line Interface

Commands:
  add        Add a new task.
  cancel     Mark a task as cancelled.
  done       Mark a task as done.
  get        Interactive shell for a specific task.
  ls         List tasks.
  note       Add or manage notes for a task.
  post       Mark a task as posted.
  rm         Remove (soft delete) a task.
  shell      Start interactive Python REPL.
  show       Show a task with all its notes.
  start      Mark a task as new (reset to initial state).
  working    Mark a task as working (in progress).
  --help -h  Display this message and exit.
  --version  Display application version.

Parameters:
  USE --use  Database name to use (optional).

Note: Running 'dolist' without a command launches the TUI by default.
```

> **Note**: Command examples below show direct `dolist` usage. If using `uvx`, prefix with `uvx dolist` (from PyPI) or `uvx --from git+https://github.com/rochacbruno/dolist dolist` (from GitHub)

### Quick Start Examples

#### 1. Textual TUI Mode (Default)

The beautiful terminal user interface launches by default:

```bash
# Using uvx from PyPI (recommended)
uvx dolist

# Or from GitHub for latest development version
uvx --from git+https://github.com/rochacbruno/dolist dolist

# Or if installed
dolist
```

Features of TUI mode:
- 📊 **Interactive table view** of tasks
- ✏️ **Add/Edit/Delete** tasks via modal dialogs
- 🔍 **Filter** by tag, status, and search (type in the search box)
- ⌨️ **Keyboard shortcuts**:
  - `a` - Add new task
  - `Enter` - Edit selected task
  - `r` - Refresh task list
  - `Esc` or `Ctrl+Q` - Quit

#### 2. Interactive Python REPL (Enhanced with ptpython)

For advanced scripting and automation, launch the interactive Python shell:

```bash
dolist shell
```

Features of the modern REPL:
- 🎨 **Syntax highlighting** for Python code
- ⚡ **Auto-completion** with Tab key
- 📝 **Signature hints** for functions
- 🔍 **History search** with Ctrl+R
- ⌨️ **Vi/Emacs mode** toggle with F2
- 📊 Access to `tasklist`, `db`, and `tasks` objects

Example REPL session:
```python
dolist >>> tasklist                           # View all tasks
[Task(id=1, name='Test task'...), ...]

dolist >>> tasklist[0].name                   # Get task name
'Test task for Python 3'

dolist >>> tasklist[0].update_status('done')  # Update task

dolist >>> [t.name for t in tasklist]         # List all names
['Test task for Python 3', 'Batata', ...]

dolist >>> quit()                             # Exit
```

#### 3. Add a New Task

With all fields specified:

```bash
dolist add "Pay the telephone bill" --tag personal --status new --reminder today
```

With default values (tag=default, status=new, no reminder):

```bash
dolist add "Implement new features on my project"
```

#### 4. List Tasks

List all open tasks:

```bash
dolist ls
```

Example output with Rich tables:
```
  ID   Name                       Tag       Status   Reminder   Notes   Created
 ──────────────────────────────────────────────────────────────────────────────
  1    Pay telephone bill         personal  new      today      0       31/12-08:03
  2    Implement features         default   new               0       31/12-08:03

TOTAL: 2 tasks
```

Filter by tag:

```bash
dolist ls --tag personal
```

Search by name:

```bash
dolist ls --search phone
```

Filter by status:

```bash
dolist ls --status done
```

List all tasks (including done/cancelled):

```bash
dolist ls --all
```

#### 5. Change Task Status

DoList provides dedicated commands for each status change:

```bash
# Mark task as working (in progress)
dolist working 2

# Mark task as done
dolist done 2

# Mark task as cancelled
dolist cancel 2

# Mark task as posted
dolist post 2

# Reset task to new status
dolist start 2
```

Available statuses: `new`, `working`, `done`, `cancel`, `post`

#### 6. Remove a Task

```bash
dolist rm 2
```

#### 7. Edit a Task in Interactive Shell

```bash
dolist get 3
```

Interactive session with new Pydantic Task model:

```python
$ dolist get 3
To show the task
>>> print task
To show a field (available name, tag, status, reminder)
>>> task.name
To edit the task assign to a field using update methods
>>> task.update_name("Other name")
>>> task.update_status("working")
To delete a task
>>> task.delete()
To exit
>>> quit()
######################################

>>> print(task)
Task(id=3, name=Pay telephone bill, tag=personal, status=new)
>>> task.status
'new'
>>> task.update_status("working")
>>> task.status
'working'
>>>
```


## Managing Notes

You can add notes to tasks using their ID (visible in `dolist ls` output).

### Adding a Note

```bash
dolist note 1 "This is the note for the task 1"
```

The above command inserts the note and prints the TASK with notes.

```
  ID   Name    Tag       Status   Reminder   Created
 ───────────────────────────────────────────────────
  1    teste   default   new                 01/01-02:14

NOTES:
+------------------------------------+
0 This is the note for task 1
+------------------------------------+

1 notes
```

### Viewing Notes

Show all notes for a task:

```bash
dolist show 1
```

Example output:

```
  ID   Name    Tag       Status   Reminder   Created
 ───────────────────────────────────────────────────
  1    teste   default   new                 01/01-02:14

NOTES:
+----------------------------------------+
0 This is the note for task 1
1 This is another note for task 1
+----------------------------------------+

2 notes
```


### Removing a Note

Notes can be removed by their index number using the `--rm-index` option:

```bash
dolist note 1 --rm-index 0
```

## Multiple Databases

You can use multiple databases by specifying the `--use` argument.

Create/use a different database:

```bash
dolist add "Including on another db" --use mynewdb
```

This creates a new database called "mynewdb" if it doesn't exist.

List tasks from specific database:

```bash
dolist ls --all --use mynewdb
```

> **Note**: You can also change the default database in the `~/.config/dolist/config.toml` configuration file.

## Testing

This project includes a comprehensive test suite with **105 tests**, all passing!

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```

**Test Coverage**: 105 tests covering all major components
- ✅ Colors module (22 tests)
- ✅ Database module (12 tests) - *New!*
- ✅ Print table module (33 tests)
- ✅ Task model with Pydantic (24 tests)
- ✅ Main application with Cyclopts (14 tests)

See [README_TESTS.md](README_TESTS.md) for detailed testing documentation.

## Development

### Project Structure

```
dolist/
├── dolist/              # Main package
│   ├── __init__.py    # Package initialization
│   ├── do.py          # Main application & Cyclopts CLI
│   ├── database.py    # Lightweight SQLite database wrapper
│   ├── taskmodel.py   # Pydantic Task model
│   ├── colors.py      # Color formatting helpers
│   ├── printtable.py  # Legacy table rendering
│   ├── rich_table.py  # Rich table rendering
│   └── tui.py         # Textual TUI application
├── tests/             # Test suite (105 tests)
│   ├── test_colors.py      # Color function tests (22 tests)
│   ├── test_database.py    # Database layer tests (12 tests)
│   ├── test_printtable.py  # Table rendering tests (33 tests)
│   ├── test_taskmodel.py   # Task model tests (24 tests)
│   └── test_do.py          # Main app tests (14 tests)
├── pyproject.toml     # Modern Python packaging
├── pytest.ini         # Pytest configuration
└── README_TESTS.md    # Testing documentation
```

### Modern Stack

This project has been modernized with:

- **Cyclopts** - Modern CLI framework with type hints (replaced docopt)
- **Rich** - Beautiful terminal output and tables
- **Textual** - Terminal user interface framework
- **ptpython** - Enhanced Python REPL with syntax highlighting and auto-completion
- **Pydantic** - Data validation and settings management
- **uv** - Fast Python package manager
- **pytest** - Modern testing framework

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `uv run pytest`
5. Ensure all 105 tests pass
6. Submit a pull request

### Python Version Support

- **Python 3.10+**: Fully supported with modern dependencies
- **Python 2.7**: No longer supported (legacy version deprecated)

## Architecture

### Task Model

The `Task` model is now powered by Pydantic with:
- Field validation (status must be one of: new, working, done, cancel, post)
- Type hints for all fields
- Automatic serialization/deserialization
- Methods for database updates: `update_name()`, `update_status()`, `add_note()`, etc.

### CLI Structure

The CLI uses Cyclopts for:
- Type-safe command definitions
- Automatic help generation
- Parameter validation
- Sub-command routing

### Database

Uses a lightweight SQLite wrapper that:
- Supports multiple databases via `--use` flag
- Stores data in `~/.config/dolist/tasks.db` by default (or `$XDG_CONFIG_HOME/dolist/tasks.db`)
- Configuration in `~/.config/dolist/config.toml` (TOML format)
- Backwards compatible with legacy `~/.dopy/dopy.db` location

## License

This project is open source. See the repository for license details.

## Roadmap

- [x] Migrate from docopt to Cyclopts ✅
- [x] Add Rich table rendering ✅
- [x] Create Textual TUI mode ✅
- [x] Implement Pydantic models ✅
- [x] Lightweight SQLite database wrapper ✅
- [x] Comprehensive test suite (105 tests) ✅
- [ ] Add export functionality (JSON, CSV, HTML)
- [ ] Implement task priorities
- [ ] Add due dates and recurring tasks
- [ ] Cloud sync support (Dropbox, Google Drive)
- [ ] Integration with external services (Todoist, Google Tasks)
- [ ] Advanced filtering and sorting options
- [ ] Task dependencies and subtasks
