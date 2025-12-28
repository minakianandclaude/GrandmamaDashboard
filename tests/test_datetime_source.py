"""Tests for the DateTimeSource module."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.data_sources.datetime_source import (
    DateTimeSource,
    format_day_with_ordinal,
    format_time_12hour,
    format_time_spoken,
    get_ordinal_suffix,
    get_time_of_day_period,
)
from src.models import DateInfo


class TestGetOrdinalSuffix:
    """Tests for the get_ordinal_suffix function."""

    def test_first(self):
        """Test 1st."""
        assert get_ordinal_suffix(1) == "st"

    def test_second(self):
        """Test 2nd."""
        assert get_ordinal_suffix(2) == "nd"

    def test_third(self):
        """Test 3rd."""
        assert get_ordinal_suffix(3) == "rd"

    def test_fourth_through_tenth(self):
        """Test 4th through 10th all use 'th'."""
        for day in range(4, 11):
            assert get_ordinal_suffix(day) == "th", f"Failed for day {day}"

    def test_eleventh(self):
        """Test 11th (special case, not 11st)."""
        assert get_ordinal_suffix(11) == "th"

    def test_twelfth(self):
        """Test 12th (special case, not 12nd)."""
        assert get_ordinal_suffix(12) == "th"

    def test_thirteenth(self):
        """Test 13th (special case, not 13rd)."""
        assert get_ordinal_suffix(13) == "th"

    def test_fourteenth_through_twentieth(self):
        """Test 14th through 20th all use 'th'."""
        for day in range(14, 21):
            assert get_ordinal_suffix(day) == "th", f"Failed for day {day}"

    def test_twenty_first(self):
        """Test 21st."""
        assert get_ordinal_suffix(21) == "st"

    def test_twenty_second(self):
        """Test 22nd."""
        assert get_ordinal_suffix(22) == "nd"

    def test_twenty_third(self):
        """Test 23rd."""
        assert get_ordinal_suffix(23) == "rd"

    def test_twenty_fourth_through_thirtieth(self):
        """Test 24th through 30th."""
        for day in range(24, 31):
            assert get_ordinal_suffix(day) == "th", f"Failed for day {day}"

    def test_thirty_first(self):
        """Test 31st."""
        assert get_ordinal_suffix(31) == "st"


class TestFormatDayWithOrdinal:
    """Tests for format_day_with_ordinal function."""

    def test_basic_formatting(self):
        """Test that day and suffix are combined correctly."""
        assert format_day_with_ordinal(1) == "1st"
        assert format_day_with_ordinal(2) == "2nd"
        assert format_day_with_ordinal(3) == "3rd"
        assert format_day_with_ordinal(4) == "4th"
        assert format_day_with_ordinal(11) == "11th"
        assert format_day_with_ordinal(21) == "21st"
        assert format_day_with_ordinal(22) == "22nd"
        assert format_day_with_ordinal(23) == "23rd"
        assert format_day_with_ordinal(31) == "31st"


class TestGetTimeOfDayPeriod:
    """Tests for get_time_of_day_period function."""

    def test_midnight(self):
        """Test midnight is morning."""
        assert get_time_of_day_period(0) == "in the morning"

    def test_early_morning(self):
        """Test early morning hours."""
        for hour in range(1, 6):
            assert get_time_of_day_period(hour) == "in the morning"

    def test_late_morning(self):
        """Test late morning hours."""
        for hour in range(6, 12):
            assert get_time_of_day_period(hour) == "in the morning"

    def test_morning_boundary(self):
        """Test 11:xx is still morning."""
        assert get_time_of_day_period(11) == "in the morning"

    def test_noon(self):
        """Test noon is afternoon."""
        assert get_time_of_day_period(12) == "in the afternoon"

    def test_early_afternoon(self):
        """Test early afternoon hours."""
        for hour in range(12, 17):
            assert get_time_of_day_period(hour) == "in the afternoon"

    def test_afternoon_boundary(self):
        """Test 4:xx PM is still afternoon."""
        assert get_time_of_day_period(16) == "in the afternoon"

    def test_evening_start(self):
        """Test 5:xx PM is evening."""
        assert get_time_of_day_period(17) == "in the evening"

    def test_evening_hours(self):
        """Test evening hours."""
        for hour in range(17, 21):
            assert get_time_of_day_period(hour) == "in the evening"

    def test_evening_boundary(self):
        """Test 8:xx PM is still evening."""
        assert get_time_of_day_period(20) == "in the evening"

    def test_night_start(self):
        """Test 9:xx PM is night."""
        assert get_time_of_day_period(21) == "at night"

    def test_late_night(self):
        """Test late night hours."""
        for hour in range(21, 24):
            assert get_time_of_day_period(hour) == "at night"


class TestFormatTime12Hour:
    """Tests for format_time_12hour function."""

    def test_midnight(self):
        """Test midnight converts to 12:00 AM."""
        hour_12, minute, am_pm = format_time_12hour(0, 0)
        assert hour_12 == 12
        assert minute == 0
        assert am_pm == "AM"

    def test_midnight_with_minutes(self):
        """Test 12:30 AM."""
        hour_12, minute, am_pm = format_time_12hour(0, 30)
        assert hour_12 == 12
        assert minute == 30
        assert am_pm == "AM"

    def test_morning_hours(self):
        """Test morning hours (1-11 AM)."""
        for hour in range(1, 12):
            hour_12, _, am_pm = format_time_12hour(hour, 0)
            assert hour_12 == hour
            assert am_pm == "AM"

    def test_noon(self):
        """Test noon converts to 12:00 PM."""
        hour_12, minute, am_pm = format_time_12hour(12, 0)
        assert hour_12 == 12
        assert minute == 0
        assert am_pm == "PM"

    def test_afternoon_hours(self):
        """Test afternoon hours (1-11 PM)."""
        for hour in range(13, 24):
            hour_12, _, am_pm = format_time_12hour(hour, 0)
            assert hour_12 == hour - 12
            assert am_pm == "PM"

    def test_preserves_minutes(self):
        """Test that minutes are preserved."""
        _, minute, _ = format_time_12hour(14, 45)
        assert minute == 45


class TestFormatTimeSpoken:
    """Tests for format_time_spoken function."""

    def test_morning_time(self):
        """Test morning time formatting."""
        result = format_time_spoken(7, 15)
        assert result == "7:15 in the morning"

    def test_afternoon_time(self):
        """Test afternoon time formatting."""
        result = format_time_spoken(14, 30)
        assert result == "2:30 in the afternoon"

    def test_evening_time(self):
        """Test evening time formatting."""
        result = format_time_spoken(19, 0)
        assert result == "7:00 in the evening"

    def test_night_time(self):
        """Test night time formatting."""
        result = format_time_spoken(22, 45)
        assert result == "10:45 at night"

    def test_midnight(self):
        """Test midnight formatting."""
        result = format_time_spoken(0, 0)
        assert result == "12:00 in the morning"

    def test_noon(self):
        """Test noon formatting."""
        result = format_time_spoken(12, 0)
        assert result == "12:00 in the afternoon"

    def test_single_digit_minutes(self):
        """Test that single-digit minutes get leading zero."""
        result = format_time_spoken(9, 5)
        assert result == "9:05 in the morning"


class TestDateTimeSource:
    """Tests for the DateTimeSource class."""

    def test_initialization_default_timezone(self):
        """Test default timezone is America/New_York."""
        source = DateTimeSource()
        assert source.timezone == "America/New_York"

    def test_initialization_custom_timezone(self):
        """Test custom timezone."""
        source = DateTimeSource("America/Los_Angeles")
        assert source.timezone == "America/Los_Angeles"

    def test_get_current_returns_dateinfo(self):
        """Test that get_current returns a DateInfo object."""
        source = DateTimeSource()
        now = datetime(2025, 1, 14, 7, 15)
        result = source.get_current(now)
        assert isinstance(result, DateInfo)

    def test_get_current_day_of_week(self):
        """Test day of week extraction."""
        source = DateTimeSource()
        # January 14, 2025 is a Tuesday
        now = datetime(2025, 1, 14, 7, 15)
        result = source.get_current(now)
        assert result.day_of_week == "Tuesday"

    def test_get_current_full_date(self):
        """Test full date formatting."""
        source = DateTimeSource()
        now = datetime(2025, 1, 14, 7, 15)
        result = source.get_current(now)
        assert result.full_date == "January 14th"

    def test_get_current_time_of_day(self):
        """Test time of day formatting."""
        source = DateTimeSource()
        now = datetime(2025, 1, 14, 7, 15)
        result = source.get_current(now)
        assert result.time_of_day == "7:15 in the morning"

    def test_get_current_12hour_components(self):
        """Test 12-hour time components."""
        source = DateTimeSource()
        now = datetime(2025, 1, 14, 14, 30)
        result = source.get_current(now)
        assert result.hour_12 == 2
        assert result.minute == 30
        assert result.am_pm == "PM"

    def test_get_current_with_timezone_aware_datetime(self):
        """Test with timezone-aware datetime."""
        source = DateTimeSource("America/New_York")
        tz = ZoneInfo("America/New_York")
        now = datetime(2025, 3, 15, 10, 30, tzinfo=tz)
        result = source.get_current(now)
        assert result.day_of_week == "Saturday"
        assert result.full_date == "March 15th"

    def test_get_current_various_days(self):
        """Test various days of the month for ordinal formatting."""
        source = DateTimeSource()

        test_cases = [
            (datetime(2025, 1, 1, 12, 0), "January 1st"),
            (datetime(2025, 1, 2, 12, 0), "January 2nd"),
            (datetime(2025, 1, 3, 12, 0), "January 3rd"),
            (datetime(2025, 1, 11, 12, 0), "January 11th"),
            (datetime(2025, 1, 21, 12, 0), "January 21st"),
            (datetime(2025, 1, 22, 12, 0), "January 22nd"),
            (datetime(2025, 1, 23, 12, 0), "January 23rd"),
            (datetime(2025, 1, 31, 12, 0), "January 31st"),
        ]

        for now, expected_date in test_cases:
            result = source.get_current(now)
            assert result.full_date == expected_date, f"Failed for {now}"

    def test_get_current_various_times(self):
        """Test various times of day."""
        source = DateTimeSource()

        test_cases = [
            (datetime(2025, 1, 14, 6, 0), "6:00 in the morning"),
            (datetime(2025, 1, 14, 12, 0), "12:00 in the afternoon"),
            (datetime(2025, 1, 14, 15, 30), "3:30 in the afternoon"),
            (datetime(2025, 1, 14, 18, 45), "6:45 in the evening"),
            (datetime(2025, 1, 14, 22, 15), "10:15 at night"),
        ]

        for now, expected_time in test_cases:
            result = source.get_current(now)
            assert result.time_of_day == expected_time, f"Failed for {now}"

    def test_get_current_without_argument_uses_current_time(self):
        """Test that calling without argument uses current time."""
        source = DateTimeSource()
        result = source.get_current()

        # Just verify it returns a valid DateInfo
        assert result.day_of_week in [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"
        ]
        assert result.am_pm in ["AM", "PM"]

    def test_different_timezones_same_utc_time(self):
        """Test that different timezones produce different local times."""
        # Create sources for different timezones
        ny_source = DateTimeSource("America/New_York")
        la_source = DateTimeSource("America/Los_Angeles")

        # Same UTC time
        utc_time = datetime(2025, 1, 14, 17, 0, tzinfo=ZoneInfo("UTC"))

        ny_result = ny_source.get_current(utc_time)
        la_result = la_source.get_current(utc_time)

        # NY is UTC-5 in January, so 17:00 UTC = 12:00 PM ET
        # LA is UTC-8 in January, so 17:00 UTC = 9:00 AM PT
        assert ny_result.hour_12 == 12
        assert ny_result.am_pm == "PM"
        assert la_result.hour_12 == 9
        assert la_result.am_pm == "AM"
