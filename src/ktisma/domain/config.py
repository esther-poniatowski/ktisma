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
    source: Optional[Path]  # Declaring config file path; None for built-in defaults and CLI
    label: str  # human-readable provenance description
    base_dir: Optional[Path] = None  # Directory to anchor relative paths against; set by infra


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
    default_filename_suffix: str = ""
    variant_filename_suffix: str = "_{variant}"


@dataclass(frozen=True)
class VariantConfig:
    payload: str = ""
    engine: Optional[str] = None
    output: Optional[str] = None
    filename_suffix: Optional[str] = None


@dataclass(frozen=True)
class ResolvedConfig:
    schema_version: int = 1
    build: BuildConfig = field(default_factory=BuildConfig)
    engines: EngineConfig = field(default_factory=EngineConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    routes: dict[str, str] = field(default_factory=dict)
    variants: dict[str, VariantConfig] = field(default_factory=dict)
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
        "default_filename_suffix",
        "variant_filename_suffix",
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
        out_dir_name = build.get("out_dir_name")
        if out_dir_name is not None and not isinstance(out_dir_name, str):
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="config",
                    code="type-mismatch",
                    message=f"'build.out_dir_name' must be a string, got {type(out_dir_name).__name__}.",
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
            if val is not None:
                if not isinstance(val, str):
                    diagnostics.append(
                        Diagnostic(
                            level=DiagnosticLevel.ERROR,
                            component="config",
                            code="type-mismatch",
                            message=f"'engines.{key}' must be a string, got {type(val).__name__}.",
                        )
                    )
                elif val not in VALID_ENGINES:
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
        for key in (
            "source_suffix",
            "output_suffix",
            "default_filename_suffix",
            "variant_filename_suffix",
        ):
            val = routing.get(key)
            if val is not None and not isinstance(val, str):
                diagnostics.append(
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        component="config",
                        code="type-mismatch",
                        message=f"'routing.{key}' must be a string, got {type(val).__name__}.",
                    )
                )
            elif val is not None and key in {"default_filename_suffix", "variant_filename_suffix"}:
                _validate_filename_suffix_template(
                    section=f"routing.{key}",
                    template=val,
                    diagnostics=diagnostics,
                )
        for key in ("preserve_relative", "collapse_entrypoint_names"):
            val = routing.get(key)
            if val is not None and not isinstance(val, bool):
                diagnostics.append(
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        component="config",
                        code="type-mismatch",
                        message=f"'routing.{key}' must be a boolean, got {type(val).__name__}.",
                    )
                )
        entrypoint_names = routing.get("entrypoint_names")
        if entrypoint_names is not None:
            if not isinstance(entrypoint_names, list):
                diagnostics.append(
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        component="config",
                        code="type-mismatch",
                        message=f"'routing.entrypoint_names' must be an array, got {type(entrypoint_names).__name__}.",
                    )
                )
            else:
                for i, name in enumerate(entrypoint_names):
                    if not isinstance(name, str):
                        diagnostics.append(
                            Diagnostic(
                                level=DiagnosticLevel.ERROR,
                                component="config",
                                code="type-mismatch",
                                message=(
                                    f"'routing.entrypoint_names[{i}]' must be a string, "
                                    f"got {type(name).__name__}."
                                ),
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
    else:
        for pattern, target in routes.items():
            if not isinstance(pattern, str):
                diagnostics.append(
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        component="config",
                        code="type-mismatch",
                        message=(
                            f"'routes' keys must be strings, got {type(pattern).__name__}."
                        ),
                    )
                )
            if not isinstance(target, str):
                diagnostics.append(
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        component="config",
                        code="type-mismatch",
                        message=(
                            f"'routes.{pattern}' must be a string, got {type(target).__name__}."
                        ),
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
    else:
        for name, definition in variants.items():
            if not isinstance(name, str):
                diagnostics.append(
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        component="config",
                        code="type-mismatch",
                        message=(
                            f"'variants' keys must be strings, got {type(name).__name__}."
                        ),
                    )
                )
                continue
            if not _is_valid_variant_name(name):
                diagnostics.append(
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        component="config",
                        code="invalid-variant-name",
                        message=(
                            f"'variants.{name}' is not a valid variant name; "
                            "names must start with a letter and contain only letters, "
                            "numbers, underscores, and dashes."
                        ),
                    )
                )
            if isinstance(definition, str):
                continue
            if not isinstance(definition, dict):
                diagnostics.append(
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        component="config",
                        code="type-mismatch",
                        message=(
                            f"'variants.{name}' must be a string or table, "
                            f"got {type(definition).__name__}."
                        ),
                    )
                )
                continue
            _validate_variant_definition(name, definition, diagnostics)

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


