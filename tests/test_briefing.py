"""Tests for the Briefing assembly module."""

import json
from datetime import datetime
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import pytest

from src.briefing import BriefingBuilder, MockDataProvider, build_briefing
from src.config import Config, WeatherConfig, CalendarConfig
from src.models import Appointment, Briefing, DateInfo, WeatherInfo


class TestMockDataProvider:
    """Tests for MockDataProvider class."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return Config(
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            timezone="America/New_York",
            prep_reminder_minutes=60,
        )

    def test_init(self, config):
        """Test MockDataProvider initialization."""
        provider = MockDataProvider(config)
        assert provider.config == config

    def test_init_with_custom_time(self, config):
        """Test initialization with custom datetime."""
        tz = ZoneInfo("America/New_York")
        custom_time = datetime(2025, 1, 14, 10, 30, tzinfo=tz)
        provider = MockDataProvider(config, now=custom_time)
        assert provider._now == custom_time

    def test_get_date_info(self, config):
        """Test that date info uses actual DateTimeSource."""
        tz = ZoneInfo("America/New_York")
        now = datetime(2025, 1, 14, 7, 15, tzinfo=tz)
        provider = MockDataProvider(config, now=now)

        date_info = provider.get_date_info()

        assert isinstance(date_info, DateInfo)
        assert date_info.day_of_week == "Tuesday"
        assert date_info.full_date == "January 14th"
        assert "7:15" in date_info.time_of_day

    def test_get_weather_morning(self, config):
        """Test mock weather in the morning."""
        tz = ZoneInfo("America/New_York")
        now = datetime(2025, 1, 14, 7, 0, tzinfo=tz)
        provider = MockDataProvider(config, now=now)

        weather = provider.get_weather()

        assert isinstance(weather, WeatherInfo)
        assert weather.temperature_f == 52
        assert weather.description == "a bit chilly"
        assert weather.conditions == "partly cloudy"

    def test_get_weather_afternoon(self, config):
        """Test mock weather in the afternoon."""
        tz = ZoneInfo("America/New_York")
        now = datetime(2025, 1, 14, 15, 0, tzinfo=tz)
        provider = MockDataProvider(config, now=now)

        weather = provider.get_weather()

        assert weather.temperature_f == 68
        assert weather.description == "pleasant"

    def test_get_weather_night(self, config):
        """Test mock weather at night shows night icon."""
        tz = ZoneInfo("America/New_York")
        now = datetime(2025, 1, 14, 22, 0, tzinfo=tz)
        provider = MockDataProvider(config, now=now)

        weather = provider.get_weather()

        assert weather.icon_code == "03n"  # Night icon

    def test_get_appointments(self, config):
        """Test mock appointments are generated."""
        tz = ZoneInfo("America/New_York")
        now = datetime(2025, 1, 14, 7, 0, tzinfo=tz)
        provider = MockDataProvider(config, now=now)

        appointments = provider.get_appointments()

        assert len(appointments) == 2
        assert all(isinstance(apt, Appointment) for apt in appointments)

    def test_get_appointments_has_prep_reminders(self, config):
        """Test that appointments have prep reminders with caregiver name."""
        provider = MockDataProvider(config)
        appointments = provider.get_appointments()

        for apt in appointments:
            assert apt.prep_reminder is not None
            assert "Sarah" in apt.prep_reminder

    def test_get_appointments_times(self, config):
        """Test appointment times are formatted correctly."""
        provider = MockDataProvider(config)
        appointments = provider.get_appointments()

        # Morning appointment at 10:00 AM
        assert appointments[0].time == "10:00 AM"
        # Afternoon appointment at 2:30 PM
        assert appointments[1].time == "2:30 PM"

    def test_get_appointments_uses_config_caregiver(self):
        """Test that caregiver name from config is used."""
        config = Config(
            recipient_name="Test",
            caregiver_name="John",
            timezone="America/New_York",
        )
        provider = MockDataProvider(config)
        appointments = provider.get_appointments()

        for apt in appointments:
            assert "John" in apt.prep_reminder


class TestBriefingBuilder:
    """Tests for BriefingBuilder class."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        return Config(
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            timezone="America/New_York",
            prep_reminder_minutes=60,
        )

    def test_init(self, config):
        """Test BriefingBuilder initialization."""
        builder = BriefingBuilder(config)
        assert builder.config == config

    def test_build_mock_returns_briefing(self, config):
        """Test that mock build returns a Briefing."""
        builder = BriefingBuilder(config)
        tz = ZoneInfo("America/New_York")
        now = datetime(2025, 1, 14, 7, 15, tzinfo=tz)

        briefing = builder.build(use_mock=True, now=now)

        assert isinstance(briefing, Briefing)
        assert briefing.recipient_name == "Eleanor"
        assert briefing.caregiver_name == "Sarah"

    def test_build_mock_has_all_data(self, config):
        """Test that mock build includes all data."""
        builder = BriefingBuilder(config)
        briefing = builder.build(use_mock=True)

        assert briefing.date_info is not None
        assert briefing.weather is not None
        assert len(briefing.appointments) > 0
        assert briefing.errors == []

    def test_build_mock_no_errors(self, config):
        """Test that mock build has no errors."""
        builder = BriefingBuilder(config)
        briefing = builder.build(use_mock=True)

        assert briefing.errors == []

    def test_build_mock_json_serializable(self, config):
        """Test that mock briefing can be serialized to JSON."""
        builder = BriefingBuilder(config)
        briefing = builder.build(use_mock=True)

        json_str = briefing.to_json()
        parsed = json.loads(json_str)

        assert parsed["recipient_name"] == "Eleanor"
        assert "date" in parsed
        assert "weather" in parsed
        assert "appointments" in parsed

    @patch("src.briefing.WeatherSource")
    @patch("src.briefing.CalendarSource")
    def test_build_real_success(self, mock_cal, mock_weather, config):
        """Test real build with mocked sources."""
        # Configure weather to succeed
        config.weather = WeatherConfig(api_key="test", city="New York")
        mock_weather_instance = Mock()
        mock_weather_instance.fetch.return_value = WeatherInfo(
            temperature_f=55,
            conditions="clear",
            description="cool",
        )
        mock_weather.return_value = mock_weather_instance

        # Configure calendar to succeed
        mock_cal_instance = Mock()
        mock_cal_instance.fetch_today.return_value = [
            Appointment(time="3:00 PM", title="Test appointment")
        ]
        mock_cal.return_value = mock_cal_instance

        builder = BriefingBuilder(config)
        briefing = builder.build(use_mock=False)

        assert briefing.weather is not None
        assert briefing.weather.temperature_f == 55
        assert len(briefing.appointments) == 1

    @patch("src.briefing.WeatherSource")
    @patch("src.briefing.CalendarSource")
    def test_build_weather_fails(self, mock_cal, mock_weather, config):
        """Test that briefing still works when weather fails."""
        config.weather = WeatherConfig(api_key="test", city="New York")

        # Weather fails
        mock_weather_instance = Mock()
        mock_weather_instance.fetch.return_value = None
        mock_weather.return_value = mock_weather_instance

        # Calendar succeeds
        mock_cal_instance = Mock()
        mock_cal_instance.fetch_today.return_value = []
        mock_cal.return_value = mock_cal_instance

        builder = BriefingBuilder(config)
        briefing = builder.build(use_mock=False)

        assert briefing.weather is None
        assert "Weather data unavailable" in briefing.errors
        # But briefing still has date info
        assert briefing.date_info is not None

    @patch("src.briefing.WeatherSource")
    @patch("src.briefing.CalendarSource")
    def test_build_calendar_fails(self, mock_cal, mock_weather, config):
        """Test that briefing still works when calendar fails."""
        config.weather = WeatherConfig(api_key="test", city="New York")

        # Weather succeeds
        mock_weather_instance = Mock()
        mock_weather_instance.fetch.return_value = WeatherInfo(
            temperature_f=60, conditions="clear", description="cool"
        )
        mock_weather.return_value = mock_weather_instance

        # Calendar raises exception
        mock_cal.side_effect = Exception("Auth failed")

        builder = BriefingBuilder(config)
        briefing = builder.build(use_mock=False)

        assert briefing.appointments == []
        assert any("Calendar fetch failed" in e for e in briefing.errors)
        # But weather still works
        assert briefing.weather is not None

    @patch("src.briefing.WeatherSource")
    @patch("src.briefing.CalendarSource")
    def test_build_both_fail(self, mock_cal, mock_weather, config):
        """Test briefing with both sources failing."""
        config.weather = WeatherConfig(api_key="test", city="New York")

        # Both fail
        mock_weather_instance = Mock()
        mock_weather_instance.fetch.return_value = None
        mock_weather.return_value = mock_weather_instance
        mock_cal.side_effect = Exception("Auth failed")

        builder = BriefingBuilder(config)
        briefing = builder.build(use_mock=False)

        # Briefing still works with just date
        assert briefing.date_info is not None
        assert briefing.weather is None
        assert briefing.appointments == []
        assert len(briefing.errors) >= 2

    def test_build_weather_not_configured(self, config):
        """Test that unconfigured weather is skipped gracefully."""
        # Weather not configured (no API key)
        config.weather = WeatherConfig()

        builder = BriefingBuilder(config)

        with patch("src.briefing.CalendarSource") as mock_cal:
            mock_cal_instance = Mock()
            mock_cal_instance.fetch_today.return_value = []
            mock_cal.return_value = mock_cal_instance

            briefing = builder.build(use_mock=False)

        # Weather is None but no error (it's expected)
        assert briefing.weather is None
        assert not any("Weather" in e for e in briefing.errors)


