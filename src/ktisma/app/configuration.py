from __future__ import annotations

import copy
from pathlib import Path
from typing import Optional

from ..domain.config import (
    BUILTIN_DEFAULTS,
    CONFIG_SCHEMAS,
    DEFAULT_CONFIG_SCHEMA,
    ConfigLayer,
    ResolvedConfig,
    check_layer_schemas,
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
    workspace_schema, schema_diagnostics = check_layer_schemas(file_layers)
    if schema_diagnostics:
        raise ConfigError(
            "Configuration validation failed with " f"{len(schema_diagnostics)} error(s).",
            diagnostics=schema_diagnostics,
        )
    additional_layers = [layer for layer in extra_layers if layer.data] if extra_layers else []
    scope_diagnostics = _validate_tex_dependency_scope([*file_layers, *additional_layers])
    if scope_diagnostics:
        raise ConfigError(
            "Configuration validation failed with " f"{len(scope_diagnostics)} error(s).",
            diagnostics=scope_diagnostics,
        )
    layers.extend(file_layers)
    layers.extend(additional_layers)

    merged, provenance = merge_config_layers(layers)

    # The outermost file governs the workspace; an overlay cannot change the schema.
    merged["_schema"] = workspace_schema or DEFAULT_CONFIG_SCHEMA
    diagnostics = validate_config(merged, CONFIG_SCHEMAS[merged["_schema"]])

    errors = [d for d in diagnostics if d.level == DiagnosticLevel.ERROR]
    if errors:
        raise ConfigError(
            f"Configuration validation failed with {len(errors)} error(s).",
            diagnostics=diagnostics,
        )

    return resolve_config(merged, provenance), diagnostics


def _validate_tex_dependency_scope(layers: list[ConfigLayer]) -> list[Diagnostic]:
    """Reject TeX dependency declarations outside the workspace-root config."""
    diagnostics: list[Diagnostic] = []
    for layer in layers:
        if "tex" not in layer.data or layer.is_workspace_root:
            continue
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="config",
                code="tex-dependencies-not-root",
                message=(
                    "TeX dependencies may be declared only in the configuration file of the "
                    f"workspace root; found a declaration in {layer.label}."
                ),
            )
        )
    return diagnostics
