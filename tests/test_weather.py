"""Tests for the WeatherSource module."""

from unittest.mock import Mock, patch

import pytest
import requests

from src.config import WeatherConfig
from src.data_sources.weather import (
    WeatherSource,
    get_temperature_description,
    parse_weather_response,
    simplify_condition,
)
from src.models import WeatherInfo


class TestGetTemperatureDescription:
    """Tests for the get_temperature_description function."""

    def test_quite_cold(self):
        """Test temperatures below freezing."""
        assert get_temperature_description(0) == "quite cold"
        assert get_temperature_description(20) == "quite cold"
        assert get_temperature_description(31) == "quite cold"

    def test_cold_boundary(self):
        """Test boundary between quite cold and cold."""
        assert get_temperature_description(31) == "quite cold"
        assert get_temperature_description(32) == "cold"

    def test_cold(self):
        """Test cold range (32-45)."""
        assert get_temperature_description(32) == "cold"
        assert get_temperature_description(40) == "cold"
        assert get_temperature_description(45) == "cold"

    def test_chilly_boundary(self):
        """Test boundary between cold and chilly."""
        assert get_temperature_description(45) == "cold"
        assert get_temperature_description(46) == "a bit chilly"

    def test_chilly(self):
        """Test chilly range (46-55)."""
        assert get_temperature_description(46) == "a bit chilly"
        assert get_temperature_description(50) == "a bit chilly"
        assert get_temperature_description(55) == "a bit chilly"

    def test_cool_boundary(self):
        """Test boundary between chilly and cool."""
        assert get_temperature_description(55) == "a bit chilly"
        assert get_temperature_description(56) == "cool"

    def test_cool(self):
        """Test cool range (56-65)."""
        assert get_temperature_description(56) == "cool"
        assert get_temperature_description(60) == "cool"
        assert get_temperature_description(65) == "cool"

    def test_pleasant_boundary(self):
        """Test boundary between cool and pleasant."""
        assert get_temperature_description(65) == "cool"
        assert get_temperature_description(66) == "pleasant"

    def test_pleasant(self):
        """Test pleasant range (66-75)."""
        assert get_temperature_description(66) == "pleasant"
        assert get_temperature_description(70) == "pleasant"
        assert get_temperature_description(75) == "pleasant"

    def test_warm_boundary(self):
        """Test boundary between pleasant and warm."""
        assert get_temperature_description(75) == "pleasant"
        assert get_temperature_description(76) == "warm"

    def test_warm(self):
        """Test warm range (76-85)."""
        assert get_temperature_description(76) == "warm"
        assert get_temperature_description(80) == "warm"
        assert get_temperature_description(85) == "warm"

    def test_quite_warm_boundary(self):
        """Test boundary between warm and quite warm."""
        assert get_temperature_description(85) == "warm"
        assert get_temperature_description(86) == "quite warm"

    def test_quite_warm(self):
        """Test quite warm range (86-95)."""
        assert get_temperature_description(86) == "quite warm"
        assert get_temperature_description(90) == "quite warm"
        assert get_temperature_description(95) == "quite warm"

    def test_very_hot_boundary(self):
        """Test boundary between quite warm and very hot."""
        assert get_temperature_description(95) == "quite warm"
        assert get_temperature_description(96) == "very hot"

    def test_very_hot(self):
        """Test very hot range (96+)."""
        assert get_temperature_description(96) == "very hot"
        assert get_temperature_description(100) == "very hot"
        assert get_temperature_description(110) == "very hot"

    def test_negative_temperatures(self):
        """Test negative temperatures."""
        assert get_temperature_description(-10) == "quite cold"
        assert get_temperature_description(-40) == "quite cold"


