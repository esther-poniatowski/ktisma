from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Optional

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


def resolve_route(
    ctx: SourceContext,
    source_inputs: SourceInputs,
    config: ResolvedConfig,
    output_dir_override: Optional[Path] = None,
) -> RouteDecision:
    """Resolve the output destination for a compiled PDF.

    Precedence per roadmap:
    1. CLI output override
    2. Magic-comment output override
    3. Explicit config route rules
    4. Suffix convention
    5. Safe fallback beside the source file
    """
    pdf_name = ctx.source_file.stem + ".pdf"

    # Step 1: CLI override
    if output_dir_override is not None:
        dest = output_dir_override / pdf_name
        return RouteDecision(destination=dest, matched_rule="--output-dir")

    # Step 2: Magic comment override
    magic_output = source_inputs.magic_comments.get("output")
    if magic_output:
        magic_path = Path(magic_output).expanduser()
        if not magic_path.is_absolute():
            magic_path = ctx.source_dir / magic_path
        if str(magic_output).endswith("/") or not magic_path.suffix:
            dest = magic_path / pdf_name
        else:
            dest = magic_path
        return RouteDecision(destination=dest, matched_rule="% !ktisma output")

    # Step 3: Explicit config route rules
    route_result = _match_route_rules(ctx, config, pdf_name)
    if route_result is not None:
        return route_result

    # Step 4: Suffix convention
    suffix_result = _apply_suffix_convention(ctx, config, pdf_name)
    if suffix_result is not None:
        return suffix_result

    # Step 5: Safe fallback
    dest = ctx.source_dir / pdf_name
    return RouteDecision(
        destination=dest,
        fallback=True,
        diagnostics=[
            Diagnostic(
                level=DiagnosticLevel.INFO,
                component="routing",
                code="fallback-routing",
                message=(
                    f"No routing rule or convention matched; "
                    f"placing output beside source file: {dest}"
                ),
            )
        ],
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
        destinations = {_resolve_route_target(ctx, t, pdf_name, rel_source) for _, t, _ in top_matches}
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

    dest = _resolve_route_target(ctx, target, pdf_name, rel_source)
    return RouteDecision(destination=dest, matched_rule=pattern, diagnostics=diagnostics)


def _resolve_route_target(
    ctx: SourceContext, target: str, pdf_name: str, rel_source: Path
) -> Path:
    """Resolve a route target to an absolute destination path."""
    target_path = Path(target).expanduser()
    if not target_path.is_absolute():
        target_path = ctx.workspace_root / target_path

    if target.endswith("/"):
        return target_path / pdf_name
    return target_path / pdf_name


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
    - preserve relative path beneath the source root
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

    top_dir = parts[0]
    if not top_dir.endswith(source_suffix):
        return None

    output_dir_name = top_dir[: -len(source_suffix)] + output_suffix

    if config.routing.collapse_entrypoint_names and len(parts) >= 3:
        stem = ctx.source_file.stem
        if stem in config.routing.entrypoint_names:
            parent_name = parts[-2] if len(parts) >= 2 else stem
            collapsed_name = parent_name + ".pdf"
            remaining = Path(*parts[1:-1]) if len(parts) > 2 else Path()
            dest = ctx.workspace_root / output_dir_name / remaining / collapsed_name
            return RouteDecision(
                destination=dest,
                matched_rule=f"suffix convention ({source_suffix} -> {output_suffix}) + entrypoint collapse",
            )

    if config.routing.preserve_relative and len(parts) > 1:
        remaining = Path(*parts[1:]).parent
        dest = ctx.workspace_root / output_dir_name / remaining / pdf_name
    else:
        dest = ctx.workspace_root / output_dir_name / pdf_name

    return RouteDecision(
        destination=dest,
        matched_rule=f"suffix convention ({source_suffix} -> {output_suffix})",
    )
