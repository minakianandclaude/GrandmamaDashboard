"""Tests for the command-line interface."""

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.cli import (
    cmd_briefing,
    cmd_script,
    create_parser,
    generate_basic_script,
    main,
)
from src.models import Appointment, Briefing, DateInfo, WeatherInfo


class TestCreateParser:
    """Tests for the argument parser."""

    def test_parser_created(self):
        """Test parser is created successfully."""
        parser = create_parser()
        assert parser is not None

    def test_parser_prog_name(self):
        """Test parser has correct program name."""
        parser = create_parser()
        assert parser.prog == "grandmama"

    def test_parser_has_config_option(self):
        """Test parser has --config option."""
        parser = create_parser()
        args = parser.parse_args(["--config", "test.yaml", "briefing"])
        assert args.config == Path("test.yaml")

    def test_parser_has_verbose_option(self):
        """Test parser has --verbose option."""
        parser = create_parser()
        args = parser.parse_args(["--verbose", "briefing"])
        assert args.verbose is True

    def test_parser_has_dashboard_command(self):
        """Test parser has dashboard subcommand."""
        parser = create_parser()
        args = parser.parse_args(["dashboard"])
        assert args.command == "dashboard"

    def test_parser_has_briefing_command(self):
        """Test parser has briefing subcommand."""
        parser = create_parser()
        args = parser.parse_args(["briefing"])
        assert args.command == "briefing"

    def test_parser_has_script_command(self):
        """Test parser has script subcommand."""
        parser = create_parser()
        args = parser.parse_args(["script"])
        assert args.command == "script"

    def test_dashboard_has_port_option(self):
        """Test dashboard command has --port option."""
        parser = create_parser()
        args = parser.parse_args(["dashboard", "--port", "3000"])
        assert args.port == 3000

    def test_dashboard_has_debug_option(self):
        """Test dashboard command has --debug option."""
        parser = create_parser()
        args = parser.parse_args(["dashboard", "--debug"])
        assert args.debug is True

    def test_dashboard_has_mock_option(self):
        """Test dashboard command has --mock option."""
        parser = create_parser()
        args = parser.parse_args(["dashboard", "--mock"])
        assert args.mock is True

    def test_briefing_has_mock_option(self):
        """Test briefing command has --mock option."""
        parser = create_parser()
        args = parser.parse_args(["briefing", "--mock"])
        assert args.mock is True

    def test_script_has_mock_option(self):
        """Test script command has --mock option."""
        parser = create_parser()
        args = parser.parse_args(["script", "--mock"])
        assert args.mock is True

    def test_short_options(self):
        """Test short option aliases work."""
        parser = create_parser()

        args = parser.parse_args(["-c", "test.yaml", "-v", "dashboard", "-m", "-p", "3000", "-d"])
        assert args.config == Path("test.yaml")
        assert args.verbose is True
        assert args.mock is True
        assert args.port == 3000
        assert args.debug is True


class TestMain:
    """Tests for the main entry point."""

    def test_no_command_shows_help(self, capsys):
        """Test running without command shows help."""
        result = main([])
        assert result == 0

        captured = capsys.readouterr()
        assert "usage:" in captured.out
        assert "commands:" in captured.out

    def test_unknown_command_fails(self):
        """Test unknown command returns error."""
        with pytest.raises(SystemExit):
            main(["unknown"])

    @patch("src.cli.build_briefing")
    @patch("src.cli.load_config")
    def test_briefing_command_success(self, mock_load_config, mock_build, capsys):
        """Test briefing command outputs JSON."""
        from datetime import datetime

        mock_load_config.return_value = MagicMock()
        mock_build.return_value = Briefing(
            generated_at=datetime(2025, 1, 14, 7, 15),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=DateInfo(
                day_of_week="Tuesday",
                full_date="January 14th",
                time_of_day="7:15 in the morning",
                hour_12=7,
                minute=15,
                am_pm="AM",
            ),
        )

        result = main(["briefing", "--mock"])
        assert result == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["recipient_name"] == "Eleanor"

    @patch("src.cli.build_briefing")
    @patch("src.cli.load_config")
    def test_script_command_success(self, mock_load_config, mock_build, capsys):
        """Test script command outputs text."""
        from datetime import datetime

        mock_load_config.return_value = MagicMock()
        mock_build.return_value = Briefing(
            generated_at=datetime(2025, 1, 14, 7, 15),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=DateInfo(
                day_of_week="Tuesday",
                full_date="January 14th",
                time_of_day="7:15 in the morning",
                hour_12=7,
                minute=15,
                am_pm="AM",
            ),
        )

        result = main(["script", "--mock"])
        assert result == 0

        captured = capsys.readouterr()
        assert "Good morning, Eleanor" in captured.out

    @patch("src.cli.load_config")
    def test_config_not_found_error(self, mock_load_config, capsys):
        """Test error when config file not found."""
        mock_load_config.side_effect = FileNotFoundError("Config not found")

        result = main(["briefing", "--mock"])
        assert result == 1

        captured = capsys.readouterr()
        assert "Error:" in captured.err


