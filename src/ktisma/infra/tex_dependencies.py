"""Filesystem, Git, and TeX-process adapters for dependency snapshots."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from ..domain.config import TexDependency
from ..domain.tex_dependencies import InstalledFile, TexReceipt, sha256_bytes

_DIGEST = re.compile(r"^[0-9a-f]{64}$")


class GitTexSourceFetcher:
    """Fetch exact Git commits without consulting another local checkout."""

    def fetch(self, repository: str, commit: str, destination: Path) -> str:
        destination.mkdir(parents=True, exist_ok=False)
        self._run(["git", "init", "--quiet"], destination)
        self._run(["git", "remote", "add", "origin", repository], destination)
        self._run(["git", "fetch", "--quiet", "--depth", "1", "origin", commit], destination)
        self._run(["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"], destination)
        return self._run(["git", "rev-parse", "HEAD"], destination).stdout.strip()

    @staticmethod
    def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip() or "Git command failed."
            raise RuntimeError(message)
        return result


class KpsewhichTexPathResolver:
    """Resolve TeX entry points with one managed TEXMFHOME."""

    def resolve(self, texmf_root: Path, entrypoint: str) -> Optional[Path]:
        environment = os.environ.copy()
        environment["TEXMFHOME"] = str(texmf_root.resolve(strict=True))
        result = subprocess.run(
            ["kpsewhich", entrypoint],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        return Path(result.stdout.strip())


class L3BuildTexPackageBuilder:
    """Install an l3build package through its ordinary runtime target."""

    def install(self, dependency: TexDependency, checkout: Path, texmf_root: Path) -> None:
        texmf_root.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["l3build", "install", "--texmfhome", str(texmf_root.resolve())],
            cwd=checkout,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(
                f"{dependency.name}: l3build installation failed"
                + (f": {message}" if message else ".")
            )


class FileTexSnapshotStore:
    """Store content-addressed snapshots and publish their active pointer."""

    def create_stage(self, workspace_root: Path) -> Path:
        staging_root = workspace_root / ".ktisma" / "tex-staging"
        staging_root.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix="install-", dir=staging_root))

    def manifest(self, root: Path) -> tuple[InstalledFile, ...]:
        if not root.is_dir():
            return ()
        files: list[InstalledFile] = []
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Managed TeX trees may not contain symlinks: {path}")
            if path.is_dir():
                continue
            if not path.is_file():
                raise ValueError(f"Unsupported filesystem entry in managed TeX tree: {path}")
            files.append(
                InstalledFile(
                    path=path.relative_to(root).as_posix(),
                    sha256=sha256_bytes(path.read_bytes()),
                )
            )
        return tuple(files)

    def merge_tree(self, source: Path, destination: Path) -> None:
        for path in sorted(source.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Managed TeX trees may not contain symlinks: {path}")
            if path.is_dir():
                continue
            relative = path.relative_to(source)
            target = destination / relative
            if target.exists():
                raise FileExistsError(
                    f"Refusing to overwrite installed path {relative.as_posix()}."
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)

    def write_receipt(self, path: Path, receipt: TexReceipt) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(receipt.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def read_receipt(self, path: Path) -> TexReceipt:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("The TeX receipt must contain a JSON object.")
        return TexReceipt.from_dict(data)

    def snapshot_path(self, workspace_root: Path, digest: str) -> Path:
        if not _DIGEST.fullmatch(digest):
            raise ValueError(
                "A TeX snapshot digest must contain 64 lowercase hexadecimal characters."
            )
        return workspace_root / ".ktisma" / "tex-snapshots" / digest

    def read_active_digest(self, workspace_root: Path) -> Optional[str]:
        pointer = workspace_root / ".ktisma" / "tex-current"
        if not pointer.is_file():
            return None
        value = pointer.read_text(encoding="utf-8").strip()
        if not _DIGEST.fullmatch(value):
            return None
        return value

    def publish(self, workspace_root: Path, digest: str, staged_snapshot: Path) -> Path:
        destination = self.snapshot_path(workspace_root, digest)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(f"Snapshot already exists: {destination}")
        os.replace(staged_snapshot, destination)
        self._write_pointer(workspace_root, digest)
        return destination

    def select_existing(self, workspace_root: Path, digest: str) -> Path:
        snapshot = self.snapshot_path(workspace_root, digest)
        if not snapshot.is_dir():
            raise FileNotFoundError(snapshot)
        if self.read_active_digest(workspace_root) != digest:
            self._write_pointer(workspace_root, digest)
        return snapshot

    def remove_tree(self, path: Path) -> None:
        shutil.rmtree(path, ignore_errors=True)

    @staticmethod
    def _write_pointer(workspace_root: Path, digest: str) -> None:
        if not _DIGEST.fullmatch(digest):
            raise ValueError(
                "A TeX snapshot digest must contain 64 lowercase hexadecimal characters."
            )
        state_root = workspace_root / ".ktisma"
        state_root.mkdir(parents=True, exist_ok=True)
        pointer = state_root / "tex-current"
        descriptor, temporary_name = tempfile.mkstemp(prefix="tex-current-", dir=state_root)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(digest + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, pointer)
        finally:
            if temporary.exists():
                temporary.unlink()
