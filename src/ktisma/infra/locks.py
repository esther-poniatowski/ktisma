from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path

from ..domain.errors import LockContention


class FileLockManager:
    """Concrete LockManager: file-based exclusive build locks.

    Lock semantics per roadmap:
    - Lock file path: <build-dir>/.ktisma.lock
    - Acquisition uses exclusive creation.
    - Lock contents: hostname, PID, source path, mode, creation timestamp.
    - Stale recovery: same host + PID no longer exists.
    - If unrecoverable, raise LockContention with dedicated exit code.
    """

    def acquire(
        self,
        lock_file: Path,
        source_path: Path,
        mode: str,
    ) -> None:
        """Acquire an exclusive build lock."""
        lock_file.parent.mkdir(parents=True, exist_ok=True)

        lock_data = {
            "hostname": socket.gethostname(),
            "pid": os.getpid(),
            "source": str(source_path),
            "mode": mode,
            "created": time.time(),
        }

        try:
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, json.dumps(lock_data, indent=2).encode())
            finally:
                os.close(fd)
        except FileExistsError:
            self._handle_existing_lock(lock_file, source_path, mode, lock_data)

    def release(self, lock_file: Path) -> None:
        """Release a previously acquired build lock."""
        try:
            lock_file.unlink(missing_ok=True)
        except OSError:
            pass

    def _handle_existing_lock(
        self,
        lock_file: Path,
        source_path: Path,
        mode: str,
        new_lock_data: dict,
    ) -> None:
        """Handle an existing lock file: attempt stale recovery or raise contention."""
        try:
            content = lock_file.read_text()
        except Exception:
            raise LockContention(
                f"Lock file exists at {lock_file} but cannot be read. "
                f"Remove it manually if the owning process is no longer running."
            )

        if not content.strip():
            # Empty lock file — likely a crash between create and write.
            # Treat as stale and recover.
            try:
                lock_file.unlink()
            except OSError:
                raise LockContention(
                    f"Empty lock file at {lock_file} but could not remove it."
                )
            try:
                fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                try:
                    os.write(fd, json.dumps(new_lock_data, indent=2).encode())
                finally:
                    os.close(fd)
                return
            except FileExistsError:
                raise LockContention(
                    f"Lock file appeared again at {lock_file} during empty-lock recovery."
                )

        try:
            existing = json.loads(content)
        except Exception:
            raise LockContention(
                f"Lock file exists at {lock_file} but contains invalid data. "
                f"Remove it manually if the owning process is no longer running."
            )

        existing_hostname = existing.get("hostname", "")
        existing_pid = existing.get("pid", -1)
        current_hostname = socket.gethostname()

        # Stale recovery: same host and PID no longer exists
        if existing_hostname == current_hostname and not _pid_exists(existing_pid):
            try:
                lock_file.unlink()
            except OSError:
                raise LockContention(
                    f"Stale lock detected at {lock_file} but could not remove it."
                )

            # Retry acquisition
            try:
                fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                try:
                    os.write(fd, json.dumps(new_lock_data, indent=2).encode())
                finally:
                    os.close(fd)
                return
            except FileExistsError:
                raise LockContention(
                    f"Lock file appeared again at {lock_file} during stale recovery."
                )

        # Different host or PID still alive: genuine contention
        owner_desc = f"PID {existing_pid} on {existing_hostname}"
        existing_source = existing.get("source", "unknown")
        existing_mode = existing.get("mode", "unknown")
        raise LockContention(
            f"Build lock held by {owner_desc} ({existing_mode} mode on {existing_source}). "
            f"Wait for the owning process to finish or remove {lock_file} manually."
        )


def _pid_exists(pid: int) -> bool:
    """Check if a process with the given PID exists."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # process exists but we can't signal it
