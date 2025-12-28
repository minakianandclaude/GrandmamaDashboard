"""Command-line interface for the Good Morning Dashboard."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from src.briefing import build_briefing
from src.config import load_config
from src.logging_config import setup_logging


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="grandmama",
        description="Good Morning Dashboard - A personalized morning briefing system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s dashboard              Start the dashboard server
  %(prog)s dashboard --mock       Start with mock data (no API keys needed)
  %(prog)s dashboard --port 3000  Start on custom port
  %(prog)s briefing --mock        Print briefing as JSON
  %(prog)s script --mock          Print spoken script for TTS
        """,
    )

    # Global options
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        help="Path to config file (default: config.yaml)",
        metavar="FILE",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    # Subcommands
    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        description="Available commands",
        metavar="COMMAND",
    )

    # Dashboard command
    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Start the dashboard web server",
        description="Start the Flask web server to display the dashboard",
    )
    dashboard_parser.add_argument(
        "--mock",
        "-m",
        action="store_true",
        help="Use mock data instead of real APIs",
    )
    dashboard_parser.add_argument(
        "--port",
        "-p",
        type=int,
        help="Port to run the server on (default: from config or 8080)",
        metavar="PORT",
    )
    dashboard_parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable Flask debug mode (auto-reload)",
    )

    # Briefing command
    briefing_parser = subparsers.add_parser(
        "briefing",
        help="Print the current briefing as JSON",
        description="Fetch current briefing data and print as JSON",
    )
    briefing_parser.add_argument(
        "--mock",
        "-m",
        action="store_true",
        help="Use mock data instead of real APIs",
    )

    # Script command (Phase 9)
    script_parser = subparsers.add_parser(
        "script",
        help="Print the spoken script for TTS",
        description="Generate a natural language script for text-to-speech",
    )
    script_parser.add_argument(
        "--mock",
        "-m",
        action="store_true",
        help="Use mock data instead of real APIs",
    )

    return parser


def cmd_dashboard(args: argparse.Namespace) -> int:
    """Run the dashboard web server."""
    from dashboard.server import create_app

    # Load config
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Override port if specified
    if args.port:
        config.dashboard.port = args.port

    # Create and run app
    app = create_app(config=config, use_mock=args.mock)

    port = config.dashboard.port
    mode = "mock" if args.mock else "live"
    print(f"Starting Good Morning Dashboard ({mode} mode)")
    print(f"Dashboard available at: http://localhost:{port}")
    print("Press Ctrl+C to stop")
    print()

    try:
        app.run(
            host="0.0.0.0",
            port=port,
            debug=args.debug,
        )
    except KeyboardInterrupt:
        print("\nShutting down...")

    return 0


def cmd_briefing(args: argparse.Namespace) -> int:
    """Print briefing as JSON."""
    # Load config
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Build briefing
    try:
        briefing = build_briefing(config=config, use_mock=args.mock)
    except Exception as e:
        print(f"Error building briefing: {e}", file=sys.stderr)
        return 1

    # Output JSON
    print(briefing.to_json(indent=2))

    return 0


def cmd_script(args: argparse.Namespace) -> int:
    """Print spoken script for TTS."""
    # Load config
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Build briefing
    try:
        briefing = build_briefing(config=config, use_mock=args.mock)
    except Exception as e:
        print(f"Error building briefing: {e}", file=sys.stderr)
        return 1

    # Generate script (Phase 9 will add proper implementation)
    # For now, generate a basic script
    script = generate_basic_script(briefing)
    print(script)

    return 0


def generate_basic_script(briefing) -> str:
    """Generate a basic spoken script from briefing data.

    This is a placeholder implementation. Phase 9 will add
    a full ScriptGenerator class with better templating.
    """
    lines = []

    # Greeting
    if briefing.date_info:
        time_of_day = briefing.date_info.time_of_day
        if "morning" in time_of_day:
            greeting = "Good morning"
        elif "afternoon" in time_of_day:
            greeting = "Good afternoon"
        elif "evening" in time_of_day:
            greeting = "Good evening"
        else:
            greeting = "Hello"
    else:
        greeting = "Hello"

    lines.append(f"{greeting}, {briefing.recipient_name}.")

    # Date
    if briefing.date_info:
        lines.append(
            f"It's {briefing.date_info.day_of_week}, {briefing.date_info.full_date}. "
            f"It's {briefing.date_info.time_of_day}."
        )

    # Weather
    if briefing.weather:
        lines.append(
            f"It's {briefing.weather.temperature_f} degrees and "
            f"{briefing.weather.conditions} outside. "
            f"It's {briefing.weather.description} today."
        )

    # Appointments
    if briefing.appointments:
        count = len(briefing.appointments)
        if count == 1:
            lines.append("You have one appointment today.")
        else:
            lines.append(f"You have {count} appointments today.")

        for apt in briefing.appointments:
            lines.append(f"At {apt.time}, you have {apt.title}.")
            if apt.prep_reminder:
                lines.append(apt.prep_reminder + ".")
    else:
        lines.append("You have no appointments scheduled for today.")

    # Closing
    lines.append(f"Let me know if you need anything, {briefing.recipient_name}.")

    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Setup logging
    setup_logging(verbose=args.verbose if hasattr(args, 'verbose') else False)

    # No command specified
    if not args.command:
        parser.print_help()
        return 0

    # Dispatch to command handler
    if args.command == "dashboard":
        return cmd_dashboard(args)
    elif args.command == "briefing":
        return cmd_briefing(args)
    elif args.command == "script":
        return cmd_script(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
