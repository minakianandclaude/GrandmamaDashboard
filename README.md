# Good Morning Dashboard

A personalized morning briefing system for elderly care companions. Displays a calming, easy-to-read dashboard on a TV and generates spoken scripts for text-to-speech.

## Current Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Project structure, config, data models | ✅ Complete |
| 2 | Date/Time source | ✅ Complete |
| 3 | Weather source (OpenWeatherMap) | ✅ Complete |
| 4 | Calendar source (Google Calendar) | ✅ Complete |
| 5 | Briefing assembly & mock data | ✅ Complete |
| 6 | Dashboard backend (Flask API) | ✅ Complete |
| 7 | Dashboard frontend (TV UI) | ✅ Complete |
| 8 | CLI integration | ✅ Complete |
| 9 | Spoken script generator (TTS) | 🔶 Partial |
| 10 | Documentation & polish | 🔶 In Progress |

## Features

- **Visual Dashboard**: Full-screen TV display with large, readable text optimized for elderly viewing
- **3-Day Weather Forecast**: Current conditions, today's high/low, and 3-day forecast with icons
- **Weather Caching**: Retains forecast data for reliability when API is unavailable
- **Calendar Integration**: Today's appointments from Google Calendar with OAuth
- **Prep Reminders**: Configurable reminders like "Sarah will help you get ready around 1:30"
- **Spoken Script**: Natural language output for text-to-speech systems
- **Three Themes**: Calm (dark), Bright (light), and High Contrast for accessibility
- **Graceful Degradation**: Skips unavailable data sources without crashing

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd GrandmamaDashboard

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Copy and edit the example config:

```bash
cp config.yaml config.local.yaml
# Edit config.local.yaml with your settings
```

Key settings in `config.yaml`:

```yaml
# Care recipient's name (used in greetings)
recipient_name: "Eleanor"

# Caregiver's name (used in appointment prep reminders)
caregiver_name: "Sarah"

# Timezone (IANA format)
timezone: "America/New_York"

# Minutes before appointment to show prep reminder
prep_reminder_minutes: 60
```

### Running the Dashboard Server

```bash
# Start the dashboard server with mock data (no API keys needed)
python -m dashboard.server --mock

# Start in debug mode (auto-reload on code changes)
python -m dashboard.server --mock --debug
```

The dashboard will be available at `http://localhost:8080`.

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Dashboard HTML page (auto-refreshes) |
| `GET /api/briefing` | Current briefing as JSON |
| `GET /api/briefing?mock=true` | Force mock data |
| `GET /api/health` | Health check with status |
| `GET /api/config` | Display configuration |

### CLI Commands

```bash
# Start the dashboard server
python -m src.cli dashboard

# Start with mock data (no API keys needed)
python -m src.cli dashboard --mock

# Start on a custom port with debug mode
python -m src.cli dashboard --mock --port 3000 --debug

# Print briefing as JSON
python -m src.cli briefing --mock

# Print spoken script for TTS
python -m src.cli script --mock

# Use a custom config file
python -m src.cli --config /path/to/config.yaml briefing

# Enable verbose logging
python -m src.cli --verbose dashboard --mock
```

## API Setup

### When Do I Need API Keys?

You can test the dashboard with **mock data** without any API keys. Real API keys are only needed when you want live data.

| Feature | Mock Mode | Real Data |
|---------|-----------|-----------|
| Date/Time | Works | Works (no API needed) |
| Weather | Fake data | Requires OpenWeatherMap key |
| Calendar | Sample appointments | Requires Google OAuth |

### OpenWeatherMap (Weather)

