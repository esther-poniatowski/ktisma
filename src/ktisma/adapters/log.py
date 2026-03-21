from __future__ import annotations

import logging
import sys
from typing import Optional

from ..domain.diagnostics import Diagnostic, DiagnosticLevel


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the CLI adapter.

    Per design principles: logging is optional developer instrumentation,
    configured only in adapters.
    """
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )


def format_diagnostics(diagnostics: list[Diagnostic], use_color: bool = True) -> str:
    """Format diagnostics for human-readable stderr output."""
    lines: list[str] = []
    for d in diagnostics:
        prefix = _level_prefix(d.level, use_color)
        lines.append(f"{prefix} [{d.code}] {d.message}")
        if d.evidence:
            for e in d.evidence:
                lines.append(f"  - {e}")
    return "\n".join(lines)


def _level_prefix(level: DiagnosticLevel, use_color: bool) -> str:
    """Format a diagnostic level as a colored prefix."""
    labels = {
        DiagnosticLevel.INFO: ("info", "\033[36m"),     # cyan
        DiagnosticLevel.WARNING: ("warning", "\033[33m"),  # yellow
        DiagnosticLevel.ERROR: ("error", "\033[31m"),    # red
    }
    label, color = labels.get(level, ("unknown", ""))
    if use_color and sys.stderr.isatty():
        return f"{color}{label}\033[0m:"
    return f"{label}:"
