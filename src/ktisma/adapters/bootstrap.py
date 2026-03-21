from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..app.build import execute_build, BuildResult
from ..app.clean import execute_clean, CleanResult
from ..app.doctor import execute_doctor, DoctorResult
from ..app.inspect import inspect_engine, inspect_route
from ..app.batch import execute_batch, BatchResult
from ..app.variants import execute_variants, VariantsResult
from ..domain.context import BuildRequest, SourceContext
from ..domain.engine import EngineDecision
from ..domain.routing import RouteDecision
from ..infra.config_loader import TomlConfigLoader
from ..infra.latexmk import LatexmkRunner
from ..infra.locks import FileLockManager
from ..infra.materialize import FileMaterializer
from ..infra.prerequisites import SystemPrerequisiteProbe
from ..infra.source_reader import FileSourceReader
from ..infra.workspace import FileWorkspaceOps, resolve_workspace_root


@dataclass
class Services:
    """Wired infrastructure implementations.

    All wiring of concrete infrastructure into application use-cases
    happens here in the composition root.
    """
    config_loader: TomlConfigLoader
    source_reader: FileSourceReader
    lock_manager: FileLockManager
    backend_runner: LatexmkRunner
    materializer: FileMaterializer
    probe: SystemPrerequisiteProbe
    workspace_ops: FileWorkspaceOps


def create_services() -> Services:
    """Construct concrete infrastructure implementations."""
    return Services(
        config_loader=TomlConfigLoader(),
        source_reader=FileSourceReader(),
        lock_manager=FileLockManager(),
        backend_runner=LatexmkRunner(),
        materializer=FileMaterializer(),
        probe=SystemPrerequisiteProbe(),
        workspace_ops=FileWorkspaceOps(),
    )


def build(
    source_file: Path,
    request: BuildRequest,
    workspace_root: Optional[Path] = None,
    adapter_workspace_root: Optional[Path] = None,
) -> BuildResult:
    """Composition root entry for the build use-case."""
    services = create_services()
    ctx = _make_context(source_file, workspace_root, adapter_workspace_root)
    return execute_build(
        ctx=ctx,
        request=request,
        config_loader=services.config_loader,
        source_reader=services.source_reader,
        lock_manager=services.lock_manager,
        backend_runner=services.backend_runner,
        materializer=services.materializer,
        prerequisite_probe=services.probe,
        workspace_ops=services.workspace_ops,
    )


def inspect_engine_cmd(
    source_file: Path,
    request: BuildRequest,
    workspace_root: Optional[Path] = None,
    adapter_workspace_root: Optional[Path] = None,
) -> EngineDecision:
    """Composition root entry for inspect engine."""
    services = create_services()
    ctx = _make_context(source_file, workspace_root, adapter_workspace_root)
    return inspect_engine(ctx, request, services.config_loader, services.source_reader)


def inspect_route_cmd(
    source_file: Path,
    request: BuildRequest,
    workspace_root: Optional[Path] = None,
    adapter_workspace_root: Optional[Path] = None,
) -> RouteDecision:
    """Composition root entry for inspect route."""
    services = create_services()
    ctx = _make_context(source_file, workspace_root, adapter_workspace_root)
    return inspect_route(ctx, request, services.config_loader, services.source_reader)


def clean(
    target: Path,
    workspace_root: Optional[Path] = None,
) -> CleanResult:
    """Composition root entry for the clean use-case."""
    services = create_services()
    return execute_clean(target, workspace_root, services.config_loader, services.workspace_ops)


def doctor(
    workspace_root: Optional[Path] = None,
) -> DoctorResult:
    """Composition root entry for the doctor use-case."""
    services = create_services()
    return execute_doctor(workspace_root, services.config_loader, services.probe)


def batch(
    source_dir: Path,
    request: BuildRequest,
    workspace_root: Optional[Path] = None,
) -> BatchResult:
    """Composition root entry for the batch use-case."""
    services = create_services()
    ws = workspace_root or resolve_workspace_root(source_dir=source_dir)
    return execute_batch(
        source_dir=source_dir,
        workspace_root=ws,
        request=request,
        config_loader=services.config_loader,
        source_reader=services.source_reader,
        lock_manager=services.lock_manager,
        backend_runner=services.backend_runner,
        materializer=services.materializer,
        prerequisite_probe=services.probe,
        workspace_ops=services.workspace_ops,
    )


def variants(
    source_file: Path,
    request: BuildRequest,
    workspace_root: Optional[Path] = None,
    adapter_workspace_root: Optional[Path] = None,
) -> VariantsResult:
    """Composition root entry for the variants use-case."""
    services = create_services()
    ctx = _make_context(source_file, workspace_root, adapter_workspace_root)
    return execute_variants(
        ctx=ctx,
        request=request,
        config_loader=services.config_loader,
        source_reader=services.source_reader,
        lock_manager=services.lock_manager,
        backend_runner=services.backend_runner,
        materializer=services.materializer,
        prerequisite_probe=services.probe,
        workspace_ops=services.workspace_ops,
    )


def _make_context(
    source_file: Path,
    cli_workspace_root: Optional[Path],
    adapter_workspace_root: Optional[Path] = None,
) -> SourceContext:
    """Construct a SourceContext with resolved workspace root."""
    source_file = source_file.expanduser().resolve()
    source_dir = source_file.parent

    workspace_root = resolve_workspace_root(
        cli_workspace_root=cli_workspace_root,
        adapter_workspace_root=adapter_workspace_root,
        source_dir=source_dir,
    )

    return SourceContext(
        source_file=source_file,
        source_dir=source_dir,
        workspace_root=workspace_root,
    )
