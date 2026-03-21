from __future__ import annotations

import signal
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..domain.build_dir import BuildDirPlan, plan_build_dir
from ..domain.config import (
    CleanupPolicy,
    ConfigLayer,
    ResolvedConfig,
    merge_config_layers,
    resolve_config,
    validate_config,
)
from ..domain.context import BuildRequest, SourceContext, VariantSpec
from ..domain.diagnostics import Diagnostic, DiagnosticLevel
from ..domain.engine import EngineDecision, detect_engine
from ..domain.exit_codes import ExitCode
from ..domain.routing import RouteDecision, resolve_route
from .protocols import (
    BackendResult,
    BackendRunner,
    ConfigLoader,
    LockManager,
    Materializer,
    SourceReader,
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


class BuildError(Exception):
    def __init__(self, exit_code: ExitCode, message: str, diagnostics: Optional[list[Diagnostic]] = None):
        super().__init__(message)
        self.exit_code = exit_code
        self.diagnostics = diagnostics or []


class LockContention(BuildError):
    def __init__(self, message: str, diagnostics: Optional[list[Diagnostic]] = None):
        super().__init__(ExitCode.LOCK_CONTENTION, message, diagnostics)


class ConfigError(BuildError):
    def __init__(self, message: str, diagnostics: Optional[list[Diagnostic]] = None):
        super().__init__(ExitCode.CONFIG_ERROR, message, diagnostics)


class PrerequisiteError(BuildError):
    def __init__(self, message: str, diagnostics: Optional[list[Diagnostic]] = None):
        super().__init__(ExitCode.PREREQUISITE_FAILURE, message, diagnostics)


def execute_build(
    ctx: SourceContext,
    request: BuildRequest,
    config_loader: ConfigLoader,
    source_reader: SourceReader,
    lock_manager: LockManager,
    backend_runner: BackendRunner,
    materializer: Materializer,
) -> BuildResult:
    """Execute the build use-case.

    Steps per roadmap / design-principles section 6.1:
    1. Load and merge configuration layers.
    2. Read source inputs.
    3. Resolve engine.
    4. Resolve route.
    5. Plan build directory.
    6. Acquire lock.
    7. Run backend compilation.
    8. Materialize final output.
    9. Apply cleanup policy.
    10. Return structured result with diagnostics.
    """
    all_diagnostics: list[Diagnostic] = []

    # Step 1: Load and merge config
    config, config_diags = _load_config(ctx, request, config_loader)
    all_diagnostics.extend(config_diags)

    # Step 2: Read source inputs
    source_inputs = source_reader.read_source(ctx.source_file)

    # Step 3: Resolve engine
    engine_override = request.engine_override
    if engine_override:
        engine_decision = EngineDecision(
            engine=engine_override, evidence=["--engine CLI override"]
        )
    else:
        engine_decision = detect_engine(source_inputs, config)
    all_diagnostics.extend(engine_decision.diagnostics)

    if _has_errors(engine_decision.diagnostics) and config.engines.strict_detection:
        return BuildResult(
            exit_code=ExitCode.CONFIG_ERROR,
            engine=engine_decision,
            diagnostics=all_diagnostics,
        )

    # Step 4: Resolve route
    route_decision = resolve_route(ctx, source_inputs, config, request.output_dir_override)
    all_diagnostics.extend(route_decision.diagnostics)

    # Step 5: Resolve variant
    variant = _resolve_variant(request, config)

    # Step 6: Plan build directory
    build_plan = plan_build_dir(ctx, config, variant)

    if request.dry_run:
        return BuildResult(
            exit_code=ExitCode.SUCCESS,
            engine=engine_decision,
            route=route_decision,
            build_plan=build_plan,
            diagnostics=all_diagnostics,
        )

    # Step 7: Acquire lock
    build_plan.build_dir.mkdir(parents=True, exist_ok=True)
    try:
        mode = "watch" if request.watch else "build"
        lock_manager.acquire(build_plan.lock_file, ctx.source_file, mode)
    except Exception as exc:
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
        # Step 8: Compile
        extra_args = _build_extra_args(variant, config)

        if request.watch:
            return _execute_watch(
                ctx, config, engine_decision, route_decision, build_plan,
                backend_runner, materializer, lock_manager, extra_args,
                all_diagnostics,
            )

        backend_result = backend_runner.compile(
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

        # Step 9: Materialize
        produced_paths: list[Path] = []
        output_name = _output_pdf_name(ctx, variant)
        final_dest = route_decision.destination.parent / output_name

        try:
            materializer.materialize(build_plan.expected_pdf, final_dest)
            produced_paths.append(final_dest)
        except Exception as exc:
            all_diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="materialize",
                    code="materialization-failed",
                    message=f"Failed to materialize PDF: {exc}",
                )
            )
            return BuildResult(
                exit_code=ExitCode.INTERNAL_ERROR,
                engine=engine_decision,
                route=route_decision,
                build_plan=build_plan,
                backend_result=backend_result,
                diagnostics=all_diagnostics,
            )

        # Step 10: Cleanup
        cleanup = _effective_cleanup(config, request)
        _apply_cleanup(cleanup, build_plan, backend_result.success, bool(produced_paths), all_diagnostics)

        return BuildResult(
            exit_code=ExitCode.SUCCESS,
            engine=engine_decision,
            route=route_decision,
            build_plan=build_plan,
            backend_result=backend_result,
            produced_paths=produced_paths,
            diagnostics=all_diagnostics,
        )

    finally:
        if not request.watch:
            lock_manager.release(build_plan.lock_file)


