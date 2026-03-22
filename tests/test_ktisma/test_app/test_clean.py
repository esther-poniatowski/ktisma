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
        layers=[ConfigLayer(data={}, source=tmp_path / ".ktisma.toml", label="test")]
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
