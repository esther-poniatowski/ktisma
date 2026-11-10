from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..domain.config import ConfigLayer
from ..domain.diagnostics import Diagnostic, DiagnosticLevel
from ..domain.errors import ConfigError, ConfigLoadError

try:
    import tomllib as toml_module
except ImportError:  # pragma: no cover - exercised on Python < 3.11
    import tomli as toml_module


# Name of every settings file of Ktisma: the file of the workspace root and each overlay below it.
CONFIG_FILENAME = "ktisma.toml"
# Folder, below the workspace root, that may hold the settings file of the root instead of the root.
CONFIG_SUBDIR = Path("config") / "tools"


def root_config_candidates(folder: Path) -> tuple[Path, Path]:
    """Return the two places of the settings file of a workspace root held by ``folder``.

    The file sits either in ``config/tools/ktisma.toml`` below the folder or in ``ktisma.toml`` at
    its level. An overlay below the root has only the second place.
    """
    return (folder / CONFIG_SUBDIR / CONFIG_FILENAME, folder / CONFIG_FILENAME)


def holds_root_config(folder: Path) -> bool:
    """Return whether ``folder`` holds a settings file in one of the two places of a root."""
    return any(candidate.is_file() for candidate in root_config_candidates(folder))


def find_root_config(workspace_root: Path) -> Optional[Path]:
    """Return the settings file of the workspace root, or ``None`` when the root has none.

    Raises:
        ConfigError: Both places hold a settings file; the error names both files.
    """
    present = [candidate for candidate in root_config_candidates(workspace_root) if candidate.is_file()]
    if len(present) > 1:
        raise ConfigError(
            "Two settings files compete for the workspace root.",
            diagnostics=[
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="config",
                    code="competing-config-files",
                    message=(
                        f"Both {present[0]} and {present[1]} exist; keep one of them as the "
                        "settings file of the workspace root."
                    ),
                )
            ],
        )
    return present[0] if present else None


class TomlConfigLoader:
    """Concrete ConfigLoader: loads the ``ktisma.toml`` files from disk."""

    def load_layers(
        self, workspace_root: Path, source_dir: Path
    ) -> list[ConfigLayer]:
        """Load config layers from workspace root toward the source directory.

        Returns layers ordered from lowest to highest precedence:
        1. The settings file of the workspace root, in ``config/tools/ktisma.toml`` or
           ``ktisma.toml`` (lowest)
        2. The overlay ``ktisma.toml`` of each intermediate folder
        3. The overlay ``ktisma.toml`` of the source directory (highest file-based precedence)

        Every layer anchors its relative paths at the workspace root, whatever folder holds it.
        """
        layers: list[ConfigLayer] = []
        seen: set[Path] = set()

        workspace_root = workspace_root.resolve()
        source_dir = source_dir.resolve()

        root_config = find_root_config(workspace_root)
        if root_config is not None:
            seen.add(root_config.resolve())
            layers.append(_load_layer(root_config, workspace_root, is_workspace_root=True))

        # Walk from the workspace root to the source directory, collecting overlays
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
                    seen.add(resolved)
                    layers.append(_load_layer(candidate, workspace_root, is_workspace_root=False))

        return layers


def _load_layer(path: Path, workspace_root: Path, *, is_workspace_root: bool) -> ConfigLayer:
    return ConfigLayer(
        data=_load_toml(path),
        source=path,
        base_dir=workspace_root,
        label=str(path),
        is_workspace_root=is_workspace_root,
    )


def _load_toml(path: Path) -> dict:
    """Load a TOML file or raise a config-specific error."""
    try:
        with open(path, "rb") as f:
            return toml_module.load(f)
    except Exception as exc:
        raise ConfigLoadError(path, str(exc)) from exc


def normalize_route_paths(data: dict) -> None:
    """Expand ``~`` and resolve symlinks on route target paths.

    This function lives in the infrastructure layer because it performs
    filesystem I/O (``expanduser``, ``resolve``).  The application layer
    calls it on the merged config dict after the domain merge completes.
    """
    routes = data.get("routes")
    if not isinstance(routes, dict):
        return
    normalized: dict[str, str] = {}
    for pattern, target in routes.items():
        if isinstance(target, str):
            keep_trailing = target.endswith("/")
            resolved = Path(target).expanduser().resolve(strict=False)
            result = str(resolved)
            if keep_trailing and not result.endswith("/"):
                result += "/"
            normalized[pattern] = result
        else:
            normalized[pattern] = target
    data["routes"] = normalized
