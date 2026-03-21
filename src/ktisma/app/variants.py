from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..domain.context import BuildRequest, SourceContext, VariantSpec
from ..domain.config import (
    BUILTIN_DEFAULTS,
    ConfigLayer,
    merge_config_layers,
    resolve_config,
)
from ..domain.diagnostics import Diagnostic, DiagnosticLevel
from ..domain.exit_codes import ExitCode
from .build import BuildResult, execute_build
from .protocols import (
    BackendRunner,
    ConfigLoader,
    LockManager,
    Materializer,
    SourceReader,
)


@dataclass(frozen=True)
class VariantsResult:
    exit_code: ExitCode
    results: list[tuple[VariantSpec, BuildResult]] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


def validate_variant_name(name: str) -> bool:
    """Check if a variant name is valid for use in filenames."""
    return bool(re.match(VariantSpec.VALID_NAME_PATTERN, name))


def execute_variants(
    ctx: SourceContext,
    request: BuildRequest,
    config_loader: ConfigLoader,
    source_reader: SourceReader,
    lock_manager: LockManager,
    backend_runner: BackendRunner,
    materializer: Materializer,
) -> VariantsResult:
    """Build all configured variants for a source file.

    Each variant uses its own build directory and produces a uniquely named output.
    """
    diagnostics: list[Diagnostic] = []

    # Load config to get variant definitions
    layers = [ConfigLayer(data=dict(BUILTIN_DEFAULTS), source=None, label="built-in defaults")]
    file_layers = config_loader.load_layers(ctx.workspace_root, ctx.source_dir)
    layers.extend(file_layers)
    merged, provenance = merge_config_layers(layers)
    config = resolve_config(merged, provenance)

    if not config.variants:
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

    for name, payload in config.variants.items():
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

        variant_spec = VariantSpec(name=name, payload=payload)
        variant_request = BuildRequest(
            watch=request.watch,
            dry_run=request.dry_run,
            engine_override=request.engine_override,
            output_dir_override=request.output_dir_override,
            variant=name,
            variant_payload=payload,
            json_output=request.json_output,
            cleanup_override=request.cleanup_override,
        )

        try:
            result = execute_build(
                ctx=ctx,
                request=variant_request,
                config_loader=config_loader,
                source_reader=source_reader,
                lock_manager=lock_manager,
                backend_runner=backend_runner,
                materializer=materializer,
            )
            results.append((variant_spec, result))
            if result.exit_code != ExitCode.SUCCESS:
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
