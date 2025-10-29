#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Task dependency tracking for DoList.

This module provides utilities for parsing and managing task dependencies
using the notes system. Tasks can be marked as depending on other tasks
using markers like 'depends #N' or 'under #N' in their notes.
"""

import re
from typing import Optional, Set


def parse_dependencies(notes: list[str]) -> tuple[Optional[int], Set[int]]:
    """Parse dependency markers from task notes.

    Args:
        notes: List of note strings

    Returns:
        Tuple of (depends_on_id, under_ids_set)
        - depends_on_id: The task ID this task depends on (blocks this task)
        - under_ids_set: Set of task IDs this task is under (parent tasks)

    Notes:
        - 'depends #N' means this task is blocked until task N is done
        - 'under #N' means this task is a child/subtask of task N
        - Only the first 'depends' marker is used (subsequent ones ignored)
        - Multiple 'under' markers are collected into a set
    """
    depends_on = None
    under_ids = set()

    for note in notes:
        # Look for 'depends #N' pattern
        depends_match = re.search(r'depends\s+#(\d+)', note, re.IGNORECASE)
        if depends_match and depends_on is None:
            # Only use the first depends marker
            depends_on = int(depends_match.group(1))

        # Look for 'under #N' pattern
        under_matches = re.finditer(r'under\s+#(\d+)', note, re.IGNORECASE)
        for match in under_matches:
            under_ids.add(int(match.group(1)))

    return depends_on, under_ids


def get_dependency_display_info(task_id: int, notes: list[str]) -> dict:
    """Get display information for a task's dependencies.

    Args:
        task_id: The task's ID
        notes: The task's notes

    Returns:
        Dictionary with:
        - is_blocked: True if task has a 'depends' marker
        - depends_on: Task ID this task depends on (or None)
        - under_ids: Set of parent task IDs
        - display_prefix: String to prepend to task name ("N!" or "N>")
        - prefix_type: "blocked" or "under" or None
    """
    depends_on, under_ids = parse_dependencies(notes)

    # 'depends' takes precedence over 'under'
    if depends_on is not None:
        return {
            'is_blocked': True,
            'depends_on': depends_on,
            'under_ids': under_ids,
            'display_prefix': f"{depends_on}!",
            'prefix_type': 'blocked'
        }
    elif under_ids:
        # Use the first parent ID for display
        parent_id = min(under_ids)
        return {
            'is_blocked': False,
            'depends_on': None,
            'under_ids': under_ids,
            'display_prefix': f"{parent_id}>",
            'prefix_type': 'under'
        }
    else:
        return {
            'is_blocked': False,
            'depends_on': None,
            'under_ids': set(),
            'display_prefix': None,
            'prefix_type': None
        }


def count_children(task_id: int, all_tasks: list) -> int:
    """Count how many tasks are under this task.

    Args:
        task_id: The parent task's ID
        all_tasks: List of all task objects/rows

    Returns:
        Number of child tasks
    """
    count = 0
    for task in all_tasks:
        if hasattr(task, 'notes') and task.notes:
            _, under_ids = parse_dependencies(task.notes)
            # Check both 'depends' and 'under' markers
            depends_on, _ = parse_dependencies(task.notes)
            if task_id in under_ids or depends_on == task_id:
                count += 1
    return count
