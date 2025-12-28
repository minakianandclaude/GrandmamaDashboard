"""Date and time data source for the Good Morning Dashboard."""

from datetime import datetime
from zoneinfo import ZoneInfo

from ..models import DateInfo


def get_ordinal_suffix(day: int) -> str:
    """
    Return the ordinal suffix for a day number.

    Args:
        day: Day of month (1-31)

    Returns:
        Ordinal suffix: 'st', 'nd', 'rd', or 'th'

    Examples:
        1 -> 'st' (1st)
        2 -> 'nd' (2nd)
        3 -> 'rd' (3rd)
        4 -> 'th' (4th)
        11 -> 'th' (11th)
        12 -> 'th' (12th)
        13 -> 'th' (13th)
        21 -> 'st' (21st)
        22 -> 'nd' (22nd)
        23 -> 'rd' (23rd)
    """
    # Special case: 11th, 12th, 13th (not 11st, 12nd, 13rd)
    if 11 <= day <= 13:
        return "th"

    # Check last digit
    last_digit = day % 10
    if last_digit == 1:
        return "st"
    elif last_digit == 2:
        return "nd"
    elif last_digit == 3:
        return "rd"
    else:
        return "th"


def format_day_with_ordinal(day: int) -> str:
    """
    Format a day number with its ordinal suffix.

    Args:
        day: Day of month (1-31)

    Returns:
        Day with suffix, e.g., '14th', '1st', '23rd'
    """
    return f"{day}{get_ordinal_suffix(day)}"


def get_time_of_day_period(hour: int) -> str:
    """
    Get the period of day description based on hour.

    Args:
        hour: Hour in 24-hour format (0-23)

    Returns:
        Period description: 'in the morning', 'in the afternoon',
        'in the evening', or 'at night'
    """
    if 0 <= hour < 12:
        return "in the morning"
    elif 12 <= hour < 17:
        return "in the afternoon"
    elif 17 <= hour < 21:
        return "in the evening"
    else:  # 21-23
        return "at night"


def format_time_12hour(hour: int, minute: int) -> tuple[int, int, str]:
    """
    Convert 24-hour time to 12-hour format.

    Args:
        hour: Hour in 24-hour format (0-23)
        minute: Minute (0-59)

    Returns:
        Tuple of (hour_12, minute, am_pm)
    """
    if hour == 0:
        return (12, minute, "AM")
    elif hour < 12:
        return (hour, minute, "AM")
    elif hour == 12:
        return (12, minute, "PM")
    else:
        return (hour - 12, minute, "PM")


def format_time_spoken(hour: int, minute: int) -> str:
    """
    Format time for spoken output.

    Args:
        hour: Hour in 24-hour format (0-23)
        minute: Minute (0-59)

    Returns:
        Spoken time string, e.g., '7:15 in the morning'
    """
    hour_12, minute, _ = format_time_12hour(hour, minute)
    period = get_time_of_day_period(hour)

    # Format minute with leading zero if needed
    minute_str = f"{minute:02d}" if minute > 0 else "00"

    return f"{hour_12}:{minute_str} {period}"


class DateTimeSource:
    """
    Provides current date and time information formatted for the dashboard.

    This class handles timezone-aware date/time operations and produces
    conversational, human-friendly date strings suitable for elderly users.
    """

    def __init__(self, timezone: str = "America/New_York"):
        """
        Initialize the DateTimeSource.

        Args:
            timezone: IANA timezone string (e.g., 'America/New_York')
        """
        self.timezone = timezone
        self._tz = ZoneInfo(timezone)

    def get_current(self, now: datetime | None = None) -> DateInfo:
        """
        Get current date/time info formatted for the briefing.

        Args:
            now: Optional datetime to use instead of current time.
                 Useful for testing. If None, uses current time.

        Returns:
            DateInfo with all fields populated for display and speech.
        """
        if now is None:
            now = datetime.now(self._tz)
        elif now.tzinfo is None:
            # If naive datetime provided, assume it's in our timezone
            now = now.replace(tzinfo=self._tz)
        else:
            # Convert timezone-aware datetime to our target timezone
            now = now.astimezone(self._tz)

        # Extract components
        day_of_week = now.strftime("%A")  # e.g., "Tuesday"
        month_name = now.strftime("%B")  # e.g., "January"
        day = now.day
        hour = now.hour
        minute = now.minute

        # Format full date with ordinal
        full_date = f"{month_name} {format_day_with_ordinal(day)}"

        # Format time
        time_of_day = format_time_spoken(hour, minute)
        hour_12, minute, am_pm = format_time_12hour(hour, minute)

        return DateInfo(
            day_of_week=day_of_week,
            full_date=full_date,
            time_of_day=time_of_day,
            hour_12=hour_12,
            minute=minute,
            am_pm=am_pm,
        )
