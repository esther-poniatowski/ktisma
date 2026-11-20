from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from .config_loader import discover_configuration


def resolve_workspace_root(
    cli_workspace_root: Optional[Path] = None,
    source_dir: Optional[Path] = None,
) -> Path:
    """Resolve the workspace root through Hodegos, stopping at the first answer.

    Resolution order:
    1. ``--root`` (CLI option), relative to the current folder
    2. ``KTISMA_ROOT`` environment variable, when set and not empty
    3. Outermost folder, from the start folder upward, that holds ``ktisma.toml`` at one of the
       places of Hodegos; the search starts at ``source_dir`` when the command names a source,
       and at the current folder otherwise
    4. Current folder

    The start changes step 3 only: a relative ``--root`` and a relative ``KTISMA_ROOT`` resolve
    against the current folder.

    Raises:
        ConfigError: Two places of the root hold a configuration file.
    """
    option = cli_workspace_root.expanduser().absolute() if cli_workspace_root is not None else None
    start = source_dir.resolve() if source_dir is not None else None
    return discover_configuration(root=option, start=start).root.resolve()


class FileWorkspaceOps:
    """Filesystem implementation for build-dir creation and cleanup helpers."""

    def ensure_directory(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def path_exists(self, path: Path) -> bool:
        return path.exists()

    def is_directory(self, path: Path) -> bool:
        return path.is_dir()

    def list_directory(self, path: Path) -> list[Path]:
        return list(path.iterdir())

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def read_bytes(self, path: Path) -> bytes:
        return path.read_bytes()

    def write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def remove_tree(self, path: Path) -> None:
        shutil.rmtree(path)

    def glob_files(self, path: Path, pattern: str) -> list[Path]:
        return sorted(path.glob(pattern))
