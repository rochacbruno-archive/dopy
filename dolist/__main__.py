"""Allow dolist to be run as a module with python -m dolist."""

from .do import main_entry

if __name__ == "__main__":
    main_entry()
