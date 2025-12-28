"""Tests for core data models."""

import json
from datetime import datetime

import pytest

from src.models import Appointment, Briefing, DateInfo, WeatherInfo


class TestDateInfo:
    """Tests for DateInfo dataclass."""

    def test_creation(self):
        """Test basic DateInfo creation."""
        date_info = DateInfo(
            day_of_week="Tuesday",
            full_date="January 14th",
            time_of_day="7:15 in the morning",
            hour_12=7,
            minute=15,
            am_pm="AM",
        )
        assert date_info.day_of_week == "Tuesday"
        assert date_info.full_date == "January 14th"
        assert date_info.time_of_day == "7:15 in the morning"
        assert date_info.hour_12 == 7
        assert date_info.minute == 15
        assert date_info.am_pm == "AM"

    def test_to_dict(self):
        """Test DateInfo serialization to dict."""
        date_info = DateInfo(
            day_of_week="Tuesday",
            full_date="January 14th",
            time_of_day="7:15 in the morning",
            hour_12=7,
            minute=15,
            am_pm="AM",
        )
        result = date_info.to_dict()
        assert result == {
            "day_of_week": "Tuesday",
            "full_date": "January 14th",
            "time_of_day": "7:15 in the morning",
            "hour_12": 7,
            "minute": 15,
            "am_pm": "AM",
        }


class TestWeatherInfo:
    """Tests for WeatherInfo dataclass."""

    def test_creation_minimal(self):
        """Test WeatherInfo with required fields only."""
        weather = WeatherInfo(
            temperature_f=45,
            conditions="cloudy",
            description="a bit chilly",
        )
        assert weather.temperature_f == 45
        assert weather.conditions == "cloudy"
        assert weather.description == "a bit chilly"
        assert weather.icon_code is None

    def test_creation_with_icon(self):
        """Test WeatherInfo with optional icon code."""
        weather = WeatherInfo(
            temperature_f=72,
            conditions="sunny",
            description="nice and warm",
            icon_code="01d",
        )
        assert weather.icon_code == "01d"

    def test_to_dict(self):
        """Test WeatherInfo serialization to dict."""
        weather = WeatherInfo(
            temperature_f=45,
            conditions="cloudy",
            description="a bit chilly",
            icon_code="04d",
        )
        result = weather.to_dict()
        assert result == {
            "temperature_f": 45,
            "conditions": "cloudy",
            "description": "a bit chilly",
            "icon_code": "04d",
        }


class TestAppointment:
    """Tests for Appointment dataclass."""

    def test_creation_minimal(self):
        """Test Appointment with required fields only."""
        apt = Appointment(
            time="2:30 PM",
            title="Doctor's appointment",
        )
        assert apt.time == "2:30 PM"
        assert apt.title == "Doctor's appointment"
        assert apt.details is None
        assert apt.prep_reminder is None
        assert apt.start_datetime is None

    def test_creation_full(self):
        """Test Appointment with all fields."""
        start = datetime(2025, 1, 14, 14, 30)
        apt = Appointment(
            time="2:30 PM",
            title="Doctor's appointment",
            details="Dr. Martinez, cardiology follow-up",
            prep_reminder="Sarah will help you get ready around 1:30",
            start_datetime=start,
        )
        assert apt.details == "Dr. Martinez, cardiology follow-up"
        assert apt.prep_reminder == "Sarah will help you get ready around 1:30"
        assert apt.start_datetime == start

    def test_to_dict_excludes_datetime(self):
        """Test that start_datetime is excluded from JSON output."""
        start = datetime(2025, 1, 14, 14, 30)
        apt = Appointment(
            time="2:30 PM",
            title="Doctor's appointment",
            start_datetime=start,
        )
        result = apt.to_dict()
        assert "start_datetime" not in result
        assert result == {
            "time": "2:30 PM",
            "title": "Doctor's appointment",
            "details": None,
            "prep_reminder": None,
        }


