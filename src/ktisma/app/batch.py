from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..domain.context import BuildRequest, SourceContext
from ..domain.diagnostics import Diagnostic, DiagnosticLevel
from ..domain.exit_codes import ExitCode
from .build import BuildResult, execute_build
from .protocols import (
    BackendRunner,
    ConfigLoader,
    LockManager,
    Materializer,
    PrerequisiteProbe,
    WorkspaceOps,
    SourceReader,
)


@dataclass(frozen=True)
class BatchResult:
    exit_code: ExitCode
    results: list[tuple[Path, BuildResult]] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


def execute_batch(
    source_dir: Path,
    workspace_root: Path,
    request: BuildRequest,
    config_loader: ConfigLoader,
    source_reader: SourceReader,
    lock_manager: LockManager,
    backend_runner: BackendRunner,
    materializer: Materializer,
    prerequisite_probe: PrerequisiteProbe,
    workspace_ops: WorkspaceOps,
) -> BatchResult:
    """Build all .tex files in a directory.

    Composes the same build use-case for each source file.
    batch --watch is unsupported in v1 and rejected explicitly.
    """
    diagnostics: list[Diagnostic] = []

    if request.watch:
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="batch",
                code="batch-watch-unsupported",
                message="batch --watch is not supported in v1.",
            )
        )
        return BatchResult(exit_code=ExitCode.CONFIG_ERROR, diagnostics=diagnostics)

    if not source_dir.is_dir():
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="batch",
                code="not-a-directory",
                message=f"{source_dir} is not a directory.",
            )
        )
        return BatchResult(exit_code=ExitCode.CONFIG_ERROR, diagnostics=diagnostics)

    tex_files = sorted(source_dir.glob("*.tex"))
    if not tex_files:
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.WARNING,
                component="batch",
                code="no-tex-files",
                message=f"No .tex files found in {source_dir}.",
            )
        )
        return BatchResult(exit_code=ExitCode.SUCCESS, diagnostics=diagnostics)

    results: list[tuple[Path, BuildResult]] = []
    any_failure = False

    for tex_file in tex_files:
        ctx = SourceContext(
            source_file=tex_file,
            source_dir=tex_file.parent,
            workspace_root=workspace_root,
        )
        try:
            result = execute_build(
                ctx=ctx,
                request=request,
                config_loader=config_loader,
                source_reader=source_reader,
                lock_manager=lock_manager,
                backend_runner=backend_runner,
                materializer=materializer,
                prerequisite_probe=prerequisite_probe,
                workspace_ops=workspace_ops,
            )
            results.append((tex_file, result))
            if result.exit_code != ExitCode.SUCCESS:
                any_failure = True
        except Exception as exc:
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="batch",
                    code="build-exception",
                    message=f"Build failed for {tex_file.name}: {exc}",
                )
            )
            any_failure = True

    exit_code = ExitCode.COMPILATION_FAILURE if any_failure else ExitCode.SUCCESS
    return BatchResult(exit_code=exit_code, results=results, diagnostics=diagnostics)
