"""Integration tests for build-log discovery and orchestration."""

from __future__ import annotations

from pathlib import Path

from ktisma.app.check_log import execute_check_log
from ktisma.domain.exit_codes import ExitCode
from ktisma.infra.workspace import FileWorkspaceOps


def _write_log(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_logs_are_found_recursively_and_sorted(tmp_path: Path) -> None:
    source_dir = tmp_path / "tex"
    _write_log(
        source_dir / ".ktisma_build" / "zeta" / "poster.log",
        "Output written on zeta.pdf (1 page).\n",
    )
    _write_log(
        source_dir / ".ktisma_build" / "alpha" / "poster.log",
        "Output written on alpha.pdf (1 page).\n",
    )

    result = execute_check_log(
        source_dir=source_dir,
        build_dir_name=".ktisma_build",
        stem="poster",
        channels=(),
        workspace_ops=FileWorkspaceOps(),
    )

    assert result.exit_code == ExitCode.SUCCESS
    assert [report.relative_path.as_posix() for report in result.reports] == [
        "alpha/poster.log",
        "zeta/poster.log",
    ]


def test_planted_warning_fails_and_channel_is_retained(tmp_path: Path) -> None:
    source_dir = tmp_path / "tex"
    _write_log(
        source_dir / "work" / "poster.log",
        "\n".join(
            [
                r"Overfull \hbox (1.0pt too wide)",
                "[layout] width=100",
                "Output written on poster.pdf (1 page).",
            ]
        ),
    )

    result = execute_check_log(
        source_dir=source_dir,
        build_dir_name="work",
        stem=None,
        channels=("layout",),
        workspace_ops=FileWorkspaceOps(),
    )

    assert result.exit_code == ExitCode.COMPILATION_FAILURE
    assert result.reports[0].evaluation.channel_lines == ("[layout] width=100",)


def test_missing_source_directory_is_a_contract_error(tmp_path: Path) -> None:
    result = execute_check_log(
        source_dir=tmp_path / "missing",
        build_dir_name=".ktisma_build",
        stem=None,
        channels=(),
        workspace_ops=FileWorkspaceOps(),
    )

    assert result.exit_code == ExitCode.CONFIG_ERROR
    assert result.diagnostics[0].code == "missing-source-dir"


def test_missing_build_directory_is_a_compilation_failure(tmp_path: Path) -> None:
    source_dir = tmp_path / "tex"
    source_dir.mkdir()

    result = execute_check_log(
        source_dir=source_dir,
        build_dir_name=".ktisma_build",
        stem=None,
        channels=(),
        workspace_ops=FileWorkspaceOps(),
    )

    assert result.exit_code == ExitCode.COMPILATION_FAILURE
    assert result.diagnostics[0].code == "missing-build-dir"


def test_missing_selected_log_is_a_compilation_failure(tmp_path: Path) -> None:
    source_dir = tmp_path / "tex"
    (source_dir / ".ktisma_build").mkdir(parents=True)

    result = execute_check_log(
        source_dir=source_dir,
        build_dir_name=".ktisma_build",
        stem="poster",
        channels=(),
        workspace_ops=FileWorkspaceOps(),
    )

    assert result.exit_code == ExitCode.COMPILATION_FAILURE
    assert result.diagnostics[0].code == "missing-log"
