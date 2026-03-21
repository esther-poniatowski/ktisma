"""Tests for the log adapter: diagnostic formatting and level prefixes."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ktisma.adapters.log import format_diagnostics, _level_prefix
from ktisma.domain.diagnostics import Diagnostic, DiagnosticLevel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def info_diagnostic() -> Diagnostic:
    return Diagnostic(
        level=DiagnosticLevel.INFO,
        component="test",
        code="T001",
        message="informational message",
    )


@pytest.fixture
def warning_diagnostic() -> Diagnostic:
    return Diagnostic(
        level=DiagnosticLevel.WARNING,
        component="test",
        code="T002",
        message="warning message",
    )


@pytest.fixture
def error_diagnostic() -> Diagnostic:
    return Diagnostic(
        level=DiagnosticLevel.ERROR,
        component="test",
        code="T003",
        message="something went wrong",
    )


@pytest.fixture
def diagnostic_with_evidence() -> Diagnostic:
    return Diagnostic(
        level=DiagnosticLevel.WARNING,
        component="test",
        code="T004",
        message="ambiguous engine",
        evidence=["found pdflatex directive", "found xelatex directive"],
    )


# ---------------------------------------------------------------------------
# _level_prefix
# ---------------------------------------------------------------------------


class TestLevelPrefix:
    """Test level prefix rendering with and without color."""

    def test_info_no_color(self):
        result = _level_prefix(DiagnosticLevel.INFO, use_color=False)
        assert result == "info:"

    def test_warning_no_color(self):
        result = _level_prefix(DiagnosticLevel.WARNING, use_color=False)
        assert result == "warning:"

    def test_error_no_color(self):
        result = _level_prefix(DiagnosticLevel.ERROR, use_color=False)
        assert result == "error:"

    @patch("ktisma.adapters.log.sys")
    def test_info_with_color_on_tty(self, mock_sys):
        mock_sys.stderr.isatty.return_value = True
        result = _level_prefix(DiagnosticLevel.INFO, use_color=True)
        assert "\033[36m" in result  # cyan
        assert "\033[0m" in result   # reset
        assert "info" in result

    @patch("ktisma.adapters.log.sys")
    def test_warning_with_color_on_tty(self, mock_sys):
        mock_sys.stderr.isatty.return_value = True
        result = _level_prefix(DiagnosticLevel.WARNING, use_color=True)
        assert "\033[33m" in result  # yellow
        assert "warning" in result

    @patch("ktisma.adapters.log.sys")
    def test_error_with_color_on_tty(self, mock_sys):
        mock_sys.stderr.isatty.return_value = True
        result = _level_prefix(DiagnosticLevel.ERROR, use_color=True)
        assert "\033[31m" in result  # red
        assert "error" in result

    @patch("ktisma.adapters.log.sys")
    def test_color_disabled_when_not_tty(self, mock_sys):
        """Even with use_color=True, no ANSI codes when stderr is not a TTY."""
        mock_sys.stderr.isatty.return_value = False
        result = _level_prefix(DiagnosticLevel.INFO, use_color=True)
        assert "\033[" not in result
        assert result == "info:"


# ---------------------------------------------------------------------------
# format_diagnostics
# ---------------------------------------------------------------------------


class TestFormatDiagnostics:
    """Test human-readable diagnostic formatting."""

    def test_empty_list(self):
        assert format_diagnostics([], use_color=False) == ""

    def test_single_info(self, info_diagnostic):
        result = format_diagnostics([info_diagnostic], use_color=False)
        assert "info:" in result
        assert "[T001]" in result
        assert "informational message" in result

    def test_single_warning(self, warning_diagnostic):
        result = format_diagnostics([warning_diagnostic], use_color=False)
        assert "warning:" in result
        assert "[T002]" in result

    def test_single_error(self, error_diagnostic):
        result = format_diagnostics([error_diagnostic], use_color=False)
        assert "error:" in result
        assert "[T003]" in result
        assert "something went wrong" in result

    def test_evidence_lines(self, diagnostic_with_evidence):
        result = format_diagnostics([diagnostic_with_evidence], use_color=False)
        assert "  - found pdflatex directive" in result
        assert "  - found xelatex directive" in result

    def test_multiple_diagnostics(self, info_diagnostic, error_diagnostic):
        result = format_diagnostics(
            [info_diagnostic, error_diagnostic], use_color=False
        )
        lines = result.split("\n")
        # At least one line per diagnostic
        assert len(lines) >= 2
        assert "info:" in lines[0]
        assert "error:" in lines[1]

    def test_format_includes_code_in_brackets(self, info_diagnostic):
        result = format_diagnostics([info_diagnostic], use_color=False)
        assert "[T001]" in result

    def test_no_evidence_when_absent(self, info_diagnostic):
        result = format_diagnostics([info_diagnostic], use_color=False)
        assert "  - " not in result
