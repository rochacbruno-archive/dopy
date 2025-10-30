"""
Reporting and metrics module for DoList tasks.

Provides metrics calculation for tasks including:
- Total number of tasks by period
- Tasks per status per period
- Tasks per tag per period
"""

from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any


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
                created = datetime.fromisoformat(created.replace("Z", "+00:00"))
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
        status = getattr(task, "status", "unknown")
        status_by_period[period_label][status] += 1
        status_totals[status] += 1

        # Count by tag
        tag = getattr(task, "tag", "default")
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
    """Format metrics as human-readable text with colored bar charts."""
    from rich.console import Console
    from io import StringIO

    # Create a console that writes to a string
    string_io = StringIO()
    console = Console(file=string_io, force_terminal=True, width=100)

    # Header
    console.print("\n[bold cyan]Task Metrics Report[/bold cyan]")
    console.print(f"[cyan]Total Tasks:[/cyan] {metrics['total_tasks']}")
    console.print(f"[cyan]Period:[/cyan] {metrics['period'].title()}\n")

    # Status distribution chart
    if metrics["status_totals"]:
        console.print("[bold yellow]Tasks by Status:[/bold yellow]\n")

        statuses = list(metrics["status_totals"].keys())
        counts = list(metrics["status_totals"].values())

        # Define colors for each status
        status_colors = {
            "new": "cyan",
            "in-progress": "yellow",
            "done": "green",
            "cancel": "red",
            "post": "magenta",
        }

        # Create colored bar chart
        max_count = max(counts) if counts else 1
        bar_width = 50  # Maximum bar width in characters

        for i, status in enumerate(statuses):
            color = status_colors.get(status, "white")
            count = metrics["status_totals"][status]
            pct = metrics["status_percentages"][status]

            # Calculate bar length
            bar_length = int((count / max_count) * bar_width) if max_count > 0 else 0
            bar = "█" * bar_length

            # Alternate background for row
            if i % 2 == 0:
                console.print(
                    f"[on grey11]{status:12s}[/] [{color}]{bar}[/] [{color} bold]{count:3d}[/] [dim]({pct:.1f}%)[/]"
                )
            else:
                console.print(
                    f"{status:12s} [{color}]{bar}[/] [{color} bold]{count:3d}[/] [dim]({pct:.1f}%)[/]"
                )

        console.print()

    # Tag distribution chart
    if metrics["tag_totals"]:
        console.print("[bold yellow]Tasks by Tag:[/bold yellow]\n")

        tags = list(metrics["tag_totals"].keys())
        tag_counts = list(metrics["tag_totals"].values())

        # Use a variety of colors for tags
        tag_colors = ["cyan", "yellow", "green", "magenta", "blue", "red"]

        # Create colored bar chart
        max_count = max(tag_counts) if tag_counts else 1
        bar_width = 50  # Maximum bar width in characters

        for i, tag in enumerate(tags):
            color = tag_colors[i % len(tag_colors)]
            count = metrics["tag_totals"][tag]
            pct = metrics["tag_percentages"][tag]

            # Calculate bar length
            bar_length = int((count / max_count) * bar_width) if max_count > 0 else 0
            bar = "█" * bar_length

            # Alternate background for row
            if i % 2 == 0:
                console.print(
                    f"[on grey11]{tag:12s}[/] [{color}]{bar}[/] [{color} bold]{count:3d}[/] [dim]({pct:.1f}%)[/]"
                )
            else:
                console.print(
                    f"{tag:12s} [{color}]{bar}[/] [{color} bold]{count:3d}[/] [dim]({pct:.1f}%)[/]"
                )

        console.print()

    # Tasks over time
    if metrics["total_by_period"] and len(metrics["total_by_period"]) > 1:
        console.print("[bold yellow]Tasks by Period:[/bold yellow]\n")

        periods = sorted(metrics["total_by_period"].keys())
        period_counts = [metrics["total_by_period"][p] for p in periods]

        max_count = max(period_counts) if period_counts else 1
        bar_width = 50

        for i, (period_label, count) in enumerate(zip(periods, period_counts)):
            # Calculate bar length
            bar_length = int((count / max_count) * bar_width) if max_count > 0 else 0
            bar = "█" * bar_length

            # Use cyan for time series
            if i % 2 == 0:
                console.print(
                    f"[on grey11]{period_label:12s}[/] [cyan]{bar}[/] [cyan bold]{count:3d}[/]"
                )
            else:
                console.print(
                    f"{period_label:12s} [cyan]{bar}[/] [cyan bold]{count:3d}[/]"
                )

        console.print()

    return string_io.getvalue()