class TestSimplifyCondition:
    """Tests for the simplify_condition function."""

    def test_clear_conditions(self):
        """Test clear sky conditions."""
        assert simplify_condition("clear sky") == "clear"
        assert simplify_condition("Clear Sky") == "clear"
        assert simplify_condition("CLEAR") == "clear"

    def test_partly_cloudy(self):
        """Test partly cloudy conditions."""
        assert simplify_condition("few clouds") == "partly cloudy"
        assert simplify_condition("scattered clouds") == "partly cloudy"

    def test_cloudy(self):
        """Test cloudy conditions."""
        assert simplify_condition("broken clouds") == "cloudy"
        assert simplify_condition("overcast clouds") == "cloudy"
        assert simplify_condition("overcast") == "cloudy"

    def test_generic_clouds(self):
        """Test generic cloud mention defaults to cloudy."""
        assert simplify_condition("clouds") == "cloudy"

    def test_stormy(self):
        """Test storm conditions."""
        assert simplify_condition("thunderstorm") == "stormy"
        assert simplify_condition("thunderstorm with rain") == "stormy"
        assert simplify_condition("heavy thunderstorm") == "stormy"

    def test_snowy(self):
        """Test snow conditions."""
        assert simplify_condition("snow") == "snowy"
        assert simplify_condition("light snow") == "snowy"
        assert simplify_condition("heavy snow") == "snowy"
        assert simplify_condition("sleet") == "snowy"

    def test_rainy(self):
        """Test rain conditions."""
        assert simplify_condition("rain") == "rainy"
        assert simplify_condition("light rain") == "rainy"
        assert simplify_condition("heavy rain") == "rainy"
        assert simplify_condition("shower rain") == "rainy"
        assert simplify_condition("drizzle") == "rainy"
        assert simplify_condition("light intensity drizzle") == "rainy"

    def test_foggy(self):
        """Test fog/mist conditions."""
        assert simplify_condition("mist") == "foggy"
        assert simplify_condition("fog") == "foggy"
        assert simplify_condition("haze") == "foggy"

    def test_hazy(self):
        """Test hazy conditions."""
        assert simplify_condition("smoke") == "hazy"
        assert simplify_condition("dust") == "hazy"
        assert simplify_condition("sand") == "hazy"

    def test_unknown_condition(self):
        """Test unknown conditions return lowercase original."""
        assert simplify_condition("tornado") == "tornado"
        assert simplify_condition("Unknown Weather") == "unknown weather"


class TestParseWeatherResponse:
    """Tests for the parse_weather_response function."""

    def test_valid_response(self):
        """Test parsing a valid API response."""
        data = {
            "main": {"temp": 72.6},
            "weather": [
                {"description": "scattered clouds", "icon": "03d"}
            ],
        }
        result = parse_weather_response(data)

        assert result is not None
        assert result.temperature_f == 73  # Rounded from 72.6
        assert result.conditions == "partly cloudy"
        assert result.description == "pleasant"
        assert result.icon_code == "03d"

    def test_cold_rainy_response(self):
        """Test parsing cold, rainy weather."""
        data = {
            "main": {"temp": 38.2},
            "weather": [
                {"description": "light rain", "icon": "10d"}
            ],
        }
        result = parse_weather_response(data)

        assert result is not None
        assert result.temperature_f == 38
        assert result.conditions == "rainy"
        assert result.description == "cold"

    def test_hot_clear_response(self):
        """Test parsing hot, clear weather."""
        data = {
            "main": {"temp": 98.6},
            "weather": [
                {"description": "clear sky", "icon": "01d"}
            ],
        }
        result = parse_weather_response(data)

        assert result is not None
        assert result.temperature_f == 99
        assert result.conditions == "clear"
        assert result.description == "very hot"

    def test_empty_weather_array(self):
        """Test handling empty weather array."""
        data = {
            "main": {"temp": 70},
            "weather": [],
        }
        result = parse_weather_response(data)

        assert result is not None
        assert result.conditions == "unknown"
        assert result.icon_code is None

    def test_missing_main_key(self):
        """Test handling missing main key."""
        data = {"weather": [{"description": "clear"}]}
        result = parse_weather_response(data)
        assert result is None

    def test_missing_temp_key(self):
        """Test handling missing temp key."""
        data = {"main": {}, "weather": [{"description": "clear"}]}
        result = parse_weather_response(data)
        assert result is None

    def test_invalid_temp_type(self):
        """Test handling non-numeric temperature."""
        data = {"main": {"temp": "warm"}, "weather": []}
        result = parse_weather_response(data)
        assert result is None


