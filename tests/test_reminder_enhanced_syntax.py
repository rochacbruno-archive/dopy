"""Tests for enhanced reminder parsing syntax.

Tests all new reminder formats:
- Weekdays: monday|mon, tuesday|tue, etc.
- Weekdays with time: monday 9, mon 14, monday 9PM
- Day of month: 25 (next day 25)
- Month+day: 25 Aug, 25 August
- Full dates: 25 Dec/27, 25 Dec/2027, 15 December/29 11AM
- ISO format: 2027-01-31 12:00:00, 2027-01-31T12:00:00
"""

from datetime import datetime, timedelta
from dolist.reminder_parser import (
    parse_reminder,
    parse_time_part,
    next_weekday,
    next_day_of_month,
    WEEKDAY_NAMES,
    MONTH_NAMES,
)


class TestTimePartParsing:
    """Test parsing of time components."""

    def test_parse_simple_hour(self):
        """Test parsing simple hour numbers."""
        assert parse_time_part("9") == 9
        assert parse_time_part("14") == 14
        assert parse_time_part("21") == 21
        assert parse_time_part("0") == 0
        assert parse_time_part("23") == 23

    def test_parse_am_pm(self):
        """Test parsing AM/PM format."""
        assert parse_time_part("9AM") == 9
        assert parse_time_part("9PM") == 21
        assert parse_time_part("12AM") == 0
        assert parse_time_part("12PM") == 12
        assert parse_time_part("1PM") == 13
        assert parse_time_part("11PM") == 23

    def test_parse_invalid_time(self):
        """Test invalid time strings."""
        assert parse_time_part("24") is None
        assert parse_time_part("25") is None
        assert parse_time_part("13AM") is None
        assert parse_time_part("0PM") is None
        assert parse_time_part("abc") is None


class TestWeekdayParsing:
    """Test weekday reminder parsing."""

    def test_weekday_names_mapping(self):
        """Test that weekday names are correctly mapped."""
        assert WEEKDAY_NAMES["monday"] == 0
        assert WEEKDAY_NAMES["mon"] == 0
        assert WEEKDAY_NAMES["friday"] == 4
        assert WEEKDAY_NAMES["fri"] == 4
        assert WEEKDAY_NAMES["sunday"] == 6
        assert WEEKDAY_NAMES["sun"] == 6

    def test_next_weekday_calculation(self):
        """Test next weekday calculation."""
        # Test from a Monday (2025-01-06 is a Monday)
        base = datetime(2025, 1, 6, 10, 0, 0)  # Monday 10 AM

        # Next Tuesday should be 2025-01-07
        result = next_weekday(base, 1, hour=9)  # Tuesday
        assert result.date() == datetime(2025, 1, 7).date()
        assert result.hour == 9

        # Next Monday (same day but time hasn't passed) should be same day
        result = next_weekday(base, 0, hour=15)  # Monday 3 PM
        assert result.date() == datetime(2025, 1, 6).date()
        assert result.hour == 15

        # Next Monday (same day but time passed) should be next week
        result = next_weekday(base, 0, hour=9)  # Monday 9 AM
        assert result.date() == datetime(2025, 1, 13).date()
        assert result.hour == 9

    def test_parse_weekday_alone(self):
        """Test parsing weekday without time."""
        base = datetime(2025, 1, 6, 10, 0, 0)  # Monday 10 AM

        # Test "monday"
        result, error, repeat = parse_reminder("monday", base)
        assert error is None
        assert result is not None
        assert result.weekday() == 0  # Monday
        assert result > base
        assert result.hour == 9  # Default hour

        # Test "fri"
        result, error, repeat = parse_reminder("fri", base)
        assert error is None
        assert result.weekday() == 4  # Friday
        assert result.date() == datetime(2025, 1, 10).date()

    def test_parse_weekday_with_time(self):
        """Test parsing weekday with time."""
        base = datetime(2025, 1, 6, 10, 0, 0)  # Monday 10 AM

        # Test "monday 9"
        result, error, repeat = parse_reminder("monday 9", base)
        assert error is None
        assert result.hour == 9

        # Test "monday 9PM"
        result, error, repeat = parse_reminder("monday 9PM", base)
        assert error is None
        assert result.hour == 21

        # Test "tue 14"
        result, error, repeat = parse_reminder("tue 14", base)
        assert error is None
        assert result.weekday() == 1  # Tuesday
        assert result.hour == 14

        # Test "friday 21"
        result, error, repeat = parse_reminder("friday 21", base)
        assert error is None
        assert result.weekday() == 4
        assert result.hour == 21

    def test_weekday_with_repeat(self):
        """Test weekday reminders with repeat keyword."""
        base = datetime(2025, 1, 6, 10, 0, 0)

        result, error, repeat = parse_reminder("monday 9AM repeat", base)
        assert error is None
        assert result is not None
        assert repeat == "monday 9am"  # Normalized to lowercase


