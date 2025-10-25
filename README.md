dopy
====

     ____                     _
    |  _ \  ___   _ __  _   _| |
    | | | |/ _ \ | '_ \| | | | |
    | |_| | (_) || |_) | |_| |_|
    |____/ \___(_) .__/ \__, (_)
                 |_|    |___/


To Do list on Command Line Interface

Manage to-do list on a shell-based interface with beautiful tables and optional TUI mode. Stores your to-do locally in a SQLite database.

optionally use your Dropbox to store the database

![image](https://raw.github.com/rochacbruno/dopy/master/dopy.png)

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

### Option 1: Using uvx (recommended - no installation needed)

Run directly from the repository without cloning:

```bash
# Run dopy commands directly
uvx --from git+https://github.com/rochacbruno/dopy dopy --help
uvx --from git+https://github.com/rochacbruno/dopy dopy add "My first task"
uvx --from git+https://github.com/rochacbruno/dopy dopy ls
```

### Option 2: Clone and install with uv

```bash
# Clone the repository
git clone https://github.com/rochacbruno/dopy
cd dopy

# Install dependencies and set up the project
uv sync

# Run dopy
uv run dopy --help
uv run dopy add "My task"
uv run dopy ls
```

### Option 3: Development installation

```bash
# Clone the repository
git clone https://github.com/rochacbruno/dopy
cd dopy

# Install in development mode
uv pip install -e .

# Now dopy is available as a command
dopy --help
dopy add "Development task"
```

> **Note**: This package is not available on PyPI. Install directly from the GitHub repository using one of the methods above.

## Usage

```
     ____                     _
    |  _ \  ___   _ __  _   _| |
    | | | |/ _ \ | '_ \| | | | |
    | |_| | (_) || |_) | |_| |_|
    |____/ \___(_) .__/ \__, (_)
                 |_|    |___/
```

### Command Reference

```bash
Usage: dopy COMMAND [ARGS]

Dopy - To-Do list on Command Line Interface

Commands:
  add        Add a new task.
  done       Mark a task as done.
  get        Interactive shell for a specific task.
  ls         List tasks.
  note       Add or manage notes for a task.
  rm         Remove (soft delete) a task.
  shell      Start interactive Python REPL.
  show       Show a task with all its notes.
  --help -h  Display this message and exit.
  --version  Display application version.

Parameters:
  USE --use  Database name to use (optional).

Note: Running 'dopy' without a command launches the TUI by default.
```

> **Note**: If using `uvx`, prefix commands with `uvx --from git+https://github.com/rochacbruno/dopy`
> If installed with `uv sync`, prefix commands with `uv run`

### Quick Start Examples

#### 1. Textual TUI Mode (Default)

The beautiful terminal user interface launches by default:

```bash
# Using uvx
uvx --from git+https://github.com/rochacbruno/dopy dopy

# Or after cloning with uv sync
uv run dopy

# Or if installed globally
dopy
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
uv run dopy shell
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
dopy >>> tasklist                           # View all tasks
[Task(id=1, name='Test task'...), ...]

dopy >>> tasklist[0].name                   # Get task name
'Test task for Python 3'

dopy >>> tasklist[0].update_status('done')  # Update task

dopy >>> [t.name for t in tasklist]         # List all names
['Test task for Python 3', 'Batata', ...]

dopy >>> quit()                             # Exit
```

#### 3. Add a New Task

With all fields specified:

```bash
uv run dopy add "Pay the telephone bill" --tag personal --status new --reminder today
```

With default values (tag=default, status=new, no reminder):

```bash
uv run dopy add "Implement new features on my project"
```

#### 4. List Tasks

List all open tasks:

```bash
uv run dopy ls
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
uv run dopy ls --tag personal
```

Search by name:

```bash
uv run dopy ls --search phone
```

Filter by status:

```bash
uv run dopy ls --status done
```

List all tasks (including done/cancelled):

```bash
uv run dopy ls --all
```

#### 5. Mark Task as Done

```bash
uv run dopy done 2
```

#### 6. Remove a Task

```bash
uv run dopy rm 2
```

#### 7. Edit a Task in Interactive Shell

```bash
uv run dopy get 3
```

Interactive session with new Pydantic Task model:

```python
$ dopy get 3
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

You can add notes to tasks using their ID (visible in `dopy ls` output).

### Adding a Note

```bash
uv run dopy note 1 "This is the note for the task 1"
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
uv run dopy show 1
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
uv run dopy note 1 --rm-index 0
```

## Multiple Databases

You can use multiple databases by specifying the `--use` argument.

Create/use a different database:

```bash
uv run dopy add "Including on another db" --use mynewdb
```

This creates a new database called "mynewdb" if it doesn't exist.

List tasks from specific database:

```bash
uv run dopy ls --all --use mynewdb
```

> **Note**: You can also change the default database in the `~/.dopyrc` configuration file.

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
dopy/
├── dopy/              # Main package
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
- Stores data in `~/.dopy/dopy.db` by default
- Configuration in `~/.dopyrc`

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
