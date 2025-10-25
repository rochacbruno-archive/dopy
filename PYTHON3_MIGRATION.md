# Python 3 Migration Notes

This document describes the Python 3.10+ migration status for the dopy project.

## What Has Been Done

### Build System Modernization
- ✅ Created `pyproject.toml` with modern Python packaging standards
- ✅ Configured `uv` as the package manager
- ✅ Updated dependencies to Python 3 compatible versions
- ✅ Created console script entry point (`dopy` command)
- ✅ Added `__init__.py` for proper package structure

### Code Conversion
- ✅ Updated all `print` statements to `print()` functions
- ✅ Changed `types.ListType` checks to `isinstance(x, list)`
- ✅ Converted relative imports to package-relative imports (`.module`)
- ✅ Fixed pickle operations to use binary mode (`'rb'`/`'wb'`)
- ✅ Updated `except` clauses from bare `except:` to `except Exception:`
- ✅ Added Python 2/3 compatibility layer in dal.py:
  - `basestring` → `str` in Python 3
  - `xrange` → `range` in Python 3
  - `unicode` → `str` in Python 3
- ✅ Fixed bytes/str handling in dal.py `adapt()` method
- ✅ Fixed `dict.iteritems()` → `dict.items()`
- ✅ Added conditional import for deprecated `cgi` module (removed in Python 3.13)
- ✅ Fixed `copy.copy(dict.keys())` → `list(dict.keys())`

## Known Issues

### Critical: DAL Row Object Incompatibility

The web2py DAL (Database Abstraction Layer) vendored in `dal.py` has significant Python 3 compatibility issues:

**Problem**: Row objects returned from database queries are empty in Python 3. The attribute access pattern (`row.id`, `row.name`) doesn't work.

**Impact**: Core functionality like `dopy ls` (list tasks) fails with `AttributeError: 'Row' object has no attribute 'id'`

**Root Cause**: The web2py DAL was written for Python 2 and uses metaclass magic and descriptor protocols that don't work the same way in Python 3. The Row object's `__dict__` is empty and attributes aren't properly set.

**Workarounds Attempted**:
1. ❌ Direct attribute access (`row.id`) - fails
2. ❌ Dictionary access (`row['id']`) - fails
3. ❌ Table-qualified access (`row.dopy_tasks.id`) - fails
4. ⚠️  `row.as_dict()` has its own issues with `dict.keys()` pickling (fixed but Row is still empty)

### Minor: SyntaxWarnings

Many regex patterns in dal.py generate `SyntaxWarning: invalid escape sequence` because they don't use raw strings. These are warnings only and don't affect functionality.

**Examples**:
```python
# Should be r'^\w+$' not '^\w+$'
REGEX_W = re.compile('^\w+$')
REGEX_CLEANUP_FN = re.compile('[\'"\s;]+')
```

## Recommended Solutions

### Option 1: Update to Modern pyDAL (Recommended)

Replace the vendored web2py DAL with the modern [pyDAL](https://github.com/web2py/pydal) package:

```bash
uv add pydal
```

Then update `dopy/do.py`:
```python
from pydal import DAL, Field  # instead of from .dal import DAL, Field
```

Remove or archive `dopy/dal.py` (380KB file).

**Pros**:
- Officially maintained
- Full Python 3 support
- Bug fixes and updates
- Smaller codebase

**Cons**:
- Need to test compatibility with existing database
- Might require minor code changes

### Option 2: Migrate to Modern ORM

Migrate to a modern, well-maintained ORM like SQLAlchemy or Peewee:

**SQLAlchemy**:
```python
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
```

**Peewee** (lightweight, similar to DAL):
```python
from peewee import *
import os

db = SqliteDatabase(os.path.expanduser('~/.dopy/dopy.db'))

class Task(Model):
    name = CharField()
    tag = CharField(default='default')
    status = CharField(default='new')
    # ... etc

    class Meta:
        database = db
```

**Pros**:
- Modern, actively maintained
- Excellent Python 3 support
- Better documentation
- More features

**Cons**:
- Requires significant refactoring
- Schema migration needed
- Learning curve

### Option 3: Fix Vendored DAL

Deep dive into dal.py and fix all Python 3 incompatibilities. This is the most work and least recommended since pyDAL already exists.

## Testing Instructions

Current state allows testing basic operations:

```bash
# Sync dependencies
uv sync

# Check version (works)
uv run dopy --version

# Add a task (works - inserts into database)
uv run dopy add "Test task"

# List tasks (fails - Row object issue)
uv run dopy ls
```

Database can be verified directly:
```bash
sqlite3 ~/.dopy/dopy.db "SELECT * FROM dopy_tasks;"
```

## Migration Priority

1. **High Priority**: Fix DAL Row object issue (blocks core functionality)
2. **Medium Priority**: Fix regex SyntaxWarnings (code cleanliness)
3. **Low Priority**: Add type hints, tests, modern Python patterns

## Next Steps

1. Choose ORM solution (pyDAL recommended for minimal changes)
2. Update imports and test
3. Add integration tests
4. Fix regex warnings
5. Consider adding type hints with `mypy`
6. Add GitHub Actions CI/CD

## Compatibility

- **Python 3.10+**: Partial (packaging works, core functionality broken)
- **Python 3.13**: Same issues + `cgi` module removed (handled with conditional import)
- **Python 2.7**: Original code (not tested after changes)

## Files Modified

- `pyproject.toml` - Created (modern packaging)
- `dopy/__init__.py` - Created
- `dopy/do.py` - Python 3 syntax, imports, entry point
- `dopy/printtable.py` - Python 3 syntax
- `dopy/dal.py` - Compatibility layer, pickle fixes, bytes handling
- `CLAUDE.md` - Updated documentation
- `PYTHON3_MIGRATION.md` - This file

## Files Unchanged

- `dopy/colors.py` - Already Python 3 compatible
- `dopy/taskmodel.py` - Already Python 3 compatible
- `dopy/docopt.py` - Vendored library, has own warnings
- `dopy/padnums.py` - Not used
- `requirements.txt` - Legacy file
- `setup.py` - Legacy file (empty)
