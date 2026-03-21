from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..domain.diagnostics import Diagnostic, DiagnosticLevel
from ..domain.errors import ConfigError
from ..domain.exit_codes import ExitCode
from .configuration import load_resolved_config
from .protocols import ConfigLoader, PrerequisiteCheck, PrerequisiteProbe


@dataclass(frozen=True)
class DoctorResult:
    exit_code: ExitCode
    checks: list[PrerequisiteCheck] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


def execute_doctor(
    workspace_root: Optional[Path],
    config_loader: ConfigLoader,
    probe: PrerequisiteProbe,
) -> DoctorResult:
    """Run prerequisite checks per roadmap doctor specification.

    Verifies:
    - latexmk is on PATH
    - configured default engines are available
    - Python meets minimum version requirement
    - TOML parsing is available
    - workspace root resolution works
    - any present .ktisma.toml validates successfully
    """
    checks: list[PrerequisiteCheck] = []
    diagnostics: list[Diagnostic] = []
    all_pass = True
    config_failed = False

    # Check latexmk
    latexmk_check = probe.check_latexmk()
    checks.append(latexmk_check)
    if not latexmk_check.available:
        all_pass = False
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="doctor",
                code="missing-latexmk",
                message=latexmk_check.message or "latexmk is not available on PATH.",
            )
        )

    # Check Python version
    python_check = probe.check_python_version()
    checks.append(python_check)
    if not python_check.available:
        all_pass = False
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="doctor",
                code="python-version",
                message=python_check.message or "Python version does not meet minimum requirements.",
            )
        )

    # Check TOML support
    toml_check = probe.check_toml_support()
    checks.append(toml_check)
    if not toml_check.available:
        all_pass = False
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="doctor",
                code="missing-toml",
                message=toml_check.message or "TOML parsing library is not available.",
            )
        )

    # Load and validate config if workspace root is available
    config = None
    if workspace_root is not None:
        try:
            config, config_diags = load_resolved_config(
                workspace_root,
                workspace_root,
                config_loader,
            )
            diagnostics.extend(config_diags)
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.INFO,
                    component="doctor",
                    code="config-valid",
                    message="Configuration validates successfully.",
                )
            )
        except ConfigError as exc:
            config_failed = True
            diagnostics.extend(exc.diagnostics)
            if not exc.diagnostics:
                diagnostics.append(
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        component="doctor",
                        code="config-load-failed",
                        message=str(exc),
                    )
                )

    # Check configured engines
    engines_to_check = set()
    if config is not None:
        engines_to_check.add(config.engines.default)
        engines_to_check.add(config.engines.modern_default)
    else:
        engines_to_check.update(["pdflatex", "lualatex"])

    for engine in sorted(engines_to_check):
        engine_check = probe.check_engine(engine)
        checks.append(engine_check)
        if not engine_check.available:
            all_pass = False
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="doctor",
                    code="missing-engine",
                    message=engine_check.message or f"Engine '{engine}' is not available.",
                )
            )

    if config_failed:
        exit_code = ExitCode.CONFIG_ERROR
    else:
        exit_code = ExitCode.SUCCESS if all_pass else ExitCode.PREREQUISITE_FAILURE
    return DoctorResult(exit_code=exit_code, checks=checks, diagnostics=diagnostics)
