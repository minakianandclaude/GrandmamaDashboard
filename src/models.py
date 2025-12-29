"""Core data models for the Good Morning Dashboard."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional
import json


@dataclass
class DateInfo:
    """Structured date and time information for the briefing."""

    day_of_week: str  # e.g., "Tuesday"
    full_date: str  # e.g., "January 14th"
    time_of_day: str  # e.g., "7:15 in the morning"
    hour_12: int  # e.g., 7
    minute: int  # e.g., 15
    am_pm: str  # e.g., "AM"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class ForecastDay:
    """Single day forecast for multi-day forecast display."""

    day_name: str  # e.g., "Mon", "Tue", "Wed"
    high_f: int  # High temperature in Fahrenheit
    low_f: int  # Low temperature in Fahrenheit
    conditions: str  # e.g., "cloudy", "sunny", "rainy"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "day_name": self.day_name,
            "high_f": self.high_f,
            "low_f": self.low_f,
            "conditions": self.conditions,
        }


@dataclass
class WeatherInfo:
    """Weather information with practical descriptions."""

    temperature_f: int  # Current/near-term temperature in Fahrenheit
    conditions: str  # e.g., "cloudy", "sunny", "rainy"
    description: str  # e.g., "a bit chilly", "quite warm"
    icon_code: Optional[str] = None  # OpenWeatherMap icon code for dashboard
    high_f: Optional[int] = None  # Today's high temperature
    low_f: Optional[int] = None  # Today's low temperature
    forecast: list["ForecastDay"] = field(default_factory=list)  # Next 3 days

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "temperature_f": self.temperature_f,
            "conditions": self.conditions,
            "description": self.description,
            "icon_code": self.icon_code,
        }
        if self.high_f is not None:
            result["high_f"] = self.high_f
        if self.low_f is not None:
            result["low_f"] = self.low_f
        if self.forecast:
            result["forecast"] = [f.to_dict() for f in self.forecast]
        return result


@dataclass
class Appointment:
    """A single calendar appointment."""

    time: str  # e.g., "2:30 PM"
    title: str  # e.g., "Doctor's appointment"
    details: Optional[str] = None  # e.g., "Dr. Martinez, cardiology follow-up"
    prep_reminder: Optional[str] = None  # e.g., "Sarah will help you get ready around 1:30"
    start_datetime: Optional[datetime] = None  # Original datetime for sorting

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "time": self.time,
            "title": self.title,
            "details": self.details,
            "prep_reminder": self.prep_reminder,
        }
        # Exclude start_datetime from JSON output (internal use only)
        return result


@dataclass
class Briefing:
    """Complete morning briefing with all data sources."""

    generated_at: datetime
    recipient_name: str
    caregiver_name: str
    date_info: DateInfo
    weather: Optional[WeatherInfo] = None
    appointments: list[Appointment] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)  # Track any data source failures

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "generated_at": self.generated_at.isoformat(),
            "recipient_name": self.recipient_name,
            "caregiver_name": self.caregiver_name,
            "date": self.date_info.to_dict(),
            "weather": self.weather.to_dict() if self.weather else None,
            "appointments": [apt.to_dict() for apt in self.appointments],
            "errors": self.errors if self.errors else None,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @property
    def has_weather(self) -> bool:
        """Check if weather data is available."""
        return self.weather is not None

    @property
    def has_appointments(self) -> bool:
        """Check if there are any appointments today."""
        return len(self.appointments) > 0

    @property
    def appointment_count(self) -> int:
        """Get the number of appointments."""
        return len(self.appointments)
