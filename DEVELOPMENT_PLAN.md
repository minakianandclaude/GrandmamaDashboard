# Good Morning Dashboard - Development Plan

## Project Overview

A Python application with two output modes for elderly care companions:

1. **Visual Dashboard**: A full-screen web-based display designed for TV viewing with large, readable text and a calming aesthetic
2. **Spoken Script**: A natural language script for TTS (text-to-speech)

The system aggregates data from multiple sources (time, weather, calendar) and presents information in both formats.

---

## Implementation Status Summary

| Phase | Description | Status | Tests |
|-------|-------------|--------|-------|
| 1 | Project Structure & Core Data Models | ✅ Complete | 43 |
| 2 | Date/Time Source | ✅ Complete | 51 |
| 3 | Weather Data Source | ✅ Complete | 51 |
| 4 | Google Calendar Data Source | ✅ Complete | 40 |
| 5 | Briefing Assembly & Mock Data | ✅ Complete | 26 |
| 6 | Dashboard Backend (API Server) | ✅ Complete | 38 |
| 7 | Dashboard Frontend (Visual UI) | ✅ Complete | - |
| 8 | CLI Integration | ✅ Complete | 29 |
| 9 | Spoken Script Generator | 🔶 Partial | - |
| 10 | Documentation & Polish | 🔶 In Progress | - |
| **Total** | | | **278** |

---

## Phase 1: Project Structure & Core Data Models ✅

### Goal
Establish the foundational project structure, configuration system, and core data models that all other components will use.

### Implementation
- Create project directory structure with clear separation of concerns
- Define `Briefing` dataclass with nested dataclasses for date, weather, and appointments
- Implement configuration loading from YAML file with environment variable overrides
- Set up logging infrastructure

### Directory Structure
```
GrandmamaDashboard/
├── src/
│   ├── __init__.py
│   ├── config.py              # Configuration loading
│   ├── models.py              # Dataclasses for Briefing, Weather, Appointment
│   ├── data_sources/
│   │   ├── __init__.py
│   │   ├── datetime_source.py
│   │   ├── weather.py
│   │   └── calendar.py
│   ├── briefing.py            # Briefing assembly logic
│   ├── script_generator.py    # Spoken script (Phase 9)
│   └── cli.py
├── dashboard/
│   ├── server.py              # Flask server
│   ├── static/
│   │   ├── css/
│   │   │   └── dashboard.css
│   │   └── js/
│   │       └── dashboard.js
│   └── templates/
│       └── index.html
├── config.yaml
├── requirements.txt
└── README.md
```

### Alternatives Considered
| Approach | Why Not Used |
|----------|--------------|
| Pydantic models | Adds dependency; stdlib dataclasses sufficient for this scope |
| Environment-only config | YAML is more readable for caregivers who may need to edit settings |
| JSON config | YAML supports comments, better for documenting config options |

### Testing
- Unit test config loading with missing/partial values
- Verify dataclass serialization to dict/JSON
- Test environment variable override precedence

### Status: ✅ COMPLETE
- 43 tests passing
- All core infrastructure in place

---

## Phase 2: Date/Time Source ✅

### Goal
Create a reliable date/time module that produces conversational date strings with proper ordinal suffixes and time-of-day descriptions.

### Implementation
- `DateTimeSource` class with `get_current()` method returning `DateInfo`
- Handle timezone via `zoneinfo` (Python 3.9+ stdlib)
- Ordinal suffix logic (1st, 2nd, 3rd, 4th, etc.)
- Time-of-day descriptions: "in the morning", "in the afternoon", "in the evening"

### Key Functions
```python
def get_ordinal_suffix(day: int) -> str:
    """Return 'st', 'nd', 'rd', or 'th' for the given day number."""

def get_time_of_day_description(hour: int, minute: int) -> str:
    """Return '7:15 in the morning', '2:30 in the afternoon', etc."""

class DateTimeSource:
    def __init__(self, timezone: str = "America/New_York"):
        ...

    def get_current(self) -> DateInfo:
        """Get current date/time formatted for the briefing."""
```

### Time-of-Day Boundaries
| Time Range | Description |
|------------|-------------|
| 12:00 AM - 11:59 AM | "in the morning" |
| 12:00 PM - 4:59 PM | "in the afternoon" |
| 5:00 PM - 8:59 PM | "in the evening" |
| 9:00 PM - 11:59 PM | "at night" |

### Alternatives Considered
| Approach | Why Not Used |
|----------|--------------|
| `pytz` library | `zoneinfo` is now stdlib (3.9+), no external dependency needed |
| `arrow` or `pendulum` | Over-engineered for simple formatting; stdlib sufficient |
| 24-hour time format | Less natural for spoken script targeting elderly users |