class TestBuildBriefingFunction:
    """Tests for the build_briefing convenience function."""

    def test_build_briefing_mock(self):
        """Test convenience function with mock data."""
        briefing = build_briefing(use_mock=True)

        assert isinstance(briefing, Briefing)
        assert briefing.weather is not None
        assert len(briefing.appointments) > 0

    def test_build_briefing_with_config(self):
        """Test convenience function with explicit config."""
        config = Config(
            recipient_name="Martha",
            caregiver_name="Tom",
            timezone="America/Chicago",
        )
        briefing = build_briefing(config=config, use_mock=True)

        assert briefing.recipient_name == "Martha"
        assert briefing.caregiver_name == "Tom"

    def test_build_briefing_with_custom_time(self):
        """Test convenience function with custom time."""
        tz = ZoneInfo("America/New_York")
        now = datetime(2025, 6, 15, 14, 30, tzinfo=tz)

        briefing = build_briefing(use_mock=True, now=now)

        assert briefing.date_info.day_of_week == "Sunday"
        assert "June 15th" in briefing.date_info.full_date


class TestBriefingIntegration:
    """Integration tests for complete briefing flow."""

    def test_full_mock_briefing_structure(self):
        """Test complete structure of a mock briefing."""
        config = Config(
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            timezone="America/New_York",
            prep_reminder_minutes=60,
        )
        tz = ZoneInfo("America/New_York")
        now = datetime(2025, 1, 14, 7, 15, tzinfo=tz)

        builder = BriefingBuilder(config)
        briefing = builder.build(use_mock=True, now=now)

        # Check all fields are populated
        assert briefing.generated_at == now
        assert briefing.recipient_name == "Eleanor"
        assert briefing.caregiver_name == "Sarah"

        # Date info
        assert briefing.date_info.day_of_week == "Tuesday"
        assert briefing.date_info.full_date == "January 14th"
        assert "morning" in briefing.date_info.time_of_day

        # Weather
        assert briefing.weather is not None
        assert isinstance(briefing.weather.temperature_f, int)
        assert briefing.weather.conditions is not None

        # Appointments
        assert len(briefing.appointments) >= 1
        for apt in briefing.appointments:
            assert apt.time is not None
            assert apt.title is not None

    def test_mock_briefing_json_output(self):
        """Test that mock briefing produces valid JSON."""
        briefing = build_briefing(use_mock=True)
        json_str = briefing.to_json()
        data = json.loads(json_str)

        # Verify expected structure
        assert "generated_at" in data
        assert "recipient_name" in data
        assert "caregiver_name" in data
        assert "date" in data
        assert "weather" in data
        assert "appointments" in data

        # Verify date structure
        assert "day_of_week" in data["date"]
        assert "full_date" in data["date"]
        assert "time_of_day" in data["date"]

        # Verify weather structure
        assert "temperature_f" in data["weather"]
        assert "conditions" in data["weather"]
        assert "description" in data["weather"]

        # Verify appointments structure
        assert isinstance(data["appointments"], list)
        if data["appointments"]:
            apt = data["appointments"][0]
            assert "time" in apt
            assert "title" in apt

    def test_briefing_properties(self):
        """Test briefing helper properties."""
        briefing = build_briefing(use_mock=True)

        assert briefing.has_weather is True
        assert briefing.has_appointments is True
        assert briefing.appointment_count >= 1
