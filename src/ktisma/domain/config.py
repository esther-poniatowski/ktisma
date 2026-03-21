from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from .diagnostics import Diagnostic, DiagnosticLevel


class CleanupPolicy(Enum):
    NEVER = "never"
    ON_SUCCESS = "on_success"
    ON_OUTPUT_SUCCESS = "on_output_success"
    ALWAYS = "always"


@dataclass(frozen=True)
class ConfigLayer:
    data: dict[str, Any]
    source: Optional[Path]  # None for built-in defaults and CLI
    label: str  # human-readable provenance description


@dataclass(frozen=True)
class BuildConfig:
    out_dir_name: str = ".ktisma_build"
    cleanup: CleanupPolicy = CleanupPolicy.ON_OUTPUT_SUCCESS
    synctex: bool = True


@dataclass(frozen=True)
class EngineConfig:
    default: str = "pdflatex"
    modern_default: str = "lualatex"
    strict_detection: bool = False


@dataclass(frozen=True)
class RoutingConfig:
    source_suffix: str = "-tex"
    output_suffix: str = "-pdfs"
    preserve_relative: bool = True
    collapse_entrypoint_names: bool = False
    entrypoint_names: list[str] = field(default_factory=lambda: ["main", "index"])


@dataclass(frozen=True)
class ResolvedConfig:
    schema_version: int = 1
    build: BuildConfig = field(default_factory=BuildConfig)
    engines: EngineConfig = field(default_factory=EngineConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    routes: dict[str, str] = field(default_factory=dict)
    variants: dict[str, str] = field(default_factory=dict)
    provenance: list[str] = field(default_factory=list)


# --- Schema validation ---

SCHEMA_V1_KEYS: dict[str, set[str]] = {
    "": {"schema_version", "build", "engines", "routing", "routes", "variants"},
    "build": {"out_dir_name", "cleanup", "synctex"},
    "engines": {"default", "modern_default", "strict_detection"},
    "routing": {
        "source_suffix",
        "output_suffix",
        "preserve_relative",
        "collapse_entrypoint_names",
        "entrypoint_names",
    },
}

VALID_ENGINES: set[str] = {"pdflatex", "lualatex", "xelatex", "latex"}


def validate_config(data: dict[str, Any], schema_version: int = 1) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    if schema_version != 1:
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="config",
                code="unsupported-schema-version",
                message=f"Unsupported schema version {schema_version}; only version 1 is supported.",
            )
        )
        return diagnostics

    _validate_keys(data, "", diagnostics)

    build = data.get("build", {})
    if isinstance(build, dict):
        _validate_keys(build, "build", diagnostics)
        cleanup = build.get("cleanup")
        if cleanup is not None:
            try:
                CleanupPolicy(cleanup)
            except ValueError:
                valid = ", ".join(p.value for p in CleanupPolicy)
                diagnostics.append(
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        component="config",
                        code="invalid-cleanup-policy",
                        message=f"Invalid cleanup policy '{cleanup}'; valid values: {valid}.",
                    )
                )
        synctex = build.get("synctex")
        if synctex is not None and not isinstance(synctex, bool):
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="config",
                    code="type-mismatch",
                    message=f"'build.synctex' must be a boolean, got {type(synctex).__name__}.",
                )
            )
    elif "build" in data:
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="config",
                code="type-mismatch",
                message="'build' must be a table.",
            )
        )

    engines = data.get("engines", {})
    if isinstance(engines, dict):
        _validate_keys(engines, "engines", diagnostics)
        for key in ("default", "modern_default"):
            val = engines.get(key)
            if val is not None and val not in VALID_ENGINES:
                diagnostics.append(
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        component="config",
                        code="invalid-engine",
                        message=f"'engines.{key}' is '{val}'; valid engines: {', '.join(sorted(VALID_ENGINES))}.",
                    )
                )
        strict = engines.get("strict_detection")
        if strict is not None and not isinstance(strict, bool):
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="config",
                    code="type-mismatch",
                    message=f"'engines.strict_detection' must be a boolean, got {type(strict).__name__}.",
                )
            )
    elif "engines" in data:
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="config",
                code="type-mismatch",
                message="'engines' must be a table.",
            )
        )

    routing = data.get("routing", {})
    if isinstance(routing, dict):
        _validate_keys(routing, "routing", diagnostics)
        entrypoint_names = routing.get("entrypoint_names")
        if entrypoint_names is not None and not isinstance(entrypoint_names, list):
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="config",
                    code="type-mismatch",
                    message=f"'routing.entrypoint_names' must be an array, got {type(entrypoint_names).__name__}.",
                )
            )
    elif "routing" in data:
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="config",
                code="type-mismatch",
                message="'routing' must be a table.",
            )
        )

    routes = data.get("routes", {})
    if not isinstance(routes, dict):
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="config",
                code="type-mismatch",
                message="'routes' must be a table.",
            )
        )

    variants = data.get("variants", {})
    if not isinstance(variants, dict):
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="config",
                code="type-mismatch",
                message="'variants' must be a table.",
            )
        )

    return diagnostics


