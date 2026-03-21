from __future__ import annotations

from ..domain.diagnostics import Diagnostic, DiagnosticLevel
from ..domain.exit_codes import ExitCode


def execute_init(*args, **kwargs) -> int:
    """Placeholder for the init command.

    Deferred per roadmap: only after workspace-edit behavior is proven safe.
    """
    print(
        "error: 'init' is deferred until workspace-editing behavior is proven stable.",
        end="\n",
    )
    return ExitCode.CONFIG_ERROR
