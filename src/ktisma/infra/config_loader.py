from __future__ import annotations

import tomllib
from pathlib import Path

from ..domain.config import ConfigLayer


CONFIG_FILENAME = ".ktisma.toml"


class TomlConfigLoader:
    """Concrete ConfigLoader: loads .ktisma.toml files from disk."""

    def load_layers(
        self, workspace_root: Path, source_dir: Path
    ) -> list[ConfigLayer]:
        """Load config layers from workspace root toward the source directory.

        Returns layers ordered from lowest to highest precedence:
        1. Workspace .ktisma.toml (lowest)
        2. Intermediate overlay .ktisma.toml files
        3. Source-dir .ktisma.toml (highest file-based precedence)
        """
        layers: list[ConfigLayer] = []
        seen: set[Path] = set()

        workspace_root = workspace_root.resolve()
        source_dir = source_dir.resolve()

        # Collect config file paths from workspace root to source directory
        config_paths: list[Path] = []

        # Workspace root config
        ws_config = workspace_root / CONFIG_FILENAME
        if ws_config.is_file():
            config_paths.append(ws_config)
            seen.add(ws_config.resolve())

        # Walk from workspace root to source directory, collecting overlays
        try:
            rel = source_dir.relative_to(workspace_root)
        except ValueError:
            rel = None

        if rel is not None:
            current = workspace_root
            for part in rel.parts:
                current = current / part
                candidate = current / CONFIG_FILENAME
                resolved = candidate.resolve()
                if candidate.is_file() and resolved not in seen:
                    config_paths.append(candidate)
                    seen.add(resolved)

        # Load each config file
        for config_path in config_paths:
            data = _load_toml(config_path)
            if data is not None:
                layers.append(
                    ConfigLayer(
                        data=data,
                        source=config_path.parent,
                        label=str(config_path),
                    )
                )

        return layers


def _load_toml(path: Path) -> dict | None:
    """Load a TOML file, returning None on failure."""
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return None
