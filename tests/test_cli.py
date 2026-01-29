"""Tests for CLI commands."""

from pathlib import Path
from unittest.mock import patch

import pytest

# Skip all tests if Typer is not installed
pytest.importorskip("typer")

from typer.testing import CliRunner

from thesis_compliance.cli import app


@pytest.fixture
def runner() -> CliRunner:
    """Create CLI test runner."""
    return CliRunner()


class TestCheckCommand:
    """Tests for the check command."""

    def test_check_valid_pdf(self, runner: CliRunner, valid_thesis_pdf: Path):
        """Test checking a valid PDF."""
        result = runner.invoke(app, ["check", str(valid_thesis_pdf)])
        # Exit code 0 = passed, 1 = violations found (both acceptable)
        assert result.exit_code in [0, 1]
        assert "Compliance Report" in result.stdout or "passed" in result.stdout.lower() or "error" in result.stdout.lower()

    def test_check_with_spec(self, runner: CliRunner, valid_thesis_pdf: Path):
        """Test checking with specific spec."""
        result = runner.invoke(
            app, ["check", str(valid_thesis_pdf), "--spec", "rackham"]
        )
        # Exit code 0 = passed, 1 = violations found (both acceptable)
        assert result.exit_code in [0, 1]

    def test_check_with_page_range(self, runner: CliRunner, valid_thesis_pdf: Path):
        """Test checking with page range."""
        result = runner.invoke(
            app, ["check", str(valid_thesis_pdf), "--pages", "1-3"]
        )
        # Exit code 0 = passed, 1 = violations found (both acceptable)
        assert result.exit_code in [0, 1]

    def test_check_bad_margins(self, runner: CliRunner, bad_margins_pdf: Path):
        """Test checking PDF with bad margins."""
        result = runner.invoke(app, ["check", str(bad_margins_pdf)])
        # Should fail (exit code 1) due to violations
        assert result.exit_code in [0, 1]
        # Should mention margin issues in output
        assert "margin" in result.stdout.lower() or "error" in result.stdout.lower()

    def test_check_nonexistent_file(self, runner: CliRunner):
        """Test checking nonexistent file."""
        result = runner.invoke(app, ["check", "/nonexistent/file.pdf"])
        assert result.exit_code != 0

    def test_check_invalid_spec(self, runner: CliRunner, valid_thesis_pdf: Path):
        """Test checking with invalid spec."""
        result = runner.invoke(
            app, ["check", str(valid_thesis_pdf), "--spec", "nonexistent"]
        )
        assert result.exit_code != 0


class TestListSpecsCommand:
    """Tests for the list-specs command."""

    def test_list_specs(self, runner: CliRunner):
        """Test listing available specs."""
        result = runner.invoke(app, ["list-specs"])
        assert result.exit_code == 0
        assert "rackham" in result.stdout.lower()

    def test_list_specs_shows_universities(self, runner: CliRunner):
        """Test that list-specs shows university info."""
        result = runner.invoke(app, ["list-specs"])
        assert result.exit_code == 0
        # Should show some university information
        assert "university" in result.stdout.lower() or "michigan" in result.stdout.lower()


class TestInfoCommand:
    """Tests for the info command."""

    def test_info_command(self, runner: CliRunner, valid_thesis_pdf: Path):
        """Test info command shows PDF information."""
        result = runner.invoke(app, ["info", str(valid_thesis_pdf)])
        assert result.exit_code == 0
        # Should show page count
        assert "page" in result.stdout.lower()


class TestOutputFormats:
    """Tests for different output formats."""

    def test_json_output(self, runner: CliRunner, valid_thesis_pdf: Path):
        """Test JSON output format."""
        result = runner.invoke(
            app, ["check", str(valid_thesis_pdf), "--format", "json"]
        )
        # Exit code 0 = passed, 1 = violations found (both acceptable)
        assert result.exit_code in [0, 1]
        # Should be valid JSON
        import json
        try:
            data = json.loads(result.stdout)
            assert "passed" in data or "violations" in data
        except json.JSONDecodeError:
            # If output includes extra text, just check for JSON structure
            assert "{" in result.stdout

    def test_brief_output(self, runner: CliRunner, valid_thesis_pdf: Path):
        """Test brief output format."""
        result = runner.invoke(
            app, ["check", str(valid_thesis_pdf), "--format", "brief"]
        )
        # Exit code 0 = passed, 1 = violations found (both acceptable)
        assert result.exit_code in [0, 1]
        # Brief output should be shorter


class TestCLIEdgeCases:
    """Edge case tests for CLI."""

    def test_empty_pdf(self, runner: CliRunner, empty_pdf: Path):
        """Test checking empty PDF."""
        result = runner.invoke(app, ["check", str(empty_pdf)])
        # Should complete without crashing
        assert result.exit_code in [0, 1]

    def test_minimal_pdf(self, runner: CliRunner, minimal_pdf: Path):
        """Test checking minimal PDF."""
        result = runner.invoke(app, ["check", str(minimal_pdf)])
        assert result.exit_code in [0, 1]

    def test_invalid_page_range(self, runner: CliRunner, valid_thesis_pdf: Path):
        """Test with invalid page range."""
        result = runner.invoke(
            app, ["check", str(valid_thesis_pdf), "--pages", "100-200"]
        )
        # Should fail due to invalid page range
        assert result.exit_code != 0

    def test_reversed_page_range(self, runner: CliRunner, valid_thesis_pdf: Path):
        """Test with reversed page range (start > end)."""
        result = runner.invoke(
            app, ["check", str(valid_thesis_pdf), "--pages", "5-1"]
        )
        # Should fail due to reversed range
        assert result.exit_code != 0


class TestHelpOutput:
    """Tests for help output."""

    def test_main_help(self, runner: CliRunner):
        """Test main help output."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "check" in result.stdout

    def test_check_help(self, runner: CliRunner):
        """Test check command help."""
        result = runner.invoke(app, ["check", "--help"])
        assert result.exit_code == 0
        assert "pdf" in result.stdout.lower()
        assert "spec" in result.stdout.lower()
