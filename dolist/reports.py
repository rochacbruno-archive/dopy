"""
Reporting and metrics module for DoList tasks.

Provides metrics calculation for tasks including:
- Total number of tasks by period
- Tasks per status per period
- Tasks per tag per period
"""

from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any, Optional


def get_period_start(date: datetime, period: str) -> datetime:
    """Get the start date for a given period."""
    if period == "day":
        return date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        # Start of week (Monday)
        start = date - timedelta(days=date.weekday())
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        return date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError(f"Unknown period: {period}")


def get_period_label(date: datetime, period: str) -> str:
    """Get a human-readable label for a period."""
    if period == "day":
        return date.strftime("%Y-%m-%d")
    elif period == "week":
        start = date - timedelta(days=date.weekday())
        return start.strftime("Week of %Y-%m-%d")
    elif period == "month":
        return date.strftime("%Y-%m")
    elif period == "year":
        return date.strftime("%Y")
    else:
        raise ValueError(f"Unknown period: {period}")


def calculate_metrics(tasks: List[Any], period: str = "month") -> Dict[str, Any]:
    """
    Calculate metrics for the given tasks.

    Args:
        tasks: List of Task objects or database rows
        period: One of 'day', 'week', 'month', 'year'

    Returns:
        Dictionary containing:
        - total_by_period: {period_label: count}
        - status_by_period: {period_label: {status: count}}
        - tag_by_period: {period_label: {tag: count}}
        - status_totals: {status: count}
        - tag_totals: {tag: count}
        - status_percentages: {status: percentage}
        - tag_percentages: {tag: percentage}
    """
    if not tasks:
        return {
            "total_by_period": {},
            "status_by_period": {},
            "tag_by_period": {},
            "status_totals": {},
            "tag_totals": {},
            "status_percentages": {},
            "tag_percentages": {},
            "total_tasks": 0,
            "period": period,
        }

    # Group tasks by period
    total_by_period = defaultdict(int)
    status_by_period = defaultdict(lambda: defaultdict(int))
    tag_by_period = defaultdict(lambda: defaultdict(int))
    status_totals = defaultdict(int)
    tag_totals = defaultdict(int)

    for task in tasks:
        # Get created date
        created = task.created_on
        if isinstance(created, str):
            # Parse string date
            try:
                created = datetime.fromisoformat(created.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                # Try alternative format
                try:
                    created = datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
                except (ValueError, AttributeError):
                    # Skip tasks with invalid dates
                    continue

        # Get period label
        period_label = get_period_label(created, period)

        # Count totals
        total_by_period[period_label] += 1

        # Count by status
        status = getattr(task, 'status', 'unknown')
        status_by_period[period_label][status] += 1
        status_totals[status] += 1

        # Count by tag
        tag = getattr(task, 'tag', 'default')
        tag_by_period[period_label][tag] += 1
        tag_totals[tag] += 1

    # Calculate percentages
    total_tasks = len(tasks)
    status_percentages = {
        status: (count / total_tasks * 100) if total_tasks > 0 else 0
        for status, count in status_totals.items()
    }
    tag_percentages = {
        tag: (count / total_tasks * 100) if total_tasks > 0 else 0
        for tag, count in tag_totals.items()
    }

    return {
        "total_by_period": dict(total_by_period),
        "status_by_period": {k: dict(v) for k, v in status_by_period.items()},
        "tag_by_period": {k: dict(v) for k, v in tag_by_period.items()},
        "status_totals": dict(status_totals),
        "tag_totals": dict(tag_totals),
        "status_percentages": status_percentages,
        "tag_percentages": tag_percentages,
        "total_tasks": total_tasks,
        "period": period,
    }


def format_metrics_json(metrics: Dict[str, Any]) -> str:
    """Format metrics as JSON string."""
    import json
    return json.dumps(metrics, indent=2)


def format_metrics_text(metrics: Dict[str, Any]) -> str:
    """Format metrics as human-readable text."""
    lines = []
    lines.append(f"Report Period: {metrics['period']}")
    lines.append(f"Total Tasks: {metrics['total_tasks']}")
    lines.append("")

    # Status breakdown
    lines.append("Tasks by Status:")
    for status, count in sorted(metrics['status_totals'].items()):
        pct = metrics['status_percentages'][status]
        lines.append(f"  {status}: {count} ({pct:.1f}%)")
    lines.append("")

    # Tag breakdown
    lines.append("Tasks by Tag:")
    for tag, count in sorted(metrics['tag_totals'].items()):
        pct = metrics['tag_percentages'][tag]
        lines.append(f"  {tag}: {count} ({pct:.1f}%)")
    lines.append("")

    # Period breakdown
    lines.append("Tasks by Period:")
    for period_label in sorted(metrics['total_by_period'].keys()):
        count = metrics['total_by_period'][period_label]
        lines.append(f"  {period_label}: {count}")

    return "\n".join(lines)
