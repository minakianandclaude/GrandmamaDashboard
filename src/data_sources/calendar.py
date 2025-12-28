"""Google Calendar data source - placeholder for Phase 4."""

from ..config import CalendarConfig
from ..models import Appointment


class CalendarSource:
    """Fetches appointments from Google Calendar."""

    def __init__(self, config: CalendarConfig, timezone: str, caregiver_name: str, prep_minutes: int):
        self.config = config
        self.timezone = timezone
        self.caregiver_name = caregiver_name
        self.prep_minutes = prep_minutes

    def fetch_today(self) -> list[Appointment]:
        """Fetch today's appointments. Implemented in Phase 4."""
        raise NotImplementedError("CalendarSource will be implemented in Phase 4")
