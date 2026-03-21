from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..domain.config import (
    BUILTIN_DEFAULTS,
    ConfigLayer,
    merge_config_layers,
    resolve_config,
    validate_config,
)
from ..domain.diagnostics import Diagnostic, DiagnosticLevel
from ..domain.exit_codes import ExitCode
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
            layers = [ConfigLayer(data=dict(BUILTIN_DEFAULTS), source=None, label="built-in defaults")]
            file_layers = config_loader.load_layers(workspace_root, workspace_root)
            layers.extend(file_layers)
            merged, provenance = merge_config_layers(layers)
            schema_version = merged.get("schema_version", 1)
            config_diags = validate_config(merged, schema_version)

            for d in config_diags:
                diagnostics.append(d)
                if d.level == DiagnosticLevel.ERROR:
                    all_pass = False

            if not any(d.level == DiagnosticLevel.ERROR for d in config_diags):
                config = resolve_config(merged, provenance)
                diagnostics.append(
                    Diagnostic(
                        level=DiagnosticLevel.INFO,
                        component="doctor",
                        code="config-valid",
                        message="Configuration validates successfully.",
                    )
                )
        except Exception as exc:
            all_pass = False
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="doctor",
                    code="config-load-failed",
                    message=f"Failed to load configuration: {exc}",
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

    exit_code = ExitCode.SUCCESS if all_pass else ExitCode.PREREQUISITE_FAILURE
    return DoctorResult(exit_code=exit_code, checks=checks, diagnostics=diagnostics)
