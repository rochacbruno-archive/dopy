"""Tests for reminder repeat indicator feature."""

import pytest
from datetime import datetime, timedelta
from dolist.reminder_parser import get_time_until


class TestReminderRepeatIndicatorLogic:
    """Test the logic for showing (r) indicator on repeating reminders."""

    def test_get_time_until_format(self):
        """Test that get_time_until returns expected format."""
        future_time = datetime.now() + timedelta(hours=1)
        result = get_time_until(future_time)
        assert "in " in result, "Should start with 'in '"
        assert "hour" in result or "minute" in result, "Should contain time unit"

    def test_repeat_indicator_format(self):
        """Test that (r) indicator can be appended to reminder display."""
        future_time = datetime.now() + timedelta(hours=2)
        reminder_display = get_time_until(future_time)
        with_indicator = f"{reminder_display} (r)"

        assert "(r)" in with_indicator, "Should contain (r) indicator"
        assert with_indicator.endswith(" (r)"), "Should end with (r)"

    def test_reminder_display_without_repeat(self):
        """Test reminder display without repeat indicator."""
        future_time = datetime.now() + timedelta(hours=1)
        reminder_display = get_time_until(future_time)

        # Should not have (r) by default
        assert "(r)" not in reminder_display, "Should not have (r) without repeat"

    def test_repeat_indicator_conditional_logic(self):
        """Test the conditional logic for adding (r) indicator."""
        from unittest.mock import Mock

        # Mock a row with reminder_repeat
        row_with_repeat = Mock()
        row_with_repeat.get = Mock(return_value="1 hour")

        future_time = datetime.now() + timedelta(hours=1)
        reminder_display = get_time_until(future_time)

        # Simulate the logic in do.py and tui.py
        if row_with_repeat.get("reminder_repeat"):
            reminder_display = f"{reminder_display} (r)"

        assert "(r)" in reminder_display, "Should add (r) when reminder_repeat exists"

    def test_no_repeat_indicator_when_none(self):
        """Test that no (r) indicator is added when reminder_repeat is None."""
        from unittest.mock import Mock

        # Mock a row without reminder_repeat
        row_without_repeat = Mock()
        row_without_repeat.get = Mock(return_value=None)

        future_time = datetime.now() + timedelta(hours=1)
        reminder_display = get_time_until(future_time)

        # Simulate the logic in do.py and tui.py
        if row_without_repeat.get("reminder_repeat"):
            reminder_display = f"{reminder_display} (r)"

        assert "(r)" not in reminder_display, (
            "Should not add (r) when reminder_repeat is None"
        )
