from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    COMPILATION_FAILURE = 1
    CONFIG_ERROR = 2
    PREREQUISITE_FAILURE = 3
    LOCK_CONTENTION = 4
    INTERNAL_ERROR = 5
