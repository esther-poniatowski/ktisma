"""Application use-cases for managed TeX dependency snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Mapping, Optional, Protocol

from ..domain.config import ResolvedConfig, TexDependency
from ..domain.diagnostics import Diagnostic, DiagnosticLevel
from ..domain.exit_codes import ExitCode
from ..domain.tex_dependencies import (
    InstalledFile,
    InstalledTexDependency,
    TexReceipt,
    dependency_record_digest,
)
from .configuration import load_resolved_config
from .protocols import ConfigLoader, LockManager, TexRuntimeCheck


class TexSourceFetcher(Protocol):
    def fetch(self, repository: str, commit: str, destination: Path) -> str:
        """Fetch an exact commit and return the checked-out commit."""


class TexPackageBuilder(Protocol):
    def install(self, dependency: TexDependency, checkout: Path, texmf_root: Path) -> None:
        """Install one package into an otherwise empty TeX tree."""


class TexPathResolver(Protocol):
    def resolve(self, texmf_root: Path, entrypoint: str) -> Optional[Path]:
        """Resolve an entry point with the supplied TeX tree active."""


class TexSnapshotStore(Protocol):
    def create_stage(self, workspace_root: Path) -> Path: ...
    def manifest(self, root: Path) -> tuple[InstalledFile, ...]: ...
    def merge_tree(self, source: Path, destination: Path) -> None: ...
    def write_receipt(self, path: Path, receipt: TexReceipt) -> None: ...
    def read_receipt(self, path: Path) -> TexReceipt: ...
    def snapshot_path(self, workspace_root: Path, digest: str) -> Path: ...
    def read_active_digest(self, workspace_root: Path) -> Optional[str]: ...
    def publish(self, workspace_root: Path, digest: str, staged_snapshot: Path) -> Path: ...
    def select_existing(self, workspace_root: Path, digest: str) -> Path: ...
    def remove_tree(self, path: Path) -> None: ...


@dataclass(frozen=True)
class TexRuntimeServices:
    config_loader: ConfigLoader
    resolver: TexPathResolver
    store: TexSnapshotStore
    supported_builders: frozenset[str] = frozenset()


@dataclass(frozen=True)
class TexInstallServices:
    runtime: TexRuntimeServices
    source_fetcher: TexSourceFetcher
    builders: Mapping[str, TexPackageBuilder]
    lock_manager: LockManager


@dataclass(frozen=True)
class TexDependencyResult:
    exit_code: ExitCode
    record_digest: Optional[str] = None
    texmf_root: Optional[Path] = None
    receipt: Optional[TexReceipt] = None
    declared_dependencies: tuple[TexDependency, ...] = ()
    resolved_entrypoints: dict[str, Path] = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)


@dataclass(frozen=True)
class ConfiguredTexRuntimeVerifier:
    """Expose snapshot validation to builds without install-time capabilities."""

    services: TexRuntimeServices

    def verify(self, workspace_root: Path) -> TexRuntimeCheck:
        result = execute_tex_check(workspace_root, self.services)
        return TexRuntimeCheck(
            texmf_root=(result.texmf_root if result.exit_code == ExitCode.SUCCESS else None),
            diagnostics=result.diagnostics,
        )


def execute_tex_install(workspace_root: Path, services: TexInstallServices) -> TexDependencyResult:
    """Install the root dependency closure and select its complete snapshot."""
    workspace_root = workspace_root.expanduser().resolve()
    runtime = services.runtime
    config = _load_root_config(workspace_root, runtime)
    dependencies = config.tex.dependencies
    digest = dependency_record_digest(dependencies)
    if not dependencies:
        return TexDependencyResult(exit_code=ExitCode.SUCCESS, record_digest=digest)
    unsupported = sorted({dep.builder for dep in dependencies} - set(services.builders))
    if unsupported:
        return _failure(
            digest,
            "unsupported-builder",
            "No registered TeX package builder handles: " + ", ".join(unsupported) + ".",
        )

    lock_path = workspace_root / ".ktisma" / "tex-install.lock"
    services.lock_manager.acquire(lock_path, workspace_root / ".ktisma.toml", "tex-install")
    try:
        existing = runtime.store.snapshot_path(workspace_root, digest)
        if existing.is_dir():
            checked = _check_snapshot(workspace_root, config, runtime, digest, require_active=False)
            if checked.exit_code != ExitCode.SUCCESS:
                return checked
            runtime.store.select_existing(workspace_root, digest)
            return checked
        return _install_new_snapshot(workspace_root, config, digest, services)
    finally:
        services.lock_manager.release(lock_path)


def _install_new_snapshot(
    workspace_root: Path,
    config: ResolvedConfig,
    digest: str,
    services: TexInstallServices,
) -> TexDependencyResult:
    runtime = services.runtime
    dependencies = config.tex.dependencies
    stage = runtime.store.create_stage(workspace_root)
    staged_snapshot = stage / "snapshot"
    assembled_texmf = staged_snapshot / "texmf"
    assembled_texmf.mkdir(parents=True)
    occupied_paths: dict[str, str] = {}
    installed: list[InstalledTexDependency] = []
    try:
        for dependency in sorted(dependencies, key=lambda item: item.name):
            checkout = stage / "sources" / dependency.name
            package_texmf = stage / "packages" / dependency.name / "texmf"
            checkout.parent.mkdir(parents=True, exist_ok=True)
            package_texmf.mkdir(parents=True, exist_ok=True)
            installed_commit = services.source_fetcher.fetch(
                dependency.repository, dependency.commit, checkout
            ).lower()
            if installed_commit != dependency.commit.lower():
                raise ValueError(
                    f"{dependency.name}: fetched {installed_commit}, expected {dependency.commit}."
                )
            services.builders[dependency.builder].install(dependency, checkout, package_texmf)
            files = runtime.store.manifest(package_texmf)
            if not files:
                raise ValueError(f"{dependency.name}: the builder installed no files.")
            for file in files:
                owner = occupied_paths.get(file.path)
                if owner is not None:
                    raise ValueError(
                        f"Installed path collision: {file.path} is provided by {owner} "
                        f"and {dependency.name}."
                    )
                occupied_paths[file.path] = dependency.name
            runtime.store.merge_tree(package_texmf, assembled_texmf)
            installed.append(
                InstalledTexDependency(
                    name=dependency.name,
                    repository=dependency.repository,
                    declared_commit=dependency.commit.lower(),
                    installed_commit=installed_commit,
                    builder=dependency.builder,
                    provides=tuple(sorted(dependency.provides)),
                    files=files,
                )
            )
        receipt = TexReceipt(record_digest=digest, dependencies=tuple(installed))
        runtime.store.write_receipt(staged_snapshot / "receipt.json", receipt)
        resolutions, diagnostics = _resolve_entrypoints(
            assembled_texmf, dependencies, runtime.resolver
        )
        if diagnostics:
            return TexDependencyResult(
                exit_code=ExitCode.CONFIG_ERROR,
                record_digest=digest,
                texmf_root=assembled_texmf,
                receipt=receipt,
                resolved_entrypoints=resolutions,
                diagnostics=diagnostics,
            )
        snapshot = runtime.store.publish(workspace_root, digest, staged_snapshot)
        return TexDependencyResult(
            exit_code=ExitCode.SUCCESS,
            record_digest=digest,
            texmf_root=snapshot / "texmf",
            receipt=receipt,
            resolved_entrypoints=resolutions,
        )
    except Exception as exc:
        return _failure(digest, "tex-install-failed", str(exc))
    finally:
        runtime.store.remove_tree(stage)


def execute_tex_check(workspace_root: Path, services: TexRuntimeServices) -> TexDependencyResult:
    """Verify the selected snapshot against the root dependency record."""
    workspace_root = workspace_root.expanduser().resolve()
    config = _load_root_config(workspace_root, services)
    if not config.tex.dependencies:
        return TexDependencyResult(
            exit_code=ExitCode.SUCCESS,
            record_digest=dependency_record_digest(config.tex.dependencies),
        )
    unsupported = sorted(
        {dependency.builder for dependency in config.tex.dependencies}
        - set(services.supported_builders)
    )
    if unsupported:
        return _failure(
            dependency_record_digest(config.tex.dependencies),
            "unsupported-builder",
            "No registered TeX package builder handles: " + ", ".join(unsupported) + ".",
        )
    return _check_snapshot(workspace_root, config, services)


def execute_tex_inspect(workspace_root: Path, services: TexRuntimeServices) -> TexDependencyResult:
    """Report the declared and derived state validated by the checker."""
    workspace_root = workspace_root.expanduser().resolve()
    config = _load_root_config(workspace_root, services)
    result = execute_tex_check(workspace_root, services)
    return replace(result, declared_dependencies=config.tex.dependencies)


def _load_root_config(workspace_root: Path, services: TexRuntimeServices) -> ResolvedConfig:
    config, _ = load_resolved_config(workspace_root, workspace_root, services.config_loader)
    return config


def _check_snapshot(
    workspace_root: Path,
    config: ResolvedConfig,
    services: TexRuntimeServices,
    expected_digest: Optional[str] = None,
    require_active: bool = True,
) -> TexDependencyResult:
    dependencies = config.tex.dependencies
    digest = expected_digest or dependency_record_digest(dependencies)
    if require_active and services.store.read_active_digest(workspace_root) != digest:
        return _failure(
            digest,
            "tex-snapshot-stale",
            "The active TeX snapshot does not match .ktisma.toml; run 'ktisma tex install'.",
        )
    snapshot = services.store.snapshot_path(workspace_root, digest)
    texmf_root = snapshot / "texmf"
    receipt_path = snapshot / "receipt.json"
    if not snapshot.is_dir() or not texmf_root.is_dir() or not receipt_path.is_file():
        return _failure(
            digest,
            "tex-snapshot-incomplete",
            "The active TeX snapshot or its receipt is missing; run 'ktisma tex install'.",
        )
    try:
        receipt = services.store.read_receipt(receipt_path)
    except Exception as exc:
        return _failure(digest, "invalid-tex-receipt", str(exc))
    receipt_error = _compare_receipt(receipt, dependencies, digest)
    if receipt_error is not None:
        return _failure(digest, "tex-receipt-mismatch", receipt_error)
    try:
        actual_files = {file.path: file.sha256 for file in services.store.manifest(texmf_root)}
    except Exception as exc:
        return _failure(digest, "invalid-tex-snapshot", str(exc))
    receipt_files: dict[str, str] = {}
    for dependency in receipt.dependencies:
        for file in dependency.files:
            if file.path in receipt_files:
                return _failure(
                    digest,
                    "tex-receipt-path-collision",
                    f"The receipt assigns {file.path} to more than one package.",
                )
            receipt_files[file.path] = file.sha256
    if actual_files != receipt_files:
        return _failure(
            digest,
            "tex-manifest-mismatch",
            "The active TeX tree differs from its receipt; run 'ktisma tex install'.",
        )
    resolutions, diagnostics = _resolve_entrypoints(texmf_root, dependencies, services.resolver)
    return TexDependencyResult(
        exit_code=ExitCode.CONFIG_ERROR if diagnostics else ExitCode.SUCCESS,
        record_digest=digest,
        texmf_root=texmf_root,
        receipt=receipt,
        resolved_entrypoints=resolutions,
        diagnostics=diagnostics,
    )


def _compare_receipt(
    receipt: TexReceipt,
    dependencies: tuple[TexDependency, ...],
    digest: str,
) -> Optional[str]:
    if receipt.schema_version != 1 or receipt.record_digest != digest:
        return "The receipt header differs from the root dependency record."
    declared = {
        dependency.name: (
            dependency.repository,
            dependency.commit.lower(),
            dependency.builder,
            tuple(sorted(dependency.provides)),
        )
        for dependency in dependencies
    }
    installed = {
        dependency.name: (
            dependency.repository,
            dependency.declared_commit,
            dependency.builder,
            tuple(sorted(dependency.provides)),
        )
        for dependency in receipt.dependencies
    }
    if installed != declared:
        return "The dependencies in the receipt differ from .ktisma.toml."
    for dependency in receipt.dependencies:
        if dependency.installed_commit != dependency.declared_commit:
            return f"{dependency.name}: the installed commit differs from the declared commit."
    return None


def _resolve_entrypoints(
    texmf_root: Path,
    dependencies: tuple[TexDependency, ...],
    resolver: TexPathResolver,
) -> tuple[dict[str, Path], list[Diagnostic]]:
    root = texmf_root.resolve(strict=True)
    resolutions: dict[str, Path] = {}
    diagnostics: list[Diagnostic] = []
    for dependency in sorted(dependencies, key=lambda item: item.name):
        for entrypoint in sorted(dependency.provides):
            try:
                resolved = resolver.resolve(root, entrypoint)
            except Exception as exc:
                diagnostics.append(
                    _diagnostic(
                        "tex-entrypoint-resolution-failed",
                        f"{dependency.name}: {entrypoint} could not be resolved: {exc}",
                    )
                )
                continue
            if resolved is None:
                diagnostics.append(
                    _diagnostic(
                        "tex-entrypoint-missing",
                        f"{dependency.name}: {entrypoint} does not resolve from the managed TeX tree.",
                    )
                )
                continue
            try:
                candidate = resolved.expanduser().resolve(strict=True)
                candidate.relative_to(root)
            except (FileNotFoundError, ValueError):
                diagnostics.append(
                    _diagnostic(
                        "tex-entrypoint-outside-snapshot",
                        f"{dependency.name}: {entrypoint} resolves outside the managed TeX tree: "
                        f"{resolved}.",
                    )
                )
                continue
            resolutions[f"{dependency.name}:{entrypoint}"] = candidate
    return resolutions, diagnostics


def _failure(digest: str, code: str, message: str) -> TexDependencyResult:
    return TexDependencyResult(
        exit_code=ExitCode.CONFIG_ERROR,
        record_digest=digest,
        diagnostics=[_diagnostic(code, message)],
    )


def _diagnostic(code: str, message: str) -> Diagnostic:
    return Diagnostic(
        level=DiagnosticLevel.ERROR,
        component="tex-dependencies",
        code=code,
        message=message,
    )
