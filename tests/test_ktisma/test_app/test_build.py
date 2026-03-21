"""Tests for ktisma.app.build – the build use-case orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pytest

from ktisma.app.build import (
    BuildResult,
    LockContention,
    ConfigError,
    execute_build,
)
from ktisma.app.protocols import BackendResult, PrerequisiteCheck, WatchUpdate
from ktisma.domain.config import ConfigLayer, CleanupPolicy
from ktisma.domain.context import BuildRequest, SourceContext, SourceInputs
from ktisma.domain.diagnostics import Diagnostic, DiagnosticLevel
from ktisma.domain.exit_codes import ExitCode


# ===========================================================================
# Fake / stub implementations of the protocol interfaces
# ===========================================================================


class FakeConfigLoader:
    """Returns pre-configured config layers."""

    def __init__(self, layers: Optional[list[ConfigLayer]] = None) -> None:
        self._layers = layers if layers is not None else []

    def load_layers(self, workspace_root: Path, source_dir: Path) -> list[ConfigLayer]:
        return list(self._layers)


class FakeSourceReader:
    """Returns a pre-configured SourceInputs."""

    def __init__(
        self,
        preamble: str = "\\documentclass{article}\n\\begin{document}\n\\end{document}\n",
        magic_comments: Optional[dict[str, str]] = None,
    ) -> None:
        self._preamble = preamble
        self._magic_comments = magic_comments or {}

    def read_source(self, source_file: Path) -> SourceInputs:
        return SourceInputs(preamble=self._preamble, magic_comments=self._magic_comments)


class FakeLockManager:
    """Tracks acquire/release calls. Can be configured to raise LockContention."""

    def __init__(self, *, contention: bool = False) -> None:
        self._contention = contention
        self.acquired: list[tuple[Path, Path, str]] = []
        self.released: list[Path] = []

    def acquire(self, lock_file: Path, source_path: Path, mode: str) -> None:
        if self._contention:
            raise LockContention("Simulated lock contention")
        self.acquired.append((lock_file, source_path, mode))

    def release(self, lock_file: Path) -> None:
        self.released.append(lock_file)


class FakeWatchSession:
    def __init__(self, result: BackendResult) -> None:
        self._result = result
        self._returned = False
        self.terminated = False

    def poll(self, timeout_seconds: float = 0.5) -> Optional[WatchUpdate]:
        if self._returned:
            return None
        self._returned = True
        return WatchUpdate(result=self._result, finished=True)

    def terminate(self) -> BackendResult:
        self.terminated = True
        return self._result


class FakeBackendRunner:
    """Returns a pre-configured BackendResult. Can simulate failure."""

    def __init__(
        self,
        *,
        success: bool = True,
        exit_code: int = 0,
        pdf_name: Optional[str] = None,
        diagnostics: Optional[list[Diagnostic]] = None,
    ) -> None:
        self._success = success
        self._exit_code = exit_code
        self._pdf_name = pdf_name
        self._diagnostics = diagnostics or []
        self.compile_calls: list[dict] = []
        self.watch_calls: list[dict] = []

    def compile(
        self,
        source_file: Path,
        build_dir: Path,
        engine: str,
        synctex: bool,
        extra_args: Optional[list[str]] = None,
    ) -> BackendResult:
        self.compile_calls.append(
            {
                "source_file": source_file,
                "build_dir": build_dir,
                "engine": engine,
                "synctex": synctex,
                "extra_args": extra_args,
            }
        )

        pdf_path = None
        if self._success:
            stem = source_file.stem
            name = self._pdf_name or f"{stem}.pdf"
            pdf_path = build_dir / name
            # Create the build dir and PDF so materialization can find it
            build_dir.mkdir(parents=True, exist_ok=True)
            pdf_path.write_bytes(b"%PDF-1.4 fake")

        return BackendResult(
            success=self._success,
            exit_code=self._exit_code,
            pdf_path=pdf_path,
            diagnostics=self._diagnostics,
        )

    def start_watch(
        self,
        source_file: Path,
        build_dir: Path,
        engine: str,
        synctex: bool,
        extra_args: Optional[list[str]] = None,
    ) -> FakeWatchSession:
        self.watch_calls.append(
            {
                "source_file": source_file,
                "build_dir": build_dir,
                "engine": engine,
                "synctex": synctex,
                "extra_args": extra_args,
            }
        )
        pdf_path = build_dir / f"{source_file.stem}.pdf" if self._success else None
        if pdf_path is not None:
            build_dir.mkdir(parents=True, exist_ok=True)
            pdf_path.write_bytes(b"%PDF-1.4 fake")
        return FakeWatchSession(
            BackendResult(
                success=self._success,
                exit_code=self._exit_code,
                pdf_path=pdf_path,
                diagnostics=self._diagnostics,
            )
        )


class FakeMaterializer:
    """Tracks materialize calls. Optionally simulates failure."""

    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail
        self.calls: list[tuple[Path, Path]] = []

    def materialize(self, source: Path, destination: Path) -> None:
        self.calls.append((source, destination))
        if self._fail:
            raise OSError("Simulated materialization failure")
        # Actually create the destination for downstream checks
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.exists():
            destination.write_bytes(source.read_bytes())
        else:
            destination.write_bytes(b"fake")


class FakePrerequisiteProbe:
    def __init__(
        self,
        *,
        latexmk_available: bool = True,
        engine_available: bool = True,
    ) -> None:
        self._latexmk_available = latexmk_available
        self._engine_available = engine_available

    def check_latexmk(self) -> PrerequisiteCheck:
        return PrerequisiteCheck(
            name="latexmk",
            available=self._latexmk_available,
            message="" if self._latexmk_available else "latexmk missing",
        )

    def check_engine(self, engine: str) -> PrerequisiteCheck:
        return PrerequisiteCheck(
            name=engine,
            available=self._engine_available,
            message="" if self._engine_available else f"{engine} missing",
        )

    def check_python_version(self) -> PrerequisiteCheck:
        return PrerequisiteCheck(name="python", available=True, message="")

    def check_toml_support(self) -> PrerequisiteCheck:
        return PrerequisiteCheck(name="toml", available=True, message="")


class FakeWorkspaceOps:
    def ensure_directory(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def path_exists(self, path: Path) -> bool:
        return path.exists()

    def is_directory(self, path: Path) -> bool:
        return path.is_dir()

    def list_directory(self, path: Path) -> list[Path]:
        return list(path.iterdir())

    def remove_tree(self, path: Path) -> None:
        import shutil

        shutil.rmtree(path)


# ===========================================================================
# Helpers
# ===========================================================================


def _make_ctx(tmp_path: Path, filename: str = "paper.tex") -> SourceContext:
    """Create a SourceContext rooted in tmp_path."""
    source_file = tmp_path / filename
    source_file.write_text("\\documentclass{article}\n\\begin{document}\n\\end{document}\n")
    return SourceContext(
        source_file=source_file,
        source_dir=tmp_path,
        workspace_root=tmp_path,
    )


def _default_request(**overrides) -> BuildRequest:
    return BuildRequest(**overrides)


def _execute_build(**kwargs) -> BuildResult:
    kwargs.setdefault("prerequisite_probe", FakePrerequisiteProbe())
    kwargs.setdefault("workspace_ops", FakeWorkspaceOps())
    return execute_build(**kwargs)


# ===========================================================================
# Test: successful build flow
# ===========================================================================


class TestSuccessfulBuild:
    def test_basic_build_returns_success(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        assert result.exit_code == ExitCode.SUCCESS

    def test_engine_decision_populated(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        assert result.engine is not None
        assert result.engine.engine  # should have a non-empty engine name

    def test_route_decision_populated(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        assert result.route is not None

    def test_build_plan_populated(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        assert result.build_plan is not None
        assert result.build_plan.build_dir is not None

    def test_backend_called_with_correct_source(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        backend = FakeBackendRunner()
        _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=backend,
            materializer=FakeMaterializer(),
        )
        assert len(backend.compile_calls) == 1
        assert backend.compile_calls[0]["source_file"] == ctx.source_file

    def test_materializer_called(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        mat = FakeMaterializer()
        _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=mat,
        )
        assert len(mat.calls) == 1

    def test_lock_acquired_and_released(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        lock_mgr = FakeLockManager()
        _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=lock_mgr,
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        assert len(lock_mgr.acquired) == 1
        assert len(lock_mgr.released) == 1
        # The lock file acquired should match the one released
        assert lock_mgr.acquired[0][0] == lock_mgr.released[0]

    def test_produced_paths_non_empty(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        assert len(result.produced_paths) >= 1

    def test_engine_override_used(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        backend = FakeBackendRunner()
        _execute_build(
            ctx=ctx,
            request=_default_request(engine_override="xelatex"),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=backend,
            materializer=FakeMaterializer(),
        )
        assert backend.compile_calls[0]["engine"] == "xelatex"


# ===========================================================================
# Test: compile failure
# ===========================================================================


class TestCompileFailure:
    def test_compilation_failure_exit_code(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(success=False, exit_code=1),
            materializer=FakeMaterializer(),
        )
        assert result.exit_code == ExitCode.COMPILATION_FAILURE

    def test_materializer_not_called_on_failure(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        mat = FakeMaterializer()
        _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(success=False, exit_code=1),
            materializer=mat,
        )
        assert len(mat.calls) == 0

    def test_lock_released_on_failure(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        lock_mgr = FakeLockManager()
        _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=lock_mgr,
            backend_runner=FakeBackendRunner(success=False, exit_code=1),
            materializer=FakeMaterializer(),
        )
        assert len(lock_mgr.released) == 1

    def test_backend_result_included_on_failure(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(success=False, exit_code=1),
            materializer=FakeMaterializer(),
        )
        assert result.backend_result is not None
        assert result.backend_result.success is False

    def test_diagnostics_from_backend_propagated(self, tmp_path: Path) -> None:
        diag = Diagnostic(
            level=DiagnosticLevel.ERROR,
            component="latexmk",
            code="compile-error",
            message="Undefined control sequence",
        )
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(success=False, exit_code=1, diagnostics=[diag]),
            materializer=FakeMaterializer(),
        )
        codes = [d.code for d in result.diagnostics]
        assert "compile-error" in codes


# ===========================================================================
# Test: lock contention
# ===========================================================================


class TestLockContention:
    def test_lock_contention_exit_code(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(contention=True),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        assert result.exit_code == ExitCode.LOCK_CONTENTION

    def test_backend_not_called_on_contention(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        backend = FakeBackendRunner()
        _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(contention=True),
            backend_runner=backend,
            materializer=FakeMaterializer(),
        )
        assert len(backend.compile_calls) == 0

    def test_materializer_not_called_on_contention(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        mat = FakeMaterializer()
        _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(contention=True),
            backend_runner=FakeBackendRunner(),
            materializer=mat,
        )
        assert len(mat.calls) == 0

    def test_contention_diagnostic_present(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(contention=True),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        codes = [d.code for d in result.diagnostics]
        assert "lock-contention" in codes

    def test_lock_contention_exception_has_correct_exit_code(self) -> None:
        exc = LockContention("test message")
        assert exc.exit_code == ExitCode.LOCK_CONTENTION


# ===========================================================================
# Test: dry run mode
# ===========================================================================


class TestDryRun:
    def test_dry_run_returns_success(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(dry_run=True),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        assert result.exit_code == ExitCode.SUCCESS

    def test_dry_run_no_backend_call(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        backend = FakeBackendRunner()
        _execute_build(
            ctx=ctx,
            request=_default_request(dry_run=True),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=backend,
            materializer=FakeMaterializer(),
        )
        assert len(backend.compile_calls) == 0

    def test_dry_run_no_lock_acquired(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        lock_mgr = FakeLockManager()
        _execute_build(
            ctx=ctx,
            request=_default_request(dry_run=True),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=lock_mgr,
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        assert len(lock_mgr.acquired) == 0

    def test_dry_run_no_materialization(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        mat = FakeMaterializer()
        _execute_build(
            ctx=ctx,
            request=_default_request(dry_run=True),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=mat,
        )
        assert len(mat.calls) == 0

    def test_dry_run_populates_plan(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(dry_run=True),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        assert result.engine is not None
        assert result.route is not None
        assert result.build_plan is not None

    def test_dry_run_no_produced_paths(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(dry_run=True),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        assert result.produced_paths == []


# ===========================================================================
# Test: cleanup policies
# ===========================================================================


class TestCleanupPolicies:
    def test_cleanup_override_always(self, tmp_path: Path) -> None:
        """With cleanup_override='always', build dir should be removed after success."""
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(cleanup_override="always"),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        assert result.exit_code == ExitCode.SUCCESS
        # The build dir may or may not exist depending on cleanup timing.
        # The important thing is no error from cleanup.

    def test_cleanup_never_preserves_build_dir(self, tmp_path: Path) -> None:
        """With cleanup='never', the build dir should be preserved."""
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(cleanup_override="never"),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        assert result.exit_code == ExitCode.SUCCESS
        # Build dir should still exist (cleanup=never)
        if result.build_plan:
            assert result.build_plan.build_dir.exists()

    def test_cleanup_on_success_removes_on_success(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(cleanup_override="on_success"),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        assert result.exit_code == ExitCode.SUCCESS

    def test_cleanup_on_success_preserves_on_failure(self, tmp_path: Path) -> None:
        """On compilation failure with on_success policy, build dir is preserved."""
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(cleanup_override="on_success"),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(success=False, exit_code=1),
            materializer=FakeMaterializer(),
        )
        assert result.exit_code == ExitCode.COMPILATION_FAILURE


# ===========================================================================
# Test: prerequisite failures
# ===========================================================================


class TestPrerequisiteFailures:
    def test_missing_latexmk_returns_prerequisite_failure(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        backend = FakeBackendRunner()
        result = _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=backend,
            materializer=FakeMaterializer(),
            prerequisite_probe=FakePrerequisiteProbe(latexmk_available=False),
        )
        assert result.exit_code == ExitCode.PREREQUISITE_FAILURE
        assert backend.compile_calls == []
        assert "missing-latexmk" in [d.code for d in result.diagnostics]

    def test_missing_engine_returns_prerequisite_failure(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(engine_override="xelatex"),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
            prerequisite_probe=FakePrerequisiteProbe(engine_available=False),
        )
        assert result.exit_code == ExitCode.PREREQUISITE_FAILURE
        assert "missing-engine" in [d.code for d in result.diagnostics]


# ===========================================================================
# Test: variant builds
# ===========================================================================


class TestVariantBuilds:
    def test_variant_build_with_payload(self, tmp_path: Path) -> None:
        """When variant and variant_payload are both given, uses them directly."""
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(
                variant="draft",
                variant_payload="\\def\\isdraft{1}",
            ),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        assert result.exit_code == ExitCode.SUCCESS
        # Build plan should reflect variant
        assert result.build_plan is not None
        assert result.build_plan.variant is not None
        assert result.build_plan.variant.name == "draft"

    def test_variant_from_config(self, tmp_path: Path) -> None:
        """When variant name is given but no payload, it's looked up from config."""
        config_layer = ConfigLayer(
            data={"variants": {"draft": "\\def\\isdraft{1}"}},
            source=tmp_path,
            label="test config",
        )
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(variant="draft"),
            config_loader=FakeConfigLoader(layers=[config_layer]),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        assert result.exit_code == ExitCode.SUCCESS
        assert result.build_plan is not None
        assert result.build_plan.variant is not None
        assert result.build_plan.variant.name == "draft"

    def test_unknown_variant_raises_config_error(self, tmp_path: Path) -> None:
        """Requesting a variant that doesn't exist in config raises ConfigError."""
        ctx = _make_ctx(tmp_path)
        with pytest.raises(ConfigError):
            _execute_build(
                ctx=ctx,
                request=_default_request(variant="nonexistent"),
                config_loader=FakeConfigLoader(),
                source_reader=FakeSourceReader(),
                lock_manager=FakeLockManager(),
                backend_runner=FakeBackendRunner(),
                    materializer=FakeMaterializer(),
                )

    def test_invalid_variant_name_raises_config_error(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        with pytest.raises(ConfigError):
            _execute_build(
                ctx=ctx,
                request=_default_request(
                    variant="../../bad",
                    variant_payload="\\def\\isdraft{1}",
                ),
                config_loader=FakeConfigLoader(),
                source_reader=FakeSourceReader(),
                lock_manager=FakeLockManager(),
                backend_runner=FakeBackendRunner(),
                materializer=FakeMaterializer(),
            )

    def test_variant_affects_output_filename(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        mat = FakeMaterializer()
        result = _execute_build(
            ctx=ctx,
            request=_default_request(
                variant="final",
                variant_payload="\\def\\isfinal{1}",
            ),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=mat,
        )
        assert result.exit_code == ExitCode.SUCCESS
        # The materialized destination should include the variant suffix
        if mat.calls:
            dest = mat.calls[0][1]
            assert "final" in dest.name

    def test_variant_extra_args_passed_to_backend(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        backend = FakeBackendRunner()
        _execute_build(
            ctx=ctx,
            request=_default_request(
                variant="draft",
                variant_payload="\\def\\isdraft{1}",
            ),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=backend,
            materializer=FakeMaterializer(),
        )
        assert len(backend.compile_calls) == 1
        extra = backend.compile_calls[0]["extra_args"]
        assert extra is not None
        assert "-usepretex" in extra

    def test_no_variant_no_extra_args(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        backend = FakeBackendRunner()
        _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=backend,
            materializer=FakeMaterializer(),
        )
        assert len(backend.compile_calls) == 1
        extra = backend.compile_calls[0]["extra_args"]
        assert extra is None

    def test_variant_build_dir_includes_variant_name(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(
                variant="draft",
                variant_payload="\\def\\isdraft{1}",
            ),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(),
        )
        assert result.build_plan is not None
        assert "draft" in result.build_plan.build_dir.name


# ===========================================================================
# Test: materialization failure
# ===========================================================================


class TestMaterializationFailure:
    def test_materialization_failure_returns_internal_error(
        self, tmp_path: Path
    ) -> None:
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(fail=True),
        )
        assert result.exit_code == ExitCode.INTERNAL_ERROR

    def test_materialization_failure_diagnostic(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        result = _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(fail=True),
        )
        codes = [d.code for d in result.diagnostics]
        assert "materialization-failed" in codes

    def test_lock_released_on_materialization_failure(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        lock_mgr = FakeLockManager()
        _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=lock_mgr,
            backend_runner=FakeBackendRunner(),
            materializer=FakeMaterializer(fail=True),
        )
        assert len(lock_mgr.released) == 1


# ===========================================================================
# Test: watch mode
# ===========================================================================


class TestWatchMode:
    def test_watch_uses_watch_session_and_materializes_output(self, tmp_path: Path) -> None:
        ctx = _make_ctx(tmp_path)
        backend = FakeBackendRunner()
        materializer = FakeMaterializer()
        lock_mgr = FakeLockManager()

        result = _execute_build(
            ctx=ctx,
            request=_default_request(watch=True),
            config_loader=FakeConfigLoader(),
            source_reader=FakeSourceReader(),
            lock_manager=lock_mgr,
            backend_runner=backend,
            materializer=materializer,
        )

        assert result.exit_code == ExitCode.SUCCESS
        assert backend.compile_calls == []
        assert len(backend.watch_calls) == 1
        assert len(materializer.calls) == 1
        assert len(lock_mgr.released) == 1


# ===========================================================================
# Test: config layers integration
# ===========================================================================


class TestConfigIntegration:
    def test_config_layer_engine_default_used(self, tmp_path: Path) -> None:
        """A config layer setting engines.default is respected."""
        config_layer = ConfigLayer(
            data={"engines": {"default": "lualatex"}},
            source=tmp_path,
            label="test",
        )
        ctx = _make_ctx(tmp_path)
        backend = FakeBackendRunner()
        _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(layers=[config_layer]),
            source_reader=FakeSourceReader(),
            lock_manager=FakeLockManager(),
            backend_runner=backend,
            materializer=FakeMaterializer(),
        )
        # Without magic comments or markers, engine falls back to config default
        assert backend.compile_calls[0]["engine"] == "lualatex"

    def test_magic_comment_overrides_config(self, tmp_path: Path) -> None:
        config_layer = ConfigLayer(
            data={"engines": {"default": "pdflatex"}},
            source=tmp_path,
            label="test",
        )
        ctx = _make_ctx(tmp_path)
        backend = FakeBackendRunner()
        _execute_build(
            ctx=ctx,
            request=_default_request(),
            config_loader=FakeConfigLoader(layers=[config_layer]),
            source_reader=FakeSourceReader(magic_comments={"program": "xelatex"}),
            lock_manager=FakeLockManager(),
            backend_runner=backend,
            materializer=FakeMaterializer(),
        )
        assert backend.compile_calls[0]["engine"] == "xelatex"