### Testing
- Test ordinal suffixes (1st, 2nd, 3rd, 11th, 12th, 13th, 21st, 22nd, 23rd)
- Test time-of-day boundaries (morning/afternoon/evening cutoffs)
- Test with various timezones
- Mock `datetime.now()` for deterministic tests

### Status: ✅ COMPLETE
- 51 tests passing

---

## Phase 3: Weather Data Source ✅

### Goal
Fetch current weather from OpenWeatherMap API and translate conditions into practical, human-friendly descriptions.

### Implementation
- `WeatherSource` class with `fetch()` method
- Use `requests` for API calls
- Map temperature ranges to descriptions ("a bit chilly", "quite warm", etc.)
- Graceful failure: return `None` if API fails, log warning
- Include weather icon code for dashboard display

### API Integration
- **Current Weather Endpoint**: `api.openweathermap.org/data/2.5/weather`
- **Forecast Endpoint**: `api.openweathermap.org/data/2.5/forecast`
- Parameters: lat/lon or city name, units=imperial, appid from env

### Temperature Descriptions
| Temperature (°F) | Description |
|------------------|-------------|
| < 32 | "quite cold" |
| 32-45 | "cold" |
| 46-55 | "a bit chilly" |
| 56-65 | "cool" |
| 66-75 | "pleasant" |
| 76-85 | "warm" |
| 86-95 | "quite warm" |
| > 95 | "very hot" |

### Alternatives Considered
| Approach | Why Not Used |
|----------|--------------|
| Multiple weather APIs with fallback | Over-engineering for MVP; single source with graceful failure is sufficient |
| Caching layer | Simple in-memory cache sufficient; Redis overkill |
| Storing raw API response | Extract only needed fields to keep Briefing clean |

### Testing
- Mock API responses for various conditions (sunny, rain, snow)
- Test temperature-to-description mapping at boundary values
- Test graceful failure when API is unreachable
- Test with missing API key

### Status: ✅ COMPLETE (Enhanced)
- 51 tests passing
- **Enhancements beyond original plan:**
  - Dual API calls: Current Weather API (actual temp) + Forecast API (high/low, forecast)
  - 3-day forecast with daily high/low and conditions
  - Weather caching to `~/.grandmama_dashboard/weather_cache.json` for API failure fallback
  - `ForecastDay` model for multi-day forecast data

---

## Phase 4: Google Calendar Data Source ✅

### Goal
Fetch today's appointments from Google Calendar using OAuth 2.0, with support for prep time reminders.

### Implementation
- `CalendarSource` class using `google-api-python-client`
- OAuth flow with token caching (credentials.json → token.json)
- Filter events to today's date in configured timezone
- Calculate prep reminder times based on config offset
- Associate caregiver name with prep reminders
- Return empty list (not error) when no appointments

### OAuth Flow
1. Check for existing `token.json`
2. If missing/expired, use `credentials.json` to initiate flow
3. Open browser for user consent (first-time only)
4. Cache token for future runs

### Alternatives Considered
| Approach | Why Not Used |
|----------|--------------|
| Service account | Requires domain-wide delegation setup; OAuth simpler for personal calendars |
| CalDAV protocol | More complex; Google's API is well-documented and maintained |
| iCal file parsing | Not real-time; misses last-minute changes |

### Testing
- Mock Google API responses
- Test timezone handling for all-day vs. timed events
- Test prep reminder calculation
- Test empty calendar scenario
- Test with `--mock` flag for no-credential testing

### Status: ✅ COMPLETE
- 40 tests passing
- OAuth flow working with browser-based authorization
- Prep reminders generated automatically based on `prep_reminder_minutes` config

---

## Phase 5: Briefing Assembly & Mock Data ✅

### Goal
Create the orchestration layer that assembles data from all sources into a complete Briefing object, with mock data support.

### Implementation
- `BriefingBuilder` class that coordinates data sources
- `MockDataProvider` for testing without credentials
- Graceful degradation: partial briefing if some sources fail
- JSON serialization for API endpoint

### Alternatives Considered
| Approach | Why Not Used |
|----------|--------------|
| Async data fetching | Adds complexity; sequential fetching fast enough for 2-3 sources |
| Dependency injection framework | Overkill; simple constructor injection sufficient |

### Testing
- End-to-end test with mock data
- Test partial failure scenarios
- Verify JSON output matches expected schema

### Status: ✅ COMPLETE
- 26 tests passing

---

## Phase 6: Dashboard Backend (API Server) ✅

### Goal
Create a lightweight web server that serves the dashboard UI and provides a JSON API for briefing data.

### Implementation
- Flask application with two routes:
  - `GET /` - serves the dashboard HTML
  - `GET /api/briefing` - returns current briefing as JSON
- Auto-refresh endpoint for live updates
- `--mock` flag support for demo mode
- CORS headers for development

