"""Weather data source for the Good Morning Dashboard."""

import logging
from typing import Optional

import requests

from ..config import WeatherConfig
from ..models import WeatherInfo

logger = logging.getLogger(__name__)

# OpenWeatherMap API endpoint
OPENWEATHERMAP_API_URL = "https://api.openweathermap.org/data/2.5/weather"

# Request timeout in seconds
REQUEST_TIMEOUT = 10


def get_temperature_description(temp_f: int) -> str:
    """
    Get a practical, human-friendly description for a temperature.

    Args:
        temp_f: Temperature in Fahrenheit

    Returns:
        Description like "a bit chilly", "pleasant", etc.
    """
    if temp_f < 32:
        return "quite cold"
    elif temp_f < 46:
        return "cold"
    elif temp_f < 56:
        return "a bit chilly"
    elif temp_f < 66:
        return "cool"
    elif temp_f < 76:
        return "pleasant"
    elif temp_f < 86:
        return "warm"
    elif temp_f < 96:
        return "quite warm"
    else:
        return "very hot"


def simplify_condition(condition: str) -> str:
    """
    Simplify OpenWeatherMap condition descriptions to simple terms.

    Args:
        condition: Raw condition string from API (e.g., "scattered clouds")

    Returns:
        Simplified condition (e.g., "partly cloudy")
    """
    condition_lower = condition.lower()

    # Clear conditions
    if "clear" in condition_lower:
        return "clear"

    # Cloudy conditions (order matters - check more specific first)
    if "few clouds" in condition_lower or "scattered clouds" in condition_lower:
        return "partly cloudy"
    if "broken clouds" in condition_lower or "overcast" in condition_lower:
        return "cloudy"
    if "cloud" in condition_lower:
        return "cloudy"

    # Precipitation
    if "thunderstorm" in condition_lower or "storm" in condition_lower:
        return "stormy"
    if "snow" in condition_lower or "sleet" in condition_lower:
        return "snowy"
    if "rain" in condition_lower or "drizzle" in condition_lower or "shower" in condition_lower:
        return "rainy"

    # Visibility conditions
    if "mist" in condition_lower or "fog" in condition_lower or "haze" in condition_lower:
        return "foggy"
    if "smoke" in condition_lower or "dust" in condition_lower or "sand" in condition_lower:
        return "hazy"

    # Fallback - return original but cleaned up
    return condition_lower


def parse_weather_response(data: dict) -> Optional[WeatherInfo]:
    """
    Parse OpenWeatherMap API response into WeatherInfo.

    Args:
        data: JSON response from API

    Returns:
        WeatherInfo object or None if parsing fails
    """
    try:
        # Extract temperature (already in Fahrenheit if units=imperial)
        temp_f = int(round(data["main"]["temp"]))

        # Extract condition from weather array
        weather_list = data.get("weather", [])
        if weather_list:
            raw_condition = weather_list[0].get("description", "unknown")
            icon_code = weather_list[0].get("icon")
        else:
            raw_condition = "unknown"
            icon_code = None

        # Simplify condition
        conditions = simplify_condition(raw_condition)

        # Get practical description
        description = get_temperature_description(temp_f)

        return WeatherInfo(
            temperature_f=temp_f,
            conditions=conditions,
            description=description,
            icon_code=icon_code,
        )

    except (KeyError, TypeError, ValueError) as e:
        logger.warning(f"Failed to parse weather response: {e}")
        return None


class WeatherSource:
    """
    Fetches weather data from OpenWeatherMap API.

    This class handles API communication and translates raw weather data
    into human-friendly descriptions suitable for elderly users.
    """

    def __init__(self, config: WeatherConfig):
        """
        Initialize the WeatherSource.

        Args:
            config: WeatherConfig with API key and location settings
        """
        self.config = config

    def _build_params(self) -> Optional[dict]:
        """
        Build API request parameters from config.

        Returns:
            Dict of parameters or None if config is invalid
        """
        if not self.config.api_key:
            logger.warning("No OpenWeatherMap API key configured")
            return None

        params = {
            "appid": self.config.api_key,
            "units": self.config.units,
        }

        # Prefer lat/lon if available, otherwise use city
        if self.config.lat is not None and self.config.lon is not None:
            params["lat"] = self.config.lat
            params["lon"] = self.config.lon
        elif self.config.city:
            params["q"] = self.config.city
        else:
            logger.warning("No location configured for weather")
            return None

        return params

    def fetch(self) -> Optional[WeatherInfo]:
        """
        Fetch current weather from OpenWeatherMap API.

        Returns:
            WeatherInfo object with current conditions, or None if fetch fails.
            Failures are logged but do not raise exceptions.
        """
        params = self._build_params()
        if params is None:
            return None

        try:
            response = requests.get(
                OPENWEATHERMAP_API_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )

            # Check for HTTP errors
            if response.status_code == 401:
                logger.warning("Invalid OpenWeatherMap API key")
                return None
            elif response.status_code == 404:
                logger.warning(f"Location not found: {self.config.city or f'{self.config.lat},{self.config.lon}'}")
                return None
            elif response.status_code == 429:
                logger.warning("OpenWeatherMap API rate limit exceeded")
                return None
            elif response.status_code != 200:
                logger.warning(f"Weather API returned status {response.status_code}")
                return None

            # Parse JSON response
            try:
                data = response.json()
            except ValueError as e:
                logger.warning(f"Invalid JSON from weather API: {e}")
                return None

            # Parse into WeatherInfo
            weather = parse_weather_response(data)
            if weather:
                logger.debug(f"Weather fetched: {weather.temperature_f}°F, {weather.conditions}")

            return weather

        except requests.exceptions.Timeout:
            logger.warning("Weather API request timed out")
            return None
        except requests.exceptions.ConnectionError:
            logger.warning("Could not connect to weather API")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Weather API request failed: {e}")
            return None
