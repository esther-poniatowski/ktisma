from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..domain.config import (
    ConfigLayer,
    merge_config_layers,
    resolve_config,
    validate_config,
    BUILTIN_DEFAULTS,
)
from ..domain.context import BuildRequest, SourceContext
from ..domain.diagnostics import Diagnostic, DiagnosticLevel
from ..domain.engine import EngineDecision, detect_engine
from ..domain.routing import RouteDecision, resolve_route
from .protocols import ConfigLoader, SourceReader


def inspect_engine(
    ctx: SourceContext,
    request: BuildRequest,
    config_loader: ConfigLoader,
    source_reader: SourceReader,
) -> EngineDecision:
    """Inspect engine selection without compiling.

    Reuses the same config and decision path as build, stopping before compilation.
    """
    config, _ = _load_config(ctx, request, config_loader)
    source_inputs = source_reader.read_source(ctx.source_file)

    if request.engine_override:
        return EngineDecision(
            engine=request.engine_override, evidence=["--engine CLI override"]
        )

    return detect_engine(source_inputs, config)


def inspect_route(
    ctx: SourceContext,
    request: BuildRequest,
    config_loader: ConfigLoader,
    source_reader: SourceReader,
) -> RouteDecision:
    """Inspect routing without compiling.

    Reuses the same config and decision path as build, stopping before compilation.
    """
    config, _ = _load_config(ctx, request, config_loader)
    source_inputs = source_reader.read_source(ctx.source_file)

    return resolve_route(ctx, source_inputs, config, request.output_dir_override)


def _load_config(ctx, request, config_loader):
    """Shared config loading for inspect commands."""
    layers = [ConfigLayer(data=dict(BUILTIN_DEFAULTS), source=None, label="built-in defaults")]
    file_layers = config_loader.load_layers(ctx.workspace_root, ctx.source_dir)
    layers.extend(file_layers)

    merged, provenance = merge_config_layers(layers)
    schema_version = merged.get("schema_version", 1)
    diagnostics = validate_config(merged, schema_version)

    errors = [d for d in diagnostics if d.level == DiagnosticLevel.ERROR]
    if errors:
        from .build import ConfigError
        raise ConfigError(
            f"Configuration validation failed with {len(errors)} error(s).",
            diagnostics=diagnostics,
        )

    config = resolve_config(merged, provenance)
    return config, diagnostics
