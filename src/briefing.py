"""Briefing assembly for the Good Morning Dashboard."""

import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from .config import Config
from .data_sources.calendar import CalendarSource
from .data_sources.datetime_source import DateTimeSource
from .data_sources.weather import WeatherSource
from .models import Appointment, Briefing, DateInfo, WeatherInfo

logger = logging.getLogger(__name__)


class MockDataProvider:
    """
    Provides realistic mock data for testing without API credentials.

    This allows the dashboard to be fully tested and demonstrated
    without requiring OpenWeatherMap or Google Calendar setup.
    """

    def __init__(self, config: Config, now: Optional[datetime] = None):
        """
        Initialize mock data provider.

        Args:
            config: Configuration for names and settings
            now: Optional datetime for testing (defaults to current time)
        """
        self.config = config
        self._tz = ZoneInfo(config.timezone)
        self._now = now or datetime.now(self._tz)

    def get_date_info(self) -> DateInfo:
        """Get date info using actual DateTimeSource."""
        source = DateTimeSource(self.config.timezone)
        return source.get_current(self._now)

    def get_weather(self) -> WeatherInfo:
        """
        Get mock weather data.

        Returns realistic weather that varies slightly based on time of day.
        """
        hour = self._now.hour

        # Vary temperature by time of day
        if hour < 6:
            temp = 45
            description = "cold"
        elif hour < 10:
            temp = 52
            description = "a bit chilly"
        elif hour < 14:
            temp = 62
            description = "cool"
        elif hour < 18:
            temp = 68
            description = "pleasant"
        else:
            temp = 55
            description = "cool"

        return WeatherInfo(
            temperature_f=temp,
            conditions="partly cloudy",
            description=description,
            icon_code="03d" if 6 <= hour < 18 else "03n",
        )

    def get_appointments(self) -> list[Appointment]:
        """
        Get mock appointments for today.

        Returns a realistic set of appointments with prep reminders.
        """
        caregiver = self.config.caregiver_name
        prep_minutes = self.config.prep_reminder_minutes

        # Create appointments relative to "today"
        today = self._now.date()

        def make_time(hour: int, minute: int = 0) -> datetime:
            return datetime(
                today.year, today.month, today.day,
                hour, minute, tzinfo=self._tz
            )

        def format_time(dt: datetime) -> str:
            hour = dt.hour
            minute = dt.minute
            if hour == 0:
                h12, ampm = 12, "AM"
            elif hour < 12:
                h12, ampm = hour, "AM"
            elif hour == 12:
                h12, ampm = 12, "PM"
            else:
                h12, ampm = hour - 12, "PM"
            return f"{h12}:{minute:02d} {ampm}"

        def format_prep(dt: datetime) -> str:
            prep_dt = dt - timedelta(minutes=prep_minutes)
            prep_hour = prep_dt.hour
            prep_min = prep_dt.minute
            if prep_hour == 0:
                h12 = 12
            elif prep_hour > 12:
                h12 = prep_hour - 12
            else:
                h12 = prep_hour
            if prep_min == 0:
                return f"{caregiver} will help you get ready around {h12}"
            return f"{caregiver} will help you get ready around {h12}:{prep_min:02d}"

        # Morning appointment
        morning_time = make_time(10, 0)
        morning_apt = Appointment(
            time=format_time(morning_time),
            title="Morning exercise class",
            details="Community center - Chair yoga",
            prep_reminder=format_prep(morning_time),
            start_datetime=morning_time,
        )

        # Afternoon appointment
        afternoon_time = make_time(14, 30)
        afternoon_apt = Appointment(
            time=format_time(afternoon_time),
            title="Doctor's appointment",
            details="Dr. Martinez - Cardiology follow-up",
            prep_reminder=format_prep(afternoon_time),
            start_datetime=afternoon_time,
        )

        return [morning_apt, afternoon_apt]


