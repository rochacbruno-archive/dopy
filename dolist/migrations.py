#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Database migration system for DoList.
Handles schema changes and data migrations for existing databases.
"""

import sqlite3


def get_schema_version(db_conn):
    """Get the current schema version from the database."""
    try:
        cursor = db_conn.execute(
            "SELECT version FROM dolist_schema_version ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        # Table doesn't exist, this is version 0
        return 0


def set_schema_version(db_conn, version):
    """Set the schema version in the database."""
    # Create version table if it doesn't exist
    db_conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dolist_schema_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL,
            applied_at TEXT NOT NULL
        )
    """
    )

    # Insert new version record
    db_conn.execute(
        "INSERT INTO dolist_schema_version (version, applied_at) VALUES (?, datetime('now'))",
        (version,),
    )
    db_conn.commit()


def column_exists(db_conn, table_name, column_name):
    """Check if a column exists in a table."""
    cursor = db_conn.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def migrate_to_v1_priority_and_size(db_conn):
    """
    Migration v1: Add priority and size fields.

    Changes:
    - Add 'priority' INTEGER DEFAULT 0 to dolist_tasks
    - Add 'size' TEXT DEFAULT 'U' to dolist_tasks
    - Add 'priority' INTEGER DEFAULT 0 to dolist_task_history
    - Add 'size' TEXT DEFAULT 'U' to dolist_task_history
    """
    # Check if dolist_tasks table exists - if not, skip migration (new database)
    cursor = db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='dolist_tasks'"
    )
    if not cursor.fetchone():
        return  # Table doesn't exist yet, skip migration

    # Check if migration is needed
    if column_exists(db_conn, "dolist_tasks", "priority"):
        return  # Already migrated

    print("Running migration v1: Adding priority and size fields...")

    # Add columns to dolist_tasks
    if not column_exists(db_conn, "dolist_tasks", "priority"):
        db_conn.execute(
            "ALTER TABLE dolist_tasks ADD COLUMN priority INTEGER DEFAULT 0"
        )

    if not column_exists(db_conn, "dolist_tasks", "size"):
        db_conn.execute("ALTER TABLE dolist_tasks ADD COLUMN size TEXT DEFAULT 'U'")

    # Add columns to dolist_task_history if it exists
    cursor = db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='dolist_task_history'"
    )
    if cursor.fetchone():
        if not column_exists(db_conn, "dolist_task_history", "priority"):
            db_conn.execute(
                "ALTER TABLE dolist_task_history ADD COLUMN priority INTEGER DEFAULT 0"
            )

        if not column_exists(db_conn, "dolist_task_history", "size"):
            db_conn.execute(
                "ALTER TABLE dolist_task_history ADD COLUMN size TEXT DEFAULT 'U'"
            )

    db_conn.commit()
    set_schema_version(db_conn, 1)
    print("Migration v1 completed successfully.")


def migrate_to_v2_recurring_reminders(db_conn):
    """
    Migration v2: Add recurring reminder support.

    Changes:
    - Add 'reminder_repeat' TEXT to dolist_tasks (stores repeat interval like "2 hours")
    - Add 'reminder_repeat' TEXT to dolist_task_history
    """
    # Check if dolist_tasks table exists - if not, skip migration (new database)
    cursor = db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='dolist_tasks'"
    )
    if not cursor.fetchone():
        return  # Table doesn't exist yet, skip migration

    # Check if migration is needed
    if column_exists(db_conn, "dolist_tasks", "reminder_repeat"):
        return  # Already migrated

    print("Running migration v2: Adding recurring reminder support...")

    # Add reminder_repeat column to dolist_tasks
    if not column_exists(db_conn, "dolist_tasks", "reminder_repeat"):
        db_conn.execute("ALTER TABLE dolist_tasks ADD COLUMN reminder_repeat TEXT")

    # Add reminder_repeat column to dolist_task_history if it exists
    cursor = db_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='dolist_task_history'"
    )
    if cursor.fetchone():
        if not column_exists(db_conn, "dolist_task_history", "reminder_repeat"):
            db_conn.execute(
                "ALTER TABLE dolist_task_history ADD COLUMN reminder_repeat TEXT"
            )

    db_conn.commit()
    set_schema_version(db_conn, 2)
    print("Migration v2 completed successfully.")


# List of all migrations in order
MIGRATIONS = [
    migrate_to_v1_priority_and_size,
    migrate_to_v2_recurring_reminders,
]


def run_migrations(db_conn):
    """Run all pending migrations."""
    current_version = get_schema_version(db_conn)

    # Run migrations that haven't been applied yet
    for i, migration in enumerate(MIGRATIONS, start=1):
        if i > current_version:
            migration(db_conn)
