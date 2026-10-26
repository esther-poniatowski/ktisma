"""Application use case for checking retained LaTeX build logs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..domain.build_log import BuildLogEvaluation, evaluate_build_log
from ..domain.diagnostics import Diagnostic, DiagnosticLevel
from ..domain.exit_codes import ExitCode
from .protocols import WorkspaceOps


@dataclass(frozen=True)
class BuildLogReport:
    """Evaluation of one log with its path relative to the build directory."""

    path: Path
    relative_path: Path
    evaluation: BuildLogEvaluation


@dataclass(frozen=True)
class CheckLogResult:
    """Outcome of checking every selected log."""

    exit_code: ExitCode
    reports: list[BuildLogReport] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


def execute_check_log(
    source_dir: Path,
    build_dir_name: str,
    stem: str | None,
    channels: tuple[str, ...],
    workspace_ops: WorkspaceOps,
) -> CheckLogResult:
    """Find and evaluate build logs below one source directory.

    Parameters
    ----------
    source_dir
        Directory holding the configured build directory.
    build_dir_name
        Build-directory path relative to ``source_dir``.
    stem
        Optional document stem restricting the selected ``.log`` files.
    channels
        Measurement channels retained in the report.
    workspace_ops
        Filesystem operations supplied by the composition root.

    Returns
    -------
    CheckLogResult
        Selected reports, diagnostics, and the public exit status.
    """
    source_dir = source_dir.expanduser().resolve()
    if not workspace_ops.is_directory(source_dir):
        return _failure(
            f"No such document directory: {source_dir}",
            "missing-source-dir",
            ExitCode.CONFIG_ERROR,
        )

    build_root = source_dir / build_dir_name
    if not workspace_ops.is_directory(build_root):
        return _failure(
            f"No {build_dir_name} under {source_dir}; build first and retain the logs.",
            "missing-build-dir",
            ExitCode.COMPILATION_FAILURE,
        )

    pattern = f"**/{stem or '*'}.log"
    logs = workspace_ops.glob_files(build_root, pattern)
    if not logs:
        selected = f"{stem} " if stem else ""
        return _failure(
            f"No {selected}logs under {build_root}; build first.",
            "missing-log",
            ExitCode.COMPILATION_FAILURE,
        )

    reports = [
        BuildLogReport(
            path=path,
            relative_path=path.relative_to(build_root),
            evaluation=evaluate_build_log(workspace_ops.read_text(path), channels),
        )
        for path in logs
    ]
    exit_code = (
        ExitCode.SUCCESS
        if all(report.evaluation.passed for report in reports)
        else ExitCode.COMPILATION_FAILURE
    )
    return CheckLogResult(exit_code=exit_code, reports=reports)


def _failure(message: str, code: str, exit_code: ExitCode) -> CheckLogResult:
    """Return a diagnostic result for an unavailable check input."""
    return CheckLogResult(
        exit_code=exit_code,
        diagnostics=[
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="check-log",
                code=code,
                message=message,
            )
        ],
    )
