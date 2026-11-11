"""Tests for managed TeX dependency installation and verification."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ktisma.app.tex_dependencies import (
    TexInstallServices,
    TexRuntimeServices,
    execute_tex_check,
    execute_tex_inspect,
    execute_tex_install,
    execute_tex_resolve,
)
from ktisma.domain.config import ConfigLayer, TexDependency
from ktisma.domain.exit_codes import ExitCode
from ktisma.infra.locks import FileLockManager
from ktisma.infra.tex_dependencies import FileTexSnapshotStore

COMMIT = "0123456789abcdef0123456789abcdef01234567"


class FakeConfigLoader:
    def __init__(self, dependencies: list[dict]) -> None:
        self.dependencies = dependencies

    def load_layers(self, workspace_root: Path, source_dir: Path) -> list[ConfigLayer]:
        return [
            ConfigLayer(
                data={
                    "_schema": "ktisma:configuration@2",
                    "tex": {"dependencies": self.dependencies},
                },
                source=workspace_root / "ktisma.toml",
                is_workspace_root=True,
                label="root config",
            )
        ]


class FakeFetcher:
    def fetch(self, repository: str, commit: str, destination: Path) -> str:
        destination.mkdir(parents=True)
        return commit


class FixtureBuilder:
    def __init__(self, installed_path: str | None = None, symlink: bool = False) -> None:
        self.installed_path = installed_path
        self.symlink = symlink

    def install(self, dependency: TexDependency, checkout: Path, texmf_root: Path) -> None:
        relative = self.installed_path or f"tex/latex/{dependency.name}/{dependency.provides[0]}"
        target = texmf_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if self.symlink:
            source = checkout / "outside.sty"
            source.write_text("fixture", encoding="utf-8")
            target.symlink_to(source)
        else:
            target.write_text(dependency.name, encoding="utf-8")


class FailingBuilder:
    def install(self, dependency: TexDependency, checkout: Path, texmf_root: Path) -> None:
        raise ValueError("The builder failed.")


class FixtureResolver:
    def __init__(self, outside: Path | None = None) -> None:
        self.outside = outside

    def resolve(self, texmf_root: Path, entrypoint: str) -> Path | None:
        if self.outside is not None:
            return self.outside
        matches = list(texmf_root.rglob(entrypoint))
        return matches[0] if matches else None


def _dependency(name: str = "fixture") -> dict:
    return {
        "name": name,
        "repository": f"https://example.test/{name}.git",
        "commit": COMMIT,
        "builder": "fixture",
        "provides": [f"{name}.sty"],
    }


def _services(
    dependencies: list[dict],
    *,
    builder: FixtureBuilder | None = None,
    resolver: FixtureResolver | None = None,
) -> TexInstallServices:
    runtime = TexRuntimeServices(
        config_loader=FakeConfigLoader(dependencies),
        resolver=resolver or FixtureResolver(),
        store=FileTexSnapshotStore(),
        supported_builders=frozenset({"fixture"}),
    )
    return TexInstallServices(
        runtime=runtime,
        source_fetcher=FakeFetcher(),
        builders={"fixture": builder or FixtureBuilder()},
        lock_manager=FileLockManager(),
    )


def test_install_publishes_a_verifiable_snapshot(tmp_path: Path) -> None:
    services = _services([_dependency()])

    installed = execute_tex_install(tmp_path, services)
    checked = execute_tex_check(tmp_path, services.runtime)

    assert installed.exit_code == ExitCode.SUCCESS
    assert installed.resolved_entrypoints["fixture:fixture.sty"].is_file()
    assert "tex-staging" not in str(installed.resolved_entrypoints["fixture:fixture.sty"])
    assert checked.exit_code == ExitCode.SUCCESS
    assert checked.texmf_root is not None
    assert checked.texmf_root.is_absolute()
    assert checked.resolved_entrypoints["fixture:fixture.sty"].is_file()
    assert (tmp_path / ".ktisma" / "tex-current").read_text().strip() == installed.record_digest


def test_install_reuses_an_unchanged_snapshot(tmp_path: Path) -> None:
    services = _services([_dependency()])
    first = execute_tex_install(tmp_path, services)
    assert first.texmf_root is not None
    receipt = first.texmf_root.parent / "receipt.json"
    first_bytes = receipt.read_bytes()

    second = execute_tex_install(tmp_path, services)

    assert second.exit_code == ExitCode.SUCCESS
    assert receipt.read_bytes() == first_bytes


def test_collision_preserves_the_previous_pointer(tmp_path: Path) -> None:
    valid_services = _services([_dependency()])
    valid = execute_tex_install(tmp_path, valid_services)
    pointer = tmp_path / ".ktisma" / "tex-current"
    previous = pointer.read_text()
    collision_services = _services(
        [_dependency("first"), _dependency("second")],
        builder=FixtureBuilder(installed_path="tex/latex/shared.sty"),
    )

    failed = execute_tex_install(tmp_path, collision_services)

    assert failed.exit_code == ExitCode.CONFIG_ERROR
    assert failed.diagnostics[0].code == "tex-install-failed"
    assert pointer.read_text() == previous
    assert valid.record_digest == previous.strip()


def test_modified_snapshot_fails_manifest_check(tmp_path: Path) -> None:
    services = _services([_dependency()])
    installed = execute_tex_install(tmp_path, services)
    assert installed.texmf_root is not None
    next(installed.texmf_root.rglob("fixture.sty")).write_text("changed", encoding="utf-8")

    checked = execute_tex_check(tmp_path, services.runtime)

    assert checked.exit_code == ExitCode.CONFIG_ERROR
    assert checked.diagnostics[0].code == "tex-manifest-mismatch"


def test_global_resolution_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "global" / "fixture.sty"
    outside.parent.mkdir()
    outside.write_text("global", encoding="utf-8")
    services = _services([_dependency()], resolver=FixtureResolver(outside))

    result = execute_tex_install(tmp_path, services)

    assert result.exit_code == ExitCode.CONFIG_ERROR
    assert result.diagnostics[0].code == "tex-entrypoint-outside-snapshot"


def test_entrypoint_must_be_owned_by_its_qualified_provider(tmp_path: Path) -> None:
    first = _dependency("first")
    second = _dependency("second")
    first["provides"] = ["shared.palette.yml"]
    second["provides"] = ["shared.palette.yml"]
    services = _services([first, second])

    result = execute_tex_install(tmp_path, services)

    assert result.exit_code == ExitCode.CONFIG_ERROR
    assert result.diagnostics[0].code == "tex-entrypoint-provider-mismatch"


def test_symlink_installed_by_builder_is_rejected(tmp_path: Path) -> None:
    services = _services([_dependency()], builder=FixtureBuilder(symlink=True))

    result = execute_tex_install(tmp_path, services)

    assert result.exit_code == ExitCode.CONFIG_ERROR
    assert result.diagnostics[0].code == "tex-install-failed"


def test_inspect_reports_declaration_when_snapshot_is_missing(tmp_path: Path) -> None:
    services = _services([_dependency()])

    result = execute_tex_inspect(tmp_path, services.runtime)

    assert result.exit_code == ExitCode.CONFIG_ERROR
    assert [dependency.name for dependency in result.declared_dependencies] == ["fixture"]


def test_resolve_returns_one_declared_entrypoint(tmp_path: Path) -> None:
    services = _services([_dependency()])
    execute_tex_install(tmp_path, services)

    result = execute_tex_resolve(tmp_path, "fixture:fixture.sty", services.runtime)

    assert result.exit_code == ExitCode.SUCCESS
    assert result.reference == "fixture:fixture.sty"
    assert result.path is not None
    assert result.path.is_file()
    assert result.record_digest is not None


def test_resolve_rejects_an_undeclared_reference(tmp_path: Path) -> None:
    services = _services([_dependency()])
    execute_tex_install(tmp_path, services)

    result = execute_tex_resolve(tmp_path, "fixture:missing.yml", services.runtime)

    assert result.exit_code == ExitCode.CONFIG_ERROR
    assert result.path is None
    assert result.diagnostics[0].code == "tex-entrypoint-undeclared"


def test_resolve_rejects_a_modified_snapshot(tmp_path: Path) -> None:
    services = _services([_dependency()])
    installed = execute_tex_install(tmp_path, services)
    assert installed.texmf_root is not None
    next(installed.texmf_root.rglob("fixture.sty")).write_text("changed", encoding="utf-8")

    result = execute_tex_resolve(tmp_path, "fixture:fixture.sty", services.runtime)

    assert result.exit_code == ExitCode.CONFIG_ERROR
    assert result.path is None
    assert result.diagnostics[0].code == "tex-manifest-mismatch"


def _receipt_path(result) -> Path:
    assert result.texmf_root is not None
    return result.texmf_root.parent / "receipt.json"


def _rewrite_receipt(path: Path, *remove: str, **add: object) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in remove:
        data.pop(key, None)
    data.update(add)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_receipt_declares_its_format_as_the_first_key(tmp_path: Path) -> None:
    services = _services([_dependency()])

    installed = execute_tex_install(tmp_path, services)

    data = json.loads(_receipt_path(installed).read_text(encoding="utf-8"))
    assert next(iter(data)) == "_schema"
    assert data["_schema"] == "ktisma:tex-dependencies@1"
    assert "schema_version" not in data


@pytest.mark.parametrize(
    ("remove", "add"),
    [
        (("_schema",), {"schema_version": 1}),
        (("_schema",), {}),
        ((), {"_schema": "ktisma:tex-dependencies@9"}),
    ],
    ids=["old-key", "absent", "wrong"],
)
def test_receipt_of_another_format_is_stale_and_regenerated(
    tmp_path: Path, remove: tuple, add: dict
) -> None:
    services = _services([_dependency()])
    installed = execute_tex_install(tmp_path, services)
    receipt = _receipt_path(installed)
    _rewrite_receipt(receipt, *remove, **add)

    checked = execute_tex_check(tmp_path, services.runtime)

    assert checked.exit_code == ExitCode.CONFIG_ERROR
    assert [d.code for d in checked.diagnostics] == ["tex-snapshot-stale"]
    assert "_schema" in checked.diagnostics[0].message
    assert "ktisma:tex-dependencies@1" in checked.diagnostics[0].message
    assert "ktisma tex install" in checked.diagnostics[0].message

    reinstalled = execute_tex_install(tmp_path, services)

    assert reinstalled.exit_code == ExitCode.SUCCESS
    assert reinstalled.record_digest == installed.record_digest
    assert json.loads(receipt.read_text(encoding="utf-8"))["_schema"] == (
        "ktisma:tex-dependencies@1"
    )
    assert execute_tex_check(tmp_path, services.runtime).exit_code == ExitCode.SUCCESS


def test_failed_regeneration_keeps_the_stale_snapshot(tmp_path: Path) -> None:
    services = _services([_dependency()])
    installed = execute_tex_install(tmp_path, services)
    receipt = _receipt_path(installed)
    _rewrite_receipt(receipt, "_schema", schema_version=1)
    failing = _services([_dependency()], builder=FailingBuilder())

    result = execute_tex_install(tmp_path, failing)

    assert result.exit_code != ExitCode.SUCCESS
    assert receipt.is_file()
