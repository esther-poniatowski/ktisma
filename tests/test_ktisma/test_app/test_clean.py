"""Tests for ktisma.app.clean — safe cleanup of source-owned build directories."""

from __future__ import annotations

import json
from pathlib import Path

from ktisma.app.clean import execute_clean
from ktisma.domain.config import ConfigLayer
from ktisma.domain.exit_codes import ExitCode

from .test_build import FakeConfigLoader, FakeWorkspaceOps


def test_clean_uses_metadata_to_avoid_prefix_collisions(tmp_path: Path) -> None:
    source = tmp_path / "paper.tex"
    other_source = tmp_path / "paper-draft.tex"
    source.write_text("\\documentclass{article}\n", encoding="utf-8")
    other_source.write_text("\\documentclass{article}\n", encoding="utf-8")

    config_loader = FakeConfigLoader(
        layers=[
            ConfigLayer(
                data={"_schema": "ktisma:configuration@1"},
                source=tmp_path / "ktisma.toml",
                label="test",
            )
        ]
    )
    workspace_ops = FakeWorkspaceOps()

    build_root = tmp_path / ".ktisma_build"
    own_variant_dir = build_root / "paper-print"
    other_base_dir = build_root / "paper-draft"
    own_variant_dir.mkdir(parents=True)
    other_base_dir.mkdir(parents=True)
    (own_variant_dir / ".ktisma.meta.json").write_text(
        json.dumps({"source": str(source), "variant": "print"}),
        encoding="utf-8",
    )
    (other_base_dir / ".ktisma.meta.json").write_text(
        json.dumps({"source": str(other_source), "variant": None}),
        encoding="utf-8",
    )

    result = execute_clean(
        target=source,
        workspace_root=tmp_path,
        config_loader=config_loader,
        workspace_ops=workspace_ops,
    )

    assert result.exit_code == ExitCode.SUCCESS
    assert own_variant_dir in result.removed_dirs
    assert not own_variant_dir.exists()
    assert other_base_dir.exists()


def test_clean_refuses_a_folder_of_the_state_directory(tmp_path: Path) -> None:
    """The TeX snapshots under .ktisma/ are managed by `ktisma tex install`, not by clean."""
    snapshots = tmp_path / ".ktisma" / "tex-snapshots"
    snapshots.mkdir(parents=True)

    result = execute_clean(
        target=snapshots,
        workspace_root=None,
        config_loader=FakeConfigLoader(layers=[]),
        workspace_ops=FakeWorkspaceOps(),
    )

    assert result.exit_code == ExitCode.CONFIG_ERROR
    assert [d.code for d in result.diagnostics] == ["not-build-dir"]
    assert snapshots.is_dir()


def test_clean_without_root_reads_the_configuration_resolved_as_build_does(
    tmp_path: Path, monkeypatch
) -> None:
    """Without --root, clean resolves the workspace root from the source, like build."""
    from ktisma.adapters import bootstrap

    monkeypatch.delenv("KTISMA_ROOT", raising=False)
    (tmp_path / "ktisma.toml").write_text(
        '_schema = "ktisma:configuration@1"\n[build]\nout_dir_name = "_out"\n', encoding="utf-8"
    )
    source_dir = tmp_path / "chapter"
    source_dir.mkdir()
    source = source_dir / "paper.tex"
    source.write_text("\\documentclass{article}\n", encoding="utf-8")
    build_dir = source_dir / "_out" / "paper"
    build_dir.mkdir(parents=True)

    result = bootstrap.clean(target=source)

    assert result.exit_code == ExitCode.SUCCESS
    assert result.removed_dirs == [build_dir]
    assert not build_dir.exists()