def _validate_variant_definition(
    name: str,
    definition: dict[str, Any],
    diagnostics: list[Diagnostic],
) -> None:
    allowed = {"payload", "engine", "output", "filename_suffix"}
    for key in definition:
        if key not in allowed:
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="config",
                    code="unknown-key",
                    message=f"'variants.{name}.{key}' is not a recognized key in schema version 1.",
                )
            )

    payload = definition.get("payload")
    if payload is not None and not isinstance(payload, str):
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="config",
                code="type-mismatch",
                message=(
                    f"'variants.{name}.payload' must be a string, got {type(payload).__name__}."
                ),
            )
        )

    engine = definition.get("engine")
    if engine is not None:
        if not isinstance(engine, str):
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="config",
                    code="type-mismatch",
                    message=(
                        f"'variants.{name}.engine' must be a string, got {type(engine).__name__}."
                    ),
                )
            )
        elif engine not in VALID_ENGINES:
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="config",
                    code="invalid-engine",
                    message=(
                        f"'variants.{name}.engine' is '{engine}'; valid engines: "
                        f"{', '.join(sorted(VALID_ENGINES))}."
                    ),
                )
            )

    output = definition.get("output")
    if output is not None and not isinstance(output, str):
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="config",
                code="type-mismatch",
                message=(
                    f"'variants.{name}.output' must be a string, got {type(output).__name__}."
                ),
            )
        )

    filename_suffix = definition.get("filename_suffix")
    if filename_suffix is not None:
        if not isinstance(filename_suffix, str):
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="config",
                    code="type-mismatch",
                    message=(
                        f"'variants.{name}.filename_suffix' must be a string, "
                        f"got {type(filename_suffix).__name__}."
                    ),
                )
            )
        else:
            _validate_filename_suffix_template(
                section=f"variants.{name}.filename_suffix",
                template=filename_suffix,
                diagnostics=diagnostics,
            )


def _is_valid_variant_name(name: str) -> bool:
    import re

    return bool(re.fullmatch(r"^[a-zA-Z][a-zA-Z0-9_-]*$", name))


def _validate_filename_suffix_template(
    section: str,
    template: str,
    diagnostics: list[Diagnostic],
) -> None:
    try:
        template.format(stem="example", variant="alt")
    except KeyError as exc:
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="config",
                code="invalid-template",
                message=(
                    f"'{section}' contains unknown placeholder {exc}; "
                    "allowed placeholders are {stem} and {variant}."
                ),
            )
        )
    except ValueError as exc:
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.ERROR,
                component="config",
                code="invalid-template",
                message=f"'{section}' is not a valid format string: {exc}.",
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
            prepared = _prepare_layer_for_merge(copy.deepcopy(layer.data), layer)
            _deep_merge(merged, prepared)
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


def _prepare_layer_for_merge(data: dict[str, Any], layer: ConfigLayer) -> dict[str, Any]:
    """Normalize layer-local path semantics before precedence merging.

    This is a pure transformation: it anchors relative route targets to the
    layer's base_dir using only Path arithmetic (no I/O).
    """
    base_dir = layer.base_dir
    if base_dir is None:
        return data

    routes = data.get("routes")
    if isinstance(routes, dict):
        anchored_routes: dict[str, Any] = {}
        for pattern, target in routes.items():
            if isinstance(target, str):
                anchored_routes[pattern] = _anchor_config_path(target, base_dir)
            else:
                anchored_routes[pattern] = target
        data["routes"] = anchored_routes

    return data


def _anchor_config_path(raw_path: str, base_dir: Path) -> str:
    """Anchor a config-declared path to the declaring config directory.

    Pure path arithmetic only — no filesystem access.
    Tilde expansion and symlink resolution are handled at the application boundary.
    """
    keep_trailing_sep = raw_path.endswith("/")
    anchored = Path(raw_path)
    if not anchored.is_absolute():
        anchored = base_dir / anchored
    normalized_str = str(anchored)
    if keep_trailing_sep and not normalized_str.endswith("/"):
        return normalized_str + "/"
    return normalized_str


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
        "default_filename_suffix": "",
        "variant_filename_suffix": "_{variant}",
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
            default_filename_suffix=routing_data.get("default_filename_suffix", ""),
            variant_filename_suffix=routing_data.get("variant_filename_suffix", "_{variant}"),
        ),
        routes=dict(merged.get("routes", {})),
        variants={
            name: _resolve_variant_config(name, definition)
            for name, definition in merged.get("variants", {}).items()
        },
        provenance=list(provenance),
    )


def default_config() -> ResolvedConfig:
    """Return a ResolvedConfig with all built-in defaults."""
    return resolve_config(BUILTIN_DEFAULTS, ["built-in defaults"])


def _resolve_variant_config(name: str, definition: Any) -> VariantConfig:
    if isinstance(definition, str):
        return VariantConfig(payload=definition)
    if isinstance(definition, dict):
        return VariantConfig(
            payload=definition.get("payload", ""),
            engine=definition.get("engine"),
            output=definition.get("output"),
            filename_suffix=definition.get("filename_suffix"),
        )
    raise TypeError(f"Variant '{name}' must resolve to a string or table definition.")
