from __future__ import annotations

import json
from typing import Optional


def generate_latex_workshop_config(
    ktisma_path: str = "%WORKSPACE_FOLDER%/vendor/ktisma/bin/ktisma",
    *,
    use_wrapper_script: bool = False,
    extra_settings: Optional[dict[str, object]] = None,
) -> dict:
    """Generate LaTeX Workshop configuration for VS Code.

    Returns a dict suitable for merging into .vscode/settings.json.

    Parameters
    ----------
    ktisma_path:
        Path (or VS Code variable expression) to the ktisma executable.
    use_wrapper_script:
        If ``True``, the tool entry calls *ktisma_path* directly as the
        command (wrapper-script pattern used by ``ktisma init``).
        If ``False`` (default), it invokes ``python3`` with *ktisma_path*
        as the first argument.
    extra_settings:
        Additional VS Code settings to include in the returned dict
        (e.g. ``{"latex-workshop.view.pdf.viewer": "tab"}``).
    """
    if use_wrapper_script:
        tool_entry = {
            "name": "ktisma",
            "command": ktisma_path,
            "args": ["build", "%DOC_EXT%"],
        }
    else:
        tool_entry = {
            "name": "ktisma",
            "command": "python3",
            "args": [ktisma_path, "build", "%DOC_EXT%"],
        }

    config: dict[str, object] = {}
    if extra_settings:
        config.update(extra_settings)

    config.update({
        "latex-workshop.latex.tools": [tool_entry],
        "latex-workshop.latex.recipes": [
            {
                "name": "ktisma",
                "tools": ["ktisma"],
            }
        ],
        "latex-workshop.latex.autoClean.run": "never",
    })

    return config


def format_latex_workshop_snippet(
    ktisma_path: str = "%WORKSPACE_FOLDER%/vendor/ktisma/bin/ktisma",
    *,
    use_wrapper_script: bool = False,
    extra_settings: Optional[dict[str, object]] = None,
) -> str:
    """Format the LaTeX Workshop configuration as a JSONC snippet."""
    config = generate_latex_workshop_config(
        ktisma_path,
        use_wrapper_script=use_wrapper_script,
        extra_settings=extra_settings,
    )
    return json.dumps(config, indent=2)
