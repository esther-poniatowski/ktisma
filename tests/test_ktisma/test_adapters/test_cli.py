"""Tests for the CLI adapter argument parsing and dispatch."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ktisma.adapters.cli import main
from ktisma.domain.exit_codes import ExitCode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _StubResult:
    """Minimal stub satisfying the interface of BuildResult and friends."""

    def __init__(self, exit_code: int = 0) -> None:
        self.exit_code = exit_code
        self.diagnostics: list = []
        self.engine = None
        self.route = None
        self.build_plan = None
        self.backend_result = None
        self.produced_paths: list = []
        self.removed_dirs: list = []
        self.checks: list = []
        self.results: list = []


class _StubDecision:
    """Minimal stub for EngineDecision / RouteDecision."""

    def __init__(self) -> None:
        self.diagnostics: list = []
        self.engine = "pdflatex"
        self.evidence: list = []
        self.ambiguous = False
        self.destination = Path("/tmp/out")
        self.matched_rule = None
        self.fallback = True

    def to_dict(self, *args, **kwargs) -> dict:
        return {"engine": self.engine}


# ---------------------------------------------------------------------------
# No subcommand -> error
# ---------------------------------------------------------------------------


def test_no_subcommand_returns_config_error():
    code = main([])
    assert code == ExitCode.CONFIG_ERROR


# ---------------------------------------------------------------------------
# --help exits with 0 (argparse raises SystemExit)
# ---------------------------------------------------------------------------


def test_help_flag_exits_zero():
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0


# ---------------------------------------------------------------------------
# build subcommand
# ---------------------------------------------------------------------------


@patch("ktisma.adapters.bootstrap.build")
def test_build_subcommand_parses_source(mock_build):
    mock_build.return_value = _StubResult()
    code = main(["build", "main.tex"])
    assert code == ExitCode.SUCCESS
    call_kwargs = mock_build.call_args
    assert call_kwargs[1]["source_file"] == Path("main.tex")


@patch("ktisma.adapters.bootstrap.build")
def test_build_with_engine_override(mock_build):
    mock_build.return_value = _StubResult()
    main(["build", "main.tex", "--engine", "xelatex"])
    request = mock_build.call_args[1]["request"]
    assert request.engine_override == "xelatex"


@patch("ktisma.adapters.bootstrap.build")
def test_build_with_watch_flag(mock_build):
    mock_build.return_value = _StubResult()
    main(["build", "main.tex", "--watch"])
    request = mock_build.call_args[1]["request"]
    assert request.watch is True


@patch("ktisma.adapters.bootstrap.build")
def test_build_with_dry_run(mock_build):
    mock_build.return_value = _StubResult()
    main(["build", "main.tex", "--dry-run"])
    request = mock_build.call_args[1]["request"]
    assert request.dry_run is True


@patch("ktisma.adapters.bootstrap.build")
def test_build_with_variant(mock_build):
    mock_build.return_value = _StubResult()
    main(["build", "main.tex", "--variant", "print"])
    request = mock_build.call_args[1]["request"]
    assert request.variant == "print"


@patch("ktisma.adapters.bootstrap.build")
def test_build_with_variant_payload(mock_build):
    mock_build.return_value = _StubResult()
    main(["build", "main.tex", "--variant-payload", "\\def\\mode{print}"])
    request = mock_build.call_args[1]["request"]
    assert request.variant_payload == "\\def\\mode{print}"


@patch("ktisma.adapters.bootstrap.build")
def test_build_with_output_dir(mock_build):
    mock_build.return_value = _StubResult()
    main(["build", "main.tex", "--output-dir", "/tmp/out"])
    request = mock_build.call_args[1]["request"]
    assert request.output_dir_override is not None


@patch("ktisma.adapters.bootstrap.build")
def test_build_with_output_path(mock_build):
    mock_build.return_value = _StubResult()
    main(["build", "main.tex", "--output", "/tmp/out/custom.pdf"])
    request = mock_build.call_args[1]["request"]
    assert request.output_path_override == Path("/tmp/out/custom.pdf").resolve()


@patch("ktisma.adapters.bootstrap.build")
def test_build_with_cleanup(mock_build):
    mock_build.return_value = _StubResult()
    main(["build", "main.tex", "--cleanup", "on_success"])
    request = mock_build.call_args[1]["request"]
    assert request.cleanup_override == "on_success"


@patch("ktisma.adapters.bootstrap.build")
def test_build_with_json_flag(mock_build):
    mock_build.return_value = _StubResult()
    main(["build", "main.tex", "--json"])
    request = mock_build.call_args[1]["request"]
    assert request.json_output is True


@patch("ktisma.adapters.bootstrap.build")
def test_build_with_workspace_root(mock_build):
    mock_build.return_value = _StubResult()
    main(["build", "main.tex", "--workspace-root", "/home/user/project"])
    call_kwargs = mock_build.call_args[1]
    assert call_kwargs["workspace_root"] == Path("/home/user/project")


# ---------------------------------------------------------------------------
# inspect engine subcommand
# ---------------------------------------------------------------------------


@patch("ktisma.adapters.bootstrap.inspect_engine_cmd")
def test_inspect_engine_parses_args(mock_fn):
    mock_fn.return_value = _StubDecision()
    code = main(["inspect", "engine", "main.tex"])
    assert code == ExitCode.SUCCESS
    assert mock_fn.call_args[1]["source_file"] == Path("main.tex")


@patch("ktisma.adapters.bootstrap.inspect_engine_cmd")
def test_inspect_engine_with_override(mock_fn):
    mock_fn.return_value = _StubDecision()
    main(["inspect", "engine", "main.tex", "--engine", "lualatex"])
    request = mock_fn.call_args[1]["request"]
    assert request.engine_override == "lualatex"


@patch("ktisma.adapters.bootstrap.inspect_engine_cmd")
def test_inspect_engine_json(mock_fn):
    mock_fn.return_value = _StubDecision()
    main(["inspect", "engine", "main.tex", "--json"])
    request = mock_fn.call_args[1]["request"]
    assert request.json_output is True


# ---------------------------------------------------------------------------
# inspect route subcommand
# ---------------------------------------------------------------------------


@patch("ktisma.adapters.bootstrap.inspect_route_cmd")
def test_inspect_route_parses_args(mock_fn):
    mock_fn.return_value = _StubDecision()
    code = main(["inspect", "route", "main.tex"])
    assert code == ExitCode.SUCCESS
    assert mock_fn.call_args[1]["source_file"] == Path("main.tex")


@patch("ktisma.adapters.bootstrap.inspect_route_cmd")
def test_inspect_route_with_output_dir(mock_fn):
    mock_fn.return_value = _StubDecision()
    main(["inspect", "route", "main.tex", "--output-dir", "/tmp/pdf"])
    request = mock_fn.call_args[1]["request"]
    assert request.output_dir_override is not None


@patch("ktisma.adapters.bootstrap.inspect_route_cmd")
def test_inspect_route_with_output_path(mock_fn):
    mock_fn.return_value = _StubDecision()
    main(["inspect", "route", "main.tex", "--output", "/tmp/custom.pdf"])
    request = mock_fn.call_args[1]["request"]
    assert request.output_path_override == Path("/tmp/custom.pdf").resolve()


# ---------------------------------------------------------------------------
# clean subcommand
# ---------------------------------------------------------------------------


@patch("ktisma.adapters.bootstrap.clean")
def test_clean_parses_target(mock_fn):
    mock_fn.return_value = _StubResult()
    code = main(["clean", "main.tex"])
    assert code == ExitCode.SUCCESS
    assert mock_fn.call_args[1]["target"] == Path("main.tex")


@patch("ktisma.adapters.bootstrap.clean")
def test_clean_with_workspace_root(mock_fn):
    mock_fn.return_value = _StubResult()
    main(["clean", "main.tex", "--workspace-root", "/home/user/project"])
    assert mock_fn.call_args[1]["workspace_root"] == Path("/home/user/project")


# ---------------------------------------------------------------------------
# doctor subcommand
# ---------------------------------------------------------------------------


@patch("ktisma.adapters.bootstrap.doctor")
def test_doctor_runs(mock_fn):
    mock_fn.return_value = _StubResult()
    code = main(["doctor"])
    assert code == ExitCode.SUCCESS


@patch("ktisma.adapters.bootstrap.doctor")
def test_doctor_with_json(mock_fn):
    result = _StubResult()
    result.checks = []
    mock_fn.return_value = result
    code = main(["doctor", "--json"])
    assert code == ExitCode.SUCCESS


# ---------------------------------------------------------------------------
# batch subcommand
# ---------------------------------------------------------------------------


@patch("ktisma.adapters.bootstrap.batch")
def test_batch_parses_source_dir(mock_fn):
    mock_fn.return_value = _StubResult()
    code = main(["batch", "/tmp/texfiles"])
    assert code == ExitCode.SUCCESS
    assert mock_fn.call_args[1]["source_dir"] == Path("/tmp/texfiles")


@patch("ktisma.adapters.bootstrap.batch")
def test_batch_with_engine_and_watch(mock_fn):
    mock_fn.return_value = _StubResult()
    main(["batch", "/tmp/texfiles", "--engine", "xelatex", "--watch"])
    request = mock_fn.call_args[1]["request"]
    assert request.engine_override == "xelatex"
    assert request.watch is True


# ---------------------------------------------------------------------------
# variants subcommand
# ---------------------------------------------------------------------------


@patch("ktisma.adapters.bootstrap.variants")
def test_variants_parses_source(mock_fn):
    mock_fn.return_value = _StubResult()
    code = main(["variants", "main.tex"])
    assert code == ExitCode.SUCCESS
    assert mock_fn.call_args[1]["source_file"] == Path("main.tex")


@patch("ktisma.adapters.bootstrap.variants")
def test_variants_with_engine_and_json(mock_fn):
    mock_fn.return_value = _StubResult()
    main(["variants", "main.tex", "--engine", "lualatex", "--json"])
    request = mock_fn.call_args[1]["request"]
    assert request.engine_override == "lualatex"
    assert request.json_output is True


# ---------------------------------------------------------------------------
# verbose flag is accepted globally
# ---------------------------------------------------------------------------


@patch("ktisma.adapters.bootstrap.build")
def test_verbose_flag_accepted(mock_build):
    mock_build.return_value = _StubResult()
    code = main(["-v", "build", "main.tex"])
    assert code == ExitCode.SUCCESS
