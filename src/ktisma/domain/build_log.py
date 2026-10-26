"""Pure classification of LaTeX build logs against a zero baseline."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FindingCount:
    """Count one class of defect found in a LaTeX log."""

    name: str
    count: int


@dataclass(frozen=True)
class BuildLogEvaluation:
    """Results obtained by evaluating one LaTeX log."""

    findings: tuple[FindingCount, ...]
    output_line: str | None
    channel_lines: tuple[str, ...]

    @property
    def passed(self) -> bool:
        """Return whether the log satisfies the zero baseline."""
        return self.output_line is not None and all(item.count == 0 for item in self.findings)


_FINDING_PATTERNS: tuple[tuple[str, str], ...] = (
    ("fatal error", "Fatal error"),
    ("font substitution", "LaTeX Font Warning"),
    ("overfull hbox", r"Overfull \hbox"),
    ("overfull vbox", r"Overfull \vbox"),
    ("underfull hbox", r"Underfull \hbox"),
    ("underfull vbox", r"Underfull \vbox"),
)
_ERROR_LINE = re.compile(r"^(?:! |\./.*:[0-9]+: |/?[^ :]+\.(?:tex|sty|cls|def):[0-9]+: )")


def evaluate_build_log(text: str, channels: tuple[str, ...] = ()) -> BuildLogEvaluation:
    """Evaluate one log and retain the requested measurement-channel lines.

    Parameters
    ----------
    text
        Complete text of one LaTeX log.
    channels
        Channel names whose lines begin with ``[<channel>]``.

    Returns
    -------
    BuildLogEvaluation
        Counts, the last output record, and the selected channel lines.
    """
    lines = text.splitlines()
    findings = tuple(
        FindingCount(name=name, count=sum(pattern in line for line in lines))
        for name, pattern in _FINDING_PATTERNS
    ) + (
        FindingCount(name="error", count=sum(bool(_ERROR_LINE.match(line)) for line in lines)),
    )

    output_lines = [
        line[line.index("Output written") :] for line in lines if "Output written" in line
    ]
    channel_lines = tuple(
        line for channel in channels for line in lines if line.startswith(f"[{channel}]")
    )
    return BuildLogEvaluation(
        findings=findings,
        output_line=output_lines[-1] if output_lines else None,
        channel_lines=channel_lines,
    )
