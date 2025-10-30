"""Tests for reporting and metrics module."""

import pytest
from datetime import datetime
from dolist.reports import (
    calculate_metrics,
    get_period_start,
    get_period_label,
    format_metrics_json,
    format_metrics_text,
)


class MockTask:
    """Mock task object for testing."""

    def __init__(self, created_on, status="new", tag="default"):
        self.created_on = created_on
        self.status = status
        self.tag = tag


def test_get_period_start_day():
    """Test getting period start for day."""
    date = datetime(2025, 10, 30, 15, 30, 45)
    start = get_period_start(date, "day")
    assert start == datetime(2025, 10, 30, 0, 0, 0)


def test_get_period_start_week():
    """Test getting period start for week (Monday)."""
    # Thursday Oct 30, 2025
    date = datetime(2025, 10, 30, 15, 30, 45)
    start = get_period_start(date, "week")
    # Should be Monday Oct 27, 2025
    assert start == datetime(2025, 10, 27, 0, 0, 0)


def test_get_period_start_month():
    """Test getting period start for month."""
    date = datetime(2025, 10, 30, 15, 30, 45)
    start = get_period_start(date, "month")
    assert start == datetime(2025, 10, 1, 0, 0, 0)


def test_get_period_start_year():
    """Test getting period start for year."""
    date = datetime(2025, 10, 30, 15, 30, 45)
    start = get_period_start(date, "year")
    assert start == datetime(2025, 1, 1, 0, 0, 0)


def test_get_period_start_invalid():
    """Test that invalid period raises ValueError."""
    date = datetime(2025, 10, 30)
    with pytest.raises(ValueError, match="Unknown period"):
        get_period_start(date, "invalid")


def test_get_period_label_day():
    """Test getting period label for day."""
    date = datetime(2025, 10, 30)
    label = get_period_label(date, "day")
    assert label == "2025-10-30"


def test_get_period_label_week():
    """Test getting period label for week."""
    date = datetime(2025, 10, 30)
    label = get_period_label(date, "week")
    assert "Week of" in label
    assert "2025-10-27" in label


def test_get_period_label_month():
    """Test getting period label for month."""
    date = datetime(2025, 10, 30)
    label = get_period_label(date, "month")
    assert label == "2025-10"


def test_get_period_label_year():
    """Test getting period label for year."""
    date = datetime(2025, 10, 30)
    label = get_period_label(date, "year")
    assert label == "2025"


def test_calculate_metrics_empty():
    """Test calculating metrics with no tasks."""
    metrics = calculate_metrics([], period="month")

    assert metrics["total_tasks"] == 0
    assert metrics["total_by_period"] == {}
    assert metrics["status_totals"] == {}
    assert metrics["tag_totals"] == {}
    assert metrics["status_percentages"] == {}
    assert metrics["tag_percentages"] == {}


def test_calculate_metrics_single_task():
    """Test calculating metrics with a single task."""
    task = MockTask(
        created_on=datetime(2025, 10, 30, 10, 0, 0), status="new", tag="work"
    )
    metrics = calculate_metrics([task], period="month")

    assert metrics["total_tasks"] == 1
    assert metrics["status_totals"]["new"] == 1
    assert metrics["tag_totals"]["work"] == 1
    assert metrics["status_percentages"]["new"] == 100.0
    assert metrics["tag_percentages"]["work"] == 100.0


def test_calculate_metrics_multiple_tasks():
    """Test calculating metrics with multiple tasks."""
    tasks = [
        MockTask(datetime(2025, 10, 1), status="new", tag="work"),
        MockTask(datetime(2025, 10, 15), status="in-progress", tag="work"),
        MockTask(datetime(2025, 10, 20), status="done", tag="personal"),
        MockTask(datetime(2025, 10, 25), status="new", tag="work"),
    ]
    metrics = calculate_metrics(tasks, period="month")

    assert metrics["total_tasks"] == 4
    assert metrics["status_totals"]["new"] == 2
    assert metrics["status_totals"]["in-progress"] == 1
    assert metrics["status_totals"]["done"] == 1
    assert metrics["tag_totals"]["work"] == 3
    assert metrics["tag_totals"]["personal"] == 1