class TestBriefing:
    """Tests for Briefing dataclass."""

    @pytest.fixture
    def sample_date_info(self):
        """Create sample DateInfo for testing."""
        return DateInfo(
            day_of_week="Tuesday",
            full_date="January 14th",
            time_of_day="7:15 in the morning",
            hour_12=7,
            minute=15,
            am_pm="AM",
        )

    @pytest.fixture
    def sample_weather(self):
        """Create sample WeatherInfo for testing."""
        return WeatherInfo(
            temperature_f=45,
            conditions="cloudy",
            description="a bit chilly",
            icon_code="04d",
        )

    @pytest.fixture
    def sample_appointment(self):
        """Create sample Appointment for testing."""
        return Appointment(
            time="2:30 PM",
            title="Doctor's appointment",
            details="Dr. Martinez, cardiology follow-up",
            prep_reminder="Sarah will help you get ready around 1:30",
        )

    def test_creation_minimal(self, sample_date_info):
        """Test Briefing with required fields only."""
        now = datetime(2025, 1, 14, 7, 15)
        briefing = Briefing(
            generated_at=now,
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=sample_date_info,
        )
        assert briefing.recipient_name == "Eleanor"
        assert briefing.caregiver_name == "Sarah"
        assert briefing.weather is None
        assert briefing.appointments == []
        assert briefing.errors == []

    def test_has_weather_false(self, sample_date_info):
        """Test has_weather property when no weather."""
        briefing = Briefing(
            generated_at=datetime.now(),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=sample_date_info,
        )
        assert briefing.has_weather is False

    def test_has_weather_true(self, sample_date_info, sample_weather):
        """Test has_weather property when weather present."""
        briefing = Briefing(
            generated_at=datetime.now(),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=sample_date_info,
            weather=sample_weather,
        )
        assert briefing.has_weather is True

    def test_has_appointments_false(self, sample_date_info):
        """Test has_appointments property when empty."""
        briefing = Briefing(
            generated_at=datetime.now(),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=sample_date_info,
        )
        assert briefing.has_appointments is False
        assert briefing.appointment_count == 0

    def test_has_appointments_true(self, sample_date_info, sample_appointment):
        """Test has_appointments property with appointments."""
        briefing = Briefing(
            generated_at=datetime.now(),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=sample_date_info,
            appointments=[sample_appointment],
        )
        assert briefing.has_appointments is True
        assert briefing.appointment_count == 1

    def test_to_dict(self, sample_date_info, sample_weather, sample_appointment):
        """Test full Briefing serialization."""
        now = datetime(2025, 1, 14, 7, 15)
        briefing = Briefing(
            generated_at=now,
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=sample_date_info,
            weather=sample_weather,
            appointments=[sample_appointment],
        )
        result = briefing.to_dict()

        assert result["generated_at"] == "2025-01-14T07:15:00"
        assert result["recipient_name"] == "Eleanor"
        assert result["caregiver_name"] == "Sarah"
        assert result["date"]["day_of_week"] == "Tuesday"
        assert result["weather"]["temperature_f"] == 45
        assert len(result["appointments"]) == 1
        assert result["appointments"][0]["time"] == "2:30 PM"
        assert result["errors"] is None

    def test_to_dict_no_weather(self, sample_date_info):
        """Test serialization when weather is None."""
        briefing = Briefing(
            generated_at=datetime.now(),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=sample_date_info,
        )
        result = briefing.to_dict()
        assert result["weather"] is None

    def test_to_dict_with_errors(self, sample_date_info):
        """Test serialization includes errors when present."""
        briefing = Briefing(
            generated_at=datetime.now(),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=sample_date_info,
            errors=["Weather API failed", "Calendar auth expired"],
        )
        result = briefing.to_dict()
        assert result["errors"] == ["Weather API failed", "Calendar auth expired"]

    def test_to_json(self, sample_date_info, sample_weather):
        """Test JSON string output."""
        now = datetime(2025, 1, 14, 7, 15)
        briefing = Briefing(
            generated_at=now,
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=sample_date_info,
            weather=sample_weather,
        )
        json_str = briefing.to_json()
        parsed = json.loads(json_str)
        assert parsed["recipient_name"] == "Eleanor"
        assert parsed["weather"]["temperature_f"] == 45
