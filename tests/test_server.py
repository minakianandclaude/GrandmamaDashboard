"""Tests for the Flask dashboard server."""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from dashboard.server import create_app
from src.config import Config, DashboardConfig
from src.models import Appointment, Briefing, DateInfo, WeatherInfo


@pytest.fixture
def config():
    """Create test configuration."""
    return Config(
        recipient_name="Eleanor",
        caregiver_name="Sarah",
        timezone="America/New_York",
        prep_reminder_minutes=60,
        dashboard=DashboardConfig(
            theme="calm",
            refresh_interval_seconds=60,
            port=8080,
        ),
    )


@pytest.fixture
def mock_briefing():
    """Create a mock briefing for testing."""
    return Briefing(
        generated_at=datetime(2025, 1, 14, 7, 15),
        recipient_name="Eleanor",
        caregiver_name="Sarah",
        date_info=DateInfo(
            day_of_week="Tuesday",
            full_date="January 14th",
            time_of_day="7:15 in the morning",
        ),
        weather=WeatherInfo(
            temperature_f=52,
            conditions="partly cloudy",
            description="a bit chilly",
        ),
        appointments=[
            Appointment(
                time="10:00 AM",
                title="Morning exercise",
                prep_reminder="Sarah will help you get ready around 9",
            ),
        ],
        errors=[],
    )


@pytest.fixture
def app(config):
    """Create test Flask app with mock mode enabled."""
    app = create_app(config=config, use_mock=True)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestCreateApp:
    """Tests for create_app factory function."""

    def test_create_app_with_config(self, config):
        """Test app creation with explicit config."""
        app = create_app(config=config, use_mock=False)

        assert app is not None
        assert app.config["APP_CONFIG"] == config
        assert app.config["USE_MOCK"] is False

    def test_create_app_mock_mode(self, config):
        """Test app creation in mock mode."""
        app = create_app(config=config, use_mock=True)

        assert app.config["USE_MOCK"] is True

    def test_create_app_loads_default_config(self):
        """Test app creation without explicit config."""
        with patch("dashboard.server.load_config") as mock_load:
            mock_load.return_value = Config()
            app = create_app()

            mock_load.assert_called_once()
            assert app.config["APP_CONFIG"] is not None

    def test_create_app_uses_defaults_on_load_failure(self):
        """Test app falls back to defaults if config load fails."""
        with patch("dashboard.server.load_config") as mock_load:
            mock_load.side_effect = FileNotFoundError("No config")
            app = create_app()

            # Should still create app with default config
            assert app is not None
            assert app.config["APP_CONFIG"].recipient_name == "Friend"


class TestHealthEndpoint:
    """Tests for /api/health endpoint."""

    def test_health_returns_200(self, client):
        """Test health endpoint returns 200 OK."""
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_returns_json(self, client):
        """Test health endpoint returns valid JSON."""
        response = client.get("/api/health")
        data = json.loads(response.data)

        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_includes_timestamp(self, client):
        """Test health endpoint includes timestamp."""
        response = client.get("/api/health")
        data = json.loads(response.data)

        assert "timestamp" in data
        # Should be valid ISO format
        datetime.fromisoformat(data["timestamp"])

    def test_health_includes_mock_mode(self, client):
        """Test health endpoint includes mock mode status."""
        response = client.get("/api/health")
        data = json.loads(response.data)

        assert "mock_mode" in data
        assert data["mock_mode"] is True  # Our fixture uses mock mode

    def test_health_includes_recipient(self, client):
        """Test health endpoint includes recipient name."""
        response = client.get("/api/health")
        data = json.loads(response.data)

        assert data["recipient"] == "Eleanor"

    def test_health_includes_theme(self, client):
        """Test health endpoint includes theme."""
        response = client.get("/api/health")
        data = json.loads(response.data)

        assert data["theme"] == "calm"


class TestBriefingEndpoint:
    """Tests for /api/briefing endpoint."""

    def test_briefing_returns_200(self, client):
        """Test briefing endpoint returns 200 OK."""
        response = client.get("/api/briefing")
        assert response.status_code == 200

    def test_briefing_returns_json(self, client):
        """Test briefing endpoint returns valid JSON."""
        response = client.get("/api/briefing")
        data = json.loads(response.data)

        assert isinstance(data, dict)

    def test_briefing_includes_recipient_name(self, client):
        """Test briefing includes recipient name."""
        response = client.get("/api/briefing")
        data = json.loads(response.data)

        assert data["recipient_name"] == "Eleanor"

    def test_briefing_includes_caregiver_name(self, client):
        """Test briefing includes caregiver name."""
        response = client.get("/api/briefing")
        data = json.loads(response.data)

        assert data["caregiver_name"] == "Sarah"

    def test_briefing_includes_date(self, client):
        """Test briefing includes date info."""
        response = client.get("/api/briefing")
        data = json.loads(response.data)

        assert "date" in data
        assert "day_of_week" in data["date"]
        assert "full_date" in data["date"]
        assert "time_of_day" in data["date"]

    def test_briefing_includes_weather(self, client):
        """Test briefing includes weather (mock mode)."""
        response = client.get("/api/briefing")
        data = json.loads(response.data)

        assert "weather" in data
        assert data["weather"] is not None
        assert "temperature_f" in data["weather"]
        assert "conditions" in data["weather"]

    def test_briefing_includes_appointments(self, client):
        """Test briefing includes appointments (mock mode)."""
        response = client.get("/api/briefing")
        data = json.loads(response.data)

        assert "appointments" in data
        assert isinstance(data["appointments"], list)
        assert len(data["appointments"]) > 0

    def test_briefing_mock_query_param(self, config):
        """Test mock=true query parameter forces mock mode."""
        # Create app without mock mode
        app = create_app(config=config, use_mock=False)
        app.config["TESTING"] = True
        client = app.test_client()

        # Request with mock=true
        response = client.get("/api/briefing?mock=true")
        data = json.loads(response.data)

        # Should still get weather (mock data)
        assert data["weather"] is not None

    def test_briefing_handles_errors(self, config):
        """Test briefing endpoint handles build errors gracefully."""
        app = create_app(config=config, use_mock=True)
        app.config["TESTING"] = True
        client = app.test_client()

        with patch("dashboard.server.build_briefing") as mock_build:
            mock_build.side_effect = Exception("Test error")

            response = client.get("/api/briefing")

            assert response.status_code == 500
            data = json.loads(response.data)
            assert "error" in data


