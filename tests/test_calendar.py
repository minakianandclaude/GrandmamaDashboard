"""Tests for the CalendarSource module."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch
from zoneinfo import ZoneInfo

import pytest

from src.config import CalendarConfig
from src.data_sources.calendar import (
    CalendarSource,
    calculate_prep_reminder,
    format_prep_time,
    format_time_12hour,
    parse_event,
    parse_event_datetime,
)
from src.models import Appointment


class TestFormatTime12Hour:
    """Tests for format_time_12hour function."""

    def test_midnight(self):
        """Test midnight formatting."""
        dt = datetime(2025, 1, 14, 0, 0)
        assert format_time_12hour(dt) == "12:00 AM"

    def test_midnight_with_minutes(self):
        """Test 12:30 AM."""
        dt = datetime(2025, 1, 14, 0, 30)
        assert format_time_12hour(dt) == "12:30 AM"

    def test_morning_single_digit_hour(self):
        """Test single digit morning hours."""
        dt = datetime(2025, 1, 14, 9, 15)
        assert format_time_12hour(dt) == "9:15 AM"

    def test_morning_double_digit_hour(self):
        """Test double digit morning hours."""
        dt = datetime(2025, 1, 14, 11, 45)
        assert format_time_12hour(dt) == "11:45 AM"

    def test_noon(self):
        """Test noon formatting."""
        dt = datetime(2025, 1, 14, 12, 0)
        assert format_time_12hour(dt) == "12:00 PM"

    def test_noon_with_minutes(self):
        """Test 12:30 PM."""
        dt = datetime(2025, 1, 14, 12, 30)
        assert format_time_12hour(dt) == "12:30 PM"

    def test_afternoon(self):
        """Test afternoon hours."""
        dt = datetime(2025, 1, 14, 14, 30)
        assert format_time_12hour(dt) == "2:30 PM"

    def test_evening(self):
        """Test evening hours."""
        dt = datetime(2025, 1, 14, 19, 0)
        assert format_time_12hour(dt) == "7:00 PM"

    def test_late_night(self):
        """Test late night hours."""
        dt = datetime(2025, 1, 14, 23, 59)
        assert format_time_12hour(dt) == "11:59 PM"

    def test_leading_zero_minutes(self):
        """Test that minutes have leading zero."""
        dt = datetime(2025, 1, 14, 9, 5)
        assert format_time_12hour(dt) == "9:05 AM"


class TestFormatPrepTime:
    """Tests for format_prep_time function."""

    def test_on_the_hour(self):
        """Test times on the hour omit minutes."""
        dt = datetime(2025, 1, 14, 13, 0)
        assert format_prep_time(dt) == "1"

    def test_with_minutes(self):
        """Test times with minutes."""
        dt = datetime(2025, 1, 14, 13, 30)
        assert format_prep_time(dt) == "1:30"

    def test_midnight(self):
        """Test midnight."""
        dt = datetime(2025, 1, 14, 0, 0)
        assert format_prep_time(dt) == "12"

    def test_noon(self):
        """Test noon."""
        dt = datetime(2025, 1, 14, 12, 0)
        assert format_prep_time(dt) == "12"

    def test_morning(self):
        """Test morning time."""
        dt = datetime(2025, 1, 14, 9, 30)
        assert format_prep_time(dt) == "9:30"

    def test_single_digit_minutes(self):
        """Test single digit minutes have leading zero."""
        dt = datetime(2025, 1, 14, 14, 5)
        assert format_prep_time(dt) == "2:05"


class TestCalculatePrepReminder:
    """Tests for calculate_prep_reminder function."""

    def test_standard_reminder(self):
        """Test standard 60-minute prep reminder."""
        event_time = datetime(2025, 1, 14, 14, 30)
        result = calculate_prep_reminder(event_time, 60, "Sarah")
        assert result == "Sarah will help you get ready around 1:30"

    def test_30_minute_reminder(self):
        """Test 30-minute prep reminder."""
        event_time = datetime(2025, 1, 14, 10, 0)
        result = calculate_prep_reminder(event_time, 30, "John")
        assert result == "John will help you get ready around 9:30"

    def test_zero_minutes(self):
        """Test that zero prep minutes returns None."""
        event_time = datetime(2025, 1, 14, 14, 30)
        result = calculate_prep_reminder(event_time, 0, "Sarah")
        assert result is None

    def test_negative_minutes(self):
        """Test that negative prep minutes returns None."""
        event_time = datetime(2025, 1, 14, 14, 30)
        result = calculate_prep_reminder(event_time, -30, "Sarah")
        assert result is None

    def test_prep_on_the_hour(self):
        """Test prep time that lands on the hour."""
        event_time = datetime(2025, 1, 14, 15, 0)
        result = calculate_prep_reminder(event_time, 60, "Sarah")
        assert result == "Sarah will help you get ready around 2"

    def test_morning_appointment(self):
        """Test morning appointment prep reminder."""
        event_time = datetime(2025, 1, 14, 9, 30)
        result = calculate_prep_reminder(event_time, 60, "Mike")
        assert result == "Mike will help you get ready around 8:30"


class TestParseEventDatetime:
    """Tests for parse_event_datetime function."""

    def test_timed_event_with_offset(self):
        """Test parsing timed event with timezone offset."""
        event = {
            "start": {"dateTime": "2025-01-14T14:30:00-05:00"}
        }
        dt, is_all_day = parse_event_datetime(event, "America/New_York")

        assert is_all_day is False
        assert dt is not None
        assert dt.hour == 14
        assert dt.minute == 30

    def test_timed_event_utc(self):
        """Test parsing timed event in UTC."""
        event = {
            "start": {"dateTime": "2025-01-14T19:30:00Z"}
        }
        dt, is_all_day = parse_event_datetime(event, "America/New_York")

        assert is_all_day is False
        assert dt is not None
        # 19:30 UTC = 14:30 EST
        assert dt.hour == 14
        assert dt.minute == 30

    def test_all_day_event(self):
        """Test parsing all-day event."""
        event = {
            "start": {"date": "2025-01-14"}
        }
        dt, is_all_day = parse_event_datetime(event, "America/New_York")

        assert is_all_day is True
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 1
        assert dt.day == 14

    def test_missing_start(self):
        """Test handling event with no start."""
        event = {}
        dt, is_all_day = parse_event_datetime(event, "America/New_York")
        assert dt is None
        assert is_all_day is False

    def test_invalid_datetime_format(self):
        """Test handling invalid datetime format."""
        event = {
            "start": {"dateTime": "not-a-date"}
        }
        dt, is_all_day = parse_event_datetime(event, "America/New_York")
        assert dt is None

    def test_invalid_date_format(self):
        """Test handling invalid date format."""
        event = {
            "start": {"date": "not-a-date"}
        }
        dt, is_all_day = parse_event_datetime(event, "America/New_York")
        assert dt is None
        assert is_all_day is True  # Still marked as all-day attempt


class TestParseEvent:
    """Tests for parse_event function."""

    def test_timed_event_full(self):
        """Test parsing a complete timed event."""
        event = {
            "summary": "Doctor's appointment",
            "description": "Dr. Martinez, cardiology",
            "start": {"dateTime": "2025-01-14T14:30:00-05:00"},
        }
        apt = parse_event(event, "America/New_York", "Sarah", 60)

        assert apt is not None
        assert apt.title == "Doctor's appointment"
        assert apt.details == "Dr. Martinez, cardiology"
        assert apt.time == "2:30 PM"
        assert apt.prep_reminder == "Sarah will help you get ready around 1:30"

    def test_timed_event_no_description(self):
        """Test parsing event without description."""
        event = {
            "summary": "Lunch",
            "start": {"dateTime": "2025-01-14T12:00:00-05:00"},
        }
        apt = parse_event(event, "America/New_York", "Sarah", 60)

        assert apt is not None
        assert apt.title == "Lunch"
        assert apt.details is None
        assert apt.time == "12:00 PM"

    def test_all_day_event(self):
        """Test parsing all-day event."""
        event = {
            "summary": "Birthday",
            "start": {"date": "2025-01-14"},
        }
        apt = parse_event(event, "America/New_York", "Sarah", 60)

        assert apt is not None
        assert apt.title == "Birthday"
        assert apt.time == "All day"
        assert apt.prep_reminder is None  # No prep for all-day events

    def test_untitled_event(self):
        """Test parsing event without summary."""
        event = {
            "start": {"dateTime": "2025-01-14T10:00:00-05:00"},
        }
        apt = parse_event(event, "America/New_York", "Sarah", 60)

        assert apt is not None
        assert apt.title == "Untitled event"

    def test_event_no_parseable_time(self):
        """Test that event with no time returns None."""
        event = {
            "summary": "Mystery event",
            "start": {},
        }
        apt = parse_event(event, "America/New_York", "Sarah", 60)
        assert apt is None

    def test_zero_prep_minutes(self):
        """Test that zero prep minutes means no reminder."""
        event = {
            "summary": "Quick meeting",
            "start": {"dateTime": "2025-01-14T14:30:00-05:00"},
        }
        apt = parse_event(event, "America/New_York", "Sarah", 0)

        assert apt is not None
        assert apt.prep_reminder is None


class TestCalendarSource:
    """Tests for the CalendarSource class."""

    @pytest.fixture
    def config(self):
        """Create test calendar config."""
        return CalendarConfig(
            credentials_file="credentials.json",
            token_file="token.json",
            calendar_id="primary",
        )

    def test_init(self, config):
        """Test CalendarSource initialization."""
        source = CalendarSource(
            config=config,
            timezone="America/New_York",
            caregiver_name="Sarah",
            prep_minutes=60,
        )
        assert source.timezone == "America/New_York"
        assert source.caregiver_name == "Sarah"
        assert source.prep_minutes == 60

    def test_get_today_range(self, config):
        """Test today's time range calculation."""
        source = CalendarSource(
            config=config,
            timezone="America/New_York",
            caregiver_name="Sarah",
            prep_minutes=60,
        )
        tz = ZoneInfo("America/New_York")
        now = datetime(2025, 1, 14, 10, 30, tzinfo=tz)

        start, end = source._get_today_range(now)

        assert "2025-01-14T00:00:00" in start
        assert "2025-01-15T00:00:00" in end

    @patch("src.data_sources.calendar.get_credentials")
    def test_fetch_today_no_credentials(self, mock_get_creds, config):
        """Test fetch_today returns empty list when no credentials."""
        mock_get_creds.return_value = None

        source = CalendarSource(
            config=config,
            timezone="America/New_York",
            caregiver_name="Sarah",
            prep_minutes=60,
        )
        result = source.fetch_today()

        assert result == []


