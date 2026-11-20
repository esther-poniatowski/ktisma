"""
Configuration files of Ktisma, `ktisma.toml`, located through Hodegos and loaded as layers.

Hodegos resolves the root of a command and the places of `ktisma.toml`, as its specification states
(https://github.com/esther-poniatowski/hodegos/blob/main/docs/specification.md). The places of a
folder are `ktisma.toml` in the folder, the same file in its subfolder `.config/`, and the same
file in its subfolder `config/`. Two places of one folder holding a file is an error. A file kept
in another folder is named by the option `--config`. Ktisma stacks one file per folder: the file
of the root configures the whole workspace, and the file of each folder below it overlays the
configuration of that folder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from hodegos import Discovery, DiscoveryError, Tool, discover

from ..domain.config import ConfigLayer
from ..domain.diagnostics import Diagnostic, DiagnosticLevel
from ..domain.errors import ConfigError, ConfigLoadError

try:
    import tomllib as toml_module
except ImportError:  # pragma: no cover - exercised on Python < 3.11
    import tomli as toml_module


TOOL = Tool("ktisma", ("toml",), stacked=True)
"""Convention of Ktisma for Hodegos: the file `ktisma.toml`, the variable `KTISMA_ROOT`, and one
file stacked per folder, so that the search of the root takes the outermost folder holding one."""

CONFIG_FILENAME = TOOL.file_names[0]
"""Name of every configuration file of Ktisma: the file of the workspace root and each overlay."""


def discover_configuration(
    root: Optional[Path] = None,
    config: Optional[Path] = None,
    start: Optional[Path] = None,
) -> Discovery:
    """Return the root of a command and the configuration file of that root, located by Hodegos.

    Args:
        root: Value of ``--root``, absolute or relative to the current folder; ``None`` to take
            the root from ``KTISMA_ROOT`` or from the search.
        config: Value of ``--config``, absolute or relative to the current folder; ``None`` to
            take the single place of the root holding ``ktisma.toml``.
        start: Folder where the search of the root starts, such as the folder of a source; the
            current folder by default. The start changes the search only: ``root``, ``config``
            and a relative ``KTISMA_ROOT`` resolve against the current folder, which also stays
            the root when the search finds no configuration.

    Returns:
        The root and the configuration of the root, ``None`` when no place holds one: Ktisma then
        runs on its built-in defaults.

    Raises:
        ConfigError: Hodegos rejects the request: the named file does not exist, or two places of
            the root hold a file. The diagnostic carries the code of Hodegos.
    """
    try:
        return discover(TOOL, root=root, config=config, start=start)
    except DiscoveryError as error:
        raise ConfigError(
            f"The configuration of Ktisma cannot be located: {error}",
            diagnostics=[
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="config",
                    code=error.code.value,
                    message=str(error),
                )
            ],
        ) from error


def _folder_configuration(folder: Path, config: Optional[Path] = None) -> Optional[Path]:
    """Return the configuration file of ``folder``: ``config`` when named, else its single place."""
    location = discover_configuration(root=folder, config=config).configuration
    return location.path if location is not None else None


class TomlConfigLoader:
    """Concrete ConfigLoader: loads the ``ktisma.toml`` files from disk.

    Args:
        config: Configuration file of the workspace root named by ``--config``, relative to the
            current folder; ``None`` to read the single place of the root holding ``ktisma.toml``.
    """

    def __init__(self, config: Optional[Path] = None) -> None:
        self._config = config

    def load_layers(self, workspace_root: Path, source_dir: Path) -> list[ConfigLayer]:
        """Load config layers from workspace root toward the source directory.

        Returns layers ordered from lowest to highest precedence:
        1. The configuration file of the workspace root, named by ``--config`` or found at one of
           the places of the root (lowest)
        2. The overlay of each intermediate folder, found at one of the places of that folder
        3. The overlay of the source directory (highest file-based precedence)

        Every layer anchors its relative paths at the workspace root, whatever folder holds it.
        """
        layers: list[ConfigLayer] = []
        seen: set[Path] = set()

        workspace_root = workspace_root.resolve()
        source_dir = source_dir.resolve()

        root_config = _folder_configuration(workspace_root, self._config)
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
                candidate = _folder_configuration(current)
                if candidate is not None and candidate.resolve() not in seen:
                    seen.add(candidate.resolve())
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
