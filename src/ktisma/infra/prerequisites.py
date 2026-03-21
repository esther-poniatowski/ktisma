from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Optional

from ..app.protocols import PrerequisiteCheck

MIN_PYTHON_VERSION = (3, 9)


class SystemPrerequisiteProbe:
    """Concrete PrerequisiteProbe: checks system prerequisites."""

    def check_latexmk(self) -> PrerequisiteCheck:
        """Check if latexmk is available on PATH."""
        path = shutil.which("latexmk")
        if path is None:
            return PrerequisiteCheck(
                name="latexmk",
                available=False,
                message="latexmk is not installed or not on PATH.",
            )

        version = _get_command_version(["latexmk", "--version"])
        return PrerequisiteCheck(
            name="latexmk",
            available=True,
            version=version,
            message=f"latexmk found at {path}" + (f" ({version})" if version else ""),
        )

    def check_engine(self, engine: str) -> PrerequisiteCheck:
        """Check if a specific LaTeX engine is available."""
        cmd = engine
        path = shutil.which(cmd)
        if path is None:
            return PrerequisiteCheck(
                name=engine,
                available=False,
                message=f"Engine '{engine}' is not installed or not on PATH.",
            )

        version = _get_command_version([cmd, "--version"])
        return PrerequisiteCheck(
            name=engine,
            available=True,
            version=version,
            message=f"{engine} found at {path}" + (f" ({version})" if version else ""),
        )

    def check_python_version(self) -> PrerequisiteCheck:
        """Check if the Python version meets minimum requirements."""
        current = sys.version_info[:2]
        version_str = f"{current[0]}.{current[1]}"
        min_str = f"{MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}"

        if current >= MIN_PYTHON_VERSION:
            return PrerequisiteCheck(
                name="python",
                available=True,
                version=version_str,
                message=f"Python {version_str} meets minimum requirement ({min_str}+).",
            )

        return PrerequisiteCheck(
            name="python",
            available=False,
            version=version_str,
            message=f"Python {version_str} does not meet minimum requirement ({min_str}+).",
        )

    def check_toml_support(self) -> PrerequisiteCheck:
        """Check if TOML parsing is available."""
        try:
            if sys.version_info >= (3, 11):
                import tomllib  # noqa: F401

                return PrerequisiteCheck(
                    name="toml",
                    available=True,
                    version="tomllib (stdlib)",
                    message="TOML parsing available via tomllib.",
                )

            import tomli  # noqa: F401

            return PrerequisiteCheck(
                name="toml",
                available=True,
                version="tomli",
                message="TOML parsing available via tomli.",
            )
        except ImportError:
            missing = "tomllib" if sys.version_info >= (3, 11) else "tomli"
            return PrerequisiteCheck(
                name="toml",
                available=False,
                message=f"TOML parsing support is unavailable: missing {missing}.",
            )


def _get_command_version(args: list[str]) -> Optional[str]:
    """Try to get a version string from a command."""
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=10
        )
        output = result.stdout.strip() or result.stderr.strip()
        if output:
            first_line = output.split("\n")[0]
            return first_line[:120]
    except Exception:
        pass
    return None
