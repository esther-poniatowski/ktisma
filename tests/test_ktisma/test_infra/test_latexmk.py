"""Tests for the latexmk subprocess adapter."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ktisma.infra.latexmk import LatexmkRunner


def test_compile_adds_environment_without_dropping_process_path(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "paper.tex"
    source.write_text("\\documentclass{article}\n", encoding="utf-8")
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    (build_dir / "paper.pdf").write_bytes(b"%PDF-1.4")
    captured: dict[str, object] = {}

    def fake_run(args, **kwargs):
        captured["env"] = kwargs["env"]
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = LatexmkRunner().compile(
        source_file=source,
        build_dir=build_dir,
        engine="pdflatex",
        synctex=False,
        environment={"TEXMFHOME": "/isolated/texmf"},
    )

    assert result.success
    environment = captured["env"]
    assert isinstance(environment, dict)
    assert environment["TEXMFHOME"] == "/isolated/texmf"
    assert "PATH" in environment
