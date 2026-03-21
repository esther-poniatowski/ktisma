"""Tests for ktisma.domain.diagnostics — Diagnostic construction and serialization."""

from __future__ import annotations

import pytest

from ktisma.domain.diagnostics import Diagnostic, DiagnosticLevel


# ---------------------------------------------------------------------------
# DiagnosticLevel basics
# ---------------------------------------------------------------------------


class TestDiagnosticLevel:
    def test_info_value(self) -> None:
        assert DiagnosticLevel.INFO.value == "info"

    def test_warning_value(self) -> None:
        assert DiagnosticLevel.WARNING.value == "warning"

    def test_error_value(self) -> None:
        assert DiagnosticLevel.ERROR.value == "error"

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("info", DiagnosticLevel.INFO),
            ("warning", DiagnosticLevel.WARNING),
            ("error", DiagnosticLevel.ERROR),
        ],
    )
    def test_from_value(self, raw: str, expected: DiagnosticLevel) -> None:
        assert DiagnosticLevel(raw) is expected

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            DiagnosticLevel("fatal")


# ---------------------------------------------------------------------------
# Diagnostic construction
# ---------------------------------------------------------------------------


class TestDiagnosticConstruction:
    def test_required_fields(self) -> None:
        d = Diagnostic(
            level=DiagnosticLevel.ERROR,
            component="config",
            code="missing-key",
            message="A required key is missing.",
        )
        assert d.level is DiagnosticLevel.ERROR
        assert d.component == "config"
        assert d.code == "missing-key"
        assert d.message == "A required key is missing."
        assert d.evidence is None

    def test_with_evidence(self) -> None:
        evidence = ["line 10: \\RequireXeTeX", "line 42: \\directlua"]
        d = Diagnostic(
            level=DiagnosticLevel.WARNING,
            component="engine",
            code="conflicting-markers",
            message="Conflicting markers.",
            evidence=evidence,
        )
        assert d.evidence == evidence

    def test_frozen(self) -> None:
        d = Diagnostic(
            level=DiagnosticLevel.INFO,
            component="routing",
            code="fallback",
            message="Fallback routing used.",
        )
        with pytest.raises(AttributeError):
            d.message = "changed"  # type: ignore[misc]

    def test_evidence_defaults_to_none(self) -> None:
        d = Diagnostic(
            level=DiagnosticLevel.INFO,
            component="test",
            code="t",
            message="m",
        )
        assert d.evidence is None


# ---------------------------------------------------------------------------
# to_dict serialization
# ---------------------------------------------------------------------------


class TestDiagnosticToDict:
    def test_without_evidence(self) -> None:
        d = Diagnostic(
            level=DiagnosticLevel.ERROR,
            component="config",
            code="unknown-key",
            message="Unrecognized key 'foo'.",
        )
        result = d.to_dict()
        assert result == {
            "level": "error",
            "component": "config",
            "code": "unknown-key",
            "message": "Unrecognized key 'foo'.",
        }
        # evidence key should not be present when None
        assert "evidence" not in result

    def test_with_evidence(self) -> None:
        evidence = ["fontspec package detected in preamble"]
        d = Diagnostic(
            level=DiagnosticLevel.WARNING,
            component="engine",
            code="ambiguous-engine",
            message="Ambiguous markers.",
            evidence=evidence,
        )
        result = d.to_dict()
        assert result == {
            "level": "warning",
            "component": "engine",
            "code": "ambiguous-engine",
            "message": "Ambiguous markers.",
            "evidence": ["fontspec package detected in preamble"],
        }

    def test_with_empty_evidence_list(self) -> None:
        d = Diagnostic(
            level=DiagnosticLevel.INFO,
            component="routing",
            code="info",
            message="Info.",
            evidence=[],
        )
        result = d.to_dict()
        # Empty list is truthy for "is not None", so evidence key IS present
        assert "evidence" in result
        assert result["evidence"] == []

    @pytest.mark.parametrize(
        "level",
        [DiagnosticLevel.INFO, DiagnosticLevel.WARNING, DiagnosticLevel.ERROR],
    )
    def test_level_serialized_as_value_string(self, level: DiagnosticLevel) -> None:
        d = Diagnostic(
            level=level,
            component="test",
            code="code",
            message="msg",
        )
        assert d.to_dict()["level"] == level.value
