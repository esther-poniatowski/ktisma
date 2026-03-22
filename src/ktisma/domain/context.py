from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import ClassVar, Optional


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
    output_path_override: Optional[Path] = None
    output_dir_override: Optional[Path] = None
    variant: Optional[str] = None
    variant_payload: Optional[str] = None
    include_default: bool = False
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
    engine_override: Optional[str] = None
    output_override: Optional[str] = None
    filename_suffix: Optional[str] = None

    VALID_NAME_PATTERN: ClassVar[str] = r"^[a-zA-Z][a-zA-Z0-9_-]*$"


def is_valid_variant_name(name: str) -> bool:
    """Return whether a variant name is safe for filenames and CLI use."""
    return bool(re.fullmatch(VariantSpec.VALID_NAME_PATTERN, name))
