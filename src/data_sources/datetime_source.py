"""Date and time data source - placeholder for Phase 2."""

from ..models import DateInfo


class DateTimeSource:
    """Provides current date and time information."""

    def __init__(self, timezone: str = "America/New_York"):
        self.timezone = timezone

    def get_current(self) -> DateInfo:
        """Get current date/time info. Implemented in Phase 2."""
        raise NotImplementedError("DateTimeSource will be implemented in Phase 2")
