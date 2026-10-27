"""Tests for filesystem and Git adapters used by TeX snapshots."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ktisma.infra.tex_dependencies import FileTexSnapshotStore, GitTexSourceFetcher


def _git(repository: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_git_fetcher_checks_out_the_exact_commit(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "--quiet")
    _git(repository, "config", "user.name", "Fixture")
    _git(repository, "config", "user.email", "fixture@example.test")
    (repository / "fixture.sty").write_text("first", encoding="utf-8")
    _git(repository, "add", "fixture.sty")
    _git(repository, "commit", "--quiet", "-m", "first")
    expected = _git(repository, "rev-parse", "HEAD")
    (repository / "fixture.sty").write_text("second", encoding="utf-8")
    _git(repository, "commit", "--quiet", "-am", "second")

    destination = tmp_path / "checkout"
    actual = GitTexSourceFetcher().fetch(str(repository), expected, destination)

    assert actual == expected
    assert (destination / "fixture.sty").read_text(encoding="utf-8") == "first"


def test_invalid_active_pointer_is_not_treated_as_a_path(tmp_path: Path) -> None:
    pointer = tmp_path / ".ktisma" / "tex-current"
    pointer.parent.mkdir()
    pointer.write_text("../../outside\n", encoding="utf-8")

    assert FileTexSnapshotStore().read_active_digest(tmp_path) is None
