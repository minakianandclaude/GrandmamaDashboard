"""Tests for configuration loading."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.config import (
    CalendarConfig,
    Config,
    DashboardConfig,
    WeatherConfig,
    get_default_config,
    load_config,
)


class TestWeatherConfig:
    """Tests for WeatherConfig dataclass."""

    def test_default_values(self):
        """Test default WeatherConfig values."""
        config = WeatherConfig()
        assert config.api_key is None
        assert config.city is None
        assert config.lat is None
        assert config.lon is None
        assert config.units == "imperial"

    def test_env_override_api_key(self):
        """Test that OPENWEATHERMAP_API_KEY env var overrides api_key."""
        with patch.dict(os.environ, {"OPENWEATHERMAP_API_KEY": "test-key-123"}):
            config = WeatherConfig(api_key="original-key")
            assert config.api_key == "test-key-123"

    def test_has_location_with_city(self):
        """Test has_location with city specified."""
        config = WeatherConfig(city="New York")
        assert config.has_location is True

    def test_has_location_with_coords(self):
        """Test has_location with lat/lon specified."""
        config = WeatherConfig(lat=40.7128, lon=-74.0060)
        assert config.has_location is True

    def test_has_location_false(self):
        """Test has_location when nothing specified."""
        config = WeatherConfig()
        assert config.has_location is False

    def test_is_configured_true(self):
        """Test is_configured when fully configured."""
        with patch.dict(os.environ, {"OPENWEATHERMAP_API_KEY": "test-key"}):
            config = WeatherConfig(city="New York")
            assert config.is_configured is True

    def test_is_configured_no_key(self):
        """Test is_configured when API key missing."""
        with patch.dict(os.environ, {}, clear=True):
            # Make sure the env var is not set
            os.environ.pop("OPENWEATHERMAP_API_KEY", None)
            config = WeatherConfig(city="New York")
            assert config.is_configured is False

    def test_is_configured_no_location(self):
        """Test is_configured when location missing."""
        with patch.dict(os.environ, {"OPENWEATHERMAP_API_KEY": "test-key"}):
            config = WeatherConfig()
            assert config.is_configured is False


class TestCalendarConfig:
    """Tests for CalendarConfig dataclass."""

    def test_default_values(self):
        """Test default CalendarConfig values."""
        config = CalendarConfig()
        assert config.credentials_file == "credentials.json"
        assert config.token_file == "token.json"
        assert config.calendar_id == "primary"

    def test_env_override_credentials(self):
        """Test environment variable override for credentials file."""
        with patch.dict(os.environ, {"GOOGLE_CREDENTIALS_FILE": "/custom/creds.json"}):
            config = CalendarConfig()
            assert config.credentials_file == "/custom/creds.json"

    def test_env_override_token(self):
        """Test environment variable override for token file."""
        with patch.dict(os.environ, {"GOOGLE_TOKEN_FILE": "/custom/token.json"}):
            config = CalendarConfig()
            assert config.token_file == "/custom/token.json"


class TestDashboardConfig:
    """Tests for DashboardConfig dataclass."""

    def test_default_values(self):
        """Test default DashboardConfig values."""
        config = DashboardConfig()
        assert config.theme == "calm"
        assert config.refresh_interval_seconds == 60
        assert config.port == 8080


class TestConfig:
    """Tests for main Config dataclass."""

    def test_default_values(self):
        """Test default Config values."""
        config = Config()
        assert config.recipient_name == "Friend"
        assert config.caregiver_name == "your caregiver"
        assert config.timezone == "America/New_York"
        assert config.prep_reminder_minutes == 60
        assert isinstance(config.weather, WeatherConfig)
        assert isinstance(config.calendar, CalendarConfig)
        assert isinstance(config.dashboard, DashboardConfig)

    def test_env_override_recipient_name(self):
        """Test environment variable override for recipient name."""
        with patch.dict(os.environ, {"DASHBOARD_RECIPIENT_NAME": "Margaret"}):
            config = Config()
            assert config.recipient_name == "Margaret"

    def test_env_override_caregiver_name(self):
        """Test environment variable override for caregiver name."""
        with patch.dict(os.environ, {"DASHBOARD_CAREGIVER_NAME": "John"}):
            config = Config()
            assert config.caregiver_name == "John"

    def test_env_override_timezone(self):
        """Test environment variable override for timezone."""
        with patch.dict(os.environ, {"DASHBOARD_TIMEZONE": "America/Los_Angeles"}):
            config = Config()
            assert config.timezone == "America/Los_Angeles"

    def test_env_override_prep_minutes(self):
        """Test environment variable override for prep reminder minutes."""
        with patch.dict(os.environ, {"DASHBOARD_PREP_REMINDER_MINUTES": "45"}):
            config = Config()
            assert config.prep_reminder_minutes == 45

    def test_env_override_prep_minutes_invalid(self):
        """Test that invalid prep minutes value is ignored."""
        with patch.dict(os.environ, {"DASHBOARD_PREP_REMINDER_MINUTES": "not-a-number"}):
            config = Config()
            assert config.prep_reminder_minutes == 60  # Default value


class TestLoadConfig:
    """Tests for load_config function."""

    @pytest.fixture
    def temp_config_file(self, tmp_path):
        """Create a temporary config file."""
        config_path = tmp_path / "config.yaml"
        config_data = {
            "recipient_name": "Eleanor",
            "caregiver_name": "Sarah",
            "timezone": "America/Chicago",
            "prep_reminder_minutes": 45,
            "weather": {
                "city": "Chicago, IL",
                "units": "imperial",
            },
            "calendar": {
                "credentials_file": "/path/to/creds.json",
                "calendar_id": "family@group.calendar.google.com",
            },
            "dashboard": {
                "theme": "bright",
                "refresh_interval_seconds": 30,
                "port": 3000,
            },
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        return config_path

    def test_load_from_explicit_path(self, temp_config_file):
        """Test loading config from an explicit path."""
        config = load_config(temp_config_file)
        assert config.recipient_name == "Eleanor"
        assert config.caregiver_name == "Sarah"
        assert config.timezone == "America/Chicago"
        assert config.prep_reminder_minutes == 45
        assert config.weather.city == "Chicago, IL"
        assert config.calendar.credentials_file == "/path/to/creds.json"
        assert config.dashboard.theme == "bright"
        assert config.dashboard.port == 3000

    def test_load_missing_file_raises(self, tmp_path):
        """Test that loading a non-existent explicit path raises."""
        missing_path = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError):
            load_config(missing_path)

    def test_load_partial_config(self, tmp_path):
        """Test loading a config with only some values specified."""
        config_path = tmp_path / "partial.yaml"
        with open(config_path, "w") as f:
            yaml.dump({"recipient_name": "Martha"}, f)

        config = load_config(config_path)
        assert config.recipient_name == "Martha"
        assert config.caregiver_name == "your caregiver"  # Default
        assert config.timezone == "America/New_York"  # Default

    def test_load_empty_config(self, tmp_path):
        """Test loading an empty config file uses defaults."""
        config_path = tmp_path / "empty.yaml"
        config_path.touch()

        config = load_config(config_path)
        assert config.recipient_name == "Friend"

    def test_env_overrides_file_values(self, temp_config_file):
        """Test that env vars override file values."""
        with patch.dict(os.environ, {"DASHBOARD_RECIPIENT_NAME": "Override Name"}):
            config = load_config(temp_config_file)
            # File says Eleanor, but env says Override Name
            assert config.recipient_name == "Override Name"

    def test_load_no_file_uses_defaults(self, tmp_path):
        """Test that missing config file uses defaults."""
        # Change to a directory with no config file
        with patch("src.config.DEFAULT_CONFIG_PATHS", [tmp_path / "nonexistent.yaml"]):
            config = load_config(None)
            assert config.recipient_name == "Friend"
            assert config.timezone == "America/New_York"


class TestGetDefaultConfig:
    """Tests for get_default_config function."""

    def test_returns_config_with_defaults(self):
        """Test that get_default_config returns proper defaults."""
        config = get_default_config()
        assert isinstance(config, Config)
        assert config.recipient_name == "Friend"
        assert config.timezone == "America/New_York"

    def test_respects_env_vars(self):
        """Test that get_default_config respects environment variables."""
        with patch.dict(os.environ, {"DASHBOARD_RECIPIENT_NAME": "EnvName"}):
            config = get_default_config()
            assert config.recipient_name == "EnvName"