class TestWeatherSource:
    """Tests for the WeatherSource class."""

    @pytest.fixture
    def valid_config(self):
        """Create a valid weather config."""
        return WeatherConfig(
            api_key="test-api-key-123",
            city="New York, NY",
            units="imperial",
        )

    @pytest.fixture
    def coords_config(self):
        """Create a config with lat/lon."""
        return WeatherConfig(
            api_key="test-api-key-123",
            lat=40.7128,
            lon=-74.0060,
            units="imperial",
        )

    @pytest.fixture
    def mock_current_response(self):
        """Create a mock successful current weather API response."""
        return {
            "main": {"temp": 48.5},
            "weather": [{"description": "clear sky", "icon": "01d"}],
        }

    @pytest.fixture
    def mock_forecast_response(self):
        """Create a mock successful forecast API response."""
        from datetime import date, timedelta
        today = date.today().strftime("%Y-%m-%d")
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        day_after = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        return {
            "list": [
                {
                    "dt_txt": f"{today} 09:00:00",
                    "main": {"temp": 45.0},
                    "weather": [{"description": "broken clouds", "icon": "04d"}],
                },
                {
                    "dt_txt": f"{today} 12:00:00",
                    "main": {"temp": 58.0},
                    "weather": [{"description": "scattered clouds", "icon": "03d"}],
                },
                {
                    "dt_txt": f"{today} 15:00:00",
                    "main": {"temp": 55.0},
                    "weather": [{"description": "broken clouds", "icon": "04d"}],
                },
                {
                    "dt_txt": f"{tomorrow} 09:00:00",
                    "main": {"temp": 42.0},
                    "weather": [{"description": "clear sky", "icon": "01d"}],
                },
                {
                    "dt_txt": f"{tomorrow} 15:00:00",
                    "main": {"temp": 52.0},
                    "weather": [{"description": "clear sky", "icon": "01d"}],
                },
                {
                    "dt_txt": f"{day_after} 09:00:00",
                    "main": {"temp": 40.0},
                    "weather": [{"description": "light rain", "icon": "10d"}],
                },
                {
                    "dt_txt": f"{day_after} 15:00:00",
                    "main": {"temp": 48.0},
                    "weather": [{"description": "light rain", "icon": "10d"}],
                },
            ],
        }

    @pytest.fixture
    def mock_success_response(self):
        """Create a mock successful forecast API response (legacy fixture)."""
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        return {
            "list": [
                {
                    "dt_txt": f"{today} 09:00:00",
                    "main": {"temp": 52.3},
                    "weather": [{"description": "broken clouds", "icon": "04d"}],
                },
                {
                    "dt_txt": f"{today} 12:00:00",
                    "main": {"temp": 58.0},
                    "weather": [{"description": "scattered clouds", "icon": "03d"}],
                },
                {
                    "dt_txt": f"{today} 15:00:00",
                    "main": {"temp": 55.0},
                    "weather": [{"description": "broken clouds", "icon": "04d"}],
                },
            ],
        }

    def test_init(self, valid_config):
        """Test WeatherSource initialization."""
        source = WeatherSource(valid_config)
        assert source.config == valid_config

    def test_build_params_with_city(self, valid_config):
        """Test parameter building with city."""
        source = WeatherSource(valid_config)
        params = source._build_params()

        assert params is not None
        assert params["appid"] == "test-api-key-123"
        assert params["units"] == "imperial"
        assert params["q"] == "New York, NY"
        assert "lat" not in params
        assert "lon" not in params

    def test_build_params_with_coords(self, coords_config):
        """Test parameter building with coordinates."""
        source = WeatherSource(coords_config)
        params = source._build_params()

        assert params is not None
        assert params["lat"] == 40.7128
        assert params["lon"] == -74.0060
        assert "q" not in params

    def test_build_params_prefers_coords(self):
        """Test that coordinates are preferred over city."""
        config = WeatherConfig(
            api_key="test-key",
            city="New York",
            lat=40.7128,
            lon=-74.0060,
        )
        source = WeatherSource(config)
        params = source._build_params()

        assert "lat" in params
        assert "lon" in params
        assert "q" not in params

    def test_build_params_no_api_key(self):
        """Test that missing API key returns None."""
        config = WeatherConfig(city="New York")
        source = WeatherSource(config)
        params = source._build_params()
        assert params is None

    def test_build_params_no_location(self):
        """Test that missing location returns None."""
        config = WeatherConfig(api_key="test-key")
        source = WeatherSource(config)
        params = source._build_params()
        assert params is None

    @patch("src.data_sources.weather.requests.get")
    def test_fetch_success(self, mock_get, valid_config, mock_current_response, mock_forecast_response):
        """Test successful weather fetch from both current and forecast APIs."""
        # Mock responses for both API calls
        mock_current = Mock()
        mock_current.status_code = 200
        mock_current.json.return_value = mock_current_response

        mock_forecast = Mock()
        mock_forecast.status_code = 200
        mock_forecast.json.return_value = mock_forecast_response

        # First call returns current weather, second returns forecast
        mock_get.side_effect = [mock_current, mock_forecast]

        source = WeatherSource(valid_config)
        result = source.fetch()

        assert result is not None
        assert isinstance(result, WeatherInfo)
        # Current temp comes from current weather API
        assert result.temperature_f == 48  # Rounded from 48.5
        assert result.conditions == "clear"  # From current API
        # High/low come from forecast API
        assert result.high_f == 58  # Max of today's forecasts
        assert result.low_f == 45  # Min of today's forecasts
        # Forecast should have future days
        assert len(result.forecast) == 2  # Tomorrow and day after
        assert result.forecast[0].high_f == 52
        assert result.forecast[0].low_f == 42

    @patch("src.data_sources.weather.requests.get")
    def test_fetch_401_invalid_key(self, mock_get, valid_config):
        """Test handling of invalid API key."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        source = WeatherSource(valid_config)
        result = source.fetch()
        assert result is None

    @patch("src.data_sources.weather.requests.get")
    def test_fetch_404_location_not_found(self, mock_get, valid_config):
        """Test handling of location not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        source = WeatherSource(valid_config)
        result = source.fetch()
        assert result is None

    @patch("src.data_sources.weather.requests.get")
    def test_fetch_429_rate_limit(self, mock_get, valid_config):
        """Test handling of rate limit."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        source = WeatherSource(valid_config)
        result = source.fetch()
        assert result is None

    @patch("src.data_sources.weather.requests.get")
    def test_fetch_500_server_error(self, mock_get, valid_config):
        """Test handling of server error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        source = WeatherSource(valid_config)
        result = source.fetch()
        assert result is None

    @patch("src.data_sources.weather.requests.get")
    def test_fetch_invalid_json(self, mock_get, valid_config):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        source = WeatherSource(valid_config)
        result = source.fetch()
        assert result is None

    @patch("src.data_sources.weather.requests.get")
    def test_fetch_timeout(self, mock_get, valid_config):
        """Test handling of request timeout."""
        mock_get.side_effect = requests.exceptions.Timeout()

        source = WeatherSource(valid_config)
        result = source.fetch()
        assert result is None

    @patch("src.data_sources.weather.requests.get")
    def test_fetch_connection_error(self, mock_get, valid_config):
        """Test handling of connection error."""
        mock_get.side_effect = requests.exceptions.ConnectionError()

        source = WeatherSource(valid_config)
        result = source.fetch()
        assert result is None

    @patch("src.data_sources.weather.requests.get")
    def test_fetch_generic_request_error(self, mock_get, valid_config):
        """Test handling of generic request error."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        source = WeatherSource(valid_config)
        result = source.fetch()
        assert result is None

    def test_fetch_no_config(self):
        """Test fetch with invalid config returns None."""
        config = WeatherConfig()  # No API key or location
        source = WeatherSource(config)
        result = source.fetch()
        assert result is None

    @patch("src.data_sources.weather.requests.get")
    def test_fetch_uses_correct_urls_and_timeout(self, mock_get, valid_config, mock_current_response, mock_forecast_response):
        """Test that fetch uses correct URLs and timeout for both API calls."""
        mock_current = Mock()
        mock_current.status_code = 200
        mock_current.json.return_value = mock_current_response

        mock_forecast = Mock()
        mock_forecast.status_code = 200
        mock_forecast.json.return_value = mock_forecast_response

        mock_get.side_effect = [mock_current, mock_forecast]

        source = WeatherSource(valid_config)
        source.fetch()

        # Should have made two API calls
        assert mock_get.call_count == 2

        # First call should be to current weather API
        first_call = mock_get.call_args_list[0]
        assert "weather" in first_call.args[0]  # Current weather endpoint
        assert first_call.kwargs["timeout"] == 10

        # Second call should be to forecast API
        second_call = mock_get.call_args_list[1]
        assert "forecast" in second_call.args[0]  # Forecast endpoint
        assert second_call.kwargs["timeout"] == 10