class TestGenerateBasicScript:
    """Tests for the basic script generator."""

    def test_morning_greeting(self):
        """Test morning greeting is generated."""
        from datetime import datetime

        briefing = Briefing(
            generated_at=datetime(2025, 1, 14, 7, 15),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=DateInfo(
                day_of_week="Tuesday",
                full_date="January 14th",
                time_of_day="7:15 in the morning",
                hour_12=7, minute=15, am_pm="AM",
            ),
        )

        script = generate_basic_script(briefing)
        assert "Good morning, Eleanor" in script

    def test_afternoon_greeting(self):
        """Test afternoon greeting is generated."""
        from datetime import datetime

        briefing = Briefing(
            generated_at=datetime(2025, 1, 14, 14, 30),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=DateInfo(
                day_of_week="Tuesday",
                full_date="January 14th",
                time_of_day="2:30 in the afternoon",
                hour_12=2, minute=30, am_pm="PM",
            ),
        )

        script = generate_basic_script(briefing)
        assert "Good afternoon, Eleanor" in script

    def test_evening_greeting(self):
        """Test evening greeting is generated."""
        from datetime import datetime

        briefing = Briefing(
            generated_at=datetime(2025, 1, 14, 18, 30),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=DateInfo(
                day_of_week="Tuesday",
                full_date="January 14th",
                time_of_day="6:30 in the evening",
                hour_12=6, minute=30, am_pm="PM",
            ),
        )

        script = generate_basic_script(briefing)
        assert "Good evening, Eleanor" in script

    def test_includes_date(self):
        """Test script includes date."""
        from datetime import datetime

        briefing = Briefing(
            generated_at=datetime(2025, 1, 14, 7, 15),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=DateInfo(
                day_of_week="Tuesday",
                full_date="January 14th",
                time_of_day="7:15 in the morning",
                hour_12=7, minute=15, am_pm="AM",
            ),
        )

        script = generate_basic_script(briefing)
        assert "Tuesday" in script
        assert "January 14th" in script

    def test_includes_weather(self):
        """Test script includes weather."""
        from datetime import datetime

        briefing = Briefing(
            generated_at=datetime(2025, 1, 14, 7, 15),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=DateInfo(
                day_of_week="Tuesday",
                full_date="January 14th",
                time_of_day="7:15 in the morning",
                hour_12=7, minute=15, am_pm="AM",
            ),
            weather=WeatherInfo(
                temperature_f=45,
                conditions="cloudy",
                description="a bit chilly",
            ),
        )

        script = generate_basic_script(briefing)
        assert "45 degrees" in script
        assert "cloudy" in script

    def test_includes_appointments(self):
        """Test script includes appointments."""
        from datetime import datetime

        briefing = Briefing(
            generated_at=datetime(2025, 1, 14, 7, 15),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=DateInfo(
                day_of_week="Tuesday",
                full_date="January 14th",
                time_of_day="7:15 in the morning",
                hour_12=7, minute=15, am_pm="AM",
            ),
            appointments=[
                Appointment(
                    time="2:30 PM",
                    title="Doctor's appointment",
                    prep_reminder="Sarah will help you get ready around 1:30",
                ),
            ],
        )

        script = generate_basic_script(briefing)
        assert "one appointment" in script
        assert "2:30 PM" in script
        assert "Doctor's appointment" in script
        assert "Sarah will help you get ready around 1:30" in script

    def test_no_appointments(self):
        """Test script handles no appointments."""
        from datetime import datetime

        briefing = Briefing(
            generated_at=datetime(2025, 1, 14, 7, 15),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=DateInfo(
                day_of_week="Tuesday",
                full_date="January 14th",
                time_of_day="7:15 in the morning",
                hour_12=7, minute=15, am_pm="AM",
            ),
            appointments=[],
        )

        script = generate_basic_script(briefing)
        assert "no appointments" in script

    def test_multiple_appointments(self):
        """Test script handles multiple appointments."""
        from datetime import datetime

        briefing = Briefing(
            generated_at=datetime(2025, 1, 14, 7, 15),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=DateInfo(
                day_of_week="Tuesday",
                full_date="January 14th",
                time_of_day="7:15 in the morning",
                hour_12=7, minute=15, am_pm="AM",
            ),
            appointments=[
                Appointment(time="10:00 AM", title="Exercise class"),
                Appointment(time="2:30 PM", title="Doctor's appointment"),
            ],
        )

        script = generate_basic_script(briefing)
        assert "2 appointments" in script

    def test_closing(self):
        """Test script includes closing."""
        from datetime import datetime

        briefing = Briefing(
            generated_at=datetime(2025, 1, 14, 7, 15),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=DateInfo(
                day_of_week="Tuesday",
                full_date="January 14th",
                time_of_day="7:15 in the morning",
                hour_12=7, minute=15, am_pm="AM",
            ),
        )

        script = generate_basic_script(briefing)
        assert "Let me know if you need anything" in script


