from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from .config_loader import holds_root_config

ROOT_ENV_VAR = "KTISMA_ROOT"


def root_from_environment() -> Optional[str]:
    """Return the workspace root set in ``KTISMA_ROOT``, or ``None``; an empty value counts as unset."""
    return os.environ.get(ROOT_ENV_VAR) or None


def resolve_workspace_root(
    cli_workspace_root: Optional[Path] = None,
    source_dir: Optional[Path] = None,
) -> Path:
    """Resolve the workspace root, stopping at the first answer.

    Resolution order:
    1. ``--root`` (CLI option), relative to the current folder
    2. ``KTISMA_ROOT`` environment variable
    3. Outermost ancestor of the start folder that holds ``ktisma.toml`` or
       ``config/tools/ktisma.toml``; the start folder is ``source_dir`` when the command names a
       source, and the current folder otherwise
    4. Current working directory
    """
    # Step 1: CLI option
    if cli_workspace_root is not None:
        return cli_workspace_root.expanduser().resolve()

    # Step 2: Environment variable
    env_root = root_from_environment()
    if env_root:
        return Path(env_root).expanduser().resolve()

    # Step 3: Outermost ancestor holding a configuration file
    start = source_dir if source_dir is not None else Path.cwd()
    found = _find_config_ancestor(start.resolve())
    if found is not None:
        return found

    # Step 4: Current working directory
    return Path.cwd()


def _find_config_ancestor(start: Path) -> Optional[Path]:
    """Walk up from start and return the outermost folder that holds a configuration file.

    A folder holds a configuration file when it has ``ktisma.toml`` or ``config/tools/ktisma.toml``.
    The outermost folder wins because Ktisma stacks one configuration file per folder: the files
    below the root overlay the configuration of their own folder and never start a workspace of
    their own.
    """
    current = start
    root = Path(current.anchor)
    found: Optional[Path] = None
    while True:
        if holds_root_config(current):
            found = current
        if current == root:
            break
        parent = current.parent
        if parent == current:
            break
        current = parent
    return found


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
