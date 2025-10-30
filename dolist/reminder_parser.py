#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Parser for reminder time expressions.

Supports flexible syntax like:
- today, tomorrow
- next hour|day|week|month|quarter|year|decade
- {number} seconds|minutes|hours|days|weeks|months|quarters|years
- Abbreviations: sec, min, hr, h, d, w, mo, q, y
- Weekdays: monday|mon, tuesday|tue, wednesday|wed, thursday|thu, friday|fri, saturday|sat, sunday|sun
- Weekdays with time: monday 9, monday 14, monday 9PM, mon 21
- Day of month: 25 (next occurrence of day 25)
- Month+day: 25 Aug, 25 August
- Full dates: 25 Dec/27, 25 Dec/2027, 15 December/29 11AM
- ISO format: 2027-01-31 12:00:00, 2027-01-31T12:00:00
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
import re


# Abbreviation mappings for time units
UNIT_ABBREV = {
    # Seconds
    "sec": "seconds",
    "secs": "seconds",
    "s": "seconds",
    "second": "seconds",
    # Minutes
    "min": "minutes",
    "mins": "minutes",
    "m": "minutes",
    "minute": "minutes",
    # Hours
    "hr": "hours",
    "hrs": "hours",
    "h": "hours",
    "ho": "hours",
    "hour": "hours",
    # Days
    "d": "days",
    "day": "days",
    # Weeks
    "w": "weeks",
    "wk": "weeks",
    "wks": "weeks",
    "week": "weeks",
    # Months (note: "mon" conflicts with Monday, so removed from here)
    "mo": "months",
    "mos": "months",
    "month": "months",
    # Quarters (3 months)
    "q": "quarters",
    "qtr": "quarters",
    "quarter": "quarters",
    # Years
    "y": "years",
    "yr": "years",
    "yrs": "years",
    "year": "years",
    # Decades
    "decade": "decades",
    "decades": "decades",
}

# Weekday mappings
WEEKDAY_NAMES = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}

# Month name mappings (1-based)
MONTH_NAMES = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def get_default_start_hour():
    """Get the default start hour from config, defaulting to 9 AM."""
    try:
        from dolist.do import CONFIG

        return CONFIG.get("day_start_hour", 9)
    except Exception:
        return 9


def normalize_unit(unit: str) -> Optional[str]:
    """Normalize a time unit to its canonical form.

    Args:
        unit: Time unit string (can be abbreviated or full)

    Returns:
        Normalized unit name or None if invalid
    """
    unit_lower = unit.lower().strip()

    # Check if already normalized
    if unit_lower in [
        "seconds",
        "minutes",
        "hours",
        "days",
        "weeks",
        "months",
        "quarters",
        "years",
        "decades",
    ]:
        return unit_lower

    # Check abbreviations
    return UNIT_ABBREV.get(unit_lower)


def parse_time_part(time_str: str) -> Optional[int]:
    """Parse time string like '9', '14', '9PM', '9AM', '21' into hour (24-hour format).

    Args:
        time_str: Time string to parse

    Returns:
        Hour in 24-hour format (0-23) or None if invalid
    """
    time_str = time_str.strip().upper()

    # Try to parse as simple number (military time or 24-hour)
    if time_str.isdigit():
        hour = int(time_str)
        if 0 <= hour <= 23:
            return hour
        return None

    # Try to parse with AM/PM suffix
    am_pm_match = re.match(r"^(\d+)(AM|PM)$", time_str)
    if am_pm_match:
        hour = int(am_pm_match.group(1))
        meridiem = am_pm_match.group(2)

        if not (1 <= hour <= 12):
            return None

        if meridiem == "AM":
            return 0 if hour == 12 else hour
        else:  # PM
            return 12 if hour == 12 else hour + 12

    return None