class TestCLIIntegration:
    """Integration tests for CLI commands."""

    @patch("src.cli.build_briefing")
    @patch("src.cli.load_config")
    def test_briefing_output_is_valid_json(self, mock_load_config, mock_build, capsys):
        """Test briefing output can be parsed as JSON."""
        from datetime import datetime

        mock_load_config.return_value = MagicMock()
        mock_build.return_value = Briefing(
            generated_at=datetime(2025, 1, 14, 7, 15),
            recipient_name="Test",
            caregiver_name="Caregiver",
            date_info=DateInfo(
                day_of_week="Tuesday",
                full_date="January 14th",
                time_of_day="7:15 in the morning",
                hour_12=7, minute=15, am_pm="AM",
            ),
            weather=WeatherInfo(
                temperature_f=50,
                conditions="clear",
                description="pleasant",
            ),
            appointments=[
                Appointment(time="10:00 AM", title="Test"),
            ],
        )

        result = main(["briefing", "--mock"])
        assert result == 0

        captured = capsys.readouterr()
        # Should be valid JSON
        data = json.loads(captured.out)
        assert "recipient_name" in data
        assert "weather" in data
        assert "appointments" in data

    @patch("src.cli.build_briefing")
    @patch("src.cli.load_config")
    def test_script_output_is_readable(self, mock_load_config, mock_build, capsys):
        """Test script output is human-readable text."""
        from datetime import datetime

        mock_load_config.return_value = MagicMock()
        mock_build.return_value = Briefing(
            generated_at=datetime(2025, 1, 14, 7, 15),
            recipient_name="Eleanor",
            caregiver_name="Sarah",
            date_info=DateInfo(
                day_of_week="Tuesday",
                full_date="January 14th",
                time_of_day="7:15 in the morning",
                hour_12=7, minute=15, am_pm="AM",
            ),
        )

        result = main(["script", "--mock"])
        assert result == 0

        captured = capsys.readouterr()
        # Should be readable text, not JSON
        assert captured.out.startswith("Good morning")
        with pytest.raises(json.JSONDecodeError):
            json.loads(captured.out)
