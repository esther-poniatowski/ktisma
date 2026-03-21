from __future__ import annotations

from pathlib import Path
from typing import Optional

from .diagnostics import Diagnostic
from .exit_codes import ExitCode


class KtismaError(Exception):
    """Base exception for ktisma failures that map to a public exit code."""

    def __init__(
        self,
        exit_code: ExitCode,
        message: str,
        diagnostics: Optional[list[Diagnostic]] = None,
    ) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.diagnostics = diagnostics or []


class ConfigError(KtismaError):
    def __init__(self, message: str, diagnostics: Optional[list[Diagnostic]] = None) -> None:
        super().__init__(ExitCode.CONFIG_ERROR, message, diagnostics)


class ConfigLoadError(ConfigError):
    def __init__(self, path: Path, message: str) -> None:
        super().__init__(f"Failed to load configuration from {path}: {message}")
        self.path = path


class PrerequisiteError(KtismaError):
    def __init__(self, message: str, diagnostics: Optional[list[Diagnostic]] = None) -> None:
        super().__init__(ExitCode.PREREQUISITE_FAILURE, message, diagnostics)


class LockContention(KtismaError):
    def __init__(self, message: str, diagnostics: Optional[list[Diagnostic]] = None) -> None:
        super().__init__(ExitCode.LOCK_CONTENTION, message, diagnostics)
