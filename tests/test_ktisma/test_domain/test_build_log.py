"""Tests for pure LaTeX build-log classification."""

from __future__ import annotations

from ktisma.domain.build_log import evaluate_build_log


def test_clean_log_passes_and_keeps_last_output_record() -> None:
    result = evaluate_build_log(
        "Output written on first.pdf (1 page).\nOutput written on final.pdf (2 pages).\n"
    )

    assert result.passed
    assert result.output_line == "Output written on final.pdf (2 pages)."
    assert all(finding.count == 0 for finding in result.findings)


def test_each_zero_baseline_finding_is_counted_by_line() -> None:
    text = "\n".join(
        [
            "Fatal error occurred",
            "LaTeX Font Warning: Font shape substituted",
            r"Overfull \hbox (1.0pt too wide)",
            r"Overfull \vbox (2.0pt too high)",
            r"Underfull \hbox (badness 10000)",
            r"Underfull \vbox (badness 10000)",
            "! Undefined control sequence.",
            "./parts/body.tex:12: Undefined control sequence.",
            "poster.sty:7: Package error.",
            "Output written on poster.pdf (1 page).",
        ]
    )

    result = evaluate_build_log(text)

    assert not result.passed
    assert {finding.name: finding.count for finding in result.findings} == {
        "fatal error": 1,
        "font substitution": 1,
        "overfull hbox": 1,
        "overfull vbox": 1,
        "underfull hbox": 1,
        "underfull vbox": 1,
        "error": 3,
    }


def test_missing_output_record_fails_an_otherwise_clean_log() -> None:
    result = evaluate_build_log("This is LuaHBTeX.\nNo pages of output.\n")

    assert not result.passed
    assert result.output_line is None


def test_requested_channels_are_reported_in_request_order() -> None:
    text = "\n".join(
        [
            "[layout] width=100",
            "[fit] overflow=0",
            "[layout] height=80",
            "[ignored] value=1",
            "Output written on poster.pdf (1 page).",
        ]
    )

    result = evaluate_build_log(text, channels=("fit", "layout"))

    assert result.channel_lines == (
        "[fit] overflow=0",
        "[layout] width=100",
        "[layout] height=80",
    )
