from __future__ import annotations

import copy
from pathlib import Path
from typing import Optional

from ..domain.config import (
    BUILTIN_DEFAULTS,
    ConfigLayer,
    ResolvedConfig,
    merge_config_layers,
    resolve_config,
    validate_config,
)
from ..domain.diagnostics import Diagnostic, DiagnosticLevel
from ..domain.errors import ConfigError
from .protocols import ConfigLoader


def load_resolved_config(
    workspace_root: Path,
    source_dir: Path,
    config_loader: ConfigLoader,
    extra_layers: Optional[list[ConfigLayer]] = None,
) -> tuple[ResolvedConfig, list[Diagnostic]]:
    """Load, merge, and validate config layers for a source context."""
    layers = [
        ConfigLayer(
            data=copy.deepcopy(BUILTIN_DEFAULTS),
            source=None,
            label="built-in defaults",
        )
    ]
    file_layers = config_loader.load_layers(workspace_root, source_dir)
    additional_layers = [layer for layer in extra_layers if layer.data] if extra_layers else []
    scope_diagnostics = _validate_tex_dependency_scope(
        workspace_root, [*file_layers, *additional_layers]
    )
    if scope_diagnostics:
        raise ConfigError(
            "Configuration validation failed with " f"{len(scope_diagnostics)} error(s).",
            diagnostics=scope_diagnostics,
        )
    layers.extend(file_layers)
    layers.extend(additional_layers)

    merged, provenance = merge_config_layers(layers)

    schema_version = merged.get("schema_version", 1)
    diagnostics = validate_config(merged, schema_version)

    errors = [d for d in diagnostics if d.level == DiagnosticLevel.ERROR]
    if errors:
        raise ConfigError(
            f"Configuration validation failed with {len(errors)} error(s).",
            diagnostics=diagnostics,
        )

    return resolve_config(merged, provenance), diagnostics


def _validate_tex_dependency_scope(
    workspace_root: Path,
    layers: list[ConfigLayer],
) -> list[Diagnostic]:
    """Reject TeX dependency declarations outside the workspace-root config."""
    root_config = (workspace_root / ".ktisma.toml").resolve()
    diagnostics: list[Diagnostic] = []
    for layer in layers:
        if "tex" not in layer.data:
            continue
        if layer.source is not None and layer.source.resolve() == root_config:
            continue
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="config",
                code="tex-dependencies-not-root",
                message=(
                    "TeX dependencies may be declared only in the workspace-root "
                    f".ktisma.toml; found a declaration in {layer.label}."
                ),
            )
        )
    return diagnostics
