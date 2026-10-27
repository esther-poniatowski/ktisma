"""Tests for canonical TeX dependency records and receipts."""

from __future__ import annotations

from dataclasses import dataclass

from ktisma.domain.tex_dependencies import (
    InstalledFile,
    InstalledTexDependency,
    TexReceipt,
    dependency_record_digest,
)


@dataclass(frozen=True)
class Dependency:
    name: str
    repository: str
    commit: str
    builder: str
    provides: tuple[str, ...]


def _dependency(name: str, provides: tuple[str, ...]) -> Dependency:
    return Dependency(
        name=name,
        repository=f"https://example.test/{name}.git",
        commit="a" * 40,
        builder="fixture",
        provides=provides,
    )


def test_record_digest_ignores_dependency_and_provides_order() -> None:
    first = _dependency("alpha", ("alpha.sty", "alpha-extra.sty"))
    reordered = _dependency("alpha", ("alpha-extra.sty", "alpha.sty"))
    second = _dependency("beta", ("beta.sty",))

    assert dependency_record_digest([first, second]) == dependency_record_digest(
        [second, reordered]
    )


def test_receipt_round_trip_preserves_manifest() -> None:
    receipt = TexReceipt(
        record_digest="b" * 64,
        dependencies=(
            InstalledTexDependency(
                name="alpha",
                repository="https://example.test/alpha.git",
                declared_commit="a" * 40,
                installed_commit="a" * 40,
                builder="fixture",
                provides=("alpha.sty",),
                files=(InstalledFile("tex/latex/alpha/alpha.sty", "c" * 64),),
            ),
        ),
    )

    assert TexReceipt.from_dict(receipt.to_dict()) == receipt
