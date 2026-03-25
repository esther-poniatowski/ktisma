from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..domain.build_dir import plan_build_dir
from ..domain.context import SourceContext
from ..domain.diagnostics import Diagnostic, DiagnosticLevel
from ..domain.exit_codes import ExitCode
from .configuration import load_resolved_config
from .protocols import ConfigLoader, WorkspaceOps


@dataclass(frozen=True)
class CleanResult:
    exit_code: ExitCode
    removed_dirs: list[Path] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


def execute_clean(
    target: Path,
    workspace_root: Optional[Path],
    config_loader: ConfigLoader,
    workspace_ops: WorkspaceOps,
) -> CleanResult:
    """Clean build directories for a source file or a specific build directory.

    If target is a .tex file, removes its build directory.
    If target is a directory, removes it directly (if it looks like a ktisma build dir).
    """
    diagnostics: list[Diagnostic] = []
    removed: list[Path] = []

    if target.suffix == ".tex":
        target = target.expanduser().resolve()
        if workspace_root is None:
            workspace_root = target.parent

        ctx = SourceContext(
            source_file=target,
            source_dir=target.parent,
            workspace_root=workspace_root,
        )

        config, _ = load_resolved_config(ctx.workspace_root, ctx.source_dir, config_loader)

        build_plan = plan_build_dir(ctx, config)
        build_dir = build_plan.build_dir

        if workspace_ops.path_exists(build_dir):
            try:
                workspace_ops.remove_tree(build_dir)
                removed.append(build_dir)
            except Exception as exc:
                diagnostics.append(
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        component="clean",
                        code="clean-failed",
                        message=f"Failed to remove {build_dir}: {exc}",
                    )
                )
                return CleanResult(exit_code=ExitCode.INTERNAL_ERROR, diagnostics=diagnostics)

        # Also clean variant build dirs that explicitly belong to this source.
        parent = build_dir.parent
        canonical_source = _canonical_source_identity(target)
        if workspace_ops.path_exists(parent):
            for entry in workspace_ops.list_directory(parent):
                if not workspace_ops.is_directory(entry) or entry == build_dir:
                    continue
                metadata = _read_build_metadata(entry / ".ktisma.meta.json", workspace_ops)
                if metadata.get("source") != canonical_source:
                    continue
                if metadata.get("variant") is None:
                    continue
                try:
                    workspace_ops.remove_tree(entry)
                    removed.append(entry)
                except Exception as exc:
                    diagnostics.append(
                        Diagnostic(
                            level=DiagnosticLevel.WARNING,
                            component="clean",
                            code="clean-variant-failed",
                            message=f"Failed to remove variant build dir {entry}: {exc}",
                        )
                    )

        if not removed:
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.INFO,
                    component="clean",
                    code="nothing-to-clean",
                    message=f"No build directories found for {target.name}.",
                )
            )

    elif workspace_ops.is_directory(target):
        lock_marker = target / ".ktisma.lock"
        parent_name = target.parent.name if target.parent else ""
        if workspace_ops.path_exists(lock_marker) or parent_name.startswith(".ktisma"):
            try:
                workspace_ops.remove_tree(target)
                removed.append(target)
            except Exception as exc:
                diagnostics.append(
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        component="clean",
                        code="clean-failed",
                        message=f"Failed to remove {target}: {exc}",
                    )
                )
                return CleanResult(exit_code=ExitCode.INTERNAL_ERROR, diagnostics=diagnostics)
        else:
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="clean",
                    code="not-build-dir",
                    message=f"{target} does not appear to be a ktisma build directory.",
                )
            )
            return CleanResult(exit_code=ExitCode.CONFIG_ERROR, diagnostics=diagnostics)
    else:
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="clean",
                code="invalid-target",
                message=f"Clean target must be a .tex file or a build directory: {target}",
            )
        )
        return CleanResult(exit_code=ExitCode.CONFIG_ERROR, diagnostics=diagnostics)

    return CleanResult(exit_code=ExitCode.SUCCESS, removed_dirs=removed, diagnostics=diagnostics)


def _read_build_metadata(metadata_file: Path, workspace_ops: WorkspaceOps) -> dict[str, object]:
    if not workspace_ops.path_exists(metadata_file):
        return {}
    try:
        return json.loads(workspace_ops.read_text(metadata_file))
    except Exception:
        return {}


def _canonical_source_identity(source_file: Path) -> str:
    """Return the canonical source identity used by build metadata."""
    return str(source_file.expanduser().resolve())
