#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Parser for reminder time expressions.

Supports flexible syntax like:
- today, tomorrow
- next hour|day|week|month|quarter|year|decade
- {number} seconds|minutes|hours|days|weeks|months|quarters|years
- Abbreviations: sec, min, hr, h, d, w, mo, q, y
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
import re


# Abbreviation mappings
UNIT_ABBREV = {
    # Seconds
    'sec': 'seconds',
    'secs': 'seconds',
    's': 'seconds',
    'second': 'seconds',

    # Minutes
    'min': 'minutes',
    'mins': 'minutes',
    'm': 'minutes',
    'minute': 'minutes',

    # Hours
    'hr': 'hours',
    'hrs': 'hours',
    'h': 'hours',
    'ho': 'hours',
    'hour': 'hours',

    # Days
    'd': 'days',
    'day': 'days',

    # Weeks
    'w': 'weeks',
    'wk': 'weeks',
    'wks': 'weeks',
    'week': 'weeks',

    # Months
    'mo': 'months',
    'mon': 'months',
    'mos': 'months',
    'month': 'months',

    # Quarters (3 months)
    'q': 'quarters',
    'qtr': 'quarters',
    'quarter': 'quarters',

    # Years
    'y': 'years',
    'yr': 'years',
    'yrs': 'years',
    'year': 'years',

    # Decades
    'decade': 'decades',
    'decades': 'decades',
}


def normalize_unit(unit: str) -> Optional[str]:
    """Normalize a time unit to its canonical form.

    Args:
        unit: Time unit string (can be abbreviated or full)

    Returns:
        Normalized unit name or None if invalid
    """
    unit_lower = unit.lower().strip()

    # Check if already normalized
    if unit_lower in ['seconds', 'minutes', 'hours', 'days', 'weeks', 'months', 'quarters', 'years', 'decades']:
        return unit_lower

    # Check abbreviations
    return UNIT_ABBREV.get(unit_lower)


def parse_reminder(text: str, base_time: Optional[datetime] = None) -> Tuple[Optional[datetime], Optional[str], Optional[str]]:
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
    if text.endswith(' repeat'):
        # Extract the repeat interval (everything before "repeat")
        text = text[:-7].strip()  # Remove " repeat"
        repeat_interval = text  # Store the interval for recurring reminders

    # Special cases
    if text == 'today':
        # Today at 15:00 (3 PM)
        result = base.replace(hour=15, minute=0, second=0, microsecond=0)
        if result <= base:
            # If it's already past 15:00, use tomorrow at 15:00
            result = result + timedelta(days=1)
        return result, None, repeat_interval

    if text == 'tomorrow':
        # Tomorrow at 9:00 AM
        result = base.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return result, None, repeat_interval

    # Pattern: "next <unit>"
    next_match = re.match(r'^next\s+(\w+)$', text)
    if next_match:
        unit = next_match.group(1)
        normalized = normalize_unit(unit)

        if normalized == 'hours':
            return base + timedelta(hours=1), None, repeat_interval
        elif normalized == 'days':
            return base + timedelta(days=1), None, repeat_interval
        elif normalized == 'weeks':
            return base + timedelta(weeks=1), None, repeat_interval
        elif normalized == 'months':
            # Approximate as 30 days
            return base + timedelta(days=30), None, repeat_interval
        elif normalized == 'quarters':
            # 3 months ≈ 90 days
            return base + timedelta(days=90), None, repeat_interval
        elif normalized == 'years':
            return base + timedelta(days=365), None, repeat_interval
        elif normalized == 'decades':
            return base + timedelta(days=3650), None, repeat_interval
        else:
            return None, f"Unknown unit in 'next {unit}'", None

    # Pattern: "<number> <unit>"
    number_match = re.match(r'^(\d+)\s+([a-zA-Z]+)$', text)
    if number_match:
        try:
            amount = int(number_match.group(1))
            unit = number_match.group(2)
            normalized = normalize_unit(unit)

            if not normalized:
                return None, f"Unknown time unit: {unit}", None

            if normalized == 'seconds':
                return base + timedelta(seconds=amount), None, repeat_interval
            elif normalized == 'minutes':
                return base + timedelta(minutes=amount), None, repeat_interval
            elif normalized == 'hours':
                return base + timedelta(hours=amount), None, repeat_interval
            elif normalized == 'days':
                return base + timedelta(days=amount), None, repeat_interval
            elif normalized == 'weeks':
                return base + timedelta(weeks=amount), None, repeat_interval
            elif normalized == 'months':
                # Approximate as 30 days per month
                return base + timedelta(days=amount * 30), None, repeat_interval
            elif normalized == 'quarters':
                # 3 months per quarter
                return base + timedelta(days=amount * 90), None, repeat_interval
            elif normalized == 'years':
                return base + timedelta(days=amount * 365), None, repeat_interval
            elif normalized == 'decades':
                return base + timedelta(days=amount * 3650), None, repeat_interval
            else:
                return None, f"Unsupported unit: {normalized}", None
        except ValueError as e:
            return None, f"Invalid number: {e}", None

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
