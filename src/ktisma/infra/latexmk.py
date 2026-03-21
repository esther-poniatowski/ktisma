from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from ..app.protocols import BackendResult
from ..domain.diagnostics import Diagnostic, DiagnosticLevel


class LatexmkRunner:
    """Concrete BackendRunner: invokes latexmk for compilation.

    Per design principles:
    - Uses argument vectors, not shell command strings.
    - Does not use shell=True.
    - Captures stdout/stderr for diagnostics.
    """

    def compile(
        self,
        source_file: Path,
        build_dir: Path,
        engine: str,
        synctex: bool,
        extra_args: Optional[list[str]] = None,
    ) -> BackendResult:
        """Run latexmk for a one-shot compilation."""
        args = self._build_args(source_file, build_dir, engine, synctex, extra_args)

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                cwd=str(source_file.parent),
                timeout=600,
            )
        except subprocess.TimeoutExpired:
            return BackendResult(
                success=False,
                exit_code=-1,
                diagnostics=[
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        component="backend",
                        code="compilation-timeout",
                        message="Compilation timed out after 600 seconds.",
                    )
                ],
            )
        except FileNotFoundError:
            return BackendResult(
                success=False,
                exit_code=-1,
                diagnostics=[
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        component="backend",
                        code="latexmk-not-found",
                        message="latexmk is not installed or not on PATH.",
                    )
                ],
            )

        pdf_path = build_dir / f"{source_file.stem}.pdf"
        success = result.returncode == 0 and pdf_path.is_file()

        diagnostics: list[Diagnostic] = []
        if not success and result.returncode != 0:
            diagnostics.append(
                Diagnostic(
                    level=DiagnosticLevel.ERROR,
                    component="backend",
                    code="compilation-failed",
                    message=f"latexmk exited with code {result.returncode}.",
                )
            )

        return BackendResult(
            success=success,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            pdf_path=pdf_path if pdf_path.is_file() else None,
            diagnostics=diagnostics,
        )

    def compile_watch(
        self,
        source_file: Path,
        build_dir: Path,
        engine: str,
        synctex: bool,
        extra_args: Optional[list[str]] = None,
    ) -> BackendResult:
        """Launch latexmk in continuous watch mode (latexmk -pvc)."""
        args = self._build_args(source_file, build_dir, engine, synctex, extra_args)
        args.append("-pvc")

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                cwd=str(source_file.parent),
            )
        except FileNotFoundError:
            return BackendResult(
                success=False,
                exit_code=-1,
                diagnostics=[
                    Diagnostic(
                        level=DiagnosticLevel.ERROR,
                        component="backend",
                        code="latexmk-not-found",
                        message="latexmk is not installed or not on PATH.",
                    )
                ],
            )

        pdf_path = build_dir / f"{source_file.stem}.pdf"
        # Watch mode exit code 0 means clean termination (e.g. via signal)
        success = result.returncode == 0

        return BackendResult(
            success=success,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            pdf_path=pdf_path if pdf_path.is_file() else None,
        )

    def _build_args(
        self,
        source_file: Path,
        build_dir: Path,
        engine: str,
        synctex: bool,
        extra_args: Optional[list[str]] = None,
    ) -> list[str]:
        """Build the latexmk argument vector."""
        engine_flag = _engine_to_flag(engine)

        args = [
            "latexmk",
            engine_flag,
            f"-outdir={build_dir}",
            "-interaction=nonstopmode",
            "-file-line-error",
        ]

        if synctex:
            args.append("-synctex=1")

        if extra_args:
            args.extend(extra_args)

        args.append(str(source_file))
        return args


def _engine_to_flag(engine: str) -> str:
    """Map engine name to latexmk flag."""
    mapping = {
        "pdflatex": "-pdf",
        "lualatex": "-lualatex",
        "xelatex": "-xelatex",
        "latex": "-dvi",
    }
    return mapping.get(engine, f"-{engine}")