def _validate_keys(data: dict[str, Any], section: str, diagnostics: list[Diagnostic]) -> None:
    allowed = SCHEMA_V1_KEYS.get(section)
    if allowed is None:
        return
    for key in data:
        if key not in allowed:
            prefix = f"'{section}.{key}'" if section else f"'{key}'"
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="config",
                    code="unknown-key",
                    message=f"{prefix} is not a recognized key in schema version 1.",
                )
            )


# --- Merge logic ---


def merge_config_layers(layers: list[ConfigLayer]) -> tuple[dict[str, Any], list[str]]:
    """Merge config layers from lowest to highest precedence.

    Returns the merged dict and a list of provenance labels.
    Layers should be ordered from lowest to highest precedence.
    """
    import copy

    merged: dict[str, Any] = {}
    provenance: list[str] = []

    for layer in layers:
        if layer.data:
            _deep_merge(merged, copy.deepcopy(layer.data))
            provenance.append(layer.label)

    return merged, provenance


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    """Merge override into base in-place.

    Semantics per roadmap:
    - Nested tables merge by key.
    - Scalars replace.
    - Arrays replace (do not concatenate).
    - Routes and variants merge by exact key (handled naturally since they are flat dicts).
    """
    for key, value in override.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            _deep_merge(base[key], value)
        else:
            base[key] = value


# --- Config construction ---

BUILTIN_DEFAULTS: dict[str, Any] = {
    "schema_version": 1,
    "build": {
        "out_dir_name": ".ktisma_build",
        "cleanup": "on_output_success",
        "synctex": True,
    },
    "engines": {
        "default": "pdflatex",
        "modern_default": "lualatex",
        "strict_detection": False,
    },
    "routing": {
        "source_suffix": "-tex",
        "output_suffix": "-pdfs",
        "preserve_relative": True,
        "collapse_entrypoint_names": False,
        "entrypoint_names": ["main", "index"],
    },
    "routes": {},
    "variants": {},
}


def resolve_config(merged: dict[str, Any], provenance: list[str]) -> ResolvedConfig:
    """Construct a ResolvedConfig from a merged config dict."""
    build_data = merged.get("build", {})
    engines_data = merged.get("engines", {})
    routing_data = merged.get("routing", {})

    return ResolvedConfig(
        schema_version=merged.get("schema_version", 1),
        build=BuildConfig(
            out_dir_name=build_data.get("out_dir_name", ".ktisma_build"),
            cleanup=CleanupPolicy(build_data.get("cleanup", "on_output_success")),
            synctex=build_data.get("synctex", True),
        ),
        engines=EngineConfig(
            default=engines_data.get("default", "pdflatex"),
            modern_default=engines_data.get("modern_default", "lualatex"),
            strict_detection=engines_data.get("strict_detection", False),
        ),
        routing=RoutingConfig(
            source_suffix=routing_data.get("source_suffix", "-tex"),
            output_suffix=routing_data.get("output_suffix", "-pdfs"),
            preserve_relative=routing_data.get("preserve_relative", True),
            collapse_entrypoint_names=routing_data.get("collapse_entrypoint_names", False),
            entrypoint_names=routing_data.get("entrypoint_names", ["main", "index"]),
        ),
        routes=dict(merged.get("routes", {})),
        variants=dict(merged.get("variants", {})),
        provenance=list(provenance),
    )


def default_config() -> ResolvedConfig:
    """Return a ResolvedConfig with all built-in defaults."""
    return resolve_config(BUILTIN_DEFAULTS, ["built-in defaults"])