def next_weekday(base: datetime, weekday: int, hour: Optional[int] = None) -> datetime:
    """Get the next occurrence of a weekday.

    Args:
        base: Base datetime
        weekday: Target weekday (0=Monday, 6=Sunday)
        hour: Optional hour to set (default: uses day_start_hour from config)

    Returns:
        Next occurrence of the weekday
    """
    if hour is None:
        hour = get_default_start_hour()

    # Calculate days until target weekday
    current_weekday = base.weekday()
    days_ahead = weekday - current_weekday

    # If it's the same day but time has passed, or it's a past day this week, go to next week
    if days_ahead <= 0:
        target_time = base.replace(hour=hour, minute=0, second=0, microsecond=0)
        if days_ahead == 0 and base < target_time:
            # Same day, but time hasn't passed yet
            return target_time
        # Either same day but time passed, or past day this week
        days_ahead += 7

    result = base + timedelta(days=days_ahead)
    return result.replace(hour=hour, minute=0, second=0, microsecond=0)


def next_day_of_month(
    base: datetime, day: int, hour: Optional[int] = None
) -> Optional[datetime]:
    """Get the next occurrence of a specific day of the month.

    Args:
        base: Base datetime
        day: Day of month (1-31)
        hour: Optional hour to set (default: uses day_start_hour from config)

    Returns:
        Next occurrence of the day, or None if invalid day
    """
    if not (1 <= day <= 31):
        return None

    if hour is None:
        hour = get_default_start_hour()

    # Try current month first
    try:
        result = base.replace(day=day, hour=hour, minute=0, second=0, microsecond=0)
        if result > base:
            return result
    except ValueError:
        pass  # Day doesn't exist in current month

    # Try next month
    next_month = base.month + 1
    next_year = base.year
    if next_month > 12:
        next_month = 1
        next_year += 1

    try:
        return datetime(next_year, next_month, day, hour, 0, 0)
    except ValueError:
        # Day doesn't exist in next month either, try the month after
        next_month += 1
        if next_month > 12:
            next_month = 1
            next_year += 1
        try:
            return datetime(next_year, next_month, day, hour, 0, 0)
        except ValueError:
            return None


