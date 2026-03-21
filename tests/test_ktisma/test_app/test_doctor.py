"""Tests for ktisma.app.doctor – prerequisite checking."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

from ktisma.app.doctor import DoctorResult, execute_doctor
from ktisma.app.protocols import PrerequisiteCheck
from ktisma.domain.config import ConfigLayer
from ktisma.domain.diagnostics import DiagnosticLevel
from ktisma.domain.exit_codes import ExitCode


# ===========================================================================
# Fake implementations
# ===========================================================================


class FakeConfigLoader:
    """Returns pre-configured config layers."""

    def __init__(self, layers: Optional[list[ConfigLayer]] = None) -> None:
        self._layers = layers if layers is not None else []

    def load_layers(self, workspace_root: Path, source_dir: Path) -> list[ConfigLayer]:
        return list(self._layers)


class FakePrerequisiteProbe:
    """Returns controlled results for each check method."""

    def __init__(
        self,
        *,
        latexmk: Optional[PrerequisiteCheck] = None,
        python: Optional[PrerequisiteCheck] = None,
        toml: Optional[PrerequisiteCheck] = None,
        engines: Optional[dict[str, PrerequisiteCheck]] = None,
    ) -> None:
        self._latexmk = latexmk or PrerequisiteCheck(
            name="latexmk", available=True, version="4.80", message=""
        )
        self._python = python or PrerequisiteCheck(
            name="python", available=True, version="3.13.0", message=""
        )
        self._toml = toml or PrerequisiteCheck(
            name="toml", available=True, version=None, message=""
        )
        self._engines = engines or {}

    def check_latexmk(self) -> PrerequisiteCheck:
        return self._latexmk

    def check_engine(self, engine: str) -> PrerequisiteCheck:
        if engine in self._engines:
            return self._engines[engine]
        return PrerequisiteCheck(
            name=engine, available=True, version="1.0", message=""
        )

    def check_python_version(self) -> PrerequisiteCheck:
        return self._python

    def check_toml_support(self) -> PrerequisiteCheck:
        return self._toml


# ===========================================================================
# Helper
# ===========================================================================


def _diag_codes(result: DoctorResult) -> list[str]:
    return [d.code for d in result.diagnostics]


def _diag_levels(result: DoctorResult) -> list[DiagnosticLevel]:
    return [d.level for d in result.diagnostics]


# ===========================================================================
# All checks pass
# ===========================================================================


class TestAllPass:
    def test_all_pass_returns_success(self) -> None:
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=FakePrerequisiteProbe(),
        )
        assert result.exit_code == ExitCode.SUCCESS

    def test_all_pass_no_error_diagnostics(self) -> None:
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=FakePrerequisiteProbe(),
        )
        error_diags = [d for d in result.diagnostics if d.level == DiagnosticLevel.ERROR]
        assert len(error_diags) == 0

    def test_all_pass_checks_populated(self) -> None:
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=FakePrerequisiteProbe(),
        )
        # Should have at least latexmk, python, toml checks + engine checks
        assert len(result.checks) >= 3

    def test_all_pass_includes_engine_checks(self) -> None:
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=FakePrerequisiteProbe(),
        )
        check_names = [c.name for c in result.checks]
        # Without a config, the doctor checks default engines: pdflatex, lualatex
        assert any("latex" in n.lower() for n in check_names)


# ===========================================================================
# Missing latexmk
# ===========================================================================


class TestMissingLatexmk:
    def test_missing_latexmk_returns_failure(self) -> None:
        probe = FakePrerequisiteProbe(
            latexmk=PrerequisiteCheck(
                name="latexmk",
                available=False,
                message="latexmk not found on PATH",
            )
        )
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=probe,
        )
        assert result.exit_code == ExitCode.PREREQUISITE_FAILURE

    def test_missing_latexmk_diagnostic(self) -> None:
        probe = FakePrerequisiteProbe(
            latexmk=PrerequisiteCheck(
                name="latexmk",
                available=False,
                message="latexmk not found on PATH",
            )
        )
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=probe,
        )
        assert "missing-latexmk" in _diag_codes(result)

    def test_missing_latexmk_message_included(self) -> None:
        probe = FakePrerequisiteProbe(
            latexmk=PrerequisiteCheck(
                name="latexmk",
                available=False,
                message="latexmk not found on PATH",
            )
        )
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=probe,
        )
        messages = [d.message for d in result.diagnostics]
        assert any("latexmk" in m.lower() for m in messages)


# ===========================================================================
# Missing Python version
# ===========================================================================


class TestPythonVersion:
    def test_bad_python_version_returns_failure(self) -> None:
        probe = FakePrerequisiteProbe(
            python=PrerequisiteCheck(
                name="python",
                available=False,
                version="3.8.0",
                message="Python 3.10+ required",
            )
        )
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=probe,
        )
        assert result.exit_code == ExitCode.PREREQUISITE_FAILURE

    def test_bad_python_version_diagnostic(self) -> None:
        probe = FakePrerequisiteProbe(
            python=PrerequisiteCheck(
                name="python",
                available=False,
                version="3.8.0",
                message="Python 3.10+ required",
            )
        )
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=probe,
        )
        assert "python-version" in _diag_codes(result)


# ===========================================================================
# Missing TOML support
# ===========================================================================


class TestTomlSupport:
    def test_missing_toml_returns_failure(self) -> None:
        probe = FakePrerequisiteProbe(
            toml=PrerequisiteCheck(
                name="toml",
                available=False,
                message="No TOML library available",
            )
        )
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=probe,
        )
        assert result.exit_code == ExitCode.PREREQUISITE_FAILURE

    def test_missing_toml_diagnostic(self) -> None:
        probe = FakePrerequisiteProbe(
            toml=PrerequisiteCheck(
                name="toml",
                available=False,
                message="No TOML library available",
            )
        )
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=probe,
        )
        assert "missing-toml" in _diag_codes(result)


# ===========================================================================
# Missing engine
# ===========================================================================


class TestMissingEngine:
    def test_missing_engine_returns_failure(self) -> None:
        probe = FakePrerequisiteProbe(
            engines={
                "pdflatex": PrerequisiteCheck(
                    name="pdflatex",
                    available=False,
                    message="pdflatex not found",
                ),
                "lualatex": PrerequisiteCheck(
                    name="lualatex",
                    available=True,
                    version="1.0",
                    message="",
                ),
            }
        )
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=probe,
        )
        assert result.exit_code == ExitCode.PREREQUISITE_FAILURE

    def test_missing_engine_diagnostic(self) -> None:
        probe = FakePrerequisiteProbe(
            engines={
                "pdflatex": PrerequisiteCheck(
                    name="pdflatex",
                    available=False,
                    message="pdflatex not found",
                ),
                "lualatex": PrerequisiteCheck(
                    name="lualatex",
                    available=True,
                    version="1.0",
                    message="",
                ),
            }
        )
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=probe,
        )
        assert "missing-engine" in _diag_codes(result)


# ===========================================================================
# Multiple failures
# ===========================================================================


class TestMultipleFailures:
    def test_multiple_failures_all_reported(self) -> None:
        probe = FakePrerequisiteProbe(
            latexmk=PrerequisiteCheck(
                name="latexmk", available=False, message="not found"
            ),
            python=PrerequisiteCheck(
                name="python", available=False, version="3.8", message="too old"
            ),
            toml=PrerequisiteCheck(
                name="toml", available=False, message="missing"
            ),
        )
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=probe,
        )
        assert result.exit_code == ExitCode.PREREQUISITE_FAILURE
        codes = _diag_codes(result)
        assert "missing-latexmk" in codes
        assert "python-version" in codes
        assert "missing-toml" in codes

    def test_multiple_failures_checks_count(self) -> None:
        """Even with failures, all checks are still run and recorded."""
        probe = FakePrerequisiteProbe(
            latexmk=PrerequisiteCheck(
                name="latexmk", available=False, message="not found"
            ),
            toml=PrerequisiteCheck(
                name="toml", available=False, message="missing"
            ),
        )
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=probe,
        )
        # latexmk, python, toml + at least 2 default engine checks
        assert len(result.checks) >= 5


# ===========================================================================
# Workspace root config validation
# ===========================================================================


class TestConfigValidation:
    def test_valid_config_produces_info_diagnostic(self, tmp_path: Path) -> None:
        (tmp_path / ".ktisma.toml").write_text("schema_version = 1\n")
        config_layer = ConfigLayer(
            data={"schema_version": 1},
            source=tmp_path,
            label=str(tmp_path / ".ktisma.toml"),
        )
        result = execute_doctor(
            workspace_root=tmp_path,
            config_loader=FakeConfigLoader(layers=[config_layer]),
            probe=FakePrerequisiteProbe(),
        )
        assert result.exit_code == ExitCode.SUCCESS
        assert "config-valid" in _diag_codes(result)

    def test_no_workspace_root_skips_config_check(self) -> None:
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=FakePrerequisiteProbe(),
        )
        assert result.exit_code == ExitCode.SUCCESS
        # Should not have config-valid or config-load-failed
        assert "config-load-failed" not in _diag_codes(result)

    def test_invalid_config_returns_config_error(self, tmp_path: Path) -> None:
        config_layer = ConfigLayer(
            data={"build": {"cleanup": "bogus"}},
            source=tmp_path,
            label="invalid",
        )
        result = execute_doctor(
            workspace_root=tmp_path,
            config_loader=FakeConfigLoader(layers=[config_layer]),
            probe=FakePrerequisiteProbe(),
        )
        assert result.exit_code == ExitCode.CONFIG_ERROR
        assert "invalid-cleanup-policy" in _diag_codes(result)


# ===========================================================================
# Engine checks from config
# ===========================================================================


class TestEngineChecksFromConfig:
    def test_configured_engines_are_checked(self, tmp_path: Path) -> None:
        """When config specifies engines, those specific engines are checked."""
        config_layer = ConfigLayer(
            data={
                "schema_version": 1,
                "engines": {"default": "xelatex", "modern_default": "lualatex"},
            },
            source=tmp_path,
            label="test",
        )
        engines_checked: list[str] = []

        class TrackingProbe(FakePrerequisiteProbe):
            def check_engine(self, engine: str) -> PrerequisiteCheck:
                engines_checked.append(engine)
                return PrerequisiteCheck(
                    name=engine, available=True, version="1.0", message=""
                )

        result = execute_doctor(
            workspace_root=tmp_path,
            config_loader=FakeConfigLoader(layers=[config_layer]),
            probe=TrackingProbe(),
        )
        assert result.exit_code == ExitCode.SUCCESS
        # Should check xelatex and lualatex (the configured engines)
        assert "xelatex" in engines_checked
        assert "lualatex" in engines_checked

    def test_default_engines_checked_without_config(self) -> None:
        """Without config, default engines (pdflatex, lualatex) are checked."""
        engines_checked: list[str] = []

        class TrackingProbe(FakePrerequisiteProbe):
            def check_engine(self, engine: str) -> PrerequisiteCheck:
                engines_checked.append(engine)
                return PrerequisiteCheck(
                    name=engine, available=True, version="1.0", message=""
                )

        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=TrackingProbe(),
        )
        assert result.exit_code == ExitCode.SUCCESS
        assert "pdflatex" in engines_checked
        assert "lualatex" in engines_checked


# ===========================================================================
# DoctorResult structure
# ===========================================================================


class TestDoctorResultStructure:
    def test_result_is_frozen_dataclass(self) -> None:
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=FakePrerequisiteProbe(),
        )
        with pytest.raises(AttributeError):
            result.exit_code = ExitCode.INTERNAL_ERROR  # type: ignore[misc]

    def test_checks_are_prerequisite_check_instances(self) -> None:
        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=FakePrerequisiteProbe(),
        )
        for check in result.checks:
            assert isinstance(check, PrerequisiteCheck)

    def test_diagnostics_are_diagnostic_instances(self) -> None:
        from ktisma.domain.diagnostics import Diagnostic

        result = execute_doctor(
            workspace_root=None,
            config_loader=FakeConfigLoader(),
            probe=FakePrerequisiteProbe(),
        )
        for diag in result.diagnostics:
            assert isinstance(diag, Diagnostic)
