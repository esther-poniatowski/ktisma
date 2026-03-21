"""Tests for the latexmkrc shim adapter."""

from __future__ import annotations

from pathlib import Path

from ktisma.adapters.latexmkrc import (
    LATEXMKRC_TEMPLATE,
    generate_latexmkrc,
    write_latexmkrc,
)


# ---------------------------------------------------------------------------
# generate_latexmkrc
# ---------------------------------------------------------------------------


class TestGenerateLatexmkrc:
    """Test shim content generation."""

    def test_returns_string(self, tmp_path):
        content = generate_latexmkrc(workspace_root=tmp_path)
        assert isinstance(content, str)

    def test_contains_pdf_mode(self, tmp_path):
        content = generate_latexmkrc(workspace_root=tmp_path)
        assert "$pdf_mode = 1;" in content

    def test_contains_ktisma_header(self, tmp_path):
        content = generate_latexmkrc(workspace_root=tmp_path)
        assert "ktisma" in content.lower()

    def test_default_stem_is_main(self, tmp_path):
        content = generate_latexmkrc(workspace_root=tmp_path)
        assert ".ktisma_build/main" in content

    def test_custom_stem(self, tmp_path):
        content = generate_latexmkrc(workspace_root=tmp_path, stem="thesis")
        assert ".ktisma_build/thesis" in content

    def test_stem_replacement_in_out_dir(self, tmp_path):
        content = generate_latexmkrc(workspace_root=tmp_path, stem="report")
        assert "%STEM%" not in content
        assert "report" in content

    def test_mentions_transitional(self, tmp_path):
        content = generate_latexmkrc(workspace_root=tmp_path)
        assert "transitional" in content.lower()

    def test_content_matches_template_with_default_stem(self, tmp_path):
        content = generate_latexmkrc(workspace_root=tmp_path)
        expected = LATEXMKRC_TEMPLATE.replace("%STEM%", "main")
        assert content == expected


# ---------------------------------------------------------------------------
# write_latexmkrc
# ---------------------------------------------------------------------------


class TestWriteLatexmkrc:
    """Test writing the shim file to disk."""

    def test_writes_file(self, tmp_path):
        result = write_latexmkrc(workspace_root=tmp_path)
        assert result.exists()
        assert result.name == ".latexmkrc"

    def test_file_path_is_in_workspace_root(self, tmp_path):
        result = write_latexmkrc(workspace_root=tmp_path)
        assert result.parent == tmp_path

    def test_written_content_matches_generated(self, tmp_path):
        result_path = write_latexmkrc(workspace_root=tmp_path, stem="article")
        written = result_path.read_text(encoding="utf-8")
        expected = generate_latexmkrc(workspace_root=tmp_path, stem="article")
        assert written == expected

    def test_returns_path_object(self, tmp_path):
        result = write_latexmkrc(workspace_root=tmp_path)
        assert isinstance(result, Path)