class TestDayOfMonthParsing:
    """Test day of month reminder parsing."""

    def test_next_day_of_month(self):
        """Test next occurrence of day of month."""
        base = datetime(2025, 1, 15, 10, 0, 0)  # Jan 15

        # Day 25 should be in current month
        result = next_day_of_month(base, 25, hour=9)
        assert result.date() == datetime(2025, 1, 25).date()
        assert result.hour == 9

        # Day 10 should be in next month (already passed)
        result = next_day_of_month(base, 10, hour=9)
        assert result.date() == datetime(2025, 2, 10).date()

        # Day 31 in Feb should skip to March
        base = datetime(2025, 2, 15, 10, 0, 0)
        result = next_day_of_month(base, 31, hour=9)
        assert result.month == 3
        assert result.day == 31

    def test_parse_day_of_month(self):
        """Test parsing just a number as day of month."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        # Test "25"
        result, error, repeat = parse_reminder("25", base)
        assert error is None
        assert result.day == 25
        assert result.month == 1

        # Test "5" (should be next month)
        result, error, repeat = parse_reminder("5", base)
        assert error is None
        assert result.day == 5
        assert result.month == 2

    def test_invalid_day_of_month(self):
        """Test invalid day numbers."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        result, error, repeat = parse_reminder("32", base)
        assert result is None
        assert "Invalid day of month" in error

        result, error, repeat = parse_reminder("0", base)
        assert result is None


class TestMonthDayParsing:
    """Test month+day reminder parsing."""

    def test_month_names_mapping(self):
        """Test that month names are correctly mapped."""
        assert MONTH_NAMES["jan"] == 1
        assert MONTH_NAMES["january"] == 1
        assert MONTH_NAMES["aug"] == 8
        assert MONTH_NAMES["august"] == 8
        assert MONTH_NAMES["dec"] == 12
        assert MONTH_NAMES["december"] == 12

    def test_parse_month_day(self):
        """Test parsing 'Day Month' format."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        # Test "25 Aug" (should be this year)
        result, error, repeat = parse_reminder("25 aug", base)
        assert error is None
        assert result.month == 8
        assert result.day == 25
        assert result.year == 2025

        # Test "25 August"
        result, error, repeat = parse_reminder("25 august", base)
        assert error is None
        assert result.month == 8
        assert result.day == 25

        # Test "1 jan" (should be next year since Jan 15 already passed)
        result, error, repeat = parse_reminder("1 jan", base)
        assert error is None
        assert result.year == 2026


class TestFullDateParsing:
    """Test full date reminder parsing with year."""

    def test_parse_day_month_year(self):
        """Test 'Day Month/Year' format."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        # Test "25 Dec/27"
        result, error, repeat = parse_reminder("25 dec/27", base)
        assert error is None
        assert result.year == 2027
        assert result.month == 12
        assert result.day == 25

        # Test "25 Dec/2027"
        result, error, repeat = parse_reminder("25 dec/2027", base)
        assert error is None
        assert result.year == 2027
        assert result.month == 12
        assert result.day == 25

    def test_parse_day_month_year_time(self):
        """Test 'Day Month/Year Time' format."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        # Test "15 December/29 11AM"
        result, error, repeat = parse_reminder("15 december/29 11AM", base)
        assert error is None
        assert result.year == 2029
        assert result.month == 12
        assert result.day == 15
        assert result.hour == 11

        # Test "25 Dec/2027 9PM"
        result, error, repeat = parse_reminder("25 dec/2027 9PM", base)
        assert error is None
        assert result.year == 2027
        assert result.hour == 21

    def test_past_date_rejected(self):
        """Test that past dates are rejected."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        result, error, repeat = parse_reminder("1 jan/2024", base)
        assert result is None
        assert "past" in error.lower()


