#!/usr/bin/env python
# -*- coding:utf-8 -*-

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from .dependency import parse_dependencies, get_dependency_display_info


class Task(BaseModel):
    """To show the task
    >>> print task
    To show a field (available name, tag, status, reminder, priority, size)
    >>> task.name
    To edit the task assign to a field
    >>> task.name = "Other name"
    To delete a task
    >>> task.delete()
    To exit
    >>> quit()
    ######################################
    """

    id: Optional[int] = None
    name: str
    tag: str = "default"
    status: str = "new"
    reminder: Optional[str] = None
    reminder_repeat: Optional[str] = None  # For recurring reminders (e.g., "2 hours")
    notes: list[str] = Field(default_factory=list)
    created_on: datetime = Field(default_factory=datetime.now)
    deleted: bool = False
    priority: int = 0
    size: str = "U"

    # Database connection for persistence (not part of the model data)
    _db: Optional[object] = None
    _row: Optional[object] = None

    model_config = {
        "arbitrary_types_allowed": True,
        "from_attributes": True,
    }

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate that status is one of the allowed values."""
        valid_statuses = {"new", "in-progress", "done", "cancel", "post"}
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")
        return v

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: str) -> str:
        """Validate and normalize size field."""
        if not v:
            return "U"
        # Normalize to uppercase first letter
        v_upper = v.upper()
        if v_upper in ("U", "S", "M", "L"):
            return v_upper
        # Handle full words (case insensitive)
        size_map = {"SMALL": "S", "MEDIUM": "M", "LARGE": "L", "UNDEFINED": "U"}
        normalized = size_map.get(v_upper)
        if normalized:
            return normalized
        raise ValueError(
            "Size must be one of: U, S, M, L (or Small, Medium, Large, Undefined)"
        )
        return v

    @classmethod
    def from_row(cls, db, row) -> "Task":
        """Create a Task instance from a database row."""
        task = cls(
            id=row.id,
            name=row.name,
            tag=row.tag,
            status=row.status,
            reminder=row.reminder,
            reminder_repeat=row.get("reminder_repeat", None),
            notes=row.notes or [],
            created_on=row.created_on,
            deleted=row.deleted,
            priority=row.get("priority", 0),
            size=row.get("size", "U"),
        )
        task._db = db
        task._row = row
        return task

    def _update_db(self, **kwargs):
        """Update the database with the given fields."""
        if self._row is not None and self._db is not None:
            self._row.update_record(**kwargs)
            self._db.commit()

    def update_name(self, value: str):
        """Update the task name."""
        self.name = value
        self._update_db(name=value)

    def update_tag(self, value: str):
        """Update the task tag."""
        self.tag = value
        self._update_db(tag=value)

    def update_status(self, value: str):
        """Update the task status."""
        self.status = value
        self._update_db(status=value)

    def update_reminder(self, value: Optional[str]):
        """Update the task reminder."""
        self.reminder = value
        self._update_db(reminder=value)

    def update_reminder_repeat(self, value: Optional[str]):
        """Update the task reminder repeat interval."""
        self.reminder_repeat = value
        self._update_db(reminder_repeat=value)

    def update_notes(self, value: list[str]):
        """Update the task notes."""
        self.notes = value
        self._update_db(notes=value)

    def update_priority(self, value: int):
        """Update the task priority."""
        self.priority = value
        self._update_db(priority=value)

    def increment_priority(self, amount: int = 1) -> int:
        """Increment the task priority (max 99).

        Args:
            amount: Amount to increment by (default: 1)

        Returns:
            New priority value
        """
        new_priority = min(99, self.priority + amount)
        self.update_priority(new_priority)
        return new_priority

    def decrement_priority(self, amount: int = 1) -> int:
        """Decrement the task priority (min 0).

        Args:
            amount: Amount to decrement by (default: 1)

        Returns:
            New priority value
        """
        new_priority = max(0, self.priority - amount)
        self.update_priority(new_priority)
        return new_priority

    def update_size(self, value: str):
        """Update the task size."""
        # Validate and normalize the size value
        self.size = self.validate_size(value)
        self._update_db(size=self.size)

    def add_note(self, note: str):
        """Add a note to the task."""
        self.notes.append(note)
        self._update_db(notes=self.notes)

    def remove_note(self, index: int):
        """Remove a note by index."""
        if 0 <= index < len(self.notes):
            del self.notes[index]
            self._update_db(notes=self.notes)

    def delete(self):
        """Soft delete the task."""
        self.deleted = True
        if self._row is not None:
            self._row.delete_record()
            if self._db is not None:
                self._db.commit()

    def __str__(self):
        return f"Task(id={self.id}, name={self.name}, tag={self.tag}, status={self.status})"

    def __repr__(self):
        return self.__str__()

    def is_blocked(self) -> bool:
        """Check if this task is blocked by a dependency.

        Returns:
            True if task has a 'depends #N' marker in notes
        """
        depends_on, _ = parse_dependencies(self.notes)
        return depends_on is not None

    def get_depends_on(self) -> Optional[int]:
        """Get the task ID this task depends on.

        Returns:
            Task ID or None if no dependency
        """
        depends_on, _ = parse_dependencies(self.notes)
        return depends_on

    def get_under_ids(self) -> set[int]:
        """Get set of parent task IDs.

        Returns:
            Set of task IDs this task is under
        """
        _, under_ids = parse_dependencies(self.notes)
        return under_ids

    def get_dependency_info(self) -> dict:
        """Get complete dependency display information.

        Returns:
            Dictionary with dependency info for display
        """
        return get_dependency_display_info(self.id or 0, self.notes)
