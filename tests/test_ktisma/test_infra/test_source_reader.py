"""Tests for ktisma.infra.source_reader – reading source files and extracting magic comments."""

from __future__ import annotations

from pathlib import Path

import pytest

from ktisma.infra.source_reader import FileSourceReader, _extract_magic_comments


@pytest.fixture
def reader() -> FileSourceReader:
    return FileSourceReader()


# ---------------------------------------------------------------------------
# Basic source reading
# ---------------------------------------------------------------------------


class TestReadSource:
    def test_reads_file_content(self, tmp_path: Path, reader: FileSourceReader) -> None:
        tex = tmp_path / "doc.tex"
        tex.write_text("\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}\n")
        result = reader.read_source(tex)
        assert "\\documentclass{article}" in result.preamble
        # "Hello" is after \begin{document}, so it's NOT in the preamble
        assert "Hello" not in result.preamble

    def test_empty_file(self, tmp_path: Path, reader: FileSourceReader) -> None:
        tex = tmp_path / "empty.tex"
        tex.write_text("")
        result = reader.read_source(tex)
        assert result.preamble == ""
        assert result.magic_comments == {}

    def test_utf8_content(self, tmp_path: Path, reader: FileSourceReader) -> None:
        tex = tmp_path / "unicode.tex"
        tex.write_text("% Umlauts: aou\n\\documentclass{article}\n", encoding="utf-8")
        result = reader.read_source(tex)
        assert "Umlauts" in result.preamble

    def test_nonexistent_file_raises(
        self, tmp_path: Path, reader: FileSourceReader
    ) -> None:
        tex = tmp_path / "missing.tex"
        with pytest.raises(FileNotFoundError):
            reader.read_source(tex)


# ---------------------------------------------------------------------------
# Magic comment extraction: % !TeX program
# ---------------------------------------------------------------------------


class TestTexProgramComment:
    def test_program_pdflatex(self) -> None:
        text = "% !TeX program = pdflatex\n\\documentclass{article}\n"
        comments = _extract_magic_comments(text)
        assert comments["program"] == "pdflatex"

    def test_program_lualatex(self) -> None:
        text = "% !TeX program = lualatex\n"
        comments = _extract_magic_comments(text)
        assert comments["program"] == "lualatex"

    def test_program_xelatex(self) -> None:
        text = "% !TeX program = xelatex\n"
        comments = _extract_magic_comments(text)
        assert comments["program"] == "xelatex"

    def test_program_case_preserved(self) -> None:
        """The key is lowered but the value is preserved."""
        text = "% !TeX program = LuaLaTeX\n"
        comments = _extract_magic_comments(text)
        assert comments["program"] == "LuaLaTeX"

    def test_program_with_extra_spaces(self) -> None:
        text = "%  !TeX  program  =  pdflatex  \n"
        comments = _extract_magic_comments(text)
        assert comments["program"] == "pdflatex"

    def test_program_on_second_line(self) -> None:
        text = "% Some preamble comment\n% !TeX program = xelatex\n"
        comments = _extract_magic_comments(text)
        assert comments["program"] == "xelatex"

    def test_no_program_comment(self) -> None:
        text = "\\documentclass{article}\n\\begin{document}\nHello\n\\end{document}\n"
        comments = _extract_magic_comments(text)
        assert "program" not in comments


# ---------------------------------------------------------------------------
# Magic comment extraction: % !ktisma output
# ---------------------------------------------------------------------------


class TestKtismaOutputComment:
    def test_output_relative_path(self) -> None:
        text = "% !ktisma output = ../pdfs/\n"
        comments = _extract_magic_comments(text)
        assert comments["output"] == "../pdfs/"

    def test_output_absolute_path(self) -> None:
        text = "% !ktisma output = /tmp/output/paper.pdf\n"
        comments = _extract_magic_comments(text)
        assert comments["output"] == "/tmp/output/paper.pdf"

    def test_output_with_spaces_in_path(self) -> None:
        text = "% !ktisma output = my output dir/\n"
        comments = _extract_magic_comments(text)
        assert comments["output"] == "my output dir/"

    def test_ktisma_key_lowered(self) -> None:
        """The key after !ktisma is lowered."""
        text = "% !ktisma OUTPUT = /tmp/out/\n"
        comments = _extract_magic_comments(text)
        assert comments["output"] == "/tmp/out/"


