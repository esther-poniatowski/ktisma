"""Tests for ktisma.domain.build_dir — build directory planning."""

from __future__ import annotations

from pathlib import Path

import pytest

from ktisma.domain.build_dir import BuildDirPlan, plan_build_dir
from ktisma.domain.config import BuildConfig, ResolvedConfig, default_config
from ktisma.domain.context import SourceContext, VariantSpec


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(
    source: str = "project-tex/ch1/main.tex",
    workspace: Path = Path("/workspace"),
) -> SourceContext:
    source_path = workspace / source
    return SourceContext(
        source_file=source_path,
        source_dir=source_path.parent,
        workspace_root=workspace,
    )


def _cfg(out_dir_name: str = ".ktisma_build") -> ResolvedConfig:
    base = default_config()
    return ResolvedConfig(
        schema_version=base.schema_version,
        build=BuildConfig(
            out_dir_name=out_dir_name,
            cleanup=base.build.cleanup,
            synctex=base.build.synctex,
        ),
        engines=base.engines,
        routing=base.routing,
        routes=base.routes,
        variants=base.variants,
        provenance=base.provenance,
    )


# ---------------------------------------------------------------------------
# Basic build directory planning (no variant)
# ---------------------------------------------------------------------------


class TestPlanBuildDirNoVariant:
    def test_default_build_dir(self) -> None:
        ctx = _ctx()
        plan = plan_build_dir(ctx, default_config())
        assert plan.build_dir == Path("/workspace/project-tex/ch1/.ktisma_build/main")
        assert plan.source_stem == "main"
        assert plan.variant is None

    def test_expected_pdf(self) -> None:
        ctx = _ctx()
        plan = plan_build_dir(ctx, default_config())
        assert plan.expected_pdf == plan.build_dir / "main.pdf"

    def test_lock_file(self) -> None:
        ctx = _ctx()
        plan = plan_build_dir(ctx, default_config())
        assert plan.lock_file == plan.build_dir / ".ktisma.lock"

    def test_custom_out_dir_name(self) -> None:
        ctx = _ctx()
        cfg = _cfg(out_dir_name="build")
        plan = plan_build_dir(ctx, cfg)
        assert plan.build_dir == Path("/workspace/project-tex/ch1/build/main")

    def test_different_source_stem(self) -> None:
        ctx = _ctx(source="project-tex/thesis.tex")
        plan = plan_build_dir(ctx, default_config())
        assert plan.source_stem == "thesis"
        assert plan.build_dir.name == "thesis"
        assert plan.expected_pdf.name == "thesis.pdf"

    def test_build_dir_under_source_dir(self) -> None:
        """Build dir should be <source_dir>/<out_dir_name>/<stem>."""
        ctx = _ctx(source="a/b/c/document.tex")
        plan = plan_build_dir(ctx, default_config())
        assert plan.build_dir.parent.parent == Path("/workspace/a/b/c")


# ---------------------------------------------------------------------------
# Build directory planning with variant
# ---------------------------------------------------------------------------


class TestPlanBuildDirWithVariant:
    def test_variant_appended_to_dir_name(self) -> None:
        ctx = _ctx()
        variant = VariantSpec(name="print", payload="\\printmodetrue")
        plan = plan_build_dir(ctx, default_config(), variant=variant)
        assert plan.build_dir == Path("/workspace/project-tex/ch1/.ktisma_build/main-print")
        assert plan.variant is variant

    def test_variant_does_not_affect_pdf_name(self) -> None:
        """The expected PDF still uses the source stem, not the variant name."""
        ctx = _ctx()
        variant = VariantSpec(name="print", payload="\\printmodetrue")
        plan = plan_build_dir(ctx, default_config(), variant=variant)
        assert plan.expected_pdf.name == "main.pdf"

    def test_variant_lock_file(self) -> None:
        ctx = _ctx()
        variant = VariantSpec(name="draft", payload="\\draftmodetrue")
        plan = plan_build_dir(ctx, default_config(), variant=variant)
        assert plan.lock_file == plan.build_dir / ".ktisma.lock"

    def test_different_variants_different_dirs(self) -> None:
        ctx = _ctx()
        v1 = VariantSpec(name="print", payload="p")
        v2 = VariantSpec(name="screen", payload="s")
        plan1 = plan_build_dir(ctx, default_config(), variant=v1)
        plan2 = plan_build_dir(ctx, default_config(), variant=v2)
        assert plan1.build_dir != plan2.build_dir

    def test_no_variant_vs_variant_different_dirs(self) -> None:
        ctx = _ctx()
        plan_no_var = plan_build_dir(ctx, default_config())
        plan_var = plan_build_dir(ctx, default_config(), variant=VariantSpec(name="x", payload="y"))
        assert plan_no_var.build_dir != plan_var.build_dir


# ---------------------------------------------------------------------------
# BuildDirPlan serialization
# ---------------------------------------------------------------------------


class TestBuildDirPlanToDict:
    def test_to_dict_no_variant(self) -> None:
        ctx = _ctx()
        plan = plan_build_dir(ctx, default_config())
        d = plan.to_dict()
        assert "build_dir" in d
        assert "expected_pdf" in d
        assert "lock_file" in d
        assert "source_stem" in d
        assert d["source_stem"] == "main"
        assert "variant" not in d

    def test_to_dict_with_variant(self) -> None:
        ctx = _ctx()
        variant = VariantSpec(name="print", payload="\\printmodetrue")
        plan = plan_build_dir(ctx, default_config(), variant=variant)
        d = plan.to_dict()
        assert d["variant"] == "print"

    def test_to_dict_paths_are_strings(self) -> None:
        ctx = _ctx()
        plan = plan_build_dir(ctx, default_config())
        d = plan.to_dict()
        assert isinstance(d["build_dir"], str)
        assert isinstance(d["expected_pdf"], str)
        assert isinstance(d["lock_file"], str)


# ---------------------------------------------------------------------------
# VariantSpec
# ---------------------------------------------------------------------------


class TestVariantSpec:
    def test_construction(self) -> None:
        vs = VariantSpec(name="print", payload="\\printmodetrue")
        assert vs.name == "print"
        assert vs.payload == "\\printmodetrue"

    def test_valid_name_pattern_defined(self) -> None:
        import re

        pattern = VariantSpec.VALID_NAME_PATTERN
        assert re.match(pattern, "print")
        assert re.match(pattern, "my-variant")
        assert re.match(pattern, "v2_draft")
        assert not re.match(pattern, "123abc")
        assert not re.match(pattern, "-bad")
        assert not re.match(pattern, "")
