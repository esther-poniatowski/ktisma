"""Tests for ktisma.domain.routing — route resolution with precedence chain."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

from ktisma.domain.config import ResolvedConfig, RoutingConfig, default_config
from ktisma.domain.context import SourceContext, SourceInputs
from ktisma.domain.diagnostics import DiagnosticLevel
from ktisma.domain.routing import (
    RouteDecision,
    _apply_suffix_convention,
    _match_route_rules,
    _specificity_score,
    resolve_route,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WS = Path("/workspace")


def _ctx(
    source: str = "project-tex/ch1/main.tex",
    workspace: Path = WS,
) -> SourceContext:
    source_path = workspace / source
    return SourceContext(
        source_file=source_path,
        source_dir=source_path.parent,
        workspace_root=workspace,
    )


def _inputs(magic: Optional[dict[str, str]] = None) -> SourceInputs:
    return SourceInputs(preamble="", magic_comments=magic or {})


def _cfg(
    routes: Optional[dict[str, str]] = None,
    source_suffix: str = "-tex",
    output_suffix: str = "-pdfs",
    preserve_relative: bool = True,
    collapse_entrypoint_names: bool = False,
    entrypoint_names: Optional[list[str]] = None,
) -> ResolvedConfig:
    base = default_config()
    return ResolvedConfig(
        schema_version=base.schema_version,
        build=base.build,
        engines=base.engines,
        routing=RoutingConfig(
            source_suffix=source_suffix,
            output_suffix=output_suffix,
            preserve_relative=preserve_relative,
            collapse_entrypoint_names=collapse_entrypoint_names,
            entrypoint_names=entrypoint_names if entrypoint_names is not None else ["main", "index"],
        ),
        routes=routes or {},
        variants=base.variants,
        provenance=base.provenance,
    )


# ---------------------------------------------------------------------------
# 1. CLI override (highest precedence)
# ---------------------------------------------------------------------------


class TestCLIOverride:
    def test_cli_override_wins(self) -> None:
        ctx = _ctx()
        decision = resolve_route(ctx, _inputs(), default_config(), output_dir_override=Path("/out"))
        assert decision.destination == Path("/out/main.pdf")
        assert decision.matched_rule == "--output-dir"
        assert decision.fallback is False

    def test_cli_override_uses_source_stem(self) -> None:
        ctx = _ctx(source="project-tex/thesis.tex")
        decision = resolve_route(ctx, _inputs(), default_config(), output_dir_override=Path("/build"))
        assert decision.destination == Path("/build/thesis.pdf")

    def test_cli_override_ignores_config_routes(self) -> None:
        cfg = _cfg(routes={"project-tex/*.tex": "routed/"})
        ctx = _ctx(source="project-tex/main.tex")
        decision = resolve_route(ctx, _inputs(), cfg, output_dir_override=Path("/cli"))
        assert decision.destination == Path("/cli/main.pdf")
        assert decision.matched_rule == "--output-dir"


# ---------------------------------------------------------------------------
# 2. Magic comment override
# ---------------------------------------------------------------------------


class TestMagicCommentRouting:
    def test_magic_comment_directory(self) -> None:
        ctx = _ctx(source="project-tex/main.tex")
        inputs = _inputs(magic={"output": "output/"})
        decision = resolve_route(ctx, inputs, default_config())
        assert decision.matched_rule == "% !ktisma output"
        # Trailing slash -> directory -> pdf_name appended
        assert decision.destination.name == "main.pdf"

    def test_magic_comment_relative_path(self) -> None:
        ctx = _ctx(source="project-tex/main.tex")
        inputs = _inputs(magic={"output": "../pdfs/"})
        decision = resolve_route(ctx, inputs, default_config())
        assert decision.matched_rule == "% !ktisma output"
        # Relative path resolved from source_dir
        assert "pdfs" in str(decision.destination)

    def test_magic_comment_absolute_path(self) -> None:
        ctx = _ctx(source="project-tex/main.tex")
        inputs = _inputs(magic={"output": "/absolute/output/"})
        decision = resolve_route(ctx, inputs, default_config())
        assert decision.destination == Path("/absolute/output/main.pdf")

    def test_magic_comment_explicit_filename(self) -> None:
        ctx = _ctx(source="project-tex/main.tex")
        inputs = _inputs(magic={"output": "output/custom.pdf"})
        decision = resolve_route(ctx, inputs, default_config())
        assert decision.destination.name == "custom.pdf"

    def test_magic_comment_overrides_config_routes(self) -> None:
        cfg = _cfg(routes={"project-tex/main.tex": "routed/"})
        ctx = _ctx(source="project-tex/main.tex")
        inputs = _inputs(magic={"output": "/magic/"})
        decision = resolve_route(ctx, inputs, cfg)
        assert decision.matched_rule == "% !ktisma output"


# ---------------------------------------------------------------------------
# 3. Config route rules
# ---------------------------------------------------------------------------


class TestConfigRouteRules:
    def test_exact_file_route(self) -> None:
        cfg = _cfg(routes={"project-tex/ch1/main.tex": "output/ch1/"})
        ctx = _ctx(source="project-tex/ch1/main.tex")
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.matched_rule == "project-tex/ch1/main.tex"
        assert decision.destination == WS / "output/ch1/main.pdf"

    def test_glob_route(self) -> None:
        cfg = _cfg(routes={"project-tex/*.tex": "output/"})
        ctx = _ctx(source="project-tex/thesis.tex")
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.matched_rule == "project-tex/*.tex"
        assert decision.destination == WS / "output/thesis.pdf"

    def test_no_matching_route_falls_through(self) -> None:
        cfg = _cfg(routes={"other/*.tex": "output/"})
        ctx = _ctx(source="project-tex/ch1/main.tex")
        decision = resolve_route(ctx, _inputs(), cfg)
        # Should fall through to suffix convention or fallback, not the route
        assert decision.matched_rule != "other/*.tex"

    def test_route_target_relative_to_workspace(self) -> None:
        cfg = _cfg(routes={"project-tex/main.tex": "build/"})
        ctx = _ctx(source="project-tex/main.tex")
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.destination == WS / "build/main.pdf"

    def test_wildcard_route_preserves_relative_subtree(self) -> None:
        cfg = _cfg(routes={"lectures-tex/**": "lectures-pdfs/"})
        ctx = _ctx(source="lectures-tex/week1/notes.tex")
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.destination == WS / "lectures-pdfs/week1/notes.pdf"


# ---------------------------------------------------------------------------
# 3a. Route specificity scoring
# ---------------------------------------------------------------------------


class TestSpecificityScore:
    def test_exact_match_highest(self) -> None:
        exact = _specificity_score("project-tex/ch1/main.tex")
        glob_score = _specificity_score("project-tex/ch1/*.tex")
        assert exact > glob_score

    def test_more_literal_segments_higher(self) -> None:
        two_literal = _specificity_score("project-tex/ch1/*.tex")
        one_literal = _specificity_score("project-tex/*.tex")
        assert two_literal > one_literal

    def test_fewer_wildcards_higher(self) -> None:
        one_wild = _specificity_score("project-tex/*.tex")
        two_wild = _specificity_score("*/*.tex")
        assert one_wild > two_wild

    def test_exact_match_no_wildcards(self) -> None:
        score = _specificity_score("a/b/c.tex")
        # exact match: len(parts)*100 = 3*100 = 300
        assert score == 300

    def test_all_wildcards(self) -> None:
        score = _specificity_score("*/*/*.tex")
        # literal_count=0 (*.tex has * in it? No, "*.tex" contains *), wait:
        # parts = ("*", "*", "*.tex"); all contain *
        # literal_count=0, wildcard_count=3 => 0*10 - 3 = -3
        assert score < 0

    def test_single_glob_segment(self) -> None:
        score = _specificity_score("*.tex")
        # parts=("*.tex",); literal=0, wildcard=1 => -1
        assert score == -1


# ---------------------------------------------------------------------------
# 3b. Ambiguous routes (equal specificity, different destinations)
# ---------------------------------------------------------------------------


class TestAmbiguousRoutes:
    def test_equal_specificity_same_destination_no_warning(self) -> None:
        cfg = _cfg(routes={
            "project-tex/*.tex": "output/",
            "project-tex/?.tex": "output/",
        })
        ctx = _ctx(source="project-tex/a.tex")
        decision = resolve_route(ctx, _inputs(), cfg)
        # Same destination -> no ambiguous warning
        warning_diags = [d for d in decision.diagnostics if d.code == "ambiguous-route"]
        assert warning_diags == []

    def test_equal_specificity_different_destinations_warns(self) -> None:
        cfg = _cfg(routes={
            "project-tex/*.tex": "output_a/",
            "project-tex/?.tex": "output_b/",
        })
        ctx = _ctx(source="project-tex/a.tex")
        decision = resolve_route(ctx, _inputs(), cfg)
        warning_diags = [d for d in decision.diagnostics if d.code == "ambiguous-route"]
        assert len(warning_diags) == 1
        assert warning_diags[0].level is DiagnosticLevel.WARNING


# ---------------------------------------------------------------------------
# 4. Suffix convention
# ---------------------------------------------------------------------------


class TestSuffixConvention:
    def test_basic_suffix_convention(self) -> None:
        """project-tex/ -> project-pdfs/"""
        ctx = _ctx(source="project-tex/main.tex")
        cfg = _cfg()
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.destination == WS / "project-pdfs/main.pdf"
        assert "suffix convention" in (decision.matched_rule or "")

    def test_preserve_relative_path(self) -> None:
        """project-tex/ch1/main.tex -> project-pdfs/ch1/main.pdf"""
        ctx = _ctx(source="project-tex/ch1/main.tex")
        cfg = _cfg(preserve_relative=True)
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.destination == WS / "project-pdfs/ch1/main.pdf"

    def test_no_preserve_relative(self) -> None:
        """With preserve_relative=False, flatten output."""
        ctx = _ctx(source="project-tex/ch1/main.tex")
        cfg = _cfg(preserve_relative=False)
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.destination == WS / "project-pdfs/main.pdf"

    def test_custom_suffixes(self) -> None:
        ctx = _ctx(source="docs-src/paper.tex")
        cfg = _cfg(source_suffix="-src", output_suffix="-out")
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.destination == WS / "docs-out/paper.pdf"

    def test_no_suffix_match_falls_through(self) -> None:
        """Directory not ending in source_suffix -> no suffix convention match."""
        ctx = _ctx(source="random_dir/paper.tex")
        cfg = _cfg()
        decision = resolve_route(ctx, _inputs(), cfg)
        # Should hit fallback since "random_dir" does not end with "-tex"
        assert decision.fallback is True

    def test_source_in_root_of_suffix_dir(self) -> None:
        """File directly in project-tex/ (no subdirectory)."""
        ctx = _ctx(source="project-tex/paper.tex")
        cfg = _cfg(preserve_relative=True)
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.destination == WS / "project-pdfs/paper.pdf"


# ---------------------------------------------------------------------------
# 4a. collapse_entrypoint_names
# ---------------------------------------------------------------------------


class TestCollapseEntrypointNames:
    def test_collapse_main_tex(self) -> None:
        """project-tex/ch1/main.tex -> project-pdfs/ch1.pdf

        Per roadmap: the parent directory name replaces the entrypoint filename,
        and the parent directory is eliminated from the path.
        """
        ctx = _ctx(source="project-tex/ch1/main.tex")
        cfg = _cfg(collapse_entrypoint_names=True)
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.destination == WS / "project-pdfs/ch1.pdf"
        assert "entrypoint collapse" in (decision.matched_rule or "")

    def test_collapse_index_tex(self) -> None:
        """project-tex/ch1/index.tex -> project-pdfs/ch1.pdf"""
        ctx = _ctx(source="project-tex/ch1/index.tex")
        cfg = _cfg(collapse_entrypoint_names=True)
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.destination == WS / "project-pdfs/ch1.pdf"

    def test_collapse_custom_entrypoint(self) -> None:
        ctx = _ctx(source="project-tex/ch1/document.tex")
        cfg = _cfg(collapse_entrypoint_names=True, entrypoint_names=["document"])
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.destination == WS / "project-pdfs/ch1.pdf"

    def test_no_collapse_for_non_entrypoint(self) -> None:
        """Non-entrypoint names should NOT collapse."""
        ctx = _ctx(source="project-tex/ch1/paper.tex")
        cfg = _cfg(collapse_entrypoint_names=True)
        decision = resolve_route(ctx, _inputs(), cfg)
        # "paper" is not in default entrypoint_names ["main", "index"]
        assert decision.destination.name == "paper.pdf"

    def test_no_collapse_when_disabled(self) -> None:
        """With collapse_entrypoint_names=False, no collapsing."""
        ctx = _ctx(source="project-tex/ch1/main.tex")
        cfg = _cfg(collapse_entrypoint_names=False)
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.destination == WS / "project-pdfs/ch1/main.pdf"

    def test_collapse_nested_subdirectory(self) -> None:
        """project-tex/part1/ch1/main.tex -> project-pdfs/part1/ch1.pdf

        Per roadmap: intermediate dirs are preserved, but the entrypoint's
        parent dir collapses into the filename.
        """
        ctx = _ctx(source="project-tex/part1/ch1/main.tex")
        cfg = _cfg(collapse_entrypoint_names=True)
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.destination == WS / "project-pdfs/part1/ch1.pdf"


# ---------------------------------------------------------------------------
# 5. Fallback (lowest precedence)
# ---------------------------------------------------------------------------


class TestFallbackRouting:
    def test_fallback_beside_source(self) -> None:
        ctx = _ctx(source="random/paper.tex")
        cfg = _cfg()
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.fallback is True
        assert decision.destination == WS / "random/paper.pdf"

    def test_fallback_diagnostic(self) -> None:
        ctx = _ctx(source="random/paper.tex")
        cfg = _cfg()
        decision = resolve_route(ctx, _inputs(), cfg)
        assert len(decision.diagnostics) == 1
        assert decision.diagnostics[0].code == "fallback-routing"
        assert decision.diagnostics[0].level is DiagnosticLevel.INFO

    def test_fallback_matched_rule_is_none(self) -> None:
        ctx = _ctx(source="random/paper.tex")
        cfg = _cfg()
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.matched_rule is None


# ---------------------------------------------------------------------------
# Full precedence chain
# ---------------------------------------------------------------------------


class TestPrecedenceChain:
    def test_cli_beats_magic(self) -> None:
        ctx = _ctx(source="project-tex/main.tex")
        inputs = _inputs(magic={"output": "/magic/"})
        decision = resolve_route(ctx, inputs, default_config(), output_dir_override=Path("/cli"))
        assert decision.matched_rule == "--output-dir"
        assert decision.destination == Path("/cli/main.pdf")

    def test_magic_beats_config_route(self) -> None:
        cfg = _cfg(routes={"project-tex/main.tex": "routed/"})
        ctx = _ctx(source="project-tex/main.tex")
        inputs = _inputs(magic={"output": "/magic/"})
        decision = resolve_route(ctx, inputs, cfg)
        assert decision.matched_rule == "% !ktisma output"

    def test_config_route_beats_suffix_convention(self) -> None:
        cfg = _cfg(routes={"project-tex/main.tex": "explicit/"})
        ctx = _ctx(source="project-tex/main.tex")
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.matched_rule == "project-tex/main.tex"
        assert decision.destination == WS / "explicit/main.pdf"

    def test_suffix_convention_beats_fallback(self) -> None:
        ctx = _ctx(source="project-tex/main.tex")
        cfg = _cfg()
        decision = resolve_route(ctx, _inputs(), cfg)
        assert decision.fallback is False
        assert "suffix convention" in (decision.matched_rule or "")


# ---------------------------------------------------------------------------
# RouteDecision serialization
# ---------------------------------------------------------------------------


class TestRouteDecisionToDict:
    def test_to_dict_basic(self) -> None:
        rd = RouteDecision(destination=Path("/out/main.pdf"), matched_rule="--output-dir")
        d = rd.to_dict(source=Path("/src/main.tex"))
        assert d["source"] == "/src/main.tex"
        assert d["destination"] == "/out/main.pdf"
        assert d["matched_rule"] == "--output-dir"
        assert d["fallback"] is False
        assert d["diagnostics"] == []

    def test_to_dict_fallback(self) -> None:
        from ktisma.domain.diagnostics import Diagnostic

        diag = Diagnostic(
            level=DiagnosticLevel.INFO,
            component="routing",
            code="fallback-routing",
            message="Fallback.",
        )
        rd = RouteDecision(destination=Path("/src/main.pdf"), fallback=True, diagnostics=[diag])
        d = rd.to_dict(source=Path("/src/main.tex"))
        assert d["fallback"] is True
        assert len(d["diagnostics"]) == 1
