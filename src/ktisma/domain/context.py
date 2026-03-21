from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class SourceContext:
    source_file: Path
    source_dir: Path
    workspace_root: Path


@dataclass(frozen=True)
class ToolkitInfo:
    toolkit_root: Path
    installation_mode: str  # "vendored" | "development" | "installed"


@dataclass(frozen=True)
class BuildRequest:
    watch: bool = False
    dry_run: bool = False
    engine_override: Optional[str] = None
    output_dir_override: Optional[Path] = None
    variant: Optional[str] = None
    variant_payload: Optional[str] = None
    json_output: bool = False
    cleanup_override: Optional[str] = None


@dataclass(frozen=True)
class SourceInputs:
    preamble: str
    magic_comments: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class VariantSpec:
    name: str
    payload: str

    VALID_NAME_PATTERN: str = r"^[a-zA-Z][a-zA-Z0-9_-]*$"
