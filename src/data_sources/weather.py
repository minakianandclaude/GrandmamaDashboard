"""Weather data source for the Good Morning Dashboard."""

import json
import logging
from collections import Counter
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import requests

from ..config import WeatherConfig
from ..models import WeatherInfo, ForecastDay

logger = logging.getLogger(__name__)

# Default cache file location
DEFAULT_CACHE_PATH = Path.home() / ".grandmama_dashboard" / "weather_cache.json"

# OpenWeatherMap API endpoints
OPENWEATHERMAP_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
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
    Also extracts forecasts for the next 3 days.

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

        # Group forecasts by date
        forecasts_by_date: dict[date, list] = {}
        for item in forecast_list:
            dt_txt = item.get("dt_txt", "")  # Format: "2025-01-14 12:00:00"
            if dt_txt:
                try:
                    forecast_dt = datetime.strptime(dt_txt, "%Y-%m-%d %H:%M:%S")
                    forecast_date = forecast_dt.date()
                    if forecast_date not in forecasts_by_date:
                        forecasts_by_date[forecast_date] = []
                    forecasts_by_date[forecast_date].append(item)
                except ValueError:
                    continue

        # Get today's forecasts
        today_forecasts = forecasts_by_date.get(target_date, [])
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

        # Build next 3 days forecast
        future_forecasts = []
        sorted_dates = sorted(forecasts_by_date.keys())
        for future_date in sorted_dates:
            if future_date <= target_date:
                continue  # Skip today and past
            if len(future_forecasts) >= 3:
                break  # Only need 3 days

            day_items = forecasts_by_date[future_date]
            day_temps = []
            day_conditions = []

            for item in day_items:
                main = item.get("main", {})
                temp = main.get("temp")
                if temp is not None:
                    day_temps.append(temp)

                weather_list = item.get("weather", [])
                if weather_list:
                    day_conditions.append(weather_list[0].get("description", ""))

            if day_temps:
                # Get abbreviated day name (Mon, Tue, etc.)
                day_name = future_date.strftime("%a")
                day_high = int(round(max(day_temps)))
                day_low = int(round(min(day_temps)))

                # Most common condition for the day
                if day_conditions:
                    simplified = [simplify_condition(c) for c in day_conditions]
                    day_condition = Counter(simplified).most_common(1)[0][0]
                else:
                    day_condition = "unknown"

                future_forecasts.append(ForecastDay(
                    day_name=day_name,
                    high_f=day_high,
                    low_f=day_low,
                    conditions=day_condition,
                ))

        return WeatherInfo(
            temperature_f=current_temp,
            conditions=most_common,
            description=description,
            icon_code=icon_code,
            high_f=high_temp,
            low_f=low_temp,
            forecast=future_forecasts,
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
    Fetches weather data from OpenWeatherMap API.

    This class handles API communication and translates raw weather data
    into human-friendly descriptions suitable for elderly users.

    Uses both the Current Weather API (for actual current temperature) and
    the Forecast API (for high/low temps and multi-day forecast).

    Caches successful responses to provide fallback data when API is unavailable.
    """

    def __init__(self, config: WeatherConfig, cache_path: Optional[Path] = None):
        """
        Initialize the WeatherSource.

        Args:
            config: WeatherConfig with API key and location settings
            cache_path: Optional path for weather cache file (defaults to ~/.grandmama_dashboard/weather_cache.json)
        """
        self.config = config
        self.cache_path = cache_path or DEFAULT_CACHE_PATH

    def _save_to_cache(self, weather: WeatherInfo) -> None:
        """Save weather data to cache file."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_data = {
                "cached_at": datetime.now().isoformat(),
                "weather": weather.to_dict(),
            }
            with open(self.cache_path, "w") as f:
                json.dump(cache_data, f)
            logger.debug(f"Weather cached to {self.cache_path}")
        except (OSError, IOError) as e:
            logger.warning(f"Failed to save weather cache: {e}")

    def _load_from_cache(self) -> Optional[WeatherInfo]:
        """Load weather data from cache file."""
        try:
            if not self.cache_path.exists():
                return None

            with open(self.cache_path) as f:
                cache_data = json.load(f)

            weather_dict = cache_data.get("weather", {})
            cached_at = cache_data.get("cached_at", "unknown")

            # Reconstruct ForecastDay objects
            forecast_list = []
            for day_dict in weather_dict.get("forecast", []):
                forecast_list.append(ForecastDay(
                    day_name=day_dict["day_name"],
                    high_f=day_dict["high_f"],
                    low_f=day_dict["low_f"],
                    conditions=day_dict["conditions"],
                ))

            weather = WeatherInfo(
                temperature_f=weather_dict["temperature_f"],
                conditions=weather_dict["conditions"],
                description=weather_dict["description"],
                icon_code=weather_dict.get("icon_code"),
                high_f=weather_dict.get("high_f"),
                low_f=weather_dict.get("low_f"),
                forecast=forecast_list,
            )

            logger.info(f"Loaded weather from cache (cached at {cached_at})")
            return weather

        except (OSError, IOError, json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to load weather cache: {e}")
            return None

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

    def _fetch_url(self, url: str, params: dict) -> Optional[dict]:
        """
        Fetch JSON data from an API endpoint.

        Args:
            url: The API endpoint URL
            params: Query parameters

        Returns:
            Parsed JSON dict or None if request fails
        """
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)

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

            return response.json()

        except ValueError as e:
            logger.warning(f"Invalid JSON from weather API: {e}")
            return None
        except requests.exceptions.Timeout:
            logger.warning("Weather API request timed out")
            return None
        except requests.exceptions.ConnectionError:
            logger.warning("Could not connect to weather API")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Weather API request failed: {e}")
            return None

    def fetch(self) -> Optional[WeatherInfo]:
        """
        Fetch weather from OpenWeatherMap APIs.

        Makes two API calls:
        1. Current Weather API - for the actual current temperature and conditions
        2. Forecast API - for today's high/low and 3-day forecast

        On success, caches the result. On failure, returns cached data if available.

        Returns:
            WeatherInfo object with current temp and forecast, or None if fetch fails
            and no cache is available. Failures are logged but do not raise exceptions.
        """
        params = self._build_params()
        if params is None:
            # No valid config - try cache as last resort
            return self._load_from_cache()

        # Fetch current weather for actual current temperature
        current_data = self._fetch_url(OPENWEATHERMAP_CURRENT_URL, params)
        if current_data is None:
            logger.info("Current weather API failed, trying cache")
            return self._load_from_cache()

        # Parse current weather
        current_weather = parse_weather_response(current_data)
        if current_weather is None:
            return self._load_from_cache()

        # Fetch forecast for high/low and multi-day forecast
        forecast_data = self._fetch_url(OPENWEATHERMAP_FORECAST_URL, params)
        if forecast_data is None:
            # Try to get forecast from cache and merge with fresh current weather
            cached = self._load_from_cache()
            if cached and cached.forecast:
                logger.info("Using cached forecast with fresh current weather")
                combined = WeatherInfo(
                    temperature_f=current_weather.temperature_f,
                    conditions=current_weather.conditions,
                    description=current_weather.description,
                    icon_code=current_weather.icon_code,
                    high_f=cached.high_f,
                    low_f=cached.low_f,
                    forecast=cached.forecast,
                )
                return combined
            # Return current weather without forecast data
            logger.info("Forecast unavailable, returning current weather only")
            return current_weather

        # Parse forecast and merge with current weather
        forecast_weather = parse_forecast_response(forecast_data)
        if forecast_weather is None:
            return current_weather

        # Combine: current temp from current API, high/low/forecast from forecast API
        combined = WeatherInfo(
            temperature_f=current_weather.temperature_f,
            conditions=current_weather.conditions,
            description=current_weather.description,
            icon_code=current_weather.icon_code,
            high_f=forecast_weather.high_f,
            low_f=forecast_weather.low_f,
            forecast=forecast_weather.forecast,
        )

        # Cache successful result
        self._save_to_cache(combined)

        logger.debug(
            f"Weather fetched: {combined.temperature_f}°F "
            f"(High: {combined.high_f}°F, Low: {combined.low_f}°F), "
            f"{combined.conditions}"
        )

        return combined
