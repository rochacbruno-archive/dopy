dopy
====

     ____                     _
    |  _ \  ___   _ __  _   _| |
    | | | |/ _ \ | '_ \| | | | |
    | |_| | (_) || |_) | |_| |_|
    |____/ \___(_) .__/ \__, (_)
                 |_|    |___/


To Do list on Command Line Interface

Manage to-do list on a shell based simple interface and stores your to-do locally on a sqlite database

optionally use your Dropbox to store the database

![image](https://raw.github.com/rochacbruno/dopy/master/dopy.png)

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

### Legacy Installation (Python 2.7 - deprecated)

The original Python 2.7 version can still be used, but is no longer maintained:

```bash
git clone https://github.com/rochacbruno/dopy
cd dopy
pip install -r requirements.txt
python dopy/do.py --help
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
Usage:
  dopy [--use=<db>] [--args]
  dopy add <name> [<tag>] [<status>] [--reminder=<reminder>] [--use=<db>]
  dopy done <id> [--use=<db>]
  dopy ls [--all] [--tag=<tag>] [--status=<status>] [--search=<term>] [--use=<db>]
  dopy rm <id> [--use=<db>]
  dopy get <id> [--use=<db>]
  dopy note <id> [--use=<db>] [--rm=<noteindex>]
  dopy show <id> [--use=<db>]
  dopy note <id> <note> [--use=<db>]
  dopy -h | --help
  dopy --version

Options:
  -h --help      Show this screen
  --version      Show version
  --use=<db>     Use alternative database
```

> **Note**: If using `uvx`, prefix commands with `uvx --from git+https://github.com/rochacbruno/dopy`
> If installed with `uv sync`, prefix commands with `uv run`

### Quick Start Examples

#### 1. Interactive Shell Mode

```bash
# Using uvx
uvx --from git+https://github.com/rochacbruno/dopy dopy

# Or after cloning with uv sync
uv run dopy

# Or if installed globally
dopy
```

#### 2. Add a New Task

With all fields specified:

```bash
uv run dopy add "Pay the telephone bill" personal new --reminder=today
```

With default values (tag=default, status=new, no reminder):

```bash
uv run dopy add "Implement new features on my project"
```

#### 3. List Tasks

List all open tasks:

```bash
uv run dopy ls
```

Example output:
    +--+-----------------------------+--------+------+--------+-------------------+
    |ID|                         Name|     Tag|Status|Reminder|            Created|
    +--+-----------------------------+--------+------+--------+-------------------+
    | 3|           Pay telephone bill|personal|   new|   today|2012-12-31 08:03:15|
    | 4|Implement features on project| default|   new|    None|2012-12-31 08:03:41|
    +--+-----------------------------+--------+------+--------+-------------------+
    TOTAL:2 tasks

Filter by tag:

```bash
uv run dopy ls --tag=personal
```

Search by name:

```bash
uv run dopy ls --search=phone
```

Filter by status:

```bash
uv run dopy ls --status=done
```

List all tasks (including done/cancelled):

```bash
uv run dopy ls --all
```

#### 4. Mark Task as Done

```bash
uv run dopy done 2
```

#### 5. Remove a Task

```bash
uv run dopy rm 2
```

#### 6. Edit a Task in Interactive Shell

```bash
uv run dopy get 3
```

Interactive session:

    $ dopy get 3
    To show the task
    >>> print task
    To show a field (available name, tag, status, reminder)
    >>> task.name
    To edit the task assign to a field
    >>> task.name = "Other name"
    To delete a task
    >>> task.delete()
    To exit
    >>> quit()
    ######################################

    >>> print task
    <Row {'status': 'new', 'name': 'Pay telephone bill', 'deleted': False, 'created_on': datetime.datetime(2012, 12, 31, 8, 3, 15), 'tag': 'personal', 'reminder': 'today', 'id': 3}>
    >>> task.status
    'new'
    >>> task.status = "working"
    >>> task.status
    'working'
    >>>


## Managing Notes

You can add notes to tasks using their ID (visible in `dopy ls` output).

### Adding a Note

```bash
uv run dopy note 1 "This is the note for the task 1"
```

The above command inserts the note and prints the TASK with notes.

    +--+-----+-------+------+--------+-----------+
    |ID| Name|    Tag|Status|Reminder|    Created|
    +--+-----+-------+------+--------+-----------+
    | 1|teste|default|   new|    None|01/01-02:14|
    +--+-----+-------+------+--------+-----------+
    NOTES:
    +------------------------------------+
    0 This is the note fot task 1
    +------------------------------------+
    1 notes

### Viewing Notes

Show all notes for a task:

```bash
uv run dopy show 1
```

Example output:

    +--+-----+-------+------+--------+-----------+
    |ID| Name|    Tag|Status|Reminder|    Created|
    +--+-----+-------+------+--------+-----------+
    | 1|teste|default|   new|    None|01/01-02:14|
    +--+-----+-------+------+--------+-----------+
    NOTES:
    +----------------------------------------+
    0 This is the note fot task 1
    1 This is another note for task 1
    +----------------------------------------+
    2 notes


### Removing a Note

Notes can be removed by their index number.

Remove the latest note:

```bash
uv run dopy note 1 --rm=-1
```

Remove the first note (index 0):

```bash
uv run dopy note 1 --rm=0
```

## Multiple Databases

You can use multiple databases by specifying the `--use` argument.

Create/use a different database:

```bash
uv run dopy add "Including on another db" --use=mynewdb
```

This creates a new database called "mynewdb" if it doesn't exist.

List tasks from specific database:

```bash
uv run dopy ls --all --use=mynewdb
```

> **Note**: You can also change the default database in the `~/.dopyrc` configuration file.

## Testing

This project includes a comprehensive test suite. See [README_TESTS.md](README_TESTS.md) for details.

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```

**Test Coverage**: 87 tests covering all major components
- Colors module (22 tests)
- Print table module (33 tests)
- Task model (18 tests)
- Main application (14 tests)

## Development

### Project Structure

```
dopy/
├── dopy/              # Main package
│   ├── __init__.py    # Package initialization
│   ├── do.py          # Main application & CLI
│   ├── dal.py         # Database abstraction layer
│   ├── taskmodel.py   # Task model
│   ├── colors.py      # Color formatting
│   └── printtable.py  # Table rendering
├── tests/             # Test suite
├── pyproject.toml     # Modern Python packaging
├── pytest.ini         # Pytest configuration
└── README_TESTS.md    # Testing documentation
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `uv run pytest`
5. Submit a pull request

### Python Version Support

- **Python 3.10+**: Fully supported with modern packaging
- **Python 2.7**: Legacy support (deprecated, not maintained)

See [PYTHON3_MIGRATION.md](PYTHON3_MIGRATION.md) for migration details and known issues.

## Known Issues

⚠️ The vendored web2py DAL has compatibility issues with Python 3. Core functionality like listing tasks (`dopy ls`) may not work correctly. See [PYTHON3_MIGRATION.md](PYTHON3_MIGRATION.md) for details and recommended solutions.

## License

This project is open source. See the repository for license details.

## Roadmap

- [ ] Migrate to modern ORM (SQLAlchemy or pyDAL)
- [ ] Fix Python 3 DAL compatibility
- [ ] Sync with Google Tasks
- [ ] Sync with Remember The Milk
- [ ] Generate HTML and PDF reports
- [ ] Add configuration management commands
- [ ] Improve test coverage for integration tests

