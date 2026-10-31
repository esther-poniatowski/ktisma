"""Tests for pure LaTeX build-log classification."""

from __future__ import annotations

from pathlib import Path

import pytest

from ktisma.domain.build_log import decode_build_log, evaluate_build_log

# A real pdfTeX log, regenerated from the ``.tex`` file of the same stem: the channel line splits
# ``é`` (C3 A9) across a wrapped line, and the overfull box displays T1 glyphs as raw bytes (E9).
_PDFTEX_SPLIT_LOG = Path(__file__).resolve().parents[2] / "fixtures" / "pdftex_split_utf8.log"


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


def test_valid_utf8_decodes_unchanged() -> None:
    assert decode_build_log("Output written on café.pdf (1 page).\n".encode()) == (
        "Output written on café.pdf (1 page).\n"
    )


def test_character_split_by_line_wrapping_keeps_both_lines() -> None:
    data = b"[layout] caf\xc3\n\xa9 width=100\nOutput written on poster.pdf (1 page).\n"

    result = evaluate_build_log(decode_build_log(data), channels=("layout",))

    assert result.passed
    assert result.channel_lines == ("[layout] caf\ufffd",)


def test_isolated_invalid_byte_is_replaced_and_neighbours_kept() -> None:
    assert decode_build_log(b"\\T1/cmr/m/n/10 \xe9t\xe9 caf\xc3\xa9") == (
        "\\T1/cmr/m/n/10 \ufffdt\ufffd café"
    )


@pytest.mark.parametrize(
    ("name", "line"),
    [
        ("fatal error", b"\xa9Fatal error\xc3 occurred"),
        ("font substitution", b"\xe9LaTeX Font Warning\xe2\x80: Font shape substituted"),
        ("overfull hbox", b"\xc3Overfull \\hbox\xe9 (1.0pt too wide)"),
        ("overfull vbox", b"\xc3Overfull \\vbox\xe9 (2.0pt too high)"),
        ("underfull hbox", b"\xc3Underfull \\hbox\xe9 (badness 10000)"),
        ("underfull vbox", b"\xc3Underfull \\vbox\xe9 (badness 10000)"),
        ("error", b"! \xc3Undefined control sequence."),
        ("error", b"./caf\xc3.tex:12: Undefined control sequence."),
        ("error", b"poster.sty:7: \xe9"),
    ],
)
def test_pattern_adjacent_to_invalid_bytes_is_counted(name: str, line: bytes) -> None:
    data = b"split caf\xc3\n" + line + b"\xa9\nOutput written on poster.pdf (1 page).\n"

    result = evaluate_build_log(decode_build_log(data))

    counts = {finding.name: finding.count for finding in result.findings}
    assert counts[name] == 1
    assert sum(counts.values()) == 1


def test_output_record_truncated_by_invalid_byte_is_reported() -> None:
    result = evaluate_build_log(decode_build_log(b"Output written on caf\xc3\n\xa9.pdf\n"))

    assert result.output_line == "Output written on caf\ufffd"


def test_real_pdftex_log_with_split_character_is_classified() -> None:
    data = _PDFTEX_SPLIT_LOG.read_bytes()
    with pytest.raises(UnicodeDecodeError):
        data.decode("utf-8")

    result = evaluate_build_log(decode_build_log(data), channels=("layout",))

    assert {finding.name: finding.count for finding in result.findings} == {
        "fatal error": 0,
        "font substitution": 0,
        "overfull hbox": 1,
        "overfull vbox": 0,
        "underfull hbox": 0,
        "underfull vbox": 0,
        "error": 0,
    }
    assert result.output_line == "Output written on pdftex_split_utf8.pdf (1 page, 11873 bytes)."
    assert result.channel_lines == ("[layout] " + "x" * 69 + "\ufffd",)
