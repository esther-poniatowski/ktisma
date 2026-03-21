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
        """Read a source file and extract preamble text and magic comments."""
        text = source_file.read_text(encoding="utf-8", errors="replace")
        magic_comments = _extract_magic_comments(text)
        return SourceInputs(preamble=text, magic_comments=magic_comments)


def _extract_magic_comments(text: str) -> dict[str, str]:
    """Extract magic comments from the source text.

    Recognized forms:
    - % !TeX program = <engine>
    - % !ktisma output = <path>
    """
    comments: dict[str, str] = {}
    for match in _MAGIC_COMMENT_RE.finditer(text):
        key = match.group(1).lower()
        value = match.group(2).strip()
        comments[key] = value
    return comments
