"""Pure models and canonical digests for managed TeX dependencies."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Protocol

# Identifier of the format of the receipt of a TeX snapshot; ktisma regenerates any other.
TEX_RECEIPT_SCHEMA = "ktisma:tex-dependencies@1"


class TexDependencyRecord(Protocol):
    """Structural type required by the canonical record functions."""

    @property
    def name(self) -> str: ...

    @property
    def repository(self) -> str: ...

    @property
    def commit(self) -> str: ...

    @property
    def builder(self) -> str: ...

    @property
    def provides(self) -> tuple[str, ...]: ...


@dataclass(frozen=True, order=True)
class InstalledFile:
    """Digest of one path installed into a managed TeX tree."""

    path: str
    sha256: str

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InstalledFile":
        return cls(path=str(data["path"]), sha256=str(data["sha256"]))


@dataclass(frozen=True)
class InstalledTexDependency:
    """Receipt entry for one fetched and installed package."""

    name: str
    repository: str
    declared_commit: str
    installed_commit: str
    builder: str
    provides: tuple[str, ...]
    files: tuple[InstalledFile, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "repository": self.repository,
            "declared_commit": self.declared_commit,
            "installed_commit": self.installed_commit,
            "builder": self.builder,
            "provides": list(self.provides),
            "files": [file.to_dict() for file in self.files],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InstalledTexDependency":
        return cls(
            name=str(data["name"]),
            repository=str(data["repository"]),
            declared_commit=str(data["declared_commit"]),
            installed_commit=str(data["installed_commit"]),
            builder=str(data["builder"]),
            provides=tuple(str(item) for item in data["provides"]),
            files=tuple(InstalledFile.from_dict(item) for item in data["files"]),
        )


class StaleTexReceiptError(ValueError):
    """Raised for a receipt in another format: ktisma regenerates the snapshot that holds it."""


def _require_receipt_schema(data: dict[str, Any]) -> None:
    """Reject a receipt whose ``_schema`` key differs from the format that ktisma writes."""
    declared = data.get("_schema")
    if declared == TEX_RECEIPT_SCHEMA:
        return
    if "schema_version" in data:
        reason = "still carries the retired key 'schema_version'"
    elif "_schema" not in data:
        reason = "does not declare '_schema'"
    else:
        reason = f"declares _schema = {declared!r}"
    raise StaleTexReceiptError(f"The receipt {reason}; expected _schema = {TEX_RECEIPT_SCHEMA}")


@dataclass(frozen=True)
class TexReceipt:
    """Complete description of one immutable dependency snapshot."""

    record_digest: str
    dependencies: tuple[InstalledTexDependency, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "_schema": TEX_RECEIPT_SCHEMA,
            "record_digest": self.record_digest,
            "dependencies": [dependency.to_dict() for dependency in self.dependencies],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TexReceipt":
        _require_receipt_schema(data)
        return cls(
            record_digest=str(data["record_digest"]),
            dependencies=tuple(
                InstalledTexDependency.from_dict(item) for item in data["dependencies"]
            ),
        )


def dependency_record_digest(dependencies: Iterable[TexDependencyRecord]) -> str:
    """Return the order-independent SHA-256 digest of a dependency closure."""
    canonical = [
        {
            "name": dependency.name,
            "repository": dependency.repository,
            "commit": dependency.commit.lower(),
            "builder": dependency.builder,
            "provides": sorted(dependency.provides),
        }
        for dependency in sorted(dependencies, key=lambda item: item.name)
    ]
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_bytes(content: bytes) -> str:
    """Return the hexadecimal SHA-256 digest of byte content."""
    return hashlib.sha256(content).hexdigest()
