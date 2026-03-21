from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..domain.build_dir import plan_build_dir
from ..domain.config import (
    BUILTIN_DEFAULTS,
    ConfigLayer,
    ResolvedConfig,
    merge_config_layers,
    resolve_config,
)
from ..domain.context import SourceContext
from ..domain.diagnostics import Diagnostic, DiagnosticLevel
from ..domain.exit_codes import ExitCode
from .protocols import ConfigLoader


@dataclass(frozen=True)
class CleanResult:
    exit_code: ExitCode
    removed_dirs: list[Path] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


def execute_clean(
    target: Path,
    workspace_root: Optional[Path],
    config_loader: ConfigLoader,
) -> CleanResult:
    """Clean build directories for a source file or a specific build directory.

    If target is a .tex file, removes its build directory.
    If target is a directory, removes it directly (if it looks like a ktisma build dir).
    """
    diagnostics: list[Diagnostic] = []
    removed: list[Path] = []

    if target.suffix == ".tex":
        if workspace_root is None:
            workspace_root = target.parent

        ctx = SourceContext(
            source_file=target,
            source_dir=target.parent,
            workspace_root=workspace_root,
        )

        layers = [ConfigLayer(data=dict(BUILTIN_DEFAULTS), source=None, label="built-in defaults")]
        file_layers = config_loader.load_layers(ctx.workspace_root, ctx.source_dir)
        layers.extend(file_layers)
        merged, provenance = merge_config_layers(layers)
        config = resolve_config(merged, provenance)

        build_plan = plan_build_dir(ctx, config)
        build_dir = build_plan.build_dir

        if build_dir.exists():
            try:
                shutil.rmtree(build_dir)
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

        # Also clean variant build dirs
        parent = build_dir.parent
        if parent.exists():
            stem = target.stem
            for entry in parent.iterdir():
                if entry.is_dir() and entry.name.startswith(f"{stem}-") and entry != build_dir:
                    try:
                        shutil.rmtree(entry)
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

    elif target.is_dir():
        lock_marker = target / ".ktisma.lock"
        parent_name = target.parent.name if target.parent else ""
        if lock_marker.exists() or parent_name.startswith(".ktisma"):
            try:
                shutil.rmtree(target)
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
