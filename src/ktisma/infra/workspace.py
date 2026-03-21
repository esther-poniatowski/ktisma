from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional


def resolve_workspace_root(
    cli_workspace_root: Optional[Path] = None,
    adapter_workspace_root: Optional[Path] = None,
    source_dir: Optional[Path] = None,
) -> Path:
    """Resolve the workspace root per roadmap precedence.

    Resolution order:
    1. --workspace-root (CLI flag)
    2. KTISMA_WORKSPACE_ROOT environment variable
    3. Adapter-provided workspace root
    4. Nearest ancestor of source_dir containing .ktisma.toml
    5. Current working directory
    """
    # Step 1: CLI flag
    if cli_workspace_root is not None:
        return cli_workspace_root.expanduser().resolve()

    # Step 2: Environment variable
    env_root = os.environ.get("KTISMA_WORKSPACE_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()

    # Step 3: Adapter-provided
    if adapter_workspace_root is not None:
        return adapter_workspace_root.expanduser().resolve()

    # Step 4: Nearest ancestor with .ktisma.toml
    if source_dir is not None:
        found = _find_config_ancestor(source_dir.resolve())
        if found is not None:
            return found

    # Step 5: Current working directory
    return Path.cwd()


def _find_config_ancestor(start: Path) -> Optional[Path]:
    """Walk up from start looking for a directory containing .ktisma.toml."""
    current = start
    root = Path(current.anchor)
    while True:
        if (current / ".ktisma.toml").is_file():
            return current
        if current == root:
            break
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


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

    def remove_tree(self, path: Path) -> None:
        shutil.rmtree(path)
