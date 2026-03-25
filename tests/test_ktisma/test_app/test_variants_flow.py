from __future__ import annotations

import json
from pathlib import Path

from ktisma.app.clean import execute_clean
from ktisma.app.protocols import BuildServices
from ktisma.app.variants import execute_variants
from ktisma.domain.config import ConfigLayer
from ktisma.domain.context import BuildRequest
from ktisma.domain.exit_codes import ExitCode

from .test_build import (
    FakeBackendRunner,
    FakeConfigLoader,
    FakeLockManager,
    FakeMaterializer,
    FakePrerequisiteProbe,
    FakeSourceReader,
    FakeWorkspaceOps,
    _make_ctx,
)


def _make_services(*, layers: list[ConfigLayer] | None = None) -> BuildServices:
    return BuildServices(
        config_loader=FakeConfigLoader(layers=layers),
        source_reader=FakeSourceReader(),
        lock_manager=FakeLockManager(),
        backend_runner=FakeBackendRunner(),
        materializer=FakeMaterializer(),
        prerequisite_probe=FakePrerequisiteProbe(),
        workspace_ops=FakeWorkspaceOps(),
    )


def test_execute_variants_preserves_structured_variant_metadata(monkeypatch, tmp_path: Path) -> None:
    config_layer = ConfigLayer(
        data={
            "variants": {
                "review": {
                    "payload": "\\def\\mode{review}",
                    "engine": "lualatex",
                    "output": "variant-output/",
                    "filename_suffix": "_review",
                }
            }
        },
        source=tmp_path / ".ktisma.toml",
        label="test config",
    )
    captured_requests: list[BuildRequest] = []

    def fake_execute_build(*, ctx, request, services, route_resolvers=None, engine_rules=None):
        captured_requests.append(request)
        from ktisma.app.build import BuildResult

        return BuildResult(exit_code=ExitCode.SUCCESS)

    monkeypatch.setattr("ktisma.app.variants.execute_build", fake_execute_build)

    result = execute_variants(
        ctx=_make_ctx(tmp_path),
        request=BuildRequest(),
        services=_make_services(layers=[config_layer]),
    )

    assert result.exit_code == ExitCode.SUCCESS
    assert len(captured_requests) == 1
    assert captured_requests[0].variant_spec is not None
    assert captured_requests[0].variant_spec.engine_override == "lualatex"
    assert captured_requests[0].variant_spec.output_override == "variant-output/"
    assert captured_requests[0].variant_spec.filename_suffix == "_review"


def test_clean_matches_canonical_source_identity(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "paper.tex"
    source.write_text("\\documentclass{article}\n", encoding="utf-8")
    workspace_ops = FakeWorkspaceOps()

    build_root = tmp_path / ".ktisma_build"
    own_variant_dir = build_root / "paper-print"
    own_variant_dir.mkdir(parents=True)
    (own_variant_dir / ".ktisma.meta.json").write_text(
        json.dumps({"source": str(source.resolve()), "variant": "print"}),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    result = execute_clean(
        target=Path("paper.tex"),
        workspace_root=tmp_path,
        config_loader=FakeConfigLoader(layers=[ConfigLayer(data={}, source=tmp_path / ".ktisma.toml", label="test")]),
        workspace_ops=workspace_ops,
    )

    assert result.exit_code == ExitCode.SUCCESS
    assert own_variant_dir in result.removed_dirs
