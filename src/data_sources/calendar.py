"""Google Calendar data source for the Good Morning Dashboard."""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from ..config import CalendarConfig
from ..models import Appointment

logger = logging.getLogger(__name__)

# Google API scopes needed
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def format_time_12hour(dt: datetime) -> str:
    """
    Format a datetime to 12-hour time string.

    Args:
        dt: Datetime to format

    Returns:
        Time string like "2:30 PM" or "9:00 AM"
    """
    hour = dt.hour
    minute = dt.minute

    if hour == 0:
        hour_12 = 12
        am_pm = "AM"
    elif hour < 12:
        hour_12 = hour
        am_pm = "AM"
    elif hour == 12:
        hour_12 = 12
        am_pm = "PM"
    else:
        hour_12 = hour - 12
        am_pm = "PM"

    return f"{hour_12}:{minute:02d} {am_pm}"


def format_prep_time(dt: datetime) -> str:
    """
    Format a datetime for prep reminder (just the time, no AM/PM).

    Args:
        dt: Datetime to format

    Returns:
        Time string like "1:30" for use in "around 1:30"
    """
    hour = dt.hour
    minute = dt.minute

    if hour == 0:
        hour_12 = 12
    elif hour > 12:
        hour_12 = hour - 12
    else:
        hour_12 = hour if hour != 0 else 12

    if minute == 0:
        return str(hour_12)
    else:
        return f"{hour_12}:{minute:02d}"


def calculate_prep_reminder(
    event_time: datetime,
    prep_minutes: int,
    caregiver_name: str,
) -> Optional[str]:
    """
    Calculate prep reminder text for an appointment.

    Args:
        event_time: When the appointment starts
        prep_minutes: Minutes before to remind
        caregiver_name: Name of caregiver to include

    Returns:
        Reminder string like "Sarah will help you get ready around 1:30"
        or None if prep_minutes is 0
    """
    if prep_minutes <= 0:
        return None

    prep_time = event_time - timedelta(minutes=prep_minutes)
    prep_time_str = format_prep_time(prep_time)

    return f"{caregiver_name} will help you get ready around {prep_time_str}"


def parse_event_datetime(
    event: dict,
    timezone: str,
) -> tuple[Optional[datetime], bool]:
    """
    Parse event start time from Google Calendar API response.

    Args:
        event: Event dict from Google Calendar API
        timezone: Target timezone for parsing

    Returns:
        Tuple of (datetime or None, is_all_day)
    """
    start = event.get("start", {})
    tz = ZoneInfo(timezone)

    # Check for timed event (has dateTime)
    if "dateTime" in start:
        dt_str = start["dateTime"]
        # Parse ISO format with timezone
        try:
            # Handle various ISO formats
            if "Z" in dt_str:
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(dt_str)
            # Convert to target timezone
            return (dt.astimezone(tz), False)
        except ValueError as e:
            logger.warning(f"Failed to parse event time '{dt_str}': {e}")
            return (None, False)

    # Check for all-day event (has date only)
    if "date" in start:
        date_str = start["date"]
        try:
            # Parse date-only format (YYYY-MM-DD)
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            dt = dt.replace(tzinfo=tz)
            return (dt, True)
        except ValueError as e:
            logger.warning(f"Failed to parse event date '{date_str}': {e}")
            return (None, True)

    return (None, False)


def parse_event(
    event: dict,
    timezone: str,
    caregiver_name: str,
    prep_minutes: int,
) -> Optional[Appointment]:
    """
    Parse a Google Calendar event into an Appointment.

    Args:
        event: Event dict from Google Calendar API
        timezone: Target timezone
        caregiver_name: Name for prep reminders
        prep_minutes: Minutes before for prep reminder

    Returns:
        Appointment object or None if parsing fails
    """
    # Get event title
    title = event.get("summary", "Untitled event")

    # Get event description/details
    details = event.get("description")

    # Parse start time
    start_dt, is_all_day = parse_event_datetime(event, timezone)

    if start_dt is None and not is_all_day:
        logger.warning(f"Skipping event with no parseable time: {title}")
        return None

    # Format time string
    if is_all_day:
        time_str = "All day"
        prep_reminder = None
        start_datetime = start_dt
    else:
        time_str = format_time_12hour(start_dt)
        prep_reminder = calculate_prep_reminder(start_dt, prep_minutes, caregiver_name)
        start_datetime = start_dt

    return Appointment(
        time=time_str,
        title=title,
        details=details,
        prep_reminder=prep_reminder,
        start_datetime=start_datetime,
    )


