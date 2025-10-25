"""Tests for database.py module."""
import pytest
import os
import tempfile
from datetime import datetime
from dopy.database import Database, FieldDef, Table, Field, Row


class TestTableFieldAccess:
    """Test that Table field access returns Field objects, not strings."""

    def test_table_name_attribute_is_internal(self):
        """Test that Table._name is used internally, not .name."""
        db = Database('sqlite://:memory:')
        tasks = db.define_table('test_tasks',
            FieldDef('name', 'string'),
            FieldDef('status', 'string'),
        )

        # Internal name should be stored in _name
        assert hasattr(tasks, '_name')
        assert tasks._name == 'test_tasks'

    def test_table_field_access_returns_field_object(self):
        """Test that accessing table.name returns a Field object, not a string."""
        db = Database('sqlite://:memory:')
        tasks = db.define_table('test_tasks',
            FieldDef('name', 'string'),
            FieldDef('status', 'string'),
        )

        # Accessing table.name should return a Field object
        field = tasks.name
        assert isinstance(field, Field)
        assert field.name == 'name'
        assert field.table == tasks

    def test_field_has_like_method(self):
        """Test that Field objects have the .like() method."""
        db = Database('sqlite://:memory:')
        tasks = db.define_table('test_tasks',
            FieldDef('name', 'string'),
        )

        field = tasks.name
        assert hasattr(field, 'like')

        # Should be able to call .like() to build a condition
        condition = field.like('%test%')
        assert condition is not None

    def test_field_has_belongs_method(self):
        """Test that Field objects have the .belongs() method."""
        db = Database('sqlite://:memory:')
        tasks = db.define_table('test_tasks',
            FieldDef('status', 'string'),
        )

        field = tasks.status
        assert hasattr(field, 'belongs')

        # Should be able to call .belongs() to build a condition
        condition = field.belongs(['done', 'cancel'])
        assert condition is not None


class TestQueryBuilding:
    """Test query building with Field objects."""

    def test_like_query_building(self):
        """Test building a LIKE query."""
        db = Database('sqlite://:memory:')
        tasks = db.define_table('test_tasks',
            FieldDef('name', 'string'),
            FieldDef('tag', 'string'),
            FieldDef('status', 'string'),
            FieldDef('deleted', 'boolean', default=False),
        )

        # Build a query like the TUI does
        query = tasks.deleted != True
        query &= tasks.name.like('%test%')

        # Should be able to convert to SQL
        sql, params = query.to_sql()
        assert 'LIKE' in sql
        assert '%test%' in params

    def test_belongs_query_building(self):
        """Test building a BELONGS (IN) query."""
        db = Database('sqlite://:memory:')
        tasks = db.define_table('test_tasks',
            FieldDef('status', 'string'),
            FieldDef('deleted', 'boolean', default=False),
        )

        # Build a query with belongs
        query = tasks.deleted != True
        query &= ~tasks.status.belongs(['done', 'cancel', 'post'])

        # Should be able to convert to SQL
        sql, params = query.to_sql()
        assert 'IN' in sql

    def test_combined_query_execution(self):
        """Test executing a combined query with LIKE and BELONGS."""
        # Use a temporary file to isolate this test
        import tempfile
        tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        tmpfile.close()

        try:
            db = Database(f'sqlite://{tmpfile.name}')
            tasks = db.define_table('test_tasks',
                FieldDef('name', 'string'),
                FieldDef('status', 'string'),
                FieldDef('deleted', 'boolean', default=False),
            )

            # Insert some test data
            tasks.insert(name='test task 1', status='new')
            tasks.insert(name='test task 2', status='done')
            tasks.insert(name='other task', status='new')
            db.commit()

            # Build and execute a query like the TUI does
            query = tasks.deleted != True
            query &= ~tasks.status.belongs(['done', 'cancel', 'post'])
            query &= tasks.name.like('%test%')

            rows = db(query).select()

            # Should find only 'test task 1' (not done, and has 'test' in name)
            assert len(rows) == 1
            assert rows[0].name == 'test task 1'
        finally:
            db.close()
            os.remove(tmpfile.name)


class TestDatabaseBasics:
    """Test basic Database functionality."""

    def test_database_creation(self):
        """Test creating a database."""
        db = Database('sqlite://:memory:')
        assert db is not None

    def test_table_definition(self):
        """Test defining a table."""
        db = Database('sqlite://:memory:')
        tasks = db.define_table('tasks',
            FieldDef('name', 'string'),
            FieldDef('status', 'string'),
        )

        assert isinstance(tasks, Table)
        assert tasks._name == 'tasks'

    def test_insert_and_select(self):
        """Test inserting and selecting rows."""
        # Use a temporary file to isolate this test
        import tempfile
        tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        tmpfile.close()

        try:
            db = Database(f'sqlite://{tmpfile.name}')
            tasks = db.define_table('tasks',
                FieldDef('name', 'string'),
            )

            # Insert a row
            row_id = tasks.insert(name='Test Task')
            db.commit()

            # Select all rows
            rows = db(tasks.id > 0).select()
            assert len(rows) == 1
            assert rows[0].name == 'Test Task'
        finally:
            db.close()
            os.remove(tmpfile.name)


class TestRowOperations:
    """Test Row object operations."""

    def test_row_attribute_access(self):
        """Test accessing row attributes."""
        db = Database('sqlite://:memory:')
        tasks = db.define_table('tasks',
            FieldDef('name', 'string'),
        )

        tasks.insert(name='Test')
        db.commit()

        row = tasks[1]
        assert row is not None
        assert row.name == 'Test'

    def test_row_update_record(self):
        """Test updating a row."""
        db = Database('sqlite://:memory:')
        tasks = db.define_table('tasks',
            FieldDef('name', 'string'),
            FieldDef('status', 'string'),
        )

        tasks.insert(name='Test', status='new')
        db.commit()

        row = tasks[1]
        row.update_record(status='done')
        db.commit()

        # Re-fetch and verify
        updated = tasks[1]
        assert updated.status == 'done'