# ---------------------------------------------------------------------------
# Multiple magic comments
# ---------------------------------------------------------------------------


class TestMultipleMagicComments:
    def test_both_program_and_output(self) -> None:
        text = (
            "% !TeX program = lualatex\n"
            "% !ktisma output = ../pdfs/\n"
            "\\documentclass{article}\n"
        )
        comments = _extract_magic_comments(text)
        assert comments["program"] == "lualatex"
        assert comments["output"] == "../pdfs/"

    def test_duplicate_key_last_wins(self) -> None:
        """When the same key appears twice, the last occurrence wins."""
        text = (
            "% !TeX program = pdflatex\n"
            "% !TeX program = lualatex\n"
        )
        comments = _extract_magic_comments(text)
        assert comments["program"] == "lualatex"

    def test_mixed_tex_and_ktisma_program(self) -> None:
        """Both !TeX and !ktisma can set 'program'; last wins."""
        text = (
            "% !TeX program = pdflatex\n"
            "% !ktisma program = xelatex\n"
        )
        comments = _extract_magic_comments(text)
        assert comments["program"] == "xelatex"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestMagicCommentEdgeCases:
    def test_comment_not_at_line_start_is_ignored(self) -> None:
        """The regex requires % at the start of a line."""
        text = "  % !TeX program = lualatex\n"
        comments = _extract_magic_comments(text)
        # The space before % means it won't match ^%
        assert "program" not in comments

    def test_missing_equals_sign_is_ignored(self) -> None:
        text = "% !TeX program lualatex\n"
        comments = _extract_magic_comments(text)
        assert "program" not in comments

    def test_empty_value_after_equals(self) -> None:
        """A trailing space after '=' is captured by .+? then stripped to empty string."""
        text = "% !TeX program = \n"
        comments = _extract_magic_comments(text)
        # The regex .+? matches the trailing space; .strip() yields ""
        assert comments.get("program") == ""

    def test_truly_empty_value_no_space(self) -> None:
        """With no characters at all after '=', the .+? cannot match."""
        text = "% !TeX program =\n"
        comments = _extract_magic_comments(text)
        assert "program" not in comments

    def test_magic_comment_in_document_body(self) -> None:
        """Magic comments anywhere in the file are extracted (the regex is MULTILINE)."""
        text = (
            "\\begin{document}\n"
            "% !TeX program = lualatex\n"
            "\\end{document}\n"
        )
        comments = _extract_magic_comments(text)
        assert comments["program"] == "lualatex"

    def test_non_magic_comments_ignored(self) -> None:
        text = (
            "% This is a regular comment\n"
            "% Author: Alice\n"
            "% !TeX program = pdflatex\n"
        )
        comments = _extract_magic_comments(text)
        assert len(comments) == 1
        assert comments["program"] == "pdflatex"


# ---------------------------------------------------------------------------
# Integration: full read_source with magic comments
# ---------------------------------------------------------------------------


class TestReadSourceWithMagic:
    def test_full_read_with_magic(
        self, tmp_path: Path, reader: FileSourceReader
    ) -> None:
        tex = tmp_path / "paper.tex"
        tex.write_text(
            "% !TeX program = lualatex\n"
            "% !ktisma output = ../out/\n"
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "Hello world\n"
            "\\end{document}\n"
        )
        result = reader.read_source(tex)
        assert result.magic_comments["program"] == "lualatex"
        assert result.magic_comments["output"] == "../out/"
        assert "\\documentclass{article}" in result.preamble

    def test_ignores_magic_comments_after_begin_document(
        self, tmp_path: Path, reader: FileSourceReader
    ) -> None:
        tex = tmp_path / "paper.tex"
        tex.write_text(
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "% !TeX program = lualatex\n"
            "\\end{document}\n"
        )
        result = reader.read_source(tex)
        assert result.magic_comments == {}

    def test_read_source_no_magic(
        self, tmp_path: Path, reader: FileSourceReader
    ) -> None:
        tex = tmp_path / "plain.tex"
        tex.write_text("\\documentclass{article}\n\\begin{document}\n\\end{document}\n")
        result = reader.read_source(tex)
        assert result.magic_comments == {}
        assert "\\documentclass{article}" in result.preamble
