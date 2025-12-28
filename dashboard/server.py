"""Flask web server for the Good Morning Dashboard."""

import logging
from datetime import datetime
from typing import Optional

from flask import Flask, jsonify, render_template, request

from src.briefing import build_briefing
from src.config import Config, load_config

logger = logging.getLogger(__name__)


def create_app(
    config: Optional[Config] = None,
    use_mock: bool = False,
) -> Flask:
    """
    Create and configure the Flask application.

    Args:
        config: Application configuration. Loads from file if None.
        use_mock: If True, use mock data instead of real APIs.

    Returns:
        Configured Flask application.
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # Load config if not provided
    if config is None:
        try:
            config = load_config()
        except Exception as e:
            logger.warning(f"Failed to load config: {e}, using defaults")
            from src.config import get_default_config
            config = get_default_config()

    # Store config and mock mode in app
    app.config["APP_CONFIG"] = config
    app.config["USE_MOCK"] = use_mock

    # Register routes
    register_routes(app)

    # Add CORS headers for development
    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    logger.info(
        f"Dashboard server created (mock={use_mock}, "
        f"port={config.dashboard.port})"
    )

    return app


def register_routes(app: Flask) -> None:
    """Register all routes on the Flask app."""

    @app.route("/")
    def index():
        """Serve the main dashboard page."""
        config = app.config["APP_CONFIG"]
        use_mock = app.config["USE_MOCK"]

        # Get briefing data for template
        briefing = build_briefing(config=config, use_mock=use_mock)

        return render_template(
            "index.html",
            briefing=briefing,
            config=config,
            refresh_interval=config.dashboard.refresh_interval_seconds * 1000,
        )

    @app.route("/api/briefing")
    def api_briefing():
        """
        Get current briefing data as JSON.

        Query parameters:
            mock: If "true", use mock data regardless of app setting

        Returns:
            JSON object with briefing data
        """
        config = app.config["APP_CONFIG"]

        # Check for mock query parameter
        use_mock = app.config["USE_MOCK"]
        if request.args.get("mock", "").lower() == "true":
            use_mock = True

        try:
            briefing = build_briefing(config=config, use_mock=use_mock)
            return jsonify(briefing.to_dict())
        except Exception as e:
            logger.error(f"Failed to build briefing: {e}")
            return jsonify({
                "error": "Failed to build briefing",
                "message": str(e),
            }), 500

    @app.route("/api/health")
    def api_health():
        """
        Health check endpoint.

        Returns:
            JSON with status and timestamp
        """
        config = app.config["APP_CONFIG"]

        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "mock_mode": app.config["USE_MOCK"],
            "recipient": config.recipient_name,
            "theme": config.dashboard.theme,
        })

    @app.route("/api/config")
    def api_config():
        """
        Get display configuration for frontend.

        Returns:
            JSON with theme and refresh settings
        """
        config = app.config["APP_CONFIG"]

        return jsonify({
            "theme": config.dashboard.theme,
            "refresh_interval_seconds": config.dashboard.refresh_interval_seconds,
            "recipient_name": config.recipient_name,
        })


def run_server(
    config: Optional[Config] = None,
    use_mock: bool = False,
    debug: bool = False,
) -> None:
    """
    Run the Flask development server.

    Args:
        config: Application configuration
        use_mock: Use mock data instead of real APIs
        debug: Enable Flask debug mode
    """
    if config is None:
        config = load_config()

    app = create_app(config=config, use_mock=use_mock)

    port = config.dashboard.port
    logger.info(f"Starting dashboard server on http://localhost:{port}")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
    )


if __name__ == "__main__":
    # Run with mock data for testing
    import sys
    from src.logging_config import setup_logging

    setup_logging()

    use_mock = "--mock" in sys.argv
    debug = "--debug" in sys.argv

    run_server(use_mock=use_mock, debug=debug)
