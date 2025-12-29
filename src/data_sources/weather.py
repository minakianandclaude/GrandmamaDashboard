"""Weather data source for the Good Morning Dashboard."""

import logging
from collections import Counter
from datetime import datetime, date
from typing import Optional

import requests

from ..config import WeatherConfig
from ..models import WeatherInfo

logger = logging.getLogger(__name__)

# OpenWeatherMap Forecast API endpoint
OPENWEATHERMAP_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

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


def parse_forecast_response(data: dict, target_date: Optional[date] = None) -> Optional[WeatherInfo]:
    """
    Parse OpenWeatherMap Forecast API response into WeatherInfo.

    Aggregates 3-hour forecast intervals for today into a single forecast
    with high/low temperatures and the most common weather condition.

    Args:
        data: JSON response from forecast API
        target_date: Date to filter forecasts for (default: today)

    Returns:
        WeatherInfo object or None if parsing fails
    """
    if target_date is None:
        target_date = date.today()

    try:
        forecast_list = data.get("list", [])
        if not forecast_list:
            logger.warning("No forecast data in API response")
            return None

        # Filter to only today's forecasts
        today_forecasts = []
        for item in forecast_list:
            # Parse the datetime from the forecast
            dt_txt = item.get("dt_txt", "")  # Format: "2025-01-14 12:00:00"
            if dt_txt:
                try:
                    forecast_dt = datetime.strptime(dt_txt, "%Y-%m-%d %H:%M:%S")
                    if forecast_dt.date() == target_date:
                        today_forecasts.append(item)
                except ValueError:
                    continue

        if not today_forecasts:
            # If no forecasts for today, use the first available forecast
            logger.info("No forecasts for today, using first available")
            today_forecasts = forecast_list[:1]

        # Extract temperatures from today's forecasts
        temperatures = []
        conditions_list = []
        icon_codes = []

        for item in today_forecasts:
            main = item.get("main", {})
            temp = main.get("temp")
            if temp is not None:
                temperatures.append(temp)

            weather_list = item.get("weather", [])
            if weather_list:
                conditions_list.append(weather_list[0].get("description", ""))
                icon_codes.append(weather_list[0].get("icon", ""))

        if not temperatures:
            logger.warning("No temperature data in forecast")
            return None

        # Calculate current/high/low temperatures
        current_temp = int(round(temperatures[0]))  # First forecast as "current"
        high_temp = int(round(max(temperatures)))
        low_temp = int(round(min(temperatures)))

        # Get most common condition
        if conditions_list:
            simplified_conditions = [simplify_condition(c) for c in conditions_list]
            most_common = Counter(simplified_conditions).most_common(1)[0][0]
        else:
            most_common = "unknown"

        # Get the first icon code (for current conditions)
        icon_code = icon_codes[0] if icon_codes else None

        # Get practical description based on current temp
        description = get_temperature_description(current_temp)

        return WeatherInfo(
            temperature_f=current_temp,
            conditions=most_common,
            description=description,
            icon_code=icon_code,
            high_f=high_temp,
            low_f=low_temp,
        )

    except (KeyError, TypeError, ValueError) as e:
        logger.warning(f"Failed to parse forecast response: {e}")
        return None


# Keep the old function for backward compatibility with tests
def parse_weather_response(data: dict) -> Optional[WeatherInfo]:
    """
    Parse OpenWeatherMap current weather API response into WeatherInfo.

    This is kept for backward compatibility. New code should use parse_forecast_response.

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
    Fetches weather forecast data from OpenWeatherMap API.

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
        Fetch weather forecast from OpenWeatherMap API.

        Returns:
            WeatherInfo object with today's forecast, or None if fetch fails.
            Failures are logged but do not raise exceptions.
        """
        params = self._build_params()
        if params is None:
            return None

        try:
            response = requests.get(
                OPENWEATHERMAP_FORECAST_URL,
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
            weather = parse_forecast_response(data)
            if weather:
                logger.debug(
                    f"Weather fetched: {weather.temperature_f}°F "
                    f"(High: {weather.high_f}°F, Low: {weather.low_f}°F), "
                    f"{weather.conditions}"
                )

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
