from __future__ import annotations

import json


def generate_latex_workshop_config(
    ktisma_path: str = "%WORKSPACE_FOLDER%/vendor/ktisma/bin/ktisma",
) -> dict:
    """Generate LaTeX Workshop configuration for VS Code.

    Returns a dict suitable for merging into .vscode/settings.json.
    The integration calls ktisma directly rather than wrapping latexmk in bash -c.
    """
    return {
        "latex-workshop.latex.tools": [
            {
                "name": "ktisma",
                "command": "python3",
                "args": [
                    ktisma_path,
                    "build",
                    "%DOC%",
                    "--workspace-root",
                    "%WORKSPACE_FOLDER%",
                ],
            }
        ],
        "latex-workshop.latex.recipes": [
            {
                "name": "ktisma",
                "tools": ["ktisma"],
            }
        ],
        "latex-workshop.latex.autoClean.run": "never",
    }


def format_latex_workshop_snippet(
    ktisma_path: str = "%WORKSPACE_FOLDER%/vendor/ktisma/bin/ktisma",
) -> str:
    """Format the LaTeX Workshop configuration as a JSONC snippet."""
    config = generate_latex_workshop_config(ktisma_path)
    return json.dumps(config, indent=2)
