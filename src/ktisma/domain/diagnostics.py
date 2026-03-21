from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DiagnosticLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class Diagnostic:
    level: DiagnosticLevel
    component: str
    code: str
    message: str
    evidence: Optional[list[str]] = field(default=None)

    def to_dict(self) -> dict:
        result: dict = {
            "level": self.level.value,
            "component": self.component,
            "code": self.code,
            "message": self.message,
        }
        if self.evidence is not None:
            result["evidence"] = self.evidence
        return result
