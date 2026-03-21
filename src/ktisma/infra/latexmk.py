from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Optional

from ..app.protocols import BackendResult, WatchSession, WatchUpdate
from ..domain.diagnostics import Diagnostic, DiagnosticLevel


class LatexmkRunner:
    """Concrete BackendRunner: invokes latexmk for compilation."""

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

    def start_watch(
        self,
        source_file: Path,
        build_dir: Path,
        engine: str,
        synctex: bool,
        extra_args: Optional[list[str]] = None,
    ) -> WatchSession:
        """Launch latexmk in continuous watch mode (latexmk -pvc)."""
        args = self._build_args(source_file, build_dir, engine, synctex, extra_args)
        args.append("-pvc")
        return LatexmkWatchSession(source_file, build_dir, args)

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


class LatexmkWatchSession:
    """Polling watch session over a live latexmk -pvc subprocess."""

    def __init__(self, source_file: Path, build_dir: Path, args: list[str]) -> None:
        self._source_file = source_file
        self._pdf_path = build_dir / f"{source_file.stem}.pdf"
        self._returned_final = False
        self._last_pdf_mtime = self._pdf_mtime()

        try:
            self._process = subprocess.Popen(
                args,
                cwd=str(source_file.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            self._startup_error: Optional[BackendResult] = None
        except FileNotFoundError:
            self._process = None
            self._startup_error = BackendResult(
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

    def poll(self, timeout_seconds: float = 0.5) -> Optional[WatchUpdate]:
        if self._startup_error is not None:
            result = self._startup_error
            self._startup_error = None
            return WatchUpdate(result=result, finished=True)

        if self._process is None or self._returned_final:
            return None

        deadline = time.monotonic() + timeout_seconds
        while True:
            pdf_mtime = self._pdf_mtime()
            if pdf_mtime is not None and (
                self._last_pdf_mtime is None or pdf_mtime > self._last_pdf_mtime
            ):
                self._last_pdf_mtime = pdf_mtime
                return WatchUpdate(
                    result=BackendResult(
                        success=True,
                        exit_code=0,
                        pdf_path=self._pdf_path,
                    ),
                    finished=False,
                )

            return_code = self._process.poll()
            if return_code is not None:
                self._returned_final = True
                return WatchUpdate(
                    result=BackendResult(
                        success=return_code == 0,
                        exit_code=return_code,
                        pdf_path=self._pdf_path if self._pdf_path.is_file() else None,
                    ),
                    finished=True,
                )

            if time.monotonic() >= deadline:
                return None

            time.sleep(0.1)

    def terminate(self) -> BackendResult:
        if self._startup_error is not None:
            result = self._startup_error
            self._startup_error = None
            return result

        if self._process is None:
            return BackendResult(success=True, exit_code=0, pdf_path=self._pdf_path)

        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=10)

        return_code = self._process.returncode or 0
        self._returned_final = True
        return BackendResult(
            success=return_code == 0,
            exit_code=return_code,
            pdf_path=self._pdf_path if self._pdf_path.is_file() else None,
        )

    def _pdf_mtime(self) -> Optional[float]:
        if not self._pdf_path.is_file():
            return None
        return self._pdf_path.stat().st_mtime


def _engine_to_flag(engine: str) -> str:
    """Map engine name to latexmk flag."""
    mapping = {
        "pdflatex": "-pdf",
        "lualatex": "-lualatex",
        "xelatex": "-xelatex",
        "latex": "-dvi",
    }
    return mapping.get(engine, f"-{engine}")
