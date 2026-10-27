"""Tests for configuration-layer rules owned by the application boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from ktisma.app.configuration import load_resolved_config
from ktisma.domain.config import ConfigLayer
from ktisma.domain.errors import ConfigError

COMMIT = "0123456789abcdef0123456789abcdef01234567"


class FakeConfigLoader:
    def __init__(self, layers: list[ConfigLayer]) -> None:
        self.layers = layers

    def load_layers(self, workspace_root: Path, source_dir: Path) -> list[ConfigLayer]:
        return list(self.layers)


def _tex_data() -> dict:
    return {
        "schema_version": 2,
        "tex": {
            "dependencies": [
                {
                    "name": "fixture",
                    "repository": "https://example.test/fixture.git",
                    "commit": COMMIT,
                    "builder": "fixture",
                    "provides": ["fixture.sty"],
                }
            ]
        },
    }


def test_workspace_root_may_declare_tex_dependencies(tmp_path: Path) -> None:
    source_dir = tmp_path / "documents"
    source_dir.mkdir()
    root_config = tmp_path / ".ktisma.toml"
    loader = FakeConfigLoader(
        [
            ConfigLayer(
                data=_tex_data(),
                source=root_config,
                base_dir=tmp_path,
                label=str(root_config),
            )
        ]
    )

    config, diagnostics = load_resolved_config(tmp_path, source_dir, loader)

    assert diagnostics == []
    assert [dependency.name for dependency in config.tex.dependencies] == ["fixture"]


def test_overlay_cannot_declare_tex_dependencies(tmp_path: Path) -> None:
    source_dir = tmp_path / "documents"
    source_dir.mkdir()
    overlay = source_dir / ".ktisma.toml"
    loader = FakeConfigLoader(
        [
            ConfigLayer(
                data=_tex_data(),
                source=overlay,
                base_dir=source_dir,
                label=str(overlay),
            )
        ]
    )

    with pytest.raises(ConfigError) as exc_info:
        load_resolved_config(tmp_path, source_dir, loader)

    assert [diagnostic.code for diagnostic in exc_info.value.diagnostics] == [
        "tex-dependencies-not-root"
    ]


def test_programmatic_layer_cannot_declare_tex_dependencies(tmp_path: Path) -> None:
    source_dir = tmp_path / "documents"
    source_dir.mkdir()
    loader = FakeConfigLoader([])
    override = ConfigLayer(
        data=_tex_data(),
        source=None,
        label="command-line override",
    )

    with pytest.raises(ConfigError) as exc_info:
        load_resolved_config(tmp_path, source_dir, loader, extra_layers=[override])

    assert [diagnostic.code for diagnostic in exc_info.value.diagnostics] == [
        "tex-dependencies-not-root"
    ]


def test_overlay_without_tex_dependencies_remains_valid(tmp_path: Path) -> None:
    source_dir = tmp_path / "documents"
    source_dir.mkdir()
    root_config = tmp_path / ".ktisma.toml"
    overlay = source_dir / ".ktisma.toml"
    loader = FakeConfigLoader(
        [
            ConfigLayer(
                data=_tex_data(),
                source=root_config,
                base_dir=tmp_path,
                label=str(root_config),
            ),
            ConfigLayer(
                data={"build": {"synctex": False}},
                source=overlay,
                base_dir=source_dir,
                label=str(overlay),
            ),
        ]
    )

    config, diagnostics = load_resolved_config(tmp_path, source_dir, loader)

    assert diagnostics == []
    assert config.build.synctex is False
    assert [dependency.name for dependency in config.tex.dependencies] == ["fixture"]


def test_overlay_schema_version_does_not_downgrade_workspace(tmp_path: Path) -> None:
    source_dir = tmp_path / "documents"
    source_dir.mkdir()
    root_config = tmp_path / ".ktisma.toml"
    overlay = source_dir / ".ktisma.toml"
    loader = FakeConfigLoader(
        [
            ConfigLayer(
                data=_tex_data(),
                source=root_config,
                base_dir=tmp_path,
                label=str(root_config),
            ),
            ConfigLayer(
                data={"schema_version": 1, "build": {"synctex": False}},
                source=overlay,
                base_dir=source_dir,
                label=str(overlay),
            ),
        ]
    )

    config, diagnostics = load_resolved_config(tmp_path, source_dir, loader)

    assert diagnostics == []
    assert config.schema_version == 2
    assert config.build.synctex is False
    assert [dependency.name for dependency in config.tex.dependencies] == ["fixture"]