def _execute_watch(
    ctx: SourceContext,
    config: ResolvedConfig,
    engine_decision: EngineDecision,
    route_decision: RouteDecision,
    build_plan: BuildDirPlan,
    backend_runner: BackendRunner,
    materializer: Materializer,
    lock_manager: LockManager,
    extra_args: Optional[list[str]],
    diagnostics: list[Diagnostic],
) -> BuildResult:
    """Execute watch mode: hold lock, launch latexmk -pvc, materialize after each rebuild."""
    teardown_done = False

    def _teardown(signum: int, frame: object) -> None:
        nonlocal teardown_done
        if not teardown_done:
            teardown_done = True
            lock_manager.release(build_plan.lock_file)
        raise SystemExit(128 + signum)

    old_sigint = signal.signal(signal.SIGINT, _teardown)
    old_sigterm = signal.signal(signal.SIGTERM, _teardown)

    try:
        backend_result = backend_runner.compile_watch(
            source_file=ctx.source_file,
            build_dir=build_plan.build_dir,
            engine=engine_decision.engine,
            synctex=config.build.synctex,
            extra_args=extra_args,
        )
        diagnostics.extend(backend_result.diagnostics)

        exit_code = ExitCode.SUCCESS if backend_result.success else ExitCode.COMPILATION_FAILURE
        return BuildResult(
            exit_code=exit_code,
            engine=engine_decision,
            route=route_decision,
            build_plan=build_plan,
            backend_result=backend_result,
            diagnostics=diagnostics,
        )
    finally:
        signal.signal(signal.SIGINT, old_sigint)
        signal.signal(signal.SIGTERM, old_sigterm)
        if not teardown_done:
            lock_manager.release(build_plan.lock_file)


def _load_config(
    ctx: SourceContext, request: BuildRequest, config_loader: ConfigLoader
) -> tuple[ResolvedConfig, list[Diagnostic]]:
    """Load, merge, validate config layers."""
    from ..domain.config import BUILTIN_DEFAULTS

    layers = [ConfigLayer(data=dict(BUILTIN_DEFAULTS), source=None, label="built-in defaults")]
    file_layers = config_loader.load_layers(ctx.workspace_root, ctx.source_dir)
    layers.extend(file_layers)

    cli_overrides = _build_cli_config_layer(request)
    if cli_overrides.data:
        layers.append(cli_overrides)

    merged, provenance = merge_config_layers(layers)

    schema_version = merged.get("schema_version", 1)
    diagnostics = validate_config(merged, schema_version)

    errors = [d for d in diagnostics if d.level == DiagnosticLevel.ERROR]
    if errors:
        raise ConfigError(
            f"Configuration validation failed with {len(errors)} error(s).",
            diagnostics=diagnostics,
        )

    config = resolve_config(merged, provenance)
    return config, diagnostics


def _build_cli_config_layer(request: BuildRequest) -> ConfigLayer:
    """Build a config layer from CLI flags."""
    data: dict = {}
    if request.engine_override:
        data.setdefault("engines", {})["default"] = request.engine_override
    if request.cleanup_override:
        data.setdefault("build", {})["cleanup"] = request.cleanup_override
    return ConfigLayer(data=data, source=None, label="CLI flags")


def _resolve_variant(request: BuildRequest, config: ResolvedConfig) -> Optional[VariantSpec]:
    """Resolve variant from request and config."""
    if request.variant_payload is not None and request.variant is not None:
        return VariantSpec(name=request.variant, payload=request.variant_payload)

    if request.variant is not None:
        payload = config.variants.get(request.variant)
        if payload is None:
            available = ", ".join(sorted(config.variants.keys())) if config.variants else "none"
            raise ConfigError(
                f"Unknown variant '{request.variant}'; available: {available}."
            )
        return VariantSpec(name=request.variant, payload=payload)

    return None


def _build_extra_args(variant: Optional[VariantSpec], config: ResolvedConfig) -> Optional[list[str]]:
    """Build extra latexmk arguments for variant injection."""
    if variant is None or not variant.payload:
        return None
    return ["-usepretex", f"-pretex={variant.payload}"]


def _output_pdf_name(ctx: SourceContext, variant: Optional[VariantSpec]) -> str:
    """Determine the output PDF filename, including variant suffix if applicable."""
    stem = ctx.source_file.stem
    if variant is not None:
        return f"{stem}_{variant.name}.pdf"
    return f"{stem}.pdf"


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
    diagnostics: list[Diagnostic],
) -> None:
    """Apply the cleanup policy to the build directory."""
    import shutil

    should_clean = False
    if policy == CleanupPolicy.ALWAYS:
        should_clean = True
    elif policy == CleanupPolicy.ON_SUCCESS and compile_success:
        should_clean = True
    elif policy == CleanupPolicy.ON_OUTPUT_SUCCESS and compile_success and materialize_success:
        should_clean = True

    if should_clean and build_plan.build_dir.exists():
        try:
            shutil.rmtree(build_plan.build_dir)
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