def get_credentials(config: CalendarConfig):
    """
    Get or refresh Google API credentials.

    Args:
        config: Calendar configuration with file paths

    Returns:
        Credentials object or None if auth fails
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        logger.error(
            "Google API libraries not installed. "
            "Run: pip install google-api-python-client google-auth-oauthlib"
        )
        return None

    creds = None
    token_path = Path(config.token_file)
    creds_path = Path(config.credentials_file)

    # Load existing token if available
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception as e:
            logger.warning(f"Failed to load token file: {e}")
            creds = None

    # If no valid credentials, need to authenticate
    if creds is None or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.debug("Refreshed expired credentials")
            except Exception as e:
                logger.warning(f"Failed to refresh credentials: {e}")
                creds = None

        if creds is None:
            # Need to do full OAuth flow
            if not creds_path.exists():
                logger.warning(
                    f"Credentials file not found: {creds_path}. "
                    "Download from Google Cloud Console."
                )
                return None

            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(creds_path), SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Successfully authenticated with Google Calendar")
            except Exception as e:
                logger.error(f"OAuth flow failed: {e}")
                return None

        # Save credentials for next run
        if creds:
            try:
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
                logger.debug(f"Saved credentials to {token_path}")
            except Exception as e:
                logger.warning(f"Failed to save token: {e}")

    return creds


class CalendarSource:
    """
    Fetches appointments from Google Calendar.

    This class handles OAuth authentication and retrieves today's
    events from the configured calendar.
    """

    def __init__(
        self,
        config: CalendarConfig,
        timezone: str,
        caregiver_name: str,
        prep_minutes: int,
    ):
        """
        Initialize the CalendarSource.

        Args:
            config: Calendar configuration with OAuth file paths
            timezone: IANA timezone for date filtering
            caregiver_name: Name to use in prep reminders
            prep_minutes: Minutes before appointment for prep reminder
        """
        self.config = config
        self.timezone = timezone
        self.caregiver_name = caregiver_name
        self.prep_minutes = prep_minutes
        self._tz = ZoneInfo(timezone)

    def _get_today_range(self, now: Optional[datetime] = None) -> tuple[str, str]:
        """
        Get ISO format time range for today.

        Args:
            now: Optional current time (for testing)

        Returns:
            Tuple of (start_of_day_iso, end_of_day_iso)
        """
        if now is None:
            now = datetime.now(self._tz)

        # Start of today
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        # End of today (start of tomorrow)
        end = start + timedelta(days=1)

        return (start.isoformat(), end.isoformat())

    def fetch_today(self, now: Optional[datetime] = None) -> list[Appointment]:
        """
        Fetch today's appointments from Google Calendar.

        Args:
            now: Optional current time (for testing)

        Returns:
            List of Appointment objects, sorted by time.
            Returns empty list on any error.
        """
        # Get credentials
        creds = get_credentials(self.config)
        if creds is None:
            return []

        try:
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError
        except ImportError:
            logger.error("Google API client not installed")
            return []

        try:
            # Build the service
            service = build("calendar", "v3", credentials=creds)

            # Get time range for today
            time_min, time_max = self._get_today_range(now)

            # Fetch events
            events_result = (
                service.events()
                .list(
                    calendarId=self.config.calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])
            logger.debug(f"Fetched {len(events)} events from calendar")

            # Parse events into appointments
            appointments = []
            for event in events:
                apt = parse_event(
                    event,
                    self.timezone,
                    self.caregiver_name,
                    self.prep_minutes,
                )
                if apt is not None:
                    appointments.append(apt)

            # Sort by start time (all-day events first, then by time)
            appointments.sort(
                key=lambda a: (
                    a.start_datetime is not None,
                    a.start_datetime or datetime.min.replace(tzinfo=self._tz),
                )
            )

            return appointments

        except HttpError as e:
            logger.warning(f"Calendar API error: {e}")
            return []
        except Exception as e:
            logger.warning(f"Failed to fetch calendar events: {e}")
            return []
