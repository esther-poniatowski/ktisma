from __future__ import annotations

import json
import signal
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..domain.build_dir import BuildDirPlan, plan_build_dir
from ..domain.config import VALID_ENGINES, CleanupPolicy, ConfigLayer, ResolvedConfig, VariantConfig
from ..domain.context import BuildRequest, SourceContext, SourceInputs, VariantSpec, is_valid_variant_name
from ..domain.diagnostics import Diagnostic, DiagnosticLevel
from ..domain.engine import EngineDecision, EngineRule, detect_engine
from ..domain.errors import ConfigError, LockContention
from ..domain.exit_codes import ExitCode
from ..domain.routing import RouteDecision, RouteResolver, resolve_route
from .configuration import load_resolved_config
from .protocols import (
    BackendResult,
    BackendRunner,
    BuildServices,
    ConfigLoader,
    LockManager,
    Materializer,
    PostProcessor,
    PrerequisiteProbe,
    SourceReader,
    WorkspaceOps,
)


@dataclass(frozen=True)
class BuildResult:
    exit_code: ExitCode
    engine: Optional[EngineDecision] = None
    route: Optional[RouteDecision] = None
    build_plan: Optional[BuildDirPlan] = None
    backend_result: Optional[BackendResult] = None
    produced_paths: list[Path] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


def execute_build(
    ctx: SourceContext,
    request: BuildRequest,
    services: BuildServices,
    route_resolvers: Optional[list[RouteResolver]] = None,
    engine_rules: Optional[list[EngineRule]] = None,
) -> BuildResult:
    """Execute the build use-case."""
    all_diagnostics: list[Diagnostic] = []
    lock_acquired = False
    build_plan: Optional[BuildDirPlan] = None

    cli_layer = _build_cli_config_layer(request)
    extra_layers = [cli_layer] if cli_layer.data else None
    config, config_diags = load_resolved_config(
        ctx.workspace_root,
        ctx.source_dir,
        services.config_loader,
        extra_layers=extra_layers,
    )
    all_diagnostics.extend(config_diags)

    source_inputs = services.source_reader.read_source(ctx.source_file)
    variant = _resolve_variant(request, config)

    engine_decision = _resolve_engine_decision(
        request=request,
        source_inputs=source_inputs,
        config=config,
        variant=variant,
        engine_rules=engine_rules,
        diagnostics=all_diagnostics,
    )
    all_diagnostics.extend(engine_decision.diagnostics)

    if _has_errors(engine_decision.diagnostics):
        return BuildResult(
            exit_code=ExitCode.CONFIG_ERROR,
            engine=engine_decision,
            diagnostics=all_diagnostics,
        )

    base_route_decision = resolve_route(
        ctx,
        source_inputs,
        config,
        output_path_override=request.output_path_override,
        output_dir_override=request.output_dir_override,
        extra_resolvers=route_resolvers,
    )
    route_decision = _finalize_route_decision(
        ctx=ctx,
        config=config,
        request=request,
        base_route=base_route_decision,
        variant=variant,
    )
    all_diagnostics.extend(route_decision.diagnostics)
    build_plan = plan_build_dir(ctx, config, variant)

    if request.dry_run:
        return BuildResult(
            exit_code=ExitCode.SUCCESS,
            engine=engine_decision,
            route=route_decision,
            build_plan=build_plan,
            diagnostics=all_diagnostics,
        )

    prerequisite_diags = _check_build_prerequisites(
        services.prerequisite_probe, engine_decision.engine
    )
    all_diagnostics.extend(prerequisite_diags)
    if prerequisite_diags:
        return BuildResult(
            exit_code=ExitCode.PREREQUISITE_FAILURE,
            engine=engine_decision,
            route=route_decision,
            build_plan=build_plan,
            diagnostics=all_diagnostics,
        )

    services.workspace_ops.ensure_directory(build_plan.build_dir)
    try:
        mode = "watch" if request.watch else "build"
        services.lock_manager.acquire(build_plan.lock_file, ctx.source_file, mode)
        lock_acquired = True
        _write_build_metadata(build_plan, ctx, variant, services.workspace_ops)
    except LockContention as exc:
        all_diagnostics.extend(exc.diagnostics)
        all_diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="lock",
                code="lock-contention",
                message=str(exc),
            )
        )
        return BuildResult(
            exit_code=ExitCode.LOCK_CONTENTION,
            engine=engine_decision,
            route=route_decision,
            build_plan=build_plan,
            diagnostics=all_diagnostics,
        )

    try:
        extra_args = _build_extra_args(variant)

        if request.watch:
            return _execute_watch(
                ctx=ctx,
                config=config,
                engine_decision=engine_decision,
                route_decision=route_decision,
                build_plan=build_plan,
                variant=variant,
                backend_runner=services.backend_runner,
                materializer=services.materializer,
                post_processor=services.post_processor,
                diagnostics=all_diagnostics,
            )

        backend_result = services.backend_runner.compile(
            source_file=ctx.source_file,
            build_dir=build_plan.build_dir,
            engine=engine_decision.engine,
            synctex=config.build.synctex,
            extra_args=extra_args,
        )
        all_diagnostics.extend(backend_result.diagnostics)

        if not backend_result.success:
            return BuildResult(
                exit_code=ExitCode.COMPILATION_FAILURE,
                engine=engine_decision,
                route=route_decision,
                build_plan=build_plan,
                backend_result=backend_result,
                diagnostics=all_diagnostics,
            )

        materialized = _materialize_output(
            source=backend_result.pdf_path or build_plan.expected_pdf,
            destination=route_decision.destination,
            ctx=ctx,
            variant=variant,
            materializer=services.materializer,
            post_processor=services.post_processor,
            diagnostics=all_diagnostics,
        )
        if not materialized:
            return BuildResult(
                exit_code=ExitCode.INTERNAL_ERROR,
                engine=engine_decision,
                route=route_decision,
                build_plan=build_plan,
                backend_result=backend_result,
                diagnostics=all_diagnostics,
            )

        cleanup = _effective_cleanup(config, request)
        _apply_cleanup(
            policy=cleanup,
            build_plan=build_plan,
            compile_success=backend_result.success,
            materialize_success=True,
            workspace_ops=services.workspace_ops,
            diagnostics=all_diagnostics,
        )

        return BuildResult(
            exit_code=ExitCode.SUCCESS,
            engine=engine_decision,
            route=route_decision,
            build_plan=build_plan,
            backend_result=backend_result,
            produced_paths=[route_decision.destination],
            diagnostics=all_diagnostics,
        )
    finally:
        if lock_acquired and build_plan is not None:
            services.lock_manager.release(build_plan.lock_file)