class TestParseMultipleEvents:
    """Tests for parsing multiple events (integration-style tests)."""

    def test_parse_multiple_timed_events(self):
        """Test parsing multiple timed events and sorting."""
        events = [
            {
                "summary": "Dinner with family",
                "start": {"dateTime": "2025-01-14T18:00:00-05:00"},
            },
            {
                "summary": "Doctor's appointment",
                "description": "Dr. Martinez",
                "start": {"dateTime": "2025-01-14T14:30:00-05:00"},
            },
        ]

        appointments = []
        for event in events:
            apt = parse_event(event, "America/New_York", "Sarah", 60)
            if apt:
                appointments.append(apt)

        assert len(appointments) == 2
        # Both should have prep reminders
        assert all(apt.prep_reminder is not None for apt in appointments)

    def test_parse_mixed_all_day_and_timed(self):
        """Test parsing mix of all-day and timed events."""
        events = [
            {
                "summary": "All day celebration",
                "start": {"date": "2025-01-14"},
            },
            {
                "summary": "Morning meeting",
                "start": {"dateTime": "2025-01-14T09:00:00-05:00"},
            },
        ]

        appointments = []
        for event in events:
            apt = parse_event(event, "America/New_York", "Sarah", 60)
            if apt:
                appointments.append(apt)

        assert len(appointments) == 2
        # Find all-day event
        all_day = next((a for a in appointments if a.time == "All day"), None)
        timed = next((a for a in appointments if a.time != "All day"), None)

        assert all_day is not None
        assert all_day.prep_reminder is None  # No prep for all-day

        assert timed is not None
        assert timed.time == "9:00 AM"
        assert timed.prep_reminder is not None

    def test_parse_events_with_different_caregiver(self):
        """Test that caregiver name is used in prep reminders."""
        event = {
            "summary": "Physical therapy",
            "start": {"dateTime": "2025-01-14T11:00:00-05:00"},
        }

        apt = parse_event(event, "America/New_York", "John", 45)

        assert apt is not None
        assert "John" in apt.prep_reminder
