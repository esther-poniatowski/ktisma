from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

ROOT_ENV_VAR = "KTISMA_ROOT"
# Former name of ROOT_ENV_VAR, read for one release when ROOT_ENV_VAR is unset.
LEGACY_ROOT_ENV_VAR = "KTISMA_WORKSPACE_ROOT"


def root_from_environment() -> Optional[str]:
    """Return the workspace root set in the environment, or ``None``.

    ``KTISMA_ROOT`` takes precedence. The former variable ``KTISMA_WORKSPACE_ROOT`` is
    read only when ``KTISMA_ROOT`` is unset or empty. An empty value counts as unset.
    """
    return os.environ.get(ROOT_ENV_VAR) or os.environ.get(LEGACY_ROOT_ENV_VAR) or None


def legacy_root_variable_in_use() -> bool:
    """Return whether the root is taken from the former variable ``KTISMA_WORKSPACE_ROOT``.

    Adapters call this to warn that the variable is deprecated in favor of ``KTISMA_ROOT``.
    """
    return not os.environ.get(ROOT_ENV_VAR) and bool(os.environ.get(LEGACY_ROOT_ENV_VAR))


def resolve_workspace_root(
    cli_workspace_root: Optional[Path] = None,
    adapter_workspace_root: Optional[Path] = None,
    source_dir: Optional[Path] = None,
) -> Path:
    """Resolve the workspace root per roadmap precedence.

    Resolution order:
    1. ``--root`` (CLI option)
    2. ``KTISMA_ROOT`` environment variable (then the deprecated ``KTISMA_WORKSPACE_ROOT``)
    3. Adapter-provided workspace root
    4. Outermost ancestor of ``source_dir`` containing ``.ktisma.toml``
    5. Current working directory
    """
    # Step 1: CLI option
    if cli_workspace_root is not None:
        return cli_workspace_root.expanduser().resolve()

    # Step 2: Environment variable
    env_root = root_from_environment()
    if env_root:
        return Path(env_root).expanduser().resolve()

    # Step 3: Adapter-provided
    if adapter_workspace_root is not None:
        return adapter_workspace_root.expanduser().resolve()

    # Step 4: Outermost ancestor with .ktisma.toml
    if source_dir is not None:
        found = _find_config_ancestor(source_dir.resolve())
        if found is not None:
            return found

    # Step 5: Current working directory
    return Path.cwd()


def _find_config_ancestor(start: Path) -> Optional[Path]:
    """Walk up from start and return the outermost directory containing .ktisma.toml."""
    current = start
    root = Path(current.anchor)
    found: Optional[Path] = None
    while True:
        if (current / ".ktisma.toml").is_file():
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