class TestISOFormatParsing:
    """Test ISO format datetime parsing."""

    def test_parse_iso_datetime(self):
        """Test ISO format with time (YYYY-MM-DD HH:MM:SS)."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        # Test "2027-01-31 12:00:00"
        result, error, repeat = parse_reminder("2027-01-31 12:00:00", base)
        assert error is None
        assert result.year == 2027
        assert result.month == 1
        assert result.day == 31
        assert result.hour == 12
        assert result.minute == 0
        assert result.second == 0

        # Test "2027-01-31T12:00:00" (T separator)
        result, error, repeat = parse_reminder("2027-01-31T12:00:00", base)
        assert error is None
        assert result.year == 2027
        assert result.month == 1
        assert result.day == 31
        assert result.hour == 12

    def test_parse_iso_date_only(self):
        """Test ISO format date only (YYYY-MM-DD)."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        result, error, repeat = parse_reminder("2027-01-31", base)
        assert error is None
        assert result.year == 2027
        assert result.month == 1
        assert result.day == 31
        assert result.hour == 9  # Default hour

    def test_iso_past_date_rejected(self):
        """Test that past ISO dates are rejected."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        result, error, repeat = parse_reminder("2024-12-25 12:00:00", base)
        assert result is None
        assert "past" in error.lower()

    def test_iso_invalid_date(self):
        """Test invalid ISO dates."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        result, error, repeat = parse_reminder("2027-13-31 12:00:00", base)
        assert result is None
        assert error is not None

        result, error, repeat = parse_reminder("2027-02-30 12:00:00", base)
        assert result is None


class TestRepeatKeyword:
    """Test repeat keyword with all formats."""

    def test_weekday_repeat(self):
        """Test weekday with repeat."""
        base = datetime(2025, 1, 6, 10, 0, 0)

        result, error, repeat = parse_reminder("monday 9am repeat", base)
        assert error is None
        assert repeat == "monday 9am"

    def test_day_of_month_repeat(self):
        """Test day of month with repeat."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        result, error, repeat = parse_reminder("25 repeat", base)
        assert error is None
        assert repeat == "25"

    def test_existing_formats_repeat(self):
        """Test that existing formats still work with repeat."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        result, error, repeat = parse_reminder("2 hours repeat", base)
        assert error is None
        assert repeat == "2 hours"


class TestBackwardsCompatibility:
    """Test that existing reminder syntax still works."""

    def test_today_tomorrow(self):
        """Test 'today' and 'tomorrow' keywords."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        result, error, repeat = parse_reminder("today", base)
        assert error is None
        assert result.date() >= base.date()

        result, error, repeat = parse_reminder("tomorrow", base)
        assert error is None
        assert result.date() == (base + timedelta(days=1)).date()

    def test_next_unit(self):
        """Test 'next hour/day/week' syntax."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        result, error, repeat = parse_reminder("next hour", base)
        assert error is None
        assert result == base + timedelta(hours=1)

        result, error, repeat = parse_reminder("next day", base)
        assert error is None

    def test_number_unit(self):
        """Test '2 hours', '3 days' syntax."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        result, error, repeat = parse_reminder("2 hours", base)
        assert error is None
        assert result == base + timedelta(hours=2)

        result, error, repeat = parse_reminder("3 days", base)
        assert error is None
        assert result == base + timedelta(days=3)

        result, error, repeat = parse_reminder("30 minutes", base)
        assert error is None
        assert result == base + timedelta(minutes=30)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_string(self):
        """Test empty reminder string."""
        result, error, repeat = parse_reminder("", None)
        assert result is None
        assert "empty" in error.lower()

    def test_invalid_syntax(self):
        """Test completely invalid syntax."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        result, error, repeat = parse_reminder("invalid syntax here", base)
        assert result is None
        assert "Could not parse" in error

    def test_case_insensitive(self):
        """Test that parsing is case insensitive."""
        base = datetime(2025, 1, 15, 10, 0, 0)

        result1, _, _ = parse_reminder("MONDAY", base)
        result2, _, _ = parse_reminder("monday", base)
        result3, _, _ = parse_reminder("Monday", base)

        assert result1 is not None
        assert result2 is not None
        assert result3 is not None
        assert result1.weekday() == result2.weekday() == result3.weekday()
