#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Simple SQLite database wrapper for dopy.
Replaces the heavy web2py DAL with a lightweight solution.
"""
import sqlite3
import json
import os
from datetime import datetime


class Row:
    """A simple row object that allows both dict-like and attribute access."""

    def __init__(self, data):
        """Initialize with a dictionary of column: value pairs."""
        self._data = data

    def __getattr__(self, key):
        """Allow attribute access like row.id"""
        if key.startswith('_'):
            return object.__getattribute__(self, key)
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError(f"Row has no attribute '{key}'")

    def __getitem__(self, key):
        """Allow dict-like access like row['id']"""
        return self._data[key]

    def __setitem__(self, key, value):
        """Allow dict-like assignment"""
        self._data[key] = value

    def get(self, key, default=None):
        """Dict-like get method"""
        return self._data.get(key, default)

    def __contains__(self, key):
        """Support 'in' operator"""
        return key in self._data

    def keys(self):
        """Return column names"""
        return self._data.keys()

    def values(self):
        """Return values"""
        return self._data.values()

    def items(self):
        """Return items"""
        return self._data.items()

    def __repr__(self):
        return f"<Row {self._data}>"

    def __str__(self):
        return str(self._data)

    def update_record(self, **fields):
        """Update this row in the database."""
        if not hasattr(self, '_db') or not hasattr(self, '_table'):
            raise RuntimeError("Row is not bound to a database table")

        if not fields:
            return self

        # Process fields (handle lists, dicts, datetimes)
        processed_fields = {}
        for key, value in fields.items():
            if isinstance(value, (list, dict)):
                processed_fields[key] = json.dumps(value)
            elif isinstance(value, datetime):
                processed_fields[key] = value.isoformat()
            else:
                processed_fields[key] = value

        # Build UPDATE query
        set_clause = ', '.join(f"{k} = ?" for k in processed_fields.keys())
        query = f"UPDATE {self._table} SET {set_clause} WHERE id = ?"
        values = list(processed_fields.values()) + [self._data['id']]

        self._db.execute(query, values)

        # Update local data (use original fields, not JSON-encoded)
        self._data.update(fields)
        return self

    def delete_record(self):
        """Delete this row from the database (soft delete)."""
        if not hasattr(self, '_db') or not hasattr(self, '_table'):
            raise RuntimeError("Row is not bound to a database table")

        self.update_record(deleted=True)


class Table:
    """Represents a database table with query building capabilities."""

    def __init__(self, db, name):
        self.db = db
        self._name = name  # Use _name to avoid conflicts with 'name' field
        self._fields = {}

    def __getattr__(self, name):
        """Return a Field object for query building."""
        # 'id' is always available as it's the primary key
        if name == 'id' or name in self._fields:
            return Field(self, name)
        raise AttributeError(f"Table has no field '{name}'")

    def __getitem__(self, id):
        """Get a row by ID."""
        cursor = self.db.conn.execute(
            f"SELECT * FROM {self._name} WHERE id = ?", (id,)
        )
        row_data = cursor.fetchone()
        if row_data:
            row = self._make_row(row_data, cursor.description)
            return row
        return None

    def insert(self, **fields):
        """Insert a new row and return its ID."""
        # Handle list:string fields (stored as JSON)
        processed_fields = {}
        for key, value in fields.items():
            if isinstance(value, (list, dict)):
                processed_fields[key] = json.dumps(value)
            elif isinstance(value, datetime):
                processed_fields[key] = value.isoformat()
            else:
                processed_fields[key] = value

        columns = ', '.join(processed_fields.keys())
        placeholders = ', '.join('?' * len(processed_fields))
        query = f"INSERT INTO {self._name} ({columns}) VALUES ({placeholders})"

        cursor = self.db.conn.execute(query, list(processed_fields.values()))
        self.db.conn.commit()
        return cursor.lastrowid

    def _make_row(self, row_data, description):
        """Convert a database row tuple into a Row object."""
        if row_data is None:
            return None

        col_names = [desc[0] for desc in description]
        data = {}

        for col_name, value in zip(col_names, row_data):
            # Handle JSON-encoded list:string fields
            if col_name == 'notes' and value:
                try:
                    data[col_name] = json.loads(value) if value else []
                except (json.JSONDecodeError, TypeError):
                    data[col_name] = []
            # Handle datetime fields
            elif col_name in ('created_on', 'reminder_timestamp', 'changed_at') and value:
                try:
                    data[col_name] = datetime.fromisoformat(value)
                except (ValueError, TypeError):
                    data[col_name] = value
            # Handle boolean fields
            elif col_name == 'deleted':
                data[col_name] = bool(value) if value is not None else False
            else:
                data[col_name] = value

        row = Row(data)
        row._db = self.db.conn
        row._table = self._name
        return row


class Field:
    """Represents a field in a table, used for query building."""

    def __init__(self, table, name):
        self.table = table
        self.name = name

    def __eq__(self, value):
        """Build equality condition."""
        return Condition(self, '=', value)

    def __ne__(self, value):
        """Build inequality condition."""
        return Condition(self, '!=', value)

    def __gt__(self, value):
        """Build greater than condition."""
        return Condition(self, '>', value)

    def __lt__(self, value):
        """Build less than condition."""
        return Condition(self, '<', value)

    def __le__(self, value):
        """Build less than or equal condition."""
        return Condition(self, '<=', value)

    def __ge__(self, value):
        """Build greater than or equal condition."""
        return Condition(self, '>=', value)

    def belongs(self, values):
        """Build IN condition."""
        return Condition(self, 'IN', values)

    def like(self, pattern):
        """Build LIKE condition."""
        return Condition(self, 'LIKE', pattern)


class Condition:
    """Represents a query condition."""

    def __init__(self, field, operator, value):
        self.field = field
        self.operator = operator
        self.value = value

    def __and__(self, other):
        """Combine conditions with AND."""
        return CompoundCondition(self, 'AND', other)

    def __or__(self, other):
        """Combine conditions with OR."""
        return CompoundCondition(self, 'OR', other)

    def __invert__(self):
        """Negate condition with NOT."""
        return NotCondition(self)

    def to_sql(self):
        """Convert to SQL WHERE clause and parameters."""
        # Handle NULL comparisons
        if self.value is None:
            if self.operator == '=':
                return f"{self.field.name} IS NULL", []
            elif self.operator == '!=' or self.operator == '<>':
                return f"{self.field.name} IS NOT NULL", []

        if self.operator == 'IN':
            placeholders = ', '.join('?' * len(self.value))
            return f"{self.field.name} IN ({placeholders})", list(self.value)
        else:
            # Handle boolean comparisons specially
            # For deleted != True, we want (deleted IS NULL OR deleted != 1 OR deleted = 'F')
            if self.field.name == 'deleted' and isinstance(self.value, bool):
                if self.operator == '!=' and self.value is True:
                    # Find non-deleted: NULL, 0, False, 'F'
                    return f"({self.field.name} IS NULL OR {self.field.name} = 0 OR {self.field.name} = 'F')", []
                elif self.operator == '=' and self.value is True:
                    # Find deleted: 1, True, 'T'
                    return f"({self.field.name} = 1 OR {self.field.name} = 'T')", []
                elif self.operator == '!=' and self.value is False:
                    # Find deleted
                    return f"({self.field.name} = 1 OR {self.field.name} = 'T')", []
                elif self.operator == '=' and self.value is False:
                    # Find non-deleted
                    return f"({self.field.name} IS NULL OR {self.field.name} = 0 OR {self.field.name} = 'F')", []

            # Convert boolean to integer for SQLite
            value = self.value
            if isinstance(value, bool):
                value = 1 if value else 0
            # Convert datetime to ISO format string for SQLite
            elif isinstance(value, datetime):
                value = value.isoformat()

            return f"{self.field.name} {self.operator} ?", [value]


class CompoundCondition:
    """Represents combined conditions (AND/OR)."""

    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

    def __and__(self, other):
        return CompoundCondition(self, 'AND', other)

    def __or__(self, other):
        return CompoundCondition(self, 'OR', other)

    def __invert__(self):
        return NotCondition(self)

    def to_sql(self):
        """Convert to SQL WHERE clause and parameters."""
        left_sql, left_params = self.left.to_sql()
        right_sql, right_params = self.right.to_sql()
        sql = f"({left_sql}) {self.operator} ({right_sql})"
        return sql, left_params + right_params


class NotCondition:
    """Represents a negated condition."""

    def __init__(self, condition):
        self.condition = condition

    def __and__(self, other):
        return CompoundCondition(self, 'AND', other)

    def __or__(self, other):
        return CompoundCondition(self, 'OR', other)

    def to_sql(self):
        """Convert to SQL WHERE clause and parameters."""
        inner_sql, params = self.condition.to_sql()
        return f"NOT ({inner_sql})", params


class Query:
    """Represents a database query."""

    def __init__(self, db, table, condition):
        self.db = db
        self.table = table
        self.condition = condition

    def select(self, *fields):
        """Execute SELECT query and return rows."""
        if self.condition:
            where_clause, params = self.condition.to_sql()
            query = f"SELECT * FROM {self.table._name} WHERE {where_clause}"
        else:
            query = f"SELECT * FROM {self.table._name}"
            params = []

        cursor = self.db.conn.execute(query, params)
        rows = []
        for row_data in cursor.fetchall():
            row = self.table._make_row(row_data, cursor.description)
            rows.append(row)
        return rows

    def update(self, **fields):
        """Execute UPDATE query."""
        if not self.condition:
            raise ValueError("UPDATE requires a WHERE condition")

        # Process fields
        processed_fields = {}
        for key, value in fields.items():
            if isinstance(value, (list, dict)):
                processed_fields[key] = json.dumps(value)
            elif isinstance(value, datetime):
                processed_fields[key] = value.isoformat()
            else:
                processed_fields[key] = value

        set_clause = ', '.join(f"{k} = ?" for k in processed_fields.keys())
        where_clause, where_params = self.condition.to_sql()

        query = f"UPDATE {self.table._name} SET {set_clause} WHERE {where_clause}"
        params = list(processed_fields.values()) + where_params

        self.db.conn.execute(query, params)
        self.db.conn.commit()

    def delete(self):
        """Execute DELETE query (soft delete by setting deleted=True)."""
        self.update(deleted=True)


class Database:
    """Simple SQLite database wrapper."""

    def __init__(self, uri, folder='.'):
        """
        Initialize database connection.

        Args:
            uri: Database URI like 'sqlite://dopy.db' or 'sqlite://:memory:'
            folder: Folder where database file is stored
        """
        # Parse URI
        if uri.startswith('sqlite://'):
            db_file = uri.replace('sqlite://', '')
        else:
            db_file = uri

        # Handle in-memory database special case
        if db_file == ':memory:':
            db_path = ':memory:'
        else:
            db_path = os.path.join(folder, db_file)

        self.conn = sqlite3.connect(db_path)
        self.tables = {}

    def define_table(self, name, *fields, **kwargs):
        """
        Define a table schema and create it if it doesn't exist.

        Args:
            name: Table name
            *fields: Field definitions

        Returns:
            Table object
        """
        # Create table if it doesn't exist
        field_defs = ['id INTEGER PRIMARY KEY AUTOINCREMENT']

        field_map = {}
        for field in fields:
            if hasattr(field, 'name') and hasattr(field, 'type'):
                field_name = field.name
                field_type = field.type
                field_map[field_name] = field_type

                # Map DAL types to SQLite types
                if field_type == 'string':
                    sql_type = 'TEXT'
                elif field_type == 'integer':
                    sql_type = 'INTEGER'
                elif field_type == 'boolean':
                    sql_type = 'INTEGER'  # SQLite uses 0/1 for boolean
                elif field_type == 'datetime':
                    sql_type = 'TEXT'  # Store as ISO format
                elif field_type == 'list:string':
                    sql_type = 'TEXT'  # Store as JSON
                else:
                    sql_type = 'TEXT'

                # Handle default values
                default = ''
                if hasattr(field, 'default') and field.default is not None:
                    if field.default is False:
                        default = ' DEFAULT 0'
                    elif field.default is True:
                        default = ' DEFAULT 1'
                    elif isinstance(field.default, str):
                        default = f" DEFAULT '{field.default}'"
                    else:
                        default = f' DEFAULT {field.default}'

                field_defs.append(f"{field_name} {sql_type}{default}")

        create_sql = f"CREATE TABLE IF NOT EXISTS {name} ({', '.join(field_defs)})"
        self.conn.execute(create_sql)
        self.conn.commit()

        # Create Table object
        table = Table(self, name)
        table._fields = field_map
        self.tables[name] = table

        return table

    def __call__(self, condition):
        """Create a query with a condition."""
        # Extract table from condition
        table = self._get_table_from_condition(condition)
        return Query(self, table, condition)

    def _get_table_from_condition(self, condition):
        """Extract table from a condition."""
        if isinstance(condition, Condition):
            return condition.field.table
        elif isinstance(condition, (CompoundCondition, NotCondition)):
            return self._get_table_from_condition(condition.left if hasattr(condition, 'left') else condition.condition)
        return None

    def commit(self):
        """Commit the current transaction."""
        self.conn.commit()

    def close(self):
        """Close database connection."""
        self.conn.close()

    def __getitem__(self, name):
        """Get a table by name."""
        return self.tables.get(name)


# Field definition class for compatibility with old DAL syntax
class FieldDef:
    """Field definition for table creation."""

    def __init__(self, name, type='string', default=None, **kwargs):
        self.name = name
        self.type = type
        self.default = default
        self.kwargs = kwargs