def parse_reminder(
    text: str, base_time: Optional[datetime] = None
) -> Tuple[Optional[datetime], Optional[str], Optional[str]]:
    """Parse reminder text into a datetime and optional repeat interval.

    Args:
        text: Reminder text (e.g., "today", "tomorrow", "2 hours", "2 hours repeat")
        base_time: Base time for calculations (defaults to now)

    Returns:
        Tuple of (datetime, error_message, repeat_interval).
        - If parsing fails, datetime is None and error_message is set.
        - If "repeat" keyword is present, repeat_interval contains the interval string (e.g., "2 hours").
        - Otherwise, repeat_interval is None.
    """
    if not text:
        return None, "Reminder text is empty", None

    text = text.strip().lower()
    base = base_time or datetime.now()

    # Check for "repeat" keyword at the end
    repeat_interval = None
    if text.endswith(" repeat"):
        # Extract the repeat interval (everything before "repeat")
        text = text[:-7].strip()  # Remove " repeat"
        repeat_interval = text  # Store the interval for recurring reminders

    # Special cases
    if text == "today":
        # Today at 15:00 (3 PM)
        result = base.replace(hour=15, minute=0, second=0, microsecond=0)
        if result <= base:
            # If it's already past 15:00, use tomorrow at 15:00
            result = result + timedelta(days=1)
        return result, None, repeat_interval

    if text == "tomorrow":
        # Tomorrow at 9:00 AM
        result = base.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(
            days=1
        )
        return result, None, repeat_interval

    # Pattern: "next <unit>"
    next_match = re.match(r"^next\s+(\w+)$", text)
    if next_match:
        unit = next_match.group(1)
        normalized = normalize_unit(unit)

        if normalized == "hours":
            return base + timedelta(hours=1), None, repeat_interval
        elif normalized == "days":
            return base + timedelta(days=1), None, repeat_interval
        elif normalized == "weeks":
            return base + timedelta(weeks=1), None, repeat_interval
        elif normalized == "months":
            # Approximate as 30 days
            return base + timedelta(days=30), None, repeat_interval
        elif normalized == "quarters":
            # 3 months ≈ 90 days
            return base + timedelta(days=90), None, repeat_interval
        elif normalized == "years":
            return base + timedelta(days=365), None, repeat_interval
        elif normalized == "decades":
            return base + timedelta(days=3650), None, repeat_interval
        else:
            return None, f"Unknown unit in 'next {unit}'", None

    # Pattern: ISO format datetime (2027-01-31 12:00:00, 2027-01-31T12:00:00)
    iso_match = re.match(
        r"^(\d{4})-(\d{2})-(\d{2})[Tt\s](\d{2}):(\d{2}):(\d{2})$", text
    )
    if iso_match:
        try:
            year = int(iso_match.group(1))
            month = int(iso_match.group(2))
            day = int(iso_match.group(3))
            hour = int(iso_match.group(4))
            minute = int(iso_match.group(5))
            second = int(iso_match.group(6))
            result = datetime(year, month, day, hour, minute, second)
            if result <= base:
                return None, "Specified datetime is in the past", None
            return result, None, repeat_interval
        except ValueError as e:
            return None, f"Invalid ISO datetime: {e}", None

    # Pattern: ISO format date only (2027-01-31)
    iso_date_match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
    if iso_date_match:
        try:
            year = int(iso_date_match.group(1))
            month = int(iso_date_match.group(2))
            day = int(iso_date_match.group(3))
            result = datetime(year, month, day, get_default_start_hour(), 0, 0)
            if result <= base:
                return None, "Specified date is in the past", None
            return result, None, repeat_interval
        except ValueError as e:
            return None, f"Invalid ISO date: {e}", None

    # Pattern: "Day Month/Year Time" (e.g., "15 December/29 11AM", "25 Dec/2027 9PM")
    full_date_time_match = re.match(
        r"^(\d{1,2})\s+([a-z]+)/(\d{2,4})\s+(\d{1,2}(?:AM|PM|am|pm)?)$", text
    )
    if full_date_time_match:
        try:
            day = int(full_date_time_match.group(1))
            month_str = full_date_time_match.group(2).lower()
            year_str = full_date_time_match.group(3)
            time_str = full_date_time_match.group(4)

            month = MONTH_NAMES.get(month_str)
            if not month:
                return None, f"Unknown month: {month_str}", None

            # Parse year (2-digit or 4-digit)
            year = int(year_str)
            if year < 100:
                year += 2000

            hour = parse_time_part(time_str)
            if hour is None:
                return None, f"Invalid time: {time_str}", None

            result = datetime(year, month, day, hour, 0, 0)
            if result <= base:
                return None, "Specified datetime is in the past", None
            return result, None, repeat_interval
        except ValueError as e:
            return None, f"Invalid date: {e}", None

    # Pattern: "Day Month/Year" (e.g., "25 Dec/27", "25 Dec/2027")
    full_date_match = re.match(r"^(\d{1,2})\s+([a-z]+)/(\d{2,4})$", text)
    if full_date_match:
        try:
            day = int(full_date_match.group(1))
            month_str = full_date_match.group(2).lower()
            year_str = full_date_match.group(3)

            month = MONTH_NAMES.get(month_str)
            if not month:
                return None, f"Unknown month: {month_str}", None

            # Parse year (2-digit or 4-digit)
            year = int(year_str)
            if year < 100:
                year += 2000

            result = datetime(year, month, day, get_default_start_hour(), 0, 0)
            if result <= base:
                return None, "Specified date is in the past", None
            return result, None, repeat_interval
        except ValueError as e:
            return None, f"Invalid date: {e}", None

    # Pattern: "Day Month" (e.g., "25 Aug", "25 August")
    month_day_match = re.match(r"^(\d{1,2})\s+([a-z]+)$", text)
    if month_day_match:
        try:
            day = int(month_day_match.group(1))
            month_str = month_day_match.group(2).lower()

            month = MONTH_NAMES.get(month_str)
            if not month:
                # Not a month name, continue to other patterns
                pass
            else:
                # Find next occurrence of this month/day
                year = base.year
                try:
                    result = datetime(year, month, day, get_default_start_hour(), 0, 0)
                    if result <= base:
                        # Try next year
                        result = datetime(
                            year + 1, month, day, get_default_start_hour(), 0, 0
                        )
                    return result, None, repeat_interval
                except ValueError as e:
                    return None, f"Invalid date: {e}", None
        except ValueError:
            pass

    # Pattern: "Weekday Time" (e.g., "monday 9", "mon 14", "monday 9PM")
    weekday_time_match = re.match(r"^([a-z]+)\s+(\d{1,2}(?:AM|PM|am|pm)?)$", text)
    if weekday_time_match:
        weekday_str = weekday_time_match.group(1).lower()
        time_str = weekday_time_match.group(2)

        weekday = WEEKDAY_NAMES.get(weekday_str)
        if weekday is not None:
            hour = parse_time_part(time_str)
            if hour is None:
                return None, f"Invalid time: {time_str}", None

            result = next_weekday(base, weekday, hour)
            return result, None, repeat_interval

    # Pattern: "Weekday" alone (e.g., "monday", "mon")
    if text in WEEKDAY_NAMES:
        weekday = WEEKDAY_NAMES[text]
        result = next_weekday(base, weekday)
        return result, None, repeat_interval

    # Pattern: "<number> <unit>"
    number_match = re.match(r"^(\d+)\s+([a-zA-Z]+)$", text)
    if number_match:
        try:
            amount = int(number_match.group(1))
            unit = number_match.group(2)
            normalized = normalize_unit(unit)

            if not normalized:
                return None, f"Unknown time unit: {unit}", None

            if normalized == "seconds":
                return base + timedelta(seconds=amount), None, repeat_interval
            elif normalized == "minutes":
                return base + timedelta(minutes=amount), None, repeat_interval
            elif normalized == "hours":
                return base + timedelta(hours=amount), None, repeat_interval
            elif normalized == "days":
                return base + timedelta(days=amount), None, repeat_interval
            elif normalized == "weeks":
                return base + timedelta(weeks=amount), None, repeat_interval
            elif normalized == "months":
                # Approximate as 30 days per month
                return base + timedelta(days=amount * 30), None, repeat_interval
            elif normalized == "quarters":
                # 3 months per quarter
                return base + timedelta(days=amount * 90), None, repeat_interval
            elif normalized == "years":
                return base + timedelta(days=amount * 365), None, repeat_interval
            elif normalized == "decades":
                return base + timedelta(days=amount * 3650), None, repeat_interval
            else:
                return None, f"Unsupported unit: {normalized}", None
        except ValueError as e:
            return None, f"Invalid number: {e}", None

    # Pattern: Just a number (day of month)
    if text.isdigit():
        day = int(text)
        result = next_day_of_month(base, day)
        if result is None:
            return None, f"Invalid day of month: {day}", None
        return result, None, repeat_interval

    return None, f"Could not parse reminder: '{text}'", None