class TestConfigEndpoint:
    """Tests for /api/config endpoint."""

    def test_config_returns_200(self, client):
        """Test config endpoint returns 200 OK."""
        response = client.get("/api/config")
        assert response.status_code == 200

    def test_config_includes_theme(self, client):
        """Test config endpoint includes theme."""
        response = client.get("/api/config")
        data = json.loads(response.data)

        assert data["theme"] == "calm"

    def test_config_includes_refresh_interval(self, client):
        """Test config endpoint includes refresh interval."""
        response = client.get("/api/config")
        data = json.loads(response.data)

        assert data["refresh_interval_seconds"] == 60

    def test_config_includes_recipient_name(self, client):
        """Test config endpoint includes recipient name."""
        response = client.get("/api/config")
        data = json.loads(response.data)

        assert data["recipient_name"] == "Eleanor"


class TestIndexRoute:
    """Tests for main dashboard route."""

    def test_index_returns_200(self, client):
        """Test index route returns 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_index_returns_html(self, client):
        """Test index route returns HTML content."""
        response = client.get("/")
        assert response.content_type.startswith("text/html")

    def test_index_includes_recipient_name(self, client):
        """Test index page includes recipient name."""
        response = client.get("/")
        html = response.data.decode("utf-8")

        assert "Eleanor" in html

    def test_index_includes_greeting(self, client):
        """Test index page includes greeting."""
        response = client.get("/")
        html = response.data.decode("utf-8")

        assert "Good morning" in html

    def test_index_includes_refresh_script(self, client):
        """Test index page includes auto-refresh script."""
        response = client.get("/")
        html = response.data.decode("utf-8")

        assert "setTimeout" in html
        assert "reload" in html


class TestCORSHeaders:
    """Tests for CORS headers on API responses."""

    def test_cors_allows_all_origins(self, client):
        """Test CORS allows all origins (for development)."""
        response = client.get("/api/health")

        assert response.headers.get("Access-Control-Allow-Origin") == "*"

    def test_cors_allows_get_method(self, client):
        """Test CORS allows GET method."""
        response = client.get("/api/health")

        allowed_methods = response.headers.get("Access-Control-Allow-Methods")
        assert "GET" in allowed_methods

    def test_cors_on_briefing_endpoint(self, client):
        """Test CORS headers on briefing endpoint."""
        response = client.get("/api/briefing")

        assert response.headers.get("Access-Control-Allow-Origin") == "*"


class TestIntegration:
    """Integration tests for the dashboard server."""

    def test_full_mock_workflow(self, client):
        """Test complete workflow with mock data."""
        # Get health
        health = client.get("/api/health")
        assert health.status_code == 200

        # Get briefing
        briefing = client.get("/api/briefing")
        assert briefing.status_code == 200

        briefing_data = json.loads(briefing.data)
        assert briefing_data["recipient_name"] == "Eleanor"
        assert briefing_data["weather"] is not None
        assert len(briefing_data["appointments"]) > 0

        # Get config
        config = client.get("/api/config")
        assert config.status_code == 200

        # Get index page
        index = client.get("/")
        assert index.status_code == 200
        assert b"Eleanor" in index.data

    def test_different_themes(self, config):
        """Test app works with different theme configurations."""
        for theme in ["calm", "bright", "high_contrast"]:
            config.dashboard.theme = theme
            app = create_app(config=config, use_mock=True)
            app.config["TESTING"] = True
            client = app.test_client()

            response = client.get("/api/config")
            data = json.loads(response.data)

            assert data["theme"] == theme

    def test_different_refresh_intervals(self, config):
        """Test app works with different refresh intervals."""
        for interval in [30, 60, 120]:
            config.dashboard.refresh_interval_seconds = interval
            app = create_app(config=config, use_mock=True)
            app.config["TESTING"] = True
            client = app.test_client()

            response = client.get("/api/config")
            data = json.loads(response.data)

            assert data["refresh_interval_seconds"] == interval