def test_calculate_metrics_by_period():
    """Test calculating metrics grouped by period."""
    tasks = [
        MockTask(datetime(2025, 9, 1), status="new", tag="work"),
        MockTask(datetime(2025, 9, 15), status="new", tag="work"),
        MockTask(datetime(2025, 10, 1), status="new", tag="work"),
    ]
    metrics = calculate_metrics(tasks, period="month")

    assert "2025-09" in metrics["total_by_period"]
    assert "2025-10" in metrics["total_by_period"]
    assert metrics["total_by_period"]["2025-09"] == 2
    assert metrics["total_by_period"]["2025-10"] == 1


def test_calculate_metrics_with_string_dates():
    """Test calculating metrics with string dates."""

    class MockTaskWithStringDate:
        def __init__(self, created_on_str, status="new", tag="default"):
            self.created_on = created_on_str
            self.status = status
            self.tag = tag

    tasks = [
        MockTaskWithStringDate("2025-10-30 10:00:00", status="new", tag="work"),
        MockTaskWithStringDate("2025-10-15 14:30:00", status="done", tag="personal"),
    ]
    metrics = calculate_metrics(tasks, period="month")

    assert metrics["total_tasks"] == 2
    assert metrics["status_totals"]["new"] == 1
    assert metrics["status_totals"]["done"] == 1


def test_calculate_metrics_percentages():
    """Test that percentages are calculated correctly."""
    tasks = [
        MockTask(datetime(2025, 10, 1), status="new", tag="work"),
        MockTask(datetime(2025, 10, 2), status="new", tag="work"),
        MockTask(datetime(2025, 10, 3), status="done", tag="work"),
        MockTask(datetime(2025, 10, 4), status="done", tag="personal"),
    ]
    metrics = calculate_metrics(tasks, period="month")

    assert metrics["status_percentages"]["new"] == 50.0
    assert metrics["status_percentages"]["done"] == 50.0
    assert metrics["tag_percentages"]["work"] == 75.0
    assert metrics["tag_percentages"]["personal"] == 25.0


def test_calculate_metrics_period_day():
    """Test calculating metrics by day."""
    tasks = [
        MockTask(datetime(2025, 10, 30, 10, 0), status="new", tag="work"),
        MockTask(datetime(2025, 10, 30, 15, 0), status="done", tag="work"),
        MockTask(datetime(2025, 10, 31, 10, 0), status="new", tag="personal"),
    ]
    metrics = calculate_metrics(tasks, period="day")

    assert "2025-10-30" in metrics["total_by_period"]
    assert "2025-10-31" in metrics["total_by_period"]
    assert metrics["total_by_period"]["2025-10-30"] == 2
    assert metrics["total_by_period"]["2025-10-31"] == 1


def test_calculate_metrics_period_year():
    """Test calculating metrics by year."""
    tasks = [
        MockTask(datetime(2024, 10, 30), status="new", tag="work"),
        MockTask(datetime(2025, 1, 15), status="done", tag="work"),
        MockTask(datetime(2025, 10, 31), status="new", tag="personal"),
    ]
    metrics = calculate_metrics(tasks, period="year")

    assert "2024" in metrics["total_by_period"]
    assert "2025" in metrics["total_by_period"]
    assert metrics["total_by_period"]["2024"] == 1
    assert metrics["total_by_period"]["2025"] == 2


def test_format_metrics_json():
    """Test formatting metrics as JSON."""
    tasks = [
        MockTask(datetime(2025, 10, 30), status="new", tag="work"),
    ]
    metrics = calculate_metrics(tasks, period="month")
    json_output = format_metrics_json(metrics)

    assert '"total_tasks": 1' in json_output
    assert '"period": "month"' in json_output
    assert "new" in json_output


def test_format_metrics_text():
    """Test formatting metrics as text."""
    tasks = [
        MockTask(datetime(2025, 10, 30), status="new", tag="work"),
        MockTask(datetime(2025, 10, 15), status="done", tag="personal"),
    ]
    metrics = calculate_metrics(tasks, period="month")
    text_output = format_metrics_text(metrics)

    # The output now contains Rich markup/ANSI codes, so just check for key content
    assert "2" in text_output  # Total tasks
    assert "Month" in text_output or "month" in text_output  # Period
    assert "Tasks by Status" in text_output
    assert "Tasks by Tag" in text_output
    assert "new" in text_output
    assert "done" in text_output
    assert "work" in text_output
    assert "personal" in text_output