def format_reminder(dt: datetime) -> str:
    """Format a datetime as a human-friendly reminder string.

    Args:
        dt: Datetime to format

    Returns:
        Human-friendly string like "Tomorrow at 9:00 AM" or "Jan 15, 2024 at 3:00 PM"
    """
    now = datetime.now()

    # Check if it's today
    if dt.date() == now.date():
        return dt.strftime("Today at %I:%M %p")

    # Check if it's tomorrow
    if dt.date() == (now + timedelta(days=1)).date():
        return dt.strftime("Tomorrow at %I:%M %p")

    # Check if it's within a week
    days_diff = (dt.date() - now.date()).days
    if 0 < days_diff <= 7:
        return dt.strftime("%A at %I:%M %p")  # "Monday at 3:00 PM"

    # For dates further out
    if dt.year == now.year:
        return dt.strftime("%b %d at %I:%M %p")  # "Jan 15 at 3:00 PM"
    else:
        return dt.strftime("%b %d, %Y at %I:%M %p")  # "Jan 15, 2024 at 3:00 PM"


def get_time_until(dt: datetime) -> str:
    """Get human-friendly string for time until a datetime.

    Args:
        dt: Target datetime

    Returns:
        String like "in 2 hours" or "in 3 days"
    """
    now = datetime.now()
    diff = dt - now

    if diff.total_seconds() < 0:
        return "overdue"

    total_seconds = int(diff.total_seconds())

    if total_seconds < 60:
        return f"in {total_seconds} second{'s' if total_seconds != 1 else ''}"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        return f"in {minutes} minute{'s' if minutes != 1 else ''}"
    elif total_seconds < 86400:
        hours = total_seconds // 3600
        return f"in {hours} hour{'s' if hours != 1 else ''}"
    elif total_seconds < 604800:
        days = total_seconds // 86400
        return f"in {days} day{'s' if days != 1 else ''}"
    else:
        weeks = total_seconds // 604800
        return f"in {weeks} week{'s' if weeks != 1 else ''}"
