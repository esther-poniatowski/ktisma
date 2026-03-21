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
    layers.extend(config_loader.load_layers(workspace_root, source_dir))
    if extra_layers:
        layers.extend(layer for layer in extra_layers if layer.data)

    merged, provenance = merge_config_layers(layers)

    # Normalize merged route targets at the application boundary (expanduser + resolve).
    _normalize_route_paths(merged)

    schema_version = merged.get("schema_version", 1)
    diagnostics = validate_config(merged, schema_version)

    errors = [d for d in diagnostics if d.level == DiagnosticLevel.ERROR]
    if errors:
        raise ConfigError(
            f"Configuration validation failed with {len(errors)} error(s).",
            diagnostics=diagnostics,
        )

    return resolve_config(merged, provenance), diagnostics


def _normalize_route_paths(merged: dict) -> None:
    """Expand ~ and resolve route target paths at the application boundary."""
    routes = merged.get("routes")
    if not isinstance(routes, dict):
        return
    normalized: dict[str, str] = {}
    for pattern, target in routes.items():
        if isinstance(target, str):
            keep_trailing = target.endswith("/")
            resolved = Path(target).expanduser().resolve(strict=False)
            result = str(resolved)
            if keep_trailing and not result.endswith("/"):
                result += "/"
            normalized[pattern] = result
        else:
            normalized[pattern] = target
    merged["routes"] = normalized