def _execute_watch(
    ctx: SourceContext,
    config: ResolvedConfig,
    engine_decision: EngineDecision,
    route_decision: RouteDecision,
    build_plan: BuildDirPlan,
    variant: Optional[VariantSpec],
    backend_runner: BackendRunner,
    materializer: Materializer,
    post_processor: Optional[PostProcessor],
    diagnostics: list[Diagnostic],
) -> BuildResult:
    """Execute watch mode with a long-lived backend session."""
    session = backend_runner.start_watch(
        source_file=ctx.source_file,
        build_dir=build_plan.build_dir,
        engine=engine_decision.engine,
        synctex=config.build.synctex,
        extra_args=_build_extra_args(variant),
    )
    produced_paths: list[Path] = []
    last_backend_result: Optional[BackendResult] = None
    signal_exit_code: Optional[int] = None
    session_finished = False
    session_closed = False

    def _teardown(signum: int, frame: object) -> None:
        nonlocal signal_exit_code, session_closed
        signal_exit_code = 128 + signum
        if not session_closed:
            session.terminate()
            session_closed = True

    is_main_thread = threading.current_thread() is threading.main_thread()
    old_sigint = None
    old_sigterm = None
    if is_main_thread:
        old_sigint = signal.signal(signal.SIGINT, _teardown)
        old_sigterm = signal.signal(signal.SIGTERM, _teardown)

    try:
        while True:
            if signal_exit_code is not None:
                raise SystemExit(signal_exit_code)

            update = session.poll(timeout_seconds=0.5)
            if signal_exit_code is not None:
                raise SystemExit(signal_exit_code)
            if update is None:
                continue

            last_backend_result = update.result
            diagnostics.extend(update.result.diagnostics)

            if update.result.success and update.result.pdf_path is not None:
                materialized = _materialize_output(
                    source=update.result.pdf_path,
                    destination=route_decision.destination,
                    ctx=ctx,
                    variant=variant,
                    materializer=materializer,
                    post_processor=post_processor,
                    diagnostics=diagnostics,
                )
                if not materialized:
                    return BuildResult(
                        exit_code=ExitCode.INTERNAL_ERROR,
                        engine=engine_decision,
                        route=route_decision,
                        build_plan=build_plan,
                        backend_result=last_backend_result,
                        produced_paths=produced_paths,
                        diagnostics=diagnostics,
                    )
                produced_paths = [route_decision.destination]

            if update.finished:
                session_finished = True
                exit_code = (
                    ExitCode.SUCCESS
                    if update.result.exit_code == 0
                    else ExitCode.COMPILATION_FAILURE
                )
                return BuildResult(
                    exit_code=exit_code,
                    engine=engine_decision,
                    route=route_decision,
                    build_plan=build_plan,
                    backend_result=last_backend_result,
                    produced_paths=produced_paths,
                    diagnostics=diagnostics,
                )
    finally:
        if is_main_thread:
            signal.signal(signal.SIGINT, old_sigint)
            signal.signal(signal.SIGTERM, old_sigterm)
        if not session_finished and not session_closed:
            session.terminate()


