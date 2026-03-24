from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..domain.context import BuildRequest, SourceContext, VariantSpec, is_valid_variant_name
from ..domain.engine import EngineRule
from ..domain.diagnostics import Diagnostic, DiagnosticLevel
from ..domain.errors import KtismaError
from ..domain.exit_codes import ExitCode
from ..domain.routing import RouteResolver
from .build import BuildResult, execute_build
from .configuration import load_resolved_config
from .protocols import BuildServices


@dataclass(frozen=True)
class VariantsResult:
    exit_code: ExitCode
    results: list[tuple[VariantSpec, BuildResult]] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


def validate_variant_name(name: str) -> bool:
    """Check if a variant name is valid for use in filenames."""
    return is_valid_variant_name(name)


def execute_variants(
    ctx: SourceContext,
    request: BuildRequest,
    services: BuildServices,
    route_resolvers: Optional[list[RouteResolver]] = None,
    engine_rules: Optional[list[EngineRule]] = None,
) -> VariantsResult:
    """Build all configured variants for a source file.

    Each variant uses its own build directory and produces a uniquely named output.
    """
    diagnostics: list[Diagnostic] = []

    # Load config to get variant definitions
    config, _ = load_resolved_config(
        ctx.workspace_root, ctx.source_dir, services.config_loader
    )

    if not config.variants and not request.include_default:
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.WARNING,
                component="variants",
                code="no-variants",
                message="No variants defined in configuration.",
            )
        )
        return VariantsResult(exit_code=ExitCode.SUCCESS, diagnostics=diagnostics)

    results: list[tuple[VariantSpec, BuildResult]] = []
    any_failure = False

    if request.include_default:
        default_request = BuildRequest(
            watch=request.watch,
            dry_run=request.dry_run,
            engine_override=request.engine_override,
            output_path_override=request.output_path_override,
            output_dir_override=request.output_dir_override,
            json_output=request.json_output,
            cleanup_override=request.cleanup_override,
        )
        result = execute_build(
            ctx=ctx,
            request=default_request,
            services=services,
            route_resolvers=route_resolvers,
            engine_rules=engine_rules,
        )
        results.append((VariantSpec(name="default", payload=""), result))
        if result.exit_code != ExitCode.SUCCESS:
            any_failure = True

    for name, variant_config in config.variants.items():
        if not validate_variant_name(name):
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="variants",
                    code="invalid-variant-name",
                    message=f"Variant name '{name}' is not a valid identifier.",
                )
            )
            any_failure = True
            continue

        variant_spec = VariantSpec(
            name=name,
            payload=variant_config.payload,
            engine_override=variant_config.engine,
            output_override=variant_config.output,
            filename_suffix=variant_config.filename_suffix,
        )
        variant_request = BuildRequest(
            watch=request.watch,
            dry_run=request.dry_run,
            engine_override=request.engine_override,
            output_path_override=request.output_path_override,
            output_dir_override=request.output_dir_override,
            variant=name,
            variant_payload=variant_config.payload,
            json_output=request.json_output,
            cleanup_override=request.cleanup_override,
        )

        try:
            result = execute_build(
                ctx=ctx,
                request=variant_request,
                services=services,
                route_resolvers=route_resolvers,
                engine_rules=engine_rules,
            )
            results.append((variant_spec, result))
            if result.exit_code != ExitCode.SUCCESS:
                any_failure = True
        except KtismaError as exc:
            diagnostics.extend(exc.diagnostics)
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="variants",
                    code="variant-build-failed",
                    message=f"Variant '{name}' build failed: {exc}",
                )
            )
            any_failure = True
        except Exception as exc:
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="variants",
                    code="variant-build-failed",
                    message=f"Variant '{name}' build failed: {exc}",
                )
            )
            any_failure = True

    exit_code = ExitCode.COMPILATION_FAILURE if any_failure else ExitCode.SUCCESS
    return VariantsResult(exit_code=exit_code, results=results, diagnostics=diagnostics)
