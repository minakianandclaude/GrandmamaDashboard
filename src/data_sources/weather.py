"""Weather data source - placeholder for Phase 3."""

from typing import Optional

from ..config import WeatherConfig
from ..models import WeatherInfo


class WeatherSource:
    """Fetches weather data from OpenWeatherMap API."""

    def __init__(self, config: WeatherConfig):
        self.config = config

    def fetch(self) -> Optional[WeatherInfo]:
        """Fetch current weather. Implemented in Phase 3."""
        raise NotImplementedError("WeatherSource will be implemented in Phase 3")