def _build_cli_config_layer(request: BuildRequest) -> ConfigLayer:
    """Build a config layer from CLI flags that participate in config precedence."""
    data: dict[str, dict[str, str]] = {}
    if request.cleanup_override:
        data.setdefault("build", {})["cleanup"] = request.cleanup_override
    return ConfigLayer(data=data, source=None, label="CLI flags")


def _resolve_variant(request: BuildRequest, config: ResolvedConfig) -> Optional[VariantSpec]:
    """Resolve and validate a variant from request and config."""
    if request.variant_spec is not None:
        if not is_valid_variant_name(request.variant_spec.name):
            raise ConfigError(
                f"Invalid variant name '{request.variant_spec.name}'; names must match "
                f"{VariantSpec.VALID_NAME_PATTERN}."
            )
        if request.variant is not None and request.variant != request.variant_spec.name:
            raise ConfigError(
                f"Variant request mismatch: '{request.variant}' != '{request.variant_spec.name}'."
            )
        return request.variant_spec

    if request.variant is None:
        return None

    if not is_valid_variant_name(request.variant):
        raise ConfigError(
            f"Invalid variant name '{request.variant}'; names must match "
            f"{VariantSpec.VALID_NAME_PATTERN}."
        )

    if request.variant_payload is not None:
        return VariantSpec(name=request.variant, payload=request.variant_payload)

    variant_config = config.variants.get(request.variant)
    if variant_config is None:
        available = ", ".join(sorted(config.variants.keys())) if config.variants else "none"
        raise ConfigError(
            f"Unknown variant '{request.variant}'; available: {available}."
        )
    return _variant_spec_from_config(request.variant, variant_config)


def _build_extra_args(variant: Optional[VariantSpec]) -> Optional[list[str]]:
    """Build extra latexmk arguments for variant injection."""
    if variant is None or not variant.payload:
        return None
    return ["-usepretex", f"-pretex={variant.payload}"]


def _finalize_route_decision(
    ctx: SourceContext,
    config: ResolvedConfig,
    request: BuildRequest,
    base_route: RouteDecision,
    variant: Optional[VariantSpec],
) -> RouteDecision:
    destination = base_route.destination
    matched_rule = base_route.matched_rule
    diagnostics = list(base_route.diagnostics)

    if request.output_path_override is not None:
        return base_route

    if (
        variant is not None
        and variant.output_override
        and request.output_dir_override is None
    ):
        destination = _resolve_output_override(
            ctx=ctx,
            raw_output=variant.output_override,
            output_name=_output_pdf_name(ctx, config, variant),
        )
        matched_rule = f"variant '{variant.name}' output override"
    elif _should_replace_output_name(config, variant):
        destination = base_route.destination.parent / _output_pdf_name(ctx, config, variant)

    if base_route.fallback and destination != base_route.destination:
        diagnostics = [
            Diagnostic(
                level=diag.level,
                component=diag.component,
                code=diag.code,
                message=(
                    f"No routing rule or convention matched; placing output beside source file: "
                    f"{destination}"
                )
                if diag.code == "fallback-routing"
                else diag.message,
                evidence=diag.evidence,
            )
            for diag in diagnostics
        ]

    return RouteDecision(
        destination=destination,
        matched_rule=matched_rule,
        fallback=base_route.fallback,
        diagnostics=diagnostics,
    )


def _output_pdf_name(
    ctx: SourceContext,
    config: ResolvedConfig,
    variant: Optional[VariantSpec],
) -> str:
    """Determine the output PDF filename, including variant suffix if applicable."""
    stem = ctx.source_file.stem
    suffix_template = config.routing.default_filename_suffix
    variant_name = None
    if variant is not None:
        suffix_template = (
            variant.filename_suffix
            if variant.filename_suffix is not None
            else config.routing.variant_filename_suffix
        )
        variant_name = variant.name
    suffix = _render_filename_suffix(suffix_template, stem, variant_name)
    return f"{stem}{suffix}.pdf"


def _check_build_prerequisites(
    probe: PrerequisiteProbe,
    engine: str,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    latexmk_check = probe.check_latexmk()
    if not latexmk_check.available:
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="prerequisite",
                code="missing-latexmk",
                message=latexmk_check.message or "latexmk is not available on PATH.",
            )
        )

    engine_check = probe.check_engine(engine)
    if not engine_check.available:
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="prerequisite",
                code="missing-engine",
                message=engine_check.message or f"Engine '{engine}' is not available.",
            )
        )

    return diagnostics


