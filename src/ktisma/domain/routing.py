from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Callable, Optional

from .config import ResolvedConfig
from .context import SourceContext, SourceInputs
from .diagnostics import Diagnostic, DiagnosticLevel


@dataclass(frozen=True)
class RouteDecision:
    destination: Path
    matched_rule: Optional[str] = None
    fallback: bool = False
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def to_dict(self, source: Path) -> dict:
        return {
            "source": str(source),
            "destination": str(self.destination),
            "matched_rule": self.matched_rule,
            "fallback": self.fallback,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }


RouteResolver = Callable[
    [SourceContext, SourceInputs, ResolvedConfig, str],
    Optional[RouteDecision],
]


def resolve_route(
    ctx: SourceContext,
    source_inputs: SourceInputs,
    config: ResolvedConfig,
    output_path_override: Optional[Path] = None,
    output_dir_override: Optional[Path] = None,
    extra_resolvers: Optional[list[RouteResolver]] = None,
) -> RouteDecision:
    """Resolve the output destination for a compiled PDF.

    Precedence per roadmap:
    1. CLI output-file override
    2. CLI output-directory override
    3. Magic-comment output override
    4. Custom route resolvers
    5. Explicit config route rules
    6. Suffix convention
    7. Safe fallback beside the source file
    """
    pdf_name = ctx.source_file.stem + ".pdf"

    # Step 1: CLI output-file override
    if output_path_override is not None:
        return RouteDecision(destination=output_path_override, matched_rule="--output")

    # Step 2: CLI output-directory override
    if output_dir_override is not None:
        dest = output_dir_override / pdf_name
        return RouteDecision(destination=dest, matched_rule="--output-dir")

    # Step 3: Magic comment override
    magic_output = source_inputs.magic_comments.get("output")
    if magic_output:
        magic_path = Path(magic_output)
        if not magic_path.is_absolute():
            magic_path = ctx.source_dir / magic_path
        if str(magic_output).endswith("/") or not magic_path.suffix:
            dest = magic_path / pdf_name
        else:
            dest = magic_path
        return RouteDecision(destination=dest, matched_rule="% !ktisma output")

    # Step 4: Custom route resolvers
    for resolver in extra_resolvers or []:
        resolved = resolver(ctx, source_inputs, config, pdf_name)
        if resolved is not None:
            return resolved

    # Step 5: Explicit config route rules
    route_result = _match_route_rules(ctx, config, pdf_name)
    if route_result is not None:
        return route_result

    # Step 6: Suffix convention
    suffix_result = _apply_suffix_convention(ctx, config, pdf_name)
    if suffix_result is not None:
        return suffix_result

    # Step 7: Safe fallback
    dest = ctx.source_dir / pdf_name
    diagnostics: list[Diagnostic] = []
    if not _is_within_workspace(ctx):
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.WARNING,
                component="routing",
                code="source-outside-workspace",
                message=(
                    f"Source '{ctx.source_file}' is outside workspace root '{ctx.workspace_root}'; "
                    "workspace-relative routes and suffix conventions were skipped."
                ),
            )
        )
    diagnostics.append(
        Diagnostic(
            level=DiagnosticLevel.INFO,
            component="routing",
            code="fallback-routing",
            message=(
                f"No routing rule or convention matched; "
                f"placing output beside source file: {dest}"
            ),
        )
    )
    return RouteDecision(
        destination=dest,
        fallback=True,
        diagnostics=diagnostics,
    )


def _match_route_rules(
    ctx: SourceContext, config: ResolvedConfig, pdf_name: str
) -> Optional[RouteDecision]:
    """Match source file against explicit config route rules.

    Specificity per roadmap:
    1. Prefer exact file matches over glob matches.
    2. Otherwise prefer the rule with more literal path segments.
    3. Otherwise prefer the rule with fewer wildcard segments.
    4. If remaining candidates resolve to the same destination, proceed silently.
    5. Otherwise warn and use first matching rule in declaration order.
    """
    if not config.routes:
        return None

    try:
        rel_source = ctx.source_file.relative_to(ctx.workspace_root)
    except ValueError:
        return None

    rel_str = str(PurePosixPath(rel_source))

    matches: list[tuple[str, str, int]] = []  # (pattern, target, specificity_score)
    for pattern, target in config.routes.items():
        if fnmatch.fnmatch(rel_str, pattern):
            score = _specificity_score(pattern)
            matches.append((pattern, target, score))

    if not matches:
        return None

    matches.sort(key=lambda m: m[2], reverse=True)
    best_score = matches[0][2]
    top_matches = [m for m in matches if m[2] == best_score]

    diagnostics: list[Diagnostic] = []
    pattern, target, _ = top_matches[0]

    if len(top_matches) > 1:
        destinations = {
            _resolve_route_target(ctx, candidate_pattern, t, pdf_name, rel_source)
            for candidate_pattern, t, _ in top_matches
        }
        if len(destinations) > 1:
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.WARNING,
                    component="routing",
                    code="ambiguous-route",
                    message=(
                        f"Multiple route rules match '{rel_str}' with equal specificity; "
                        f"using first in declaration order: '{pattern}'."
                    ),
                    )
                )

    dest = _resolve_route_target(ctx, pattern, target, pdf_name, rel_source)
    return RouteDecision(destination=dest, matched_rule=pattern, diagnostics=diagnostics)


