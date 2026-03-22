from __future__ import annotations

import re
from pathlib import Path

from ..domain.context import SourceInputs

# Magic comment patterns:
# % !TeX program = <engine>
# % !ktisma output = <path>
_MAGIC_COMMENT_RE = re.compile(
    r"^%\s*!(?:TeX|ktisma)\s+(\w+)\s*=\s*(.+?)\s*$", re.MULTILINE
)


class FileSourceReader:
    """Concrete SourceReader: reads .tex files from disk and extracts magic comments."""

    def read_source(self, source_file: Path) -> SourceInputs:
        """Read a source file and extract preamble text and magic comments.

        Per roadmap, infrastructure extracts the preamble (up to \\begin{document})
        so domain code receives only the preamble text.
        """
        text = source_file.read_text(encoding="utf-8", errors="replace")
        preamble = _extract_preamble(text)
        magic_comments = _extract_magic_comments(preamble)
        return SourceInputs(preamble=preamble, magic_comments=magic_comments)


def _extract_preamble(source: str) -> str:
    """Extract text before \\begin{document}."""
    match = re.search(r"\\begin\{document\}", source)
    if match:
        return source[: match.start()]
    return source


def _extract_magic_comments(text: str) -> dict[str, str]:
    """Extract magic comments from the source text.

    Recognized forms:
    - % !TeX program = <engine>
    - % !ktisma output = <path>

    Path values have ~ expanded at this boundary so domain code stays pure.
    """
    comments: dict[str, str] = {}
    for match in _MAGIC_COMMENT_RE.finditer(text):
        key = match.group(1).lower()
        value = match.group(2).strip()
        if key == "output" and value:
            value = str(Path(value).expanduser())
            if match.group(2).strip().endswith("/") and not value.endswith("/"):
                value += "/"
        comments[key] = value
    return comments
