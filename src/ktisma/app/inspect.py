from __future__ import annotations

from typing import Optional

from ..domain.context import BuildRequest, SourceContext
from ..domain.engine import EngineDecision, EngineRule, detect_engine
from ..domain.routing import RouteDecision, RouteResolver, resolve_route
from .configuration import load_resolved_config
from .protocols import ConfigLoader, SourceReader


def inspect_engine(
    ctx: SourceContext,
    request: BuildRequest,
    config_loader: ConfigLoader,
    source_reader: SourceReader,
    engine_rules: Optional[list[EngineRule]] = None,
) -> EngineDecision:
    """Inspect engine selection without compiling.

    Reuses the same config and decision path as build, stopping before compilation.
    """
    config, _ = load_resolved_config(ctx.workspace_root, ctx.source_dir, config_loader)
    source_inputs = source_reader.read_source(ctx.source_file)

    if request.engine_override:
        return EngineDecision(
            engine=request.engine_override, evidence=["--engine CLI override"]
        )

    return detect_engine(source_inputs, config, custom_rules=engine_rules)


def inspect_route(
    ctx: SourceContext,
    request: BuildRequest,
    config_loader: ConfigLoader,
    source_reader: SourceReader,
    route_resolvers: Optional[list[RouteResolver]] = None,
) -> RouteDecision:
    """Inspect routing without compiling.

    Reuses the same config and decision path as build, stopping before compilation.
    """
    config, _ = load_resolved_config(ctx.workspace_root, ctx.source_dir, config_loader)
    source_inputs = source_reader.read_source(ctx.source_file)

    return resolve_route(
        ctx,
        source_inputs,
        config,
        request.output_dir_override,
        extra_resolvers=route_resolvers,
    )
