"""Tests for ktisma.domain.engine — engine detection from source markers and config."""

from __future__ import annotations

import pytest

from ktisma.domain.config import EngineConfig, ResolvedConfig, default_config
from ktisma.domain.context import SourceInputs
from ktisma.domain.diagnostics import DiagnosticLevel
from ktisma.domain.engine import (
    EngineDecision,
    _extract_preamble,
    _normalize_engine,
    _scan_markers,
    AMBIGUOUS_MODERN_MARKERS,
    LUALATEX_MARKERS,
    XELATEX_MARKERS,
    detect_engine,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cfg(**engine_kwargs: object) -> ResolvedConfig:
    """Build a ResolvedConfig with custom engine settings, defaults for the rest."""
    base = default_config()
    return ResolvedConfig(
        schema_version=base.schema_version,
        build=base.build,
        engines=EngineConfig(**{**vars(base.engines), **engine_kwargs}),  # type: ignore[arg-type]
        routing=base.routing,
        routes=base.routes,
        variants=base.variants,
        provenance=base.provenance,
    )


def _inputs(preamble: str = "", magic: dict[str, str] | None = None) -> SourceInputs:
    return SourceInputs(preamble=preamble, magic_comments=magic or {})


# ---------------------------------------------------------------------------
# Magic comment detection (step 1)
# ---------------------------------------------------------------------------


class TestMagicCommentDetection:
    @pytest.mark.parametrize(
        "program, expected_engine",
        [
            ("pdflatex", "pdflatex"),
            ("lualatex", "lualatex"),
            ("xelatex", "xelatex"),
            ("latex", "latex"),
            ("LuaLaTeX", "lualatex"),
            ("XeLaTeX", "xelatex"),
            ("luatex", "lualatex"),
            ("xetex", "xelatex"),
            ("pdftex", "pdflatex"),
        ],
    )
    def test_magic_comment_selects_engine(self, program: str, expected_engine: str) -> None:
        inputs = _inputs(magic={"program": program})
        decision = detect_engine(inputs, default_config())
        assert decision.engine == expected_engine
        assert not decision.ambiguous
        assert decision.diagnostics == []

    def test_magic_comment_evidence(self) -> None:
        inputs = _inputs(magic={"program": "xelatex"})
        decision = detect_engine(inputs, default_config())
        assert any("program" in e for e in decision.evidence)

    def test_magic_comment_overrides_preamble_markers(self) -> None:
        """Magic comment takes priority over preamble markers."""
        preamble = "\\RequireXeTeX\n\\documentclass{article}\n\\begin{document}"
        inputs = _inputs(preamble=preamble, magic={"program": "lualatex"})
        decision = detect_engine(inputs, default_config())
        assert decision.engine == "lualatex"

    def test_unknown_magic_engine_passes_through(self) -> None:
        """Unknown engine names are returned as-is (lowered, stripped)."""
        inputs = _inputs(magic={"program": "CustomEngine"})
        decision = detect_engine(inputs, default_config())
        assert decision.engine == "customengine"


# ---------------------------------------------------------------------------
# Definitive XeLaTeX markers (step 2)
# ---------------------------------------------------------------------------


class TestXeLaTeXMarkers:
    @pytest.mark.parametrize(
        "snippet, marker_desc",
        [
            ("\\RequireXeTeX", "RequireXeTeX"),
            ("\\ifxetex", "ifxetex"),
            ("\\XeTeXinterchartokenstate=1", "XeTeXinterchartokenstate"),
            ("\\XeTeXinputencoding \"utf-8\"", "XeTeXinputencoding"),
            ("\\XeTeXdefaultencoding \"utf-8\"", "XeTeXdefaultencoding"),
            ("\\XeTeXlinebreaklocale \"en\"", "XeTeXlinebreaklocale"),
        ],
    )
    def test_xelatex_marker_detected(self, snippet: str, marker_desc: str) -> None:
        preamble = f"\\documentclass{{article}}\n{snippet}\n\\begin{{document}}"
        inputs = _inputs(preamble=preamble)
        decision = detect_engine(inputs, default_config())
        assert decision.engine == "xelatex"
        assert not decision.ambiguous
        assert decision.diagnostics == []
        assert len(decision.evidence) >= 1

    def test_xelatex_marker_after_begin_document_ignored(self) -> None:
        """Markers after \\begin{document} should not be scanned."""
        source = "\\documentclass{article}\n\\begin{document}\n\\RequireXeTeX"
        inputs = _inputs(preamble=source)
        decision = detect_engine(inputs, default_config())
        assert decision.engine != "xelatex" or decision.engine == default_config().engines.default


# ---------------------------------------------------------------------------
# Definitive LuaLaTeX markers (step 2)
# ---------------------------------------------------------------------------


class TestLuaLaTeXMarkers:
    @pytest.mark.parametrize(
        "snippet",
        [
            "\\RequireLuaTeX",
            "\\begin{luacode}\nprint('hello')\n\\end{luacode}",
            "\\begin{luacode*}\nprint('hello')\n\\end{luacode*}",
            "\\directlua{tex.print('hi')}",
            "\\ifluatex",
            "\\luaexec{print('x')}",
        ],
    )
    def test_lualatex_marker_detected(self, snippet: str) -> None:
        preamble = f"\\documentclass{{article}}\n{snippet}\n\\begin{{document}}"
        inputs = _inputs(preamble=preamble)
        decision = detect_engine(inputs, default_config())
        assert decision.engine == "lualatex"
        assert not decision.ambiguous
        assert decision.diagnostics == []


# ---------------------------------------------------------------------------
# Ambiguous modern markers (step 3)
# ---------------------------------------------------------------------------


class TestAmbiguousModernMarkers:
    @pytest.mark.parametrize(
        "snippet",
        [
            "\\usepackage{fontspec}",
            "\\usepackage[main=english]{polyglossia}",
            "\\usepackage{unicode-math}",
        ],
    )
    def test_ambiguous_marker_selects_modern_default(self, snippet: str) -> None:
        preamble = f"\\documentclass{{article}}\n{snippet}\n\\begin{{document}}"
        inputs = _inputs(preamble=preamble)
        cfg = default_config()
        decision = detect_engine(inputs, cfg)
        assert decision.engine == cfg.engines.modern_default
        assert decision.ambiguous is True

    def test_ambiguous_marker_warning_non_strict(self) -> None:
        preamble = "\\documentclass{article}\n\\usepackage{fontspec}\n\\begin{document}"
        inputs = _inputs(preamble=preamble)
        cfg = _cfg(strict_detection=False)
        decision = detect_engine(inputs, cfg)
        assert len(decision.diagnostics) == 1
        assert decision.diagnostics[0].level is DiagnosticLevel.WARNING
        assert decision.diagnostics[0].code == "ambiguous-engine"

    def test_ambiguous_marker_error_strict(self) -> None:
        preamble = "\\documentclass{article}\n\\usepackage{fontspec}\n\\begin{document}"
        inputs = _inputs(preamble=preamble)
        cfg = _cfg(strict_detection=True)
        decision = detect_engine(inputs, cfg)
        assert decision.ambiguous is True
        assert len(decision.diagnostics) == 1
        assert decision.diagnostics[0].level is DiagnosticLevel.ERROR
        assert decision.diagnostics[0].code == "ambiguous-engine-strict"

    def test_ambiguous_respects_custom_modern_default(self) -> None:
        preamble = "\\documentclass{article}\n\\usepackage{fontspec}\n\\begin{document}"
        inputs = _inputs(preamble=preamble)
        cfg = _cfg(modern_default="xelatex")
        decision = detect_engine(inputs, cfg)
        assert decision.engine == "xelatex"

    def test_ambiguous_marker_with_options(self) -> None:
        preamble = "\\documentclass{article}\n\\usepackage[no-math]{fontspec}\n\\begin{document}"
        inputs = _inputs(preamble=preamble)
        decision = detect_engine(inputs, default_config())
        assert decision.engine == default_config().engines.modern_default
        assert decision.ambiguous is True


# ---------------------------------------------------------------------------
# Conflicting markers (step 2 — both XeLaTeX and LuaLaTeX)
# ---------------------------------------------------------------------------


class TestConflictingMarkers:
    def test_both_xelatex_and_lualatex_markers(self) -> None:
        preamble = (
            "\\documentclass{article}\n"
            "\\RequireXeTeX\n"
            "\\directlua{tex.print('hi')}\n"
            "\\begin{document}"
        )
        inputs = _inputs(preamble=preamble)
        cfg = default_config()
        decision = detect_engine(inputs, cfg)
        assert decision.engine == cfg.engines.default  # falls back to config default
        assert decision.ambiguous is True
        assert len(decision.diagnostics) == 1
        assert decision.diagnostics[0].code == "conflicting-engine-markers"
        assert decision.diagnostics[0].level is DiagnosticLevel.WARNING

    def test_conflicting_markers_evidence_combined(self) -> None:
        preamble = (
            "\\documentclass{article}\n"
            "\\RequireXeTeX\n"
            "\\RequireLuaTeX\n"
            "\\begin{document}"
        )
        inputs = _inputs(preamble=preamble)
        decision = detect_engine(inputs, default_config())
        # Evidence should include markers from both engines
        assert len(decision.evidence) >= 2

    def test_conflicting_markers_uses_config_default(self) -> None:
        preamble = (
            "\\documentclass{article}\n"
            "\\XeTeXinterchartokenstate=1\n"
            "\\begin{luacode}\nprint('x')\n\\end{luacode}\n"
            "\\begin{document}"
        )
        inputs = _inputs(preamble=preamble)
        cfg = _cfg(default="xelatex")
        decision = detect_engine(inputs, cfg)
        assert decision.engine == "xelatex"


# ---------------------------------------------------------------------------
# Config default fallback (step 4)
# ---------------------------------------------------------------------------


class TestConfigDefaultFallback:
    def test_no_markers_uses_config_default(self) -> None:
        preamble = "\\documentclass{article}\n\\begin{document}"
        inputs = _inputs(preamble=preamble)
        cfg = default_config()
        decision = detect_engine(inputs, cfg)
        assert decision.engine == "pdflatex"
        assert not decision.ambiguous
        assert decision.diagnostics == []

    def test_custom_default_engine(self) -> None:
        preamble = "\\documentclass{article}\n\\begin{document}"
        inputs = _inputs(preamble=preamble)
        cfg = _cfg(default="lualatex")
        decision = detect_engine(inputs, cfg)
        assert decision.engine == "lualatex"

    def test_fallback_evidence_message(self) -> None:
        inputs = _inputs(preamble="\\documentclass{article}\n\\begin{document}")
        decision = detect_engine(inputs, default_config())
        assert any("config default" in e for e in decision.evidence)

    def test_empty_preamble(self) -> None:
        inputs = _inputs(preamble="")
        decision = detect_engine(inputs, default_config())
        assert decision.engine == default_config().engines.default


# ---------------------------------------------------------------------------
# EngineDecision serialization
# ---------------------------------------------------------------------------


class TestEngineDecisionToDict:
    def test_to_dict_basic(self) -> None:
        decision = EngineDecision(engine="pdflatex", evidence=["fallback"])
        d = decision.to_dict()
        assert d["engine"] == "pdflatex"
        assert d["evidence"] == ["fallback"]
        assert d["ambiguous"] is False
        assert d["diagnostics"] == []

    def test_to_dict_with_diagnostics(self) -> None:
        from ktisma.domain.diagnostics import Diagnostic

        diag = Diagnostic(
            level=DiagnosticLevel.WARNING,
            component="engine",
            code="ambiguous-engine",
            message="Ambiguous.",
        )
        decision = EngineDecision(
            engine="lualatex",
            evidence=["fontspec"],
            ambiguous=True,
            diagnostics=[diag],
        )
        d = decision.to_dict()
        assert d["ambiguous"] is True
        assert len(d["diagnostics"]) == 1
        assert d["diagnostics"][0]["code"] == "ambiguous-engine"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class TestNormalizeEngine:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("pdflatex", "pdflatex"),
            ("PdfLaTeX", "pdflatex"),
            ("LUALATEX", "lualatex"),
            ("xelatex", "xelatex"),
            ("latex", "latex"),
            ("luatex", "lualatex"),
            ("xetex", "xelatex"),
            ("pdftex", "pdflatex"),
            ("  xelatex  ", "xelatex"),
            ("unknownengine", "unknownengine"),
        ],
    )
    def test_normalization(self, raw: str, expected: str) -> None:
        assert _normalize_engine(raw) == expected


class TestExtractPreamble:
    def test_with_begin_document(self) -> None:
        source = "preamble stuff\n\\begin{document}\nbody"
        assert _extract_preamble(source) == "preamble stuff\n"

    def test_without_begin_document(self) -> None:
        source = "preamble only, no begin document"
        assert _extract_preamble(source) == source

    def test_empty_string(self) -> None:
        assert _extract_preamble("") == ""


class TestScanMarkers:
    def test_finds_matching_markers(self) -> None:
        preamble = "\\RequireXeTeX\n\\XeTeXinterchartokenstate=1"
        evidence = _scan_markers(preamble, XELATEX_MARKERS)
        assert len(evidence) >= 2

    def test_no_match(self) -> None:
        preamble = "\\documentclass{article}"
        evidence = _scan_markers(preamble, XELATEX_MARKERS)
        assert evidence == []

    def test_evidence_description_format(self) -> None:
        preamble = "\\RequireXeTeX"
        evidence = _scan_markers(preamble, XELATEX_MARKERS)
        assert len(evidence) == 1
        assert "detected in preamble" in evidence[0]
