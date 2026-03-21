from __future__ import annotations

import sys

from ..domain.exit_codes import ExitCode


def execute_init(*args, **kwargs) -> int:
    """Placeholder for the init command.

    Deferred per roadmap: only after workspace-edit behavior is proven safe.
    """
    from ..domain.diagnostics import Diagnostic, DiagnosticLevel
    from .log import format_diagnostics

    diag = Diagnostic(
        level=DiagnosticLevel.ERROR,
        component="init",
        code="init-deferred",
        message="'init' is deferred until workspace-editing behavior is proven stable.",
    )
    output = format_diagnostics([diag], use_color=sys.stderr.isatty())
    if output:
        print(output, file=sys.stderr)
    return ExitCode.CONFIG_ERROR
