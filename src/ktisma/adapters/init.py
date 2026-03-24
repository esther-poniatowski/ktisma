from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

from ..domain.diagnostics import Diagnostic, DiagnosticLevel
from ..domain.exit_codes import ExitCode
from .log import format_diagnostics
from .vscode import generate_latex_workshop_config

_WRAPPER_SCRIPT = """\
#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 &>/dev/null; then
  echo "python3 is required but not found on PATH" >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
ktisma="$repo_root/vendor/ktisma/bin/ktisma"

if [[ ! -f "$ktisma" ]]; then
  echo "ktisma is not available at $ktisma" >&2
  echo "Initialize the submodule with:" >&2
  echo "  git submodule update --init --recursive vendor/ktisma" >&2
  exit 1
fi

export KTISMA_WORKSPACE_ROOT="$repo_root"
exec python3 "$ktisma" "$@"
"""


_INIT_VSCODE_EXTRA_SETTINGS: dict[str, object] = {
    "latex-workshop.view.pdf.viewer": "tab",
    "latex-workshop.latex.autoBuild.run": "onSave",
}


def execute_init(workspace_root: Path) -> int:
    """Initialize ktisma integration files in the workspace.

    Creates a wrapper script at ``scripts/ktisma`` and prints the VS Code
    LaTeX Workshop configuration snippet to stdout.
    """
    diagnostics: list[Diagnostic] = []
    wrapper_path = workspace_root / "scripts" / "ktisma"

    # --- Wrapper script ---
    if wrapper_path.exists():
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.INFO,
                component="init",
                code="wrapper-exists",
                message=f"Wrapper script already exists at {wrapper_path.relative_to(workspace_root)}, skipping.",
            )
        )
    else:
        wrapper_path.parent.mkdir(parents=True, exist_ok=True)
        wrapper_path.write_text(_WRAPPER_SCRIPT)
        wrapper_path.chmod(wrapper_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        diagnostics.append(
            Diagnostic(
                level=DiagnosticLevel.INFO,
                component="init",
                code="wrapper-created",
                message=f"Created {wrapper_path.relative_to(workspace_root)}",
            )
        )

    # --- Diagnostics ---
    output = format_diagnostics(diagnostics, use_color=sys.stderr.isatty())
    if output:
        print(output, file=sys.stderr)

    # --- VS Code config snippet ---
    config = generate_latex_workshop_config(
        ktisma_path="%WORKSPACE_FOLDER%/scripts/ktisma",
        use_wrapper_script=True,
        extra_settings=_INIT_VSCODE_EXTRA_SETTINGS,
    )
    print("Add the following to your .code-workspace or .vscode/settings.json:\n")
    print(json.dumps(config, indent=2))

    return ExitCode.SUCCESS
