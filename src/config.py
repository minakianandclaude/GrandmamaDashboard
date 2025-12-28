"""Configuration management for the Good Morning Dashboard."""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# Default config file locations to search
DEFAULT_CONFIG_PATHS = [
    Path("config.yaml"),
    Path("config.yml"),
    Path.home() / ".grandmama" / "config.yaml",
]


@dataclass
class WeatherConfig:
    """Weather API configuration."""

    api_key: Optional[str] = None
    city: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    units: str = "imperial"  # imperial (F) or metric (C)

    def __post_init__(self):
        # Environment variable override for API key
        env_key = os.environ.get("OPENWEATHERMAP_API_KEY")
        if env_key:
            self.api_key = env_key

    @property
    def has_location(self) -> bool:
        """Check if location is configured."""
        return self.city is not None or (self.lat is not None and self.lon is not None)

    @property
    def is_configured(self) -> bool:
        """Check if weather API is fully configured."""
        return self.api_key is not None and self.has_location


@dataclass
class CalendarConfig:
    """Google Calendar configuration."""

    credentials_file: str = "credentials.json"
    token_file: str = "token.json"
    calendar_id: str = "primary"

    def __post_init__(self):
        # Environment variable overrides
        env_creds = os.environ.get("GOOGLE_CREDENTIALS_FILE")
        if env_creds:
            self.credentials_file = env_creds

        env_token = os.environ.get("GOOGLE_TOKEN_FILE")
        if env_token:
            self.token_file = env_token


@dataclass
class DashboardConfig:
    """Dashboard display configuration."""

    theme: str = "calm"  # calm, bright, or high_contrast
    refresh_interval_seconds: int = 60
    port: int = 8080


@dataclass
class Config:
    """Main configuration container."""

    # Care recipient and caregiver names
    recipient_name: str = "Friend"
    caregiver_name: str = "your caregiver"

    # Timezone (IANA format, e.g., "America/New_York")
    timezone: str = "America/New_York"

    # Prep reminder offset in minutes (remind this many minutes before appointment)
    prep_reminder_minutes: int = 60

    # Nested configurations
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    calendar: CalendarConfig = field(default_factory=CalendarConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)

    def __post_init__(self):
        # Environment variable overrides for top-level settings
        env_recipient = os.environ.get("DASHBOARD_RECIPIENT_NAME")
        if env_recipient:
            self.recipient_name = env_recipient

        env_caregiver = os.environ.get("DASHBOARD_CAREGIVER_NAME")
        if env_caregiver:
            self.caregiver_name = env_caregiver

        env_timezone = os.environ.get("DASHBOARD_TIMEZONE")
        if env_timezone:
            self.timezone = env_timezone

        env_prep = os.environ.get("DASHBOARD_PREP_REMINDER_MINUTES")
        if env_prep:
            try:
                self.prep_reminder_minutes = int(env_prep)
            except ValueError:
                logger.warning(f"Invalid DASHBOARD_PREP_REMINDER_MINUTES: {env_prep}")


def _parse_weather_config(data: dict) -> WeatherConfig:
    """Parse weather configuration from dict."""
    weather_data = data.get("weather", {})
    return WeatherConfig(
        api_key=weather_data.get("api_key"),
        city=weather_data.get("city"),
        lat=weather_data.get("lat"),
        lon=weather_data.get("lon"),
        units=weather_data.get("units", "imperial"),
    )


def _parse_calendar_config(data: dict) -> CalendarConfig:
    """Parse calendar configuration from dict."""
    calendar_data = data.get("calendar", {})
    return CalendarConfig(
        credentials_file=calendar_data.get("credentials_file", "credentials.json"),
        token_file=calendar_data.get("token_file", "token.json"),
        calendar_id=calendar_data.get("calendar_id", "primary"),
    )


def _parse_dashboard_config(data: dict) -> DashboardConfig:
    """Parse dashboard configuration from dict."""
    dashboard_data = data.get("dashboard", {})
    return DashboardConfig(
        theme=dashboard_data.get("theme", "calm"),
        refresh_interval_seconds=dashboard_data.get("refresh_interval_seconds", 60),
        port=dashboard_data.get("port", 8080),
    )


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from YAML file with environment variable overrides.

    Args:
        config_path: Explicit path to config file. If None, searches default locations.

    Returns:
        Config object with all settings loaded.

    Raises:
        FileNotFoundError: If explicit config_path is provided but doesn't exist.
    """
    # If explicit path provided, use it
    if config_path is not None:
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        paths_to_try = [config_path]
    else:
        paths_to_try = DEFAULT_CONFIG_PATHS

    # Try to find and load config file
    config_data = {}
    loaded_from = None

    for path in paths_to_try:
        if path.exists():
            try:
                with open(path, "r") as f:
                    config_data = yaml.safe_load(f) or {}
                loaded_from = path
                logger.info(f"Loaded configuration from {path}")
                break
            except yaml.YAMLError as e:
                logger.error(f"Failed to parse YAML config at {path}: {e}")
                raise

    if loaded_from is None and config_path is None:
        logger.info("No config file found, using defaults with environment overrides")

    # Parse nested configs
    weather_config = _parse_weather_config(config_data)
    calendar_config = _parse_calendar_config(config_data)
    dashboard_config = _parse_dashboard_config(config_data)

    # Build main config
    config = Config(
        recipient_name=config_data.get("recipient_name", "Friend"),
        caregiver_name=config_data.get("caregiver_name", "your caregiver"),
        timezone=config_data.get("timezone", "America/New_York"),
        prep_reminder_minutes=config_data.get("prep_reminder_minutes", 60),
        weather=weather_config,
        calendar=calendar_config,
        dashboard=dashboard_config,
    )

    return config


def get_default_config() -> Config:
    """Get a Config object with all defaults (no file loading)."""
    return Config()