### Server Routes
```
GET /                  # Dashboard HTML page
GET /api/briefing      # JSON briefing data
GET /api/health        # Health check
GET /api/config        # Display configuration
```

### Alternatives Considered
| Approach | Why Not Used |
|----------|--------------|
| FastAPI | Flask simpler for this scope; async not needed |
| Django | Too heavyweight for single-page dashboard |
| Static file generation | Live updates require server; cron + static files less responsive |
| WebSockets | Polling every 60s sufficient; WebSockets add complexity |

### Testing
- Test API endpoints return valid JSON
- Test mock mode serves fake data
- Test error responses for failed data sources

### Status: ✅ COMPLETE
- 38 tests passing
- Flask app with `/`, `/api/briefing`, `/api/health`, `/api/config` endpoints
- CORS headers for development
- Mock mode support via `--mock` flag

---

## Phase 7: Dashboard Frontend (Visual UI) ✅

### Goal
Create a beautiful, TV-optimized dashboard interface with large readable text, calming colors, and clear visual hierarchy.

### Design Principles
- **Large text**: Minimum 32px body, 72px+ for key info (time, temp)
- **High contrast**: Dark background with light text, or vice versa
- **Simple layout**: Grid-based, no scrolling required
- **Calming aesthetic**: Soft colors, gentle animations
- **Glanceable**: Key info visible from across the room

### Implementation
- Single-page HTML with CSS Grid layout
- Vanilla JavaScript for data fetching and updates
- CSS custom properties for theming
- Weather icons (emoji or simple SVG)
- Auto-refresh every 60 seconds
- Smooth transitions when data updates

### Dashboard Layout
```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│              Good Morning, Eleanor                      │
│                                                         │
│    ┌─────────────────┐    ┌─────────────────────────┐  │
│    │                 │    │  52°F     │  Sat  ☀ 55° │  │
│    │   7:15 AM       │    │  ☁️ Cloudy │  Sun  🌧 48° │  │
│    │   Tuesday       │    │  H:58 L:45│  Mon  ⛅ 52° │  │
│    │   January 14th  │    │           │             │  │
│    └─────────────────┘    └─────────────────────────┘  │
│                                                         │
│    ┌───────────────────────────────────────────────┐   │
│    │  Today's Schedule                              │   │
│    │                                                │   │
│    │  2:30 PM  Doctor's Appointment                 │   │
│    │           Sarah will help you get ready at 1:30│   │
│    │                                                │   │
│    └───────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Theme Options
| Theme | Background | Text | Accent | Best For |
|-------|------------|------|--------|----------|
| **Calm** (default) | Soft navy `#1a1a2e` | Warm white `#f5f5f5` | Soft gold `#e8c547` | Low-light rooms |
| **Bright** | Warm cream `#faf8f5` | Dark gray `#2d2d2d` | Teal `#2a9d8f` | Well-lit rooms |
| **High Contrast** | Pure black `#000` | Pure white `#fff` | Yellow `#ffdd00` | Vision impairment |

### Alternatives Considered
| Approach | Why Not Used |
|----------|--------------|
| React/Vue/Svelte | Overkill for single static page; vanilla JS simpler, no build step |
| Server-side rendering | Client-side fetch allows smooth updates without page reload |
| Tailwind CSS | Adds build complexity; custom CSS more maintainable for small project |
| Pre-built dashboard framework (Grafana, etc.) | Not designed for this use case; custom UI better fits elderly care needs |
| Electron app | Browser-based is simpler; works on any device with browser |

### Testing
- Visual testing across screen sizes (TV resolutions: 1080p, 4K)
- Test with missing data sections (no weather, no appointments)
- Test auto-refresh functionality
- Accessibility testing (contrast ratios, font sizes)

### Status: ✅ COMPLETE (Enhanced)
- Full CSS implementation with three themes (calm, bright, high_contrast)
- Responsive grid layout optimized for TV displays
- Weather icons via emoji mapping
- Vanilla JavaScript for API data fetching and DOM updates
- Auto-refresh every 60 seconds (configurable)
- Smooth fade animations on data updates
- Loading spinner and error states
- noscript fallback for meta refresh
- **Enhancements beyond original plan:**
  - Weather tile redesigned with 3-day forecast display
  - Today's weather on left (50%), 3-day forecast stacked on right (50%)
  - High/low temperatures displayed for today
  - AM/PM time display fixes for all time periods

---

## Phase 8: CLI Integration ✅

### Goal
Provide command-line interface for running the dashboard server and generating output.

### Implementation
- `python -m src.cli dashboard` - start dashboard server
- `python -m src.cli briefing` - print JSON briefing to stdout
- `python -m src.cli script` - print spoken script (Phase 9)
- Global `--mock` flag for all commands
- `--port` option for dashboard server

