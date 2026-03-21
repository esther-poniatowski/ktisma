from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol

from ..domain.config import ConfigLayer
from ..domain.context import SourceContext, SourceInputs, VariantSpec
from ..domain.diagnostics import Diagnostic


class ConfigLoader(Protocol):
    def load_layers(
        self, workspace_root: Path, source_dir: Path
    ) -> list[ConfigLayer]:
        """Load config layers from workspace root to source directory.

        Returns layers ordered from lowest to highest precedence
        (workspace config first, nearest overlays last).
        """
        ...


class SourceReader(Protocol):
    def read_source(self, source_file: Path) -> SourceInputs:
        """Read a source file and extract preamble text and magic comments."""
        ...


class LockManager(Protocol):
    def acquire(
        self,
        lock_file: Path,
        source_path: Path,
        mode: str,
    ) -> None:
        """Acquire an exclusive build lock.

        Raises LockContention if the lock cannot be acquired.
        """
        ...

    def release(self, lock_file: Path) -> None:
        """Release a previously acquired build lock."""
        ...


@dataclass(frozen=True)
class BackendResult:
    success: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    pdf_path: Optional[Path] = None
    diagnostics: list[Diagnostic] = field(default_factory=list)


@dataclass(frozen=True)
class WatchUpdate:
    result: BackendResult
    finished: bool = False


class WatchSession(Protocol):
    def poll(self, timeout_seconds: float = 0.5) -> Optional[WatchUpdate]:
        """Wait briefly for a rebuild update or final process completion."""
        ...

    def terminate(self) -> BackendResult:
        """Terminate the active watch process and return its final status."""
        ...


class BackendRunner(Protocol):
    def compile(
        self,
        source_file: Path,
        build_dir: Path,
        engine: str,
        synctex: bool,
        extra_args: Optional[list[str]] = None,
    ) -> BackendResult:
        """Run the compilation backend and return structured results."""
        ...

    def start_watch(
        self,
        source_file: Path,
        build_dir: Path,
        engine: str,
        synctex: bool,
        extra_args: Optional[list[str]] = None,
    ) -> WatchSession:
        """Launch the backend in continuous watch mode."""
        ...


class Materializer(Protocol):
    def materialize(self, source: Path, destination: Path) -> None:
        """Copy or move a build artifact to its final destination.

        Creates parent directories as needed.
        """
        ...


class WorkspaceOps(Protocol):
    def ensure_directory(self, path: Path) -> None:
        """Create a directory and any missing parents."""
        ...

    def path_exists(self, path: Path) -> bool:
        """Return whether a path exists."""
        ...

    def is_directory(self, path: Path) -> bool:
        """Return whether a path is a directory."""
        ...

    def list_directory(self, path: Path) -> list[Path]:
        """List a directory's entries."""
        ...

    def remove_tree(self, path: Path) -> None:
        """Recursively remove a directory tree."""
        ...


@dataclass(frozen=True)
class PrerequisiteCheck:
    name: str
    available: bool
    version: Optional[str] = None
    message: str = ""


class PrerequisiteProbe(Protocol):
    def check_latexmk(self) -> PrerequisiteCheck:
        """Check if latexmk is available on PATH."""
        ...

    def check_engine(self, engine: str) -> PrerequisiteCheck:
        """Check if a specific LaTeX engine is available."""
        ...

    def check_python_version(self) -> PrerequisiteCheck:
        """Check if the Python version meets minimum requirements."""
        ...

    def check_toml_support(self) -> PrerequisiteCheck:
        """Check if TOML parsing is available."""
        ...


class PostProcessor(Protocol):
    def process(
        self,
        materialized_pdf: Path,
        ctx: SourceContext,
        variant: Optional[VariantSpec] = None,
    ) -> list[Diagnostic]:
        """Run post-materialization steps before cleanup."""
        ...
