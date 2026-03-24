"""Tests for ktisma.app.batch — recursive entrypoint-aware batch builds."""

from __future__ import annotations

from pathlib import Path

from ktisma.app.batch import execute_batch
from ktisma.app.protocols import BuildServices
from ktisma.domain.context import BuildRequest
from ktisma.domain.exit_codes import ExitCode
from ktisma.infra.source_reader import FileSourceReader

from .test_build import (
    FakeBackendRunner,
    FakeConfigLoader,
    FakeLockManager,
    FakeMaterializer,
    FakePrerequisiteProbe,
    FakeWorkspaceOps,
)


def test_batch_recurses_and_only_builds_entrypoints(tmp_path: Path) -> None:
    source_dir = tmp_path / "presentations-tex"
    deck_dir = source_dir / "deck"
    deck_dir.mkdir(parents=True)
    (deck_dir / "main.tex").write_text(
        "\\documentclass{beamer}\n\\begin{document}\n\\end{document}\n",
        encoding="utf-8",
    )
    (deck_dir / "section.tex").write_text("\\section{Intro}\n", encoding="utf-8")

    backend = FakeBackendRunner()
    services = BuildServices(
        config_loader=FakeConfigLoader(),
        source_reader=FileSourceReader(),
        lock_manager=FakeLockManager(),
        backend_runner=backend,
        materializer=FakeMaterializer(),
        prerequisite_probe=FakePrerequisiteProbe(),
        workspace_ops=FakeWorkspaceOps(),
    )
    result = execute_batch(
        source_dir=source_dir,
        workspace_root=tmp_path,
        request=BuildRequest(),
        services=services,
    )

    assert result.exit_code == ExitCode.SUCCESS
    assert len(result.results) == 1
    assert result.results[0][0].name == "main.tex"
    assert len(backend.compile_calls) == 1
    assert backend.compile_calls[0]["source_file"].name == "main.tex"
