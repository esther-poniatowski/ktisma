"""Tests for the CLI adapter argument parsing and dispatch."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ktisma.adapters.cli import _build_parser, main
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
        self.reports: list = []
        self.record_digest = None
        self.texmf_root = None
        self.receipt = None
        self.declared_dependencies: tuple = ()
        self.resolved_entrypoints: dict = {}
        self.reference = "fixture:fixture.sty"
        self.path = None


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
def test_build_with_json_format(mock_build):
    mock_build.return_value = _StubResult()
    main(["build", "main.tex", "--format", "json"])
    request = mock_build.call_args[1]["request"]
    assert request.json_output is True


@patch("ktisma.adapters.bootstrap.build")
def test_build_with_root(mock_build):
    mock_build.return_value = _StubResult()
    main(["build", "main.tex", "--root", "/home/user/project"])
    call_kwargs = mock_build.call_args[1]
    assert call_kwargs["workspace_root"] == Path("/home/user/project")


@pytest.mark.parametrize(
    ("command", "bootstrap_name"),
    [("install", "tex_install"), ("check", "tex_check"), ("inspect", "tex_inspect")],
)
def test_tex_subcommands_dispatch(command, bootstrap_name):
    with patch(f"ktisma.adapters.bootstrap.{bootstrap_name}") as mock_fn:
        mock_fn.return_value = _StubResult()

        code = main(["tex", command, "--root", "/tmp/workspace", "--format", "json"])

    assert code == ExitCode.SUCCESS
    assert mock_fn.call_args.args == (Path("/tmp/workspace"),)


@patch("ktisma.adapters.bootstrap.tex_resolve")
def test_tex_resolve_prints_only_the_selected_path(mock_fn, capsys):
    result = _StubResult()
    result.path = Path("/tmp/snapshot/fixture.sty")
    mock_fn.return_value = result

    code = main(
        [
            "tex",
            "resolve",
            "fixture:fixture.sty",
            "--root",
            "/tmp/workspace",
        ]
    )

    assert code == ExitCode.SUCCESS
    assert capsys.readouterr().out == "/tmp/snapshot/fixture.sty\n"
    assert mock_fn.call_args.args == ("fixture:fixture.sty", Path("/tmp/workspace"))


@patch("ktisma.adapters.bootstrap.tex_resolve")
def test_tex_resolve_json_reports_the_resolution(mock_fn, capsys):
    result = _StubResult()
    result.path = Path("/tmp/snapshot/fixture.sty")
    result.record_digest = "record-digest"
    mock_fn.return_value = result

    code = main(["tex", "resolve", "fixture:fixture.sty", "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == ExitCode.SUCCESS
    assert payload == {
        "diagnostics": [],
        "exit_code": 0,
        "path": "/tmp/snapshot/fixture.sty",
        "record_digest": "record-digest",
        "reference": "fixture:fixture.sty",
    }


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
    main(["inspect", "engine", "main.tex", "--format", "json"])
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
def test_clean_with_root(mock_fn):
    mock_fn.return_value = _StubResult()
    main(["clean", "main.tex", "--root", "/home/user/project"])
    assert mock_fn.call_args[1]["workspace_root"] == Path("/home/user/project")


# ---------------------------------------------------------------------------
# check-log subcommand
# ---------------------------------------------------------------------------


@patch("ktisma.adapters.bootstrap.check_log")
def test_check_log_parses_paths_and_channels(mock_fn):
    mock_fn.return_value = _StubResult()

    code = main(
        [
            "check-log",
            "tex",
            "poster",
            "--build-dir",
            "work",
            "--channel",
            "layout,fit",
            "--channel",
            "banner",
        ]
    )

    assert code == ExitCode.SUCCESS
    assert mock_fn.call_args.kwargs == {
        "source_dir": Path("tex"),
        "build_dir_name": "work",
        "stem": "poster",
        "channels": ("layout", "fit", "banner"),
    }


def test_check_log_cli_reports_planted_failure(tmp_path, capsys):
    log = tmp_path / ".ktisma_build" / "poster" / "poster.log"
    log.parent.mkdir(parents=True)
    log.write_text(
        "Overfull \\hbox (1.0pt too wide)\nOutput written on poster.pdf (1 page).\n",
        encoding="utf-8",
    )

    code = main(["check-log", str(tmp_path), "--channel", "layout"])

    captured = capsys.readouterr()
    assert code == ExitCode.COMPILATION_FAILURE
    assert "FAIL  1 x overfull hbox" in captured.out
    assert "BASELINE VIOLATED." in captured.out


def test_check_log_cli_reads_log_that_is_not_valid_utf8(tmp_path, capsys):
    log = tmp_path / ".ktisma_build" / "poster.log"
    log.parent.mkdir(parents=True)
    log.write_bytes(
        b"Overfull \\hbox (1.0pt too wide)\n\\T1/cmr/m/n/10 \xe9t\xe9\n"
        b"Output written on caf\xc3\n\xa9.pdf (1 page).\n"
    )

    code = main(["check-log", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == ExitCode.COMPILATION_FAILURE
    assert "FAIL  1 x overfull hbox" in captured.out
    assert "ok    Output written on caf�" in captured.out


def test_check_log_cli_returns_contract_error_for_missing_source(tmp_path, capsys):
    code = main(["check-log", str(tmp_path / "missing")])

    captured = capsys.readouterr()
    assert code == ExitCode.CONFIG_ERROR
    assert "missing-source-dir" in captured.err


def test_check_log_cli_returns_failure_for_missing_build_directory(tmp_path, capsys):
    code = main(["check-log", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == ExitCode.COMPILATION_FAILURE
    assert "missing-build-dir" in captured.err


def test_check_log_cli_returns_failure_for_missing_selected_log(tmp_path, capsys):
    (tmp_path / ".ktisma_build").mkdir()

    code = main(["check-log", str(tmp_path), "poster"])

    captured = capsys.readouterr()
    assert code == ExitCode.COMPILATION_FAILURE
    assert "missing-log" in captured.err


def test_check_log_cli_returns_success_for_clean_log(tmp_path, capsys):
    log = tmp_path / ".ktisma_build" / "poster.log"
    log.parent.mkdir(parents=True)
    log.write_text("Output written on poster.pdf (1 page).\n", encoding="utf-8")

    code = main(["check-log", str(tmp_path)])

    captured = capsys.readouterr()
    assert code == ExitCode.SUCCESS
    assert "zero baseline holds." in captured.out


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
    code = main(["doctor", "--format", "json"])
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
    main(["variants", "main.tex", "--engine", "lualatex", "--format", "json"])
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


# ---------------------------------------------------------------------------
# Renamed options and their deprecated aliases
# ---------------------------------------------------------------------------

# Every command taking --root, as the arguments that precede the option.
_ROOT_COMMANDS = [
    ["build", "main.tex"],
    ["inspect", "engine", "main.tex"],
    ["inspect", "route", "main.tex"],
    ["clean", "main.tex"],
    ["doctor"],
    ["batch", "/tmp/texfiles"],
    ["variants", "main.tex"],
    ["init"],
    ["tex", "install"],
    ["tex", "check"],
    ["tex", "inspect"],
    ["tex", "resolve", "fixture:fixture.sty"],
]

# Every command taking --format, with the bootstrap entry and the stub it returns.
_FORMAT_COMMANDS = [
    (["build", "main.tex"], "build", _StubResult),
    (["inspect", "engine", "main.tex"], "inspect_engine_cmd", _StubDecision),
    (["inspect", "route", "main.tex"], "inspect_route_cmd", _StubDecision),
    (["doctor"], "doctor", _StubResult),
    (["batch", "/tmp/texfiles"], "batch", _StubResult),
    (["variants", "main.tex"], "variants", _StubResult),
    (["tex", "install"], "tex_install", _StubResult),
    (["tex", "check"], "tex_check", _StubResult),
    (["tex", "inspect"], "tex_inspect", _StubResult),
    (["tex", "resolve", "fixture:fixture.sty"], "tex_resolve", _StubResult),
]


@pytest.fixture
def clean_root_environment(monkeypatch):
    monkeypatch.delenv("KTISMA_ROOT", raising=False)
    monkeypatch.delenv("KTISMA_WORKSPACE_ROOT", raising=False)


@pytest.mark.parametrize("command", _ROOT_COMMANDS, ids=" ".join)
def test_root_option_sets_the_workspace_root(command):
    args = _build_parser().parse_args([*command, "--root", "/tmp/workspace"])
    assert args.workspace_root == Path("/tmp/workspace")
    assert not getattr(args, "_deprecations", None)


@pytest.mark.parametrize("command", _ROOT_COMMANDS, ids=" ".join)
def test_workspace_root_alias_still_works_and_records_a_warning(command):
    args = _build_parser().parse_args([*command, "--workspace-root", "/tmp/workspace"])
    assert args.workspace_root == Path("/tmp/workspace")
    assert [d.code for d in args._deprecations] == ["deprecated-option"]
    assert "--root" in args._deprecations[0].message


@pytest.mark.parametrize("command", [c for c, _, _ in _FORMAT_COMMANDS], ids=" ".join)
def test_format_defaults_to_text_and_json_alias_selects_json(command):
    parser = _build_parser()
    assert parser.parse_args(command).format == "text"
    assert parser.parse_args([*command, "--format", "json"]).format == "json"
    legacy = parser.parse_args([*command, "--json"])
    assert legacy.format == "json"
    assert "--format json" in legacy._deprecations[0].message


@pytest.mark.parametrize("command", [["build", "--help"], ["tex", "check", "--help"]])
def test_help_lists_only_the_new_names(command, capsys):
    with pytest.raises(SystemExit):
        main(command)
    out = capsys.readouterr().out
    assert "--root PATH" in out
    assert "--format {text,json}" in out
    assert "--workspace-root" not in out
    assert "--json" not in out


@patch("ktisma.adapters.bootstrap.build")
def test_workspace_root_alias_warns_on_stderr(mock_build, capsys, clean_root_environment):
    mock_build.return_value = _StubResult()
    main(["build", "main.tex", "--workspace-root", "/tmp/workspace"])
    err = capsys.readouterr().err
    assert "[deprecated-option] --workspace-root is deprecated" in err
    assert "use --root." in err
    assert mock_build.call_args[1]["workspace_root"] == Path("/tmp/workspace")


@patch("ktisma.adapters.bootstrap.build")
def test_new_names_do_not_warn(mock_build, capsys, clean_root_environment):
    mock_build.return_value = _StubResult()
    main(["build", "main.tex", "--root", "/tmp/workspace", "--format", "json"])
    assert "deprecated" not in capsys.readouterr().err


@pytest.mark.parametrize(
    ("command", "bootstrap_name", "stub"), _FORMAT_COMMANDS, ids=lambda v: str(v)
)
def test_format_json_output_equals_legacy_json_output(
    command, bootstrap_name, stub, capsys, clean_root_environment
):
    outputs = []
    errors = []
    for flags in (["--format", "json"], ["--json"]):
        with patch(f"ktisma.adapters.bootstrap.{bootstrap_name}") as mock_fn:
            mock_fn.return_value = stub()
            main([*command, *flags])
        captured = capsys.readouterr()
        outputs.append(captured.out)
        errors.append(captured.err)
    assert outputs[0] == outputs[1]
    json.loads(outputs[0])
    assert "deprecated" not in errors[0]
    assert "[deprecated-option] --json is deprecated" in errors[1]


@patch("ktisma.adapters.bootstrap.build")
def test_legacy_root_variable_warns_on_stderr(mock_build, capsys, monkeypatch):
    monkeypatch.delenv("KTISMA_ROOT", raising=False)
    monkeypatch.setenv("KTISMA_WORKSPACE_ROOT", "/tmp/workspace")
    mock_build.return_value = _StubResult()
    main(["build", "main.tex"])
    err = capsys.readouterr().err
    assert "[deprecated-variable] KTISMA_WORKSPACE_ROOT is deprecated" in err
    assert "set KTISMA_ROOT instead." in err


@patch("ktisma.adapters.bootstrap.build")
def test_new_root_variable_silences_the_legacy_warning(mock_build, capsys, monkeypatch):
    monkeypatch.setenv("KTISMA_ROOT", "/tmp/new")
    monkeypatch.setenv("KTISMA_WORKSPACE_ROOT", "/tmp/legacy")
    mock_build.return_value = _StubResult()
    main(["build", "main.tex"])
    assert "deprecated" not in capsys.readouterr().err