### CLI Interface
```bash
# Start dashboard server
python -m src.cli dashboard              # Start on default port 8080
python -m src.cli dashboard --port 3000  # Custom port
python -m src.cli dashboard --mock       # Use mock data

# Output briefing data
python -m src.cli briefing               # Print JSON
python -m src.cli briefing --mock        # With mock data

# Spoken script
python -m src.cli script                 # Print spoken script
python -m src.cli script --mock          # With mock data
```

### Alternatives Considered
| Approach | Why Not Used |
|----------|--------------|
| `click` library | `argparse` is stdlib; fewer dependencies for simple CLI |
| Separate entry points | Single CLI with subcommands is more discoverable |

### Testing
- Test each subcommand
- Test flag combinations
- Test error handling and exit codes

### Status: ✅ COMPLETE
- Full CLI with `dashboard`, `briefing`, and `script` commands
- `--mock` flag on each command for testing without APIs
- `--port` and `--debug` flags for dashboard command
- `--config` and `--verbose` global options
- Basic script generator (placeholder for Phase 9 improvements)
- 29 tests for CLI functionality

---

## Phase 9: Spoken Script Generator 🔶

### Goal
Transform the structured Briefing into a warm, natural spoken script suitable for TTS.

### Implementation
- `generate_script(briefing: Briefing) -> str`
- Template-based generation with conditional sections
- Proper pluralization ("one appointment" vs "two appointments")
- Time formatting for speech ("2:30 this afternoon" not "14:30")
- Skip sections gracefully when data is missing

### Script Structure
1. Greeting with name
2. Day orientation (day of week, date, time)
3. Weather (if available) with practical framing
4. Appointments (if any) with prep reminders
5. Closing prompt

### Example Output
```
Good morning, Eleanor.
It's Tuesday, January 14th. It's 7:15 in the morning.
It's 45 degrees and cloudy outside—a bit chilly today.
You have one appointment today. At 2:30 this afternoon, you have a doctor's appointment. Sarah will help you get ready around 1:30.
Let me know if you need anything.
```

### Alternatives Considered
| Approach | Why Not Used |
|----------|--------------|
| Jinja2 templates | Overkill for single template; f-strings and conditionals suffice |
| LLM-generated scripts | Adds latency, cost, and unpredictability; deterministic output preferred |

### Testing
- Test each section independently
- Test with missing weather data
- Test with 0, 1, and multiple appointments
- Verify warm, unhurried tone in output

### Status: 🔶 PARTIAL
- Basic script generation implemented in CLI
- **TODO:**
  - Add high/low temperatures to spoken script
  - Add 3-day forecast summary to spoken script (optional)
  - Improve pluralization and natural language flow
  - Add unit tests for script generator

---

## Phase 10: Documentation & Polish 🔶

### Goal
Finalize the project with comprehensive documentation and example configurations.

### Implementation
- README with setup instructions, usage examples
- Example config.yaml with documented options
- requirements.txt with pinned versions
- Screenshots of dashboard
- Setup guide for OAuth credentials

### Status: 🔶 IN PROGRESS
- ✅ README with comprehensive setup instructions
- ✅ API setup guides (OpenWeatherMap, Google Calendar)
- ✅ CLI usage documentation
- ✅ Configuration reference with environment variables
- ✅ Data files documentation (weather cache location)
- ✅ Example JSON output with forecast data
- **TODO:**
  - Add screenshots of dashboard
  - Create CLAUDE.md with project context for AI assistants
  - Final review and polish

---

## Dependency Summary

```
# requirements.txt
flask>=3.0.0
google-api-python-client>=2.100.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.1.0
requests>=2.28.0
pyyaml>=6.0
pytest>=7.0.0
pytest-cov>=4.0.0
```

---

## Mock Data Strategy

The `--mock` flag will provide:
- Fixed date: current system time (or configurable)
- Fake weather: 52°F, partly cloudy
- Sample appointments: 1-2 events with realistic titles
- Allows full dashboard testing without any API credentials

---

## Recent Enhancements (Beyond Original Plan)

### Weather System Improvements
1. **Dual API Architecture**: Separate calls to Current Weather and Forecast APIs for accurate current temperature + forecast data
2. **3-Day Forecast**: Added `ForecastDay` model and UI display for upcoming days
3. **Weather Caching**: Automatic caching to `~/.grandmama_dashboard/weather_cache.json` with fallback on API failure
4. **Enhanced Weather Tile**: Split layout with today's weather (left) and 3-day forecast (right)

### UI/UX Fixes
1. **Time Display**: Fixed AM/PM display for all time periods (morning, afternoon, evening, night)
2. **Temperature Spacing**: Added proper spacing between temperature number and °F unit
3. **Removed Time Period Badge**: Cleaned up "in the morning" redundant display