def _resolve_engine_decision(
    request: BuildRequest,
    source_inputs: SourceInputs,
    config: ResolvedConfig,
    variant: Optional[VariantSpec],
    engine_rules: Optional[list[EngineRule]],
    diagnostics: list[Diagnostic],
) -> EngineDecision:
    if request.engine_override:
        if request.engine_override not in VALID_ENGINES:
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.WARNING,
                    component="engine",
                    code="unknown-engine-override",
                    message=(
                        f"Engine override '{request.engine_override}' is not a recognized engine; "
                        f"valid engines: {', '.join(sorted(VALID_ENGINES))}."
                    ),
                )
            )
        return EngineDecision(
            engine=request.engine_override,
            evidence=["--engine CLI override"],
        )

    if variant is not None and variant.engine_override is not None:
        return EngineDecision(
            engine=variant.engine_override,
            evidence=[f"variant '{variant.name}' engine override"],
        )

    return detect_engine(source_inputs, config, custom_rules=engine_rules)


def _variant_spec_from_config(name: str, variant_config: VariantConfig) -> VariantSpec:
    return VariantSpec(
        name=name,
        payload=variant_config.payload,
        engine_override=variant_config.engine,
        output_override=variant_config.output,
        filename_suffix=variant_config.filename_suffix,
    )


def _render_filename_suffix(
    template: str,
    stem: str,
    variant_name: Optional[str],
) -> str:
    try:
        return template.format(stem=stem, variant=variant_name or "")
    except KeyError as exc:  # pragma: no cover - validated in config and guarded here
        raise ConfigError(
            f"Invalid filename suffix template '{template}'; unknown placeholder {exc}."
        ) from exc


def _should_replace_output_name(
    config: ResolvedConfig,
    variant: Optional[VariantSpec],
) -> bool:
    if variant is not None:
        return True
    return config.routing.default_filename_suffix != ""


def _resolve_output_override(
    ctx: SourceContext,
    raw_output: str,
    output_name: str,
) -> Path:
    override_path = Path(raw_output).expanduser()
    if not override_path.is_absolute():
        override_path = ctx.source_dir / override_path
    if raw_output.endswith("/") or not override_path.suffix:
        return override_path / output_name
    return override_path


def _write_build_metadata(
    build_plan: BuildDirPlan,
    ctx: SourceContext,
    variant: Optional[VariantSpec],
    workspace_ops: WorkspaceOps,
) -> None:
    payload = {
        "source": _canonical_source_identity(ctx.source_file),
        "variant": variant.name if variant is not None else None,
    }
    workspace_ops.write_text(build_plan.metadata_file, json.dumps(payload, indent=2))


def _canonical_source_identity(source_file: Path) -> str:
    """Return the canonical source identity used across build and clean flows."""
    return str(source_file.expanduser().resolve())


def _materialize_output(
    source: Path,
    destination: Path,
    ctx: SourceContext,
    variant: Optional[VariantSpec],
    materializer: Materializer,
    post_processor: Optional[PostProcessor],
    diagnostics: list[Diagnostic],
) -> bool:
    try:
        materializer.materialize(source, destination)
        if post_processor is not None:
            diagnostics.extend(post_processor.process(destination, ctx, variant))
        return True
    except Exception as exc:
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="materialize",
                code="materialization-failed",
                message=f"Failed to materialize PDF: {exc}",
            )
        )
        return False


def _effective_cleanup(config: ResolvedConfig, request: BuildRequest) -> CleanupPolicy:
    """Determine the effective cleanup policy."""
    if request.cleanup_override:
        return CleanupPolicy(request.cleanup_override)
    if request.watch:
        return CleanupPolicy.NEVER
    return config.build.cleanup


def _apply_cleanup(
    policy: CleanupPolicy,
    build_plan: BuildDirPlan,
    compile_success: bool,
    materialize_success: bool,
    workspace_ops: WorkspaceOps,
    diagnostics: list[Diagnostic],
) -> None:
    """Apply the cleanup policy to the build directory."""
    if not compile_success:
        return  # never clean after compile failure per roadmap

    should_clean = False
    if policy == CleanupPolicy.ALWAYS:
        should_clean = True
    elif policy == CleanupPolicy.ON_SUCCESS:
        should_clean = True
    elif policy == CleanupPolicy.ON_OUTPUT_SUCCESS and materialize_success:
        should_clean = True

    if should_clean and workspace_ops.path_exists(build_plan.build_dir):
        try:
            workspace_ops.remove_tree(build_plan.build_dir)
        except Exception as exc:
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.WARNING,
                    component="cleanup",
                    code="cleanup-failed",
                    message=f"Failed to clean build directory: {exc}",
                )
            )


def _has_errors(diagnostics: list[Diagnostic]) -> bool:
    return any(d.level == DiagnosticLevel.ERROR for d in diagnostics)
