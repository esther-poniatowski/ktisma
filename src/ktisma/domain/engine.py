from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .config import ResolvedConfig
from .context import SourceInputs
from .diagnostics import Diagnostic, DiagnosticLevel


@dataclass(frozen=True)
class EngineDecision:
    engine: str
    evidence: list[str] = field(default_factory=list)
    ambiguous: bool = False
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "engine": self.engine,
            "evidence": self.evidence,
            "ambiguous": self.ambiguous,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }


# --- Marker definitions ---

XELATEX_MARKERS: list[tuple[str, str]] = [
    (r"\\RequireXeTeX", "\\RequireXeTeX directive"),
    (r"\\(?:ifxetex|fi)", "ifxetex conditional"),
    (r"\\XeTeXinterchartokenstate", "XeTeX primitive \\XeTeXinterchartokenstate"),
    (r"\\XeTeXinputencoding", "XeTeX primitive \\XeTeXinputencoding"),
    (r"\\XeTeXdefaultencoding", "XeTeX primitive \\XeTeXdefaultencoding"),
    (r"\\XeTeXlinebreaklocale", "XeTeX primitive \\XeTeXlinebreaklocale"),
]

LUALATEX_MARKERS: list[tuple[str, str]] = [
    (r"\\RequireLuaTeX", "\\RequireLuaTeX directive"),
    (r"\\begin\{luacode\*?\}", "luacode environment"),
    (r"\\directlua\b", "\\directlua command"),
    (r"\\(?:ifluatex|fi)", "ifluatex conditional"),
    (r"\\luaexec\b", "\\luaexec command"),
]

AMBIGUOUS_MODERN_MARKERS: list[tuple[str, str]] = [
    (r"\\usepackage(?:\[.*?\])?\{fontspec\}", "fontspec package"),
    (r"\\usepackage(?:\[.*?\])?\{polyglossia\}", "polyglossia package"),
    (r"\\usepackage(?:\[.*?\])?\{unicode-math\}", "unicode-math package"),
]


def detect_engine(source_inputs: SourceInputs, config: ResolvedConfig) -> EngineDecision:
    """Detect the appropriate LaTeX engine from source inputs and config.

    Detection steps per roadmap:
    1. Honor magic comment if present.
    2. Scan preamble for definitive markers.
    3. Handle ambiguous markers.
    4. Fall back to config default.
    """
    # Step 1: Magic comment
    magic_engine = source_inputs.magic_comments.get("program")
    if magic_engine:
        engine = _normalize_engine(magic_engine)
        return EngineDecision(
            engine=engine,
            evidence=[f"% !TeX program = {magic_engine}"],
        )

    # Step 2: Scan preamble for definitive markers
    preamble = _extract_preamble(source_inputs.preamble)

    xelatex_evidence = _scan_markers(preamble, XELATEX_MARKERS)
    lualatex_evidence = _scan_markers(preamble, LUALATEX_MARKERS)

    if xelatex_evidence and lualatex_evidence:
        return EngineDecision(
            engine=config.engines.default,
            evidence=xelatex_evidence + lualatex_evidence,
            ambiguous=True,
            diagnostics=[
                Diagnostic(
                    level=DiagnosticLevel.WARNING,
                    component="engine",
                    code="conflicting-engine-markers",
                    message="Found markers for both XeLaTeX and LuaLaTeX; falling back to config default.",
                    evidence=xelatex_evidence + lualatex_evidence,
                )
            ],
        )

    if xelatex_evidence:
        return EngineDecision(engine="xelatex", evidence=xelatex_evidence)

    if lualatex_evidence:
        return EngineDecision(engine="lualatex", evidence=lualatex_evidence)

    # Step 3: Ambiguous modern markers
    ambiguous_evidence = _scan_markers(preamble, AMBIGUOUS_MODERN_MARKERS)
    if ambiguous_evidence:
        if config.engines.strict_detection:
            return EngineDecision(
                engine=config.engines.modern_default,
                evidence=ambiguous_evidence,
                ambiguous=True,
                diagnostics=[
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        component="engine",
                        code="ambiguous-engine-strict",
                        message=(
                            "Ambiguous modern-engine markers found and strict_detection is enabled. "
                            "Pin the engine via magic comment or config."
                        ),
                        evidence=ambiguous_evidence,
                    )
                ],
            )
        return EngineDecision(
            engine=config.engines.modern_default,
            evidence=ambiguous_evidence,
            ambiguous=True,
            diagnostics=[
                Diagnostic(
                    level=DiagnosticLevel.WARNING,
                    component="engine",
                    code="ambiguous-engine",
                    message=(
                        f"Ambiguous markers suggest a modern engine; "
                        f"selecting '{config.engines.modern_default}'. "
                        f"Pin the engine via magic comment or config to suppress this warning."
                    ),
                    evidence=ambiguous_evidence,
                )
            ],
        )

    # Step 4: Config default
    return EngineDecision(
        engine=config.engines.default,
        evidence=["no engine markers found; using config default"],
    )


def _normalize_engine(engine: str) -> str:
    """Normalize engine name to canonical form."""
    mapping = {
        "pdflatex": "pdflatex",
        "lualatex": "lualatex",
        "xelatex": "xelatex",
        "latex": "latex",
        "luatex": "lualatex",
        "xetex": "xelatex",
        "pdftex": "pdflatex",
    }
    return mapping.get(engine.lower().strip(), engine.lower().strip())


def _extract_preamble(source: str) -> str:
    """Extract text before \\begin{document}."""
    match = re.search(r"\\begin\{document\}", source)
    if match:
        return source[: match.start()]
    return source


def _scan_markers(preamble: str, markers: list[tuple[str, str]]) -> list[str]:
    """Scan preamble for marker patterns, returning evidence descriptions."""
    found: list[str] = []
    for pattern, description in markers:
        if re.search(pattern, preamble):
            found.append(f"{description} detected in preamble")
    return found
