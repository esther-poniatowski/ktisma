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
        "_schema": "ktisma:configuration@2",
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
    root_config = tmp_path / "ktisma.toml"
    loader = FakeConfigLoader(
        [
            ConfigLayer(
                data=_tex_data(),
                source=root_config,
                is_workspace_root=True,
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
    overlay = source_dir / "ktisma.toml"
    loader = FakeConfigLoader(
        [
            ConfigLayer(
                data=_tex_data(),
                source=overlay,
                base_dir=tmp_path,
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
    root_config = tmp_path / "ktisma.toml"
    overlay = source_dir / "ktisma.toml"
    loader = FakeConfigLoader(
        [
            ConfigLayer(
                data=_tex_data(),
                source=root_config,
                is_workspace_root=True,
                base_dir=tmp_path,
                label=str(root_config),
            ),
            ConfigLayer(
                data={"build": {"synctex": False}},
                source=overlay,
                base_dir=tmp_path,
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
    root_config = tmp_path / "ktisma.toml"
    overlay = source_dir / "ktisma.toml"
    loader = FakeConfigLoader(
        [
            ConfigLayer(
                data=_tex_data(),
                source=root_config,
                is_workspace_root=True,
                base_dir=tmp_path,
                label=str(root_config),
            ),
            ConfigLayer(
                data={"_schema": "ktisma:configuration@1", "build": {"synctex": False}},
                source=overlay,
                base_dir=tmp_path,
                label=str(overlay),
            ),
        ]
    )

    config, diagnostics = load_resolved_config(tmp_path, source_dir, loader)

    assert diagnostics == []
    assert config.schema_version == 2
    assert config.build.synctex is False
    assert [dependency.name for dependency in config.tex.dependencies] == ["fixture"]


def test_route_target_of_an_overlay_is_relative_to_the_root(tmp_path: Path) -> None:
    """A path written in an overlay reads from the root, like a path in the root file."""
    from ktisma.infra.config_loader import TomlConfigLoader

    (tmp_path / "ktisma.toml").write_text(
        '_schema = "ktisma:configuration@1"\n[routes]\n"a/*.tex" = "root-out/"\n'
    )
    source_dir = tmp_path / "papers"
    source_dir.mkdir()
    (source_dir / "ktisma.toml").write_text('[routes]\n"papers/*.tex" = "overlay-out/"\n')

    config, _ = load_resolved_config(tmp_path, source_dir, TomlConfigLoader())

    root = tmp_path.resolve()
    assert config.routes["a/*.tex"] == f"{root / 'root-out'}/"
    assert config.routes["papers/*.tex"] == f"{root / 'overlay-out'}/"


# ---------------------------------------------------------------------------
# The `_schema` key of the configuration files
# ---------------------------------------------------------------------------


def _root_layer(tmp_path: Path, data: dict) -> ConfigLayer:
    root_config = tmp_path / "ktisma.toml"
    return ConfigLayer(
        data=data,
        source=root_config,
        is_workspace_root=True,
        base_dir=tmp_path,
        label=str(root_config),
    )


def _overlay_layer(tmp_path: Path, data: dict) -> ConfigLayer:
    overlay = tmp_path / "documents" / "ktisma.toml"
    return ConfigLayer(data=data, source=overlay, base_dir=tmp_path, label=str(overlay))


def _load(tmp_path: Path, layers: list[ConfigLayer]):
    source_dir = tmp_path / "documents"
    source_dir.mkdir(exist_ok=True)
    return load_resolved_config(tmp_path, source_dir, FakeConfigLoader(layers))


@pytest.mark.parametrize(
    ("identifier", "version"),
    [("ktisma:configuration@1", 1), ("ktisma:configuration@2", 2)],
)
def test_outermost_file_declares_a_supported_schema(
    tmp_path: Path, identifier: str, version: int
) -> None:
    config, diagnostics = _load(tmp_path, [_root_layer(tmp_path, {"_schema": identifier})])

    assert diagnostics == []
    assert config.schema_version == version


def test_absent_schema_key_in_the_outermost_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as excinfo:
        _load(tmp_path, [_root_layer(tmp_path, {"build": {"synctex": False}})])

    assert excinfo.value.exit_code == 2
    assert [d.code for d in excinfo.value.diagnostics] == ["missing-schema"]
    message = excinfo.value.diagnostics[0].message
    assert "_schema" in message
    assert "ktisma:configuration@1" in message
    assert "ktisma:configuration@2" in message


def test_overlay_may_omit_the_schema_key(tmp_path: Path) -> None:
    config, diagnostics = _load(
        tmp_path,
        [
            _root_layer(tmp_path, {"_schema": "ktisma:configuration@2"}),
            _overlay_layer(tmp_path, {"build": {"synctex": False}}),
        ],
    )

    assert diagnostics == []
    assert config.schema_version == 2
    assert config.build.synctex is False


def test_outermost_overlay_requires_the_schema_key_without_a_root_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as excinfo:
        _load(tmp_path, [_overlay_layer(tmp_path, {"build": {"synctex": False}})])

    assert [d.code for d in excinfo.value.diagnostics] == ["missing-schema"]


@pytest.mark.parametrize(
    "value",
    [
        "ktisma:configuration@9",
        "ktisma:configuration",
        "elenchos:configuration@1",
        2,
        ["ktisma:configuration@2"],
    ],
)
def test_wrong_identifier_is_an_error(tmp_path: Path, value: object) -> None:
    with pytest.raises(ConfigError) as excinfo:
        _load(tmp_path, [_root_layer(tmp_path, {"_schema": value})])

    assert excinfo.value.exit_code == 2
    assert [d.code for d in excinfo.value.diagnostics] == ["unsupported-schema"]
    assert "ktisma:configuration@2" in excinfo.value.diagnostics[0].message


def test_wrong_identifier_in_an_overlay_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as excinfo:
        _load(
            tmp_path,
            [
                _root_layer(tmp_path, {"_schema": "ktisma:configuration@2"}),
                _overlay_layer(tmp_path, {"_schema": "ktisma:configuration@7"}),
            ],
        )

    assert [d.code for d in excinfo.value.diagnostics] == ["unsupported-schema"]


@pytest.mark.parametrize(("old", "expected"), [(1, "@1"), (2, "@2")])
def test_retired_key_names_the_value_to_write(tmp_path: Path, old: int, expected: str) -> None:
    with pytest.raises(ConfigError) as excinfo:
        _load(tmp_path, [_root_layer(tmp_path, {"schema_version": old})])

    assert excinfo.value.exit_code == 2
    assert [d.code for d in excinfo.value.diagnostics] == ["retired-schema-key"]
    message = excinfo.value.diagnostics[0].message
    assert "schema_version" in message
    assert f'_schema = "ktisma:configuration{expected}"' in message


def test_retired_key_in_an_overlay_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as excinfo:
        _load(
            tmp_path,
            [
                _root_layer(tmp_path, {"_schema": "ktisma:configuration@2"}),
                _overlay_layer(tmp_path, {"schema_version": 1}),
            ],
        )

    assert [d.code for d in excinfo.value.diagnostics] == ["retired-schema-key"]


def test_no_configuration_file_runs_on_the_built_in_defaults(tmp_path: Path) -> None:
    config, diagnostics = _load(tmp_path, [])

    assert diagnostics == []
    assert config.schema_version == 1