1. Sign up at [OpenWeatherMap](https://openweathermap.org/api)
2. Get your free API key (free tier: 1000 calls/day)
3. Set via environment variable or config:

```bash
# Option 1: Environment variable (recommended)
export OPENWEATHERMAP_API_KEY="your-api-key-here"

# Option 2: In config.yaml
weather:
  api_key: "your-api-key-here"
  city: "New York, NY"
```

#### Weather Features

- **Current Temperature**: Real-time temperature from OpenWeatherMap Current Weather API
- **Today's High/Low**: Calculated from the day's forecast intervals
- **3-Day Forecast**: Shows upcoming days with icons and high/low temps
- **Caching**: Weather data is cached for reliability (see Data Files below)

### Google Calendar

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Google Calendar API
4. Create OAuth 2.0 credentials (Desktop application)
5. Download `credentials.json` to the project root
6. On first run, a browser will open for authorization
7. Token is cached in `token.json` for future runs

```yaml
# In config.yaml
calendar:
  credentials_file: "credentials.json"
  token_file: "token.json"
  calendar_id: "primary"  # or specific calendar ID
```

## Configuration Reference

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENWEATHERMAP_API_KEY` | Weather API key | None |
| `DASHBOARD_RECIPIENT_NAME` | Care recipient's name | "Friend" |
| `DASHBOARD_CAREGIVER_NAME` | Caregiver's name | "your caregiver" |
| `DASHBOARD_TIMEZONE` | Timezone (IANA) | "America/New_York" |
| `DASHBOARD_PREP_REMINDER_MINUTES` | Prep reminder offset | 60 |
| `GOOGLE_CREDENTIALS_FILE` | Path to credentials.json | "credentials.json" |
| `GOOGLE_TOKEN_FILE` | Path to token.json | "token.json" |

### Full Config Example

```yaml
recipient_name: "Eleanor"
caregiver_name: "Sarah"
timezone: "America/New_York"
prep_reminder_minutes: 60

weather:
  api_key: null  # Use OPENWEATHERMAP_API_KEY env var
  city: "New York, NY"
  # Or use coordinates:
  # lat: 40.7128
  # lon: -74.0060
  units: "imperial"  # or "metric"

calendar:
  credentials_file: "credentials.json"
  token_file: "token.json"
  calendar_id: "primary"

dashboard:
  theme: "calm"  # calm, bright, or high_contrast
  refresh_interval_seconds: 60
  port: 8080
```

## Data Files

The dashboard stores data files in your home directory for caching and tokens:

| File | Location | Purpose |
|------|----------|---------|
| Weather Cache | `~/.grandmama_dashboard/weather_cache.json` | Cached weather & forecast data |
| Google Token | `./token.json` (configurable) | Google Calendar OAuth token |

### Weather Cache

Weather data is automatically cached after each successful API fetch. This provides:

- **Reliability**: If the OpenWeatherMap API is temporarily unavailable, the dashboard displays cached data
- **Forecast Preservation**: The 3-day forecast remains visible even if only the current weather API fails
- **Graceful Degradation**: Fresh current temperature is combined with cached forecast when possible

The cache includes a timestamp showing when the data was last updated. To clear the cache:

```bash
rm ~/.grandmama_dashboard/weather_cache.json
```

## Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_weather.py -v
```

### Current Test Coverage

| Module | Tests |
|--------|-------|
| Config | 26 |
| Models | 17 |
| DateTime Source | 51 |
| Weather Source | 51 |
| Calendar Source | 40 |
| Briefing | 26 |
| Dashboard Server | 38 |
| CLI | 29 |
| **Total** | **278** |

### Project Structure

```
GrandmamaDashboard/
├── src/
│   ├── __init__.py
│   ├── cli.py                 # Command-line interface
│   ├── config.py              # Configuration loading
│   ├── models.py              # Data models (Briefing, DateInfo, etc.)
│   ├── logging_config.py      # Logging setup
│   ├── briefing.py            # Briefing assembly & mock data
│   └── data_sources/
│       ├── datetime_source.py # Date/time formatting
│       ├── weather.py         # OpenWeatherMap integration
│       └── calendar.py        # Google Calendar integration
├── dashboard/
│   ├── __init__.py
│   ├── server.py              # Flask API server
│   ├── static/
│   │   ├── css/
│   │   │   └── dashboard.css  # TV-optimized styling
│   │   └── js/
│   │       └── dashboard.js   # Data fetching & updates
│   └── templates/
│       └── index.html         # Dashboard template
├── tests/
│   ├── test_config.py
│   ├── test_models.py
│   ├── test_datetime_source.py
│   ├── test_weather.py
│   ├── test_calendar.py
│   ├── test_briefing.py
│   └── test_server.py
├── config.yaml                 # Example configuration
├── requirements.txt
├── DEVELOPMENT_PLAN.md         # Detailed phase planning
└── README.md
```

## Example Output

### Structured Data (JSON)

```json
{
  "generated_at": "2025-01-14T07:15:00",
  "recipient_name": "Eleanor",
  "caregiver_name": "Sarah",
  "date": {
    "day_of_week": "Tuesday",
    "full_date": "January 14th",
    "time_of_day": "7:15 in the morning"
  },
  "weather": {
    "temperature_f": 34,
    "conditions": "clear",
    "description": "cold",
    "high_f": 42,
    "low_f": 28,
    "forecast": [
      { "day_name": "Wed", "high_f": 45, "low_f": 32, "conditions": "cloudy" },
      { "day_name": "Thu", "high_f": 38, "low_f": 25, "conditions": "snowy" },
      { "day_name": "Fri", "high_f": 40, "low_f": 30, "conditions": "clear" }
    ]
  },
  "appointments": [
    {
      "time": "2:30 PM",
      "title": "Doctor's appointment",
      "prep_reminder": "Sarah will help you get ready around 1:30"
    }
  ]
}
```

### Spoken Script (TTS)

```
Good morning, Eleanor.
It's Tuesday, January 14th. It's 7:15 in the morning.
It's 45 degrees and cloudy outside—a bit chilly today.
You have one appointment today. At 2:30 this afternoon,
you have a doctor's appointment. Sarah will help you
get ready around 1:30.
Let me know if you need anything.
```

## Dashboard Themes

| Theme | Best For | Colors |
|-------|----------|--------|
| **Calm** (default) | Low-light rooms | Dark navy + warm white |
| **Bright** | Well-lit rooms | Cream + dark gray |
| **High Contrast** | Vision impairment | Black + white + yellow |

## License

MIT License - See LICENSE file for details.