class BriefingBuilder:
    """
    Orchestrates data collection from all sources to build a complete Briefing.

    Handles graceful degradation when individual sources fail,
    ensuring the briefing is always generated with available data.
    """

    def __init__(self, config: Config):
        """
        Initialize the BriefingBuilder.

        Args:
            config: Application configuration
        """
        self.config = config

    def build(
        self,
        use_mock: bool = False,
        now: Optional[datetime] = None,
    ) -> Briefing:
        """
        Build a complete briefing from all data sources.

        Args:
            use_mock: If True, use mock data instead of real APIs
            now: Optional datetime override for testing

        Returns:
            Briefing object with all available data
        """
        errors: list[str] = []
        tz = ZoneInfo(self.config.timezone)

        if now is None:
            now = datetime.now(tz)

        if use_mock:
            return self._build_mock(now)

        # Get date/time (always succeeds)
        datetime_source = DateTimeSource(self.config.timezone)
        date_info = datetime_source.get_current(now)

        # Get weather (may fail)
        weather = self._fetch_weather(errors)

        # Get appointments (may fail)
        appointments = self._fetch_appointments(errors, now)

        return Briefing(
            generated_at=now,
            recipient_name=self.config.recipient_name,
            caregiver_name=self.config.caregiver_name,
            date_info=date_info,
            weather=weather,
            appointments=appointments,
            errors=errors,
        )

    def _build_mock(self, now: datetime) -> Briefing:
        """Build a briefing using mock data."""
        mock = MockDataProvider(self.config, now)

        return Briefing(
            generated_at=now,
            recipient_name=self.config.recipient_name,
            caregiver_name=self.config.caregiver_name,
            date_info=mock.get_date_info(),
            weather=mock.get_weather(),
            appointments=mock.get_appointments(),
            errors=[],
        )

    def _fetch_weather(self, errors: list[str]) -> Optional[WeatherInfo]:
        """
        Fetch weather data, logging any errors.

        Args:
            errors: List to append error messages to

        Returns:
            WeatherInfo or None if fetch failed
        """
        if not self.config.weather.is_configured:
            logger.info("Weather not configured, skipping")
            return None

        try:
            weather_source = WeatherSource(self.config.weather)
            weather = weather_source.fetch()

            if weather is None:
                errors.append("Weather data unavailable")
                logger.warning("Weather fetch returned None")

            return weather

        except Exception as e:
            error_msg = f"Weather fetch failed: {e}"
            errors.append(error_msg)
            logger.error(error_msg)
            return None

    def _fetch_appointments(
        self,
        errors: list[str],
        now: datetime,
    ) -> list[Appointment]:
        """
        Fetch today's appointments, logging any errors.

        Args:
            errors: List to append error messages to
            now: Current datetime for filtering

        Returns:
            List of appointments (empty if fetch failed)
        """
        try:
            calendar_source = CalendarSource(
                config=self.config.calendar,
                timezone=self.config.timezone,
                caregiver_name=self.config.caregiver_name,
                prep_minutes=self.config.prep_reminder_minutes,
            )
            appointments = calendar_source.fetch_today(now)

            # Note: empty list might be valid (no appointments today)
            # We only log as error if there was an actual failure
            # The CalendarSource already handles this internally

            return appointments

        except Exception as e:
            error_msg = f"Calendar fetch failed: {e}"
            errors.append(error_msg)
            logger.error(error_msg)
            return []


def build_briefing(
    config: Optional[Config] = None,
    use_mock: bool = False,
    now: Optional[datetime] = None,
) -> Briefing:
    """
    Convenience function to build a briefing.

    Args:
        config: Configuration (loads default if None)
        use_mock: Use mock data instead of real APIs
        now: Optional datetime override

    Returns:
        Complete Briefing object
    """
    if config is None:
        from .config import load_config
        config = load_config()

    builder = BriefingBuilder(config)
    return builder.build(use_mock=use_mock, now=now)