def _resolve_route_target(
    ctx: SourceContext,
    pattern: str,
    target: str,
    pdf_name: str,
    rel_source: Path,
) -> Path:
    """Resolve a route target to an absolute destination path."""
    target_path = Path(target)
    if not target_path.is_absolute():
        target_path = ctx.workspace_root / target_path

    if _is_explicit_file_target(target):
        return target_path

    relative_parent = _matched_relative_parent(pattern, rel_source)
    return target_path / relative_parent / pdf_name


def _is_explicit_file_target(target: str) -> bool:
    return not target.endswith("/") and Path(target).suffix != ""


def _matched_relative_parent(pattern: str, rel_source: Path) -> Path:
    """Return the relative parent path preserved by a wildcard route match."""
    if "*" not in pattern and "?" not in pattern:
        return Path()

    prefix_parts: list[str] = []
    for part in PurePosixPath(pattern).parts:
        if "*" in part or "?" in part:
            break
        prefix_parts.append(part)

    rel_parts = PurePosixPath(rel_source).parts
    suffix_parts = rel_parts[len(prefix_parts) :]
    if not suffix_parts:
        return Path()
    return Path(*suffix_parts).parent


def _specificity_score(pattern: str) -> int:
    """Compute a specificity score for a route pattern.

    Higher score = more specific.
    Exact matches (no wildcards) get the highest score.
    """
    parts = PurePosixPath(pattern).parts
    if "*" not in pattern and "?" not in pattern:
        return len(parts) * 100  # exact match bonus

    literal_count = sum(1 for p in parts if "*" not in p and "?" not in p)
    wildcard_count = sum(1 for p in parts if "*" in p or "?" in p)
    return literal_count * 10 - wildcard_count


def _apply_suffix_convention(
    ctx: SourceContext, config: ResolvedConfig, pdf_name: str
) -> Optional[RouteDecision]:
    """Apply the -tex -> -pdfs suffix naming convention.

    Built-in convention:
    - *-tex/ maps to sibling *-pdfs/
    - The -tex directory may appear at any depth below the workspace root
    - preserve relative path beneath the matched -tex directory
    - preserve source basename
    """
    source_suffix = config.routing.source_suffix
    output_suffix = config.routing.output_suffix

    try:
        rel_source = ctx.source_file.relative_to(ctx.workspace_root)
    except ValueError:
        return None

    parts = rel_source.parts
    if not parts:
        return None

    # Find the deepest directory component ending with the source suffix.
    # Scan right-to-left (skipping the filename) to match the nearest ancestor,
    # consistent with the behavior of walking up from the source file.
    matching_indices = [
        i for i in range(len(parts) - 2, -1, -1) if parts[i].endswith(source_suffix)
    ]

    if not matching_indices:
        return None
    matched_index = matching_indices[0]
    diagnostics: list[Diagnostic] = []
    if len(matching_indices) > 1:
        selected = parts[matched_index]
        ignored = [parts[i] for i in matching_indices[1:]]
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.WARNING,
                component="routing",
                code="multiple-source-suffix-matches",
                message=(
                    f"Multiple '*{source_suffix}' ancestors match '{rel_source}'; "
                    f"using nearest ancestor '{selected}' and ignoring {ignored}."
                ),
            )
        )

    prefix_parts = parts[:matched_index]
    matched_dir = parts[matched_index]
    output_dir_name = matched_dir[: -len(source_suffix)] + output_suffix
    inner_parts = parts[matched_index + 1 :]  # after the matched dir, includes filename
    inner_dirs = inner_parts[:-1]  # directory parts between -tex dir and file

    if prefix_parts:
        base = ctx.workspace_root / Path(*prefix_parts) / output_dir_name
    else:
        base = ctx.workspace_root / output_dir_name

    if config.routing.collapse_entrypoint_names and inner_dirs:
        stem = ctx.source_file.stem
        if stem in config.routing.entrypoint_names:
            parent_name = inner_dirs[-1]
            collapsed_name = parent_name + ".pdf"
            remaining = Path(*inner_dirs[:-1]) if len(inner_dirs) > 1 else Path()
            dest = base / remaining / collapsed_name
            return RouteDecision(
                destination=dest,
                matched_rule=f"suffix convention ({source_suffix} -> {output_suffix}) + entrypoint collapse",
                diagnostics=diagnostics,
            )

    if config.routing.preserve_relative and inner_dirs:
        remaining = Path(*inner_dirs)
        dest = base / remaining / pdf_name
    else:
        dest = base / pdf_name

    return RouteDecision(
        destination=dest,
        matched_rule=f"suffix convention ({source_suffix} -> {output_suffix})",
        diagnostics=diagnostics,
    )


def _is_within_workspace(ctx: SourceContext) -> bool:
    try:
        ctx.source_file.relative_to(ctx.workspace_root)
        return True
    except ValueError:
        return False
