"""Tests for ktisma.infra.locks – file-based exclusive build locks."""

from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from ktisma.app.build import LockContention
from ktisma.infra.locks import FileLockManager, _pid_exists


@pytest.fixture
def lock_mgr() -> FileLockManager:
    return FileLockManager()


# ---------------------------------------------------------------------------
# Lock acquisition
# ---------------------------------------------------------------------------


class TestAcquire:
    def test_creates_lock_file(
        self, tmp_path: Path, lock_mgr: FileLockManager
    ) -> None:
        lock_file = tmp_path / "build" / ".ktisma.lock"
        source = tmp_path / "doc.tex"
        lock_mgr.acquire(lock_file, source, "build")
        assert lock_file.exists()

    def test_lock_file_contains_expected_data(
        self, tmp_path: Path, lock_mgr: FileLockManager
    ) -> None:
        lock_file = tmp_path / "build" / ".ktisma.lock"
        source = tmp_path / "doc.tex"
        lock_mgr.acquire(lock_file, source, "build")
        data = json.loads(lock_file.read_text())
        assert data["hostname"] == socket.gethostname()
        assert data["pid"] == os.getpid()
        assert data["source"] == str(source)
        assert data["mode"] == "build"
        assert "created" in data

    def test_creates_parent_directories(
        self, tmp_path: Path, lock_mgr: FileLockManager
    ) -> None:
        lock_file = tmp_path / "deep" / "nested" / "dir" / ".ktisma.lock"
        source = tmp_path / "doc.tex"
        lock_mgr.acquire(lock_file, source, "build")
        assert lock_file.exists()

    def test_mode_stored_in_lock(
        self, tmp_path: Path, lock_mgr: FileLockManager
    ) -> None:
        lock_file = tmp_path / ".ktisma.lock"
        source = tmp_path / "doc.tex"
        lock_mgr.acquire(lock_file, source, "watch")
        data = json.loads(lock_file.read_text())
        assert data["mode"] == "watch"

    def test_timestamp_is_recent(
        self, tmp_path: Path, lock_mgr: FileLockManager
    ) -> None:
        lock_file = tmp_path / ".ktisma.lock"
        source = tmp_path / "doc.tex"
        before = time.time()
        lock_mgr.acquire(lock_file, source, "build")
        after = time.time()
        data = json.loads(lock_file.read_text())
        assert before <= data["created"] <= after


# ---------------------------------------------------------------------------
# Lock release
# ---------------------------------------------------------------------------


class TestRelease:
    def test_release_removes_lock_file(
        self, tmp_path: Path, lock_mgr: FileLockManager
    ) -> None:
        lock_file = tmp_path / ".ktisma.lock"
        source = tmp_path / "doc.tex"
        lock_mgr.acquire(lock_file, source, "build")
        assert lock_file.exists()
        lock_mgr.release(lock_file)
        assert not lock_file.exists()

    def test_release_nonexistent_is_safe(
        self, tmp_path: Path, lock_mgr: FileLockManager
    ) -> None:
        lock_file = tmp_path / "no_such_lock"
        # Should not raise
        lock_mgr.release(lock_file)

    def test_release_twice_is_safe(
        self, tmp_path: Path, lock_mgr: FileLockManager
    ) -> None:
        lock_file = tmp_path / ".ktisma.lock"
        source = tmp_path / "doc.tex"
        lock_mgr.acquire(lock_file, source, "build")
        lock_mgr.release(lock_file)
        lock_mgr.release(lock_file)  # second release should be safe
        assert not lock_file.exists()


# ---------------------------------------------------------------------------
# Stale lock recovery – same host, dead PID
# ---------------------------------------------------------------------------


class TestStaleLockRecovery:
    def test_recovers_stale_lock_same_host_dead_pid(
        self, tmp_path: Path, lock_mgr: FileLockManager
    ) -> None:
        """A lock from the same host with a dead PID should be recovered."""
        lock_file = tmp_path / ".ktisma.lock"
        source = tmp_path / "doc.tex"

        # Plant a stale lock with a PID that does not exist
        stale_data = {
            "hostname": socket.gethostname(),
            "pid": 999999999,  # almost certainly not a real PID
            "source": str(source),
            "mode": "build",
            "created": time.time() - 3600,
        }
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text(json.dumps(stale_data))

        # Mock _pid_exists to ensure it returns False for the stale PID
        with patch("ktisma.infra.locks._pid_exists", return_value=False):
            lock_mgr.acquire(lock_file, source, "build")

        # The lock should now be held by our process
        data = json.loads(lock_file.read_text())
        assert data["pid"] == os.getpid()

    def test_stale_lock_replaced_with_new_data(
        self, tmp_path: Path, lock_mgr: FileLockManager
    ) -> None:
        lock_file = tmp_path / ".ktisma.lock"
        source = tmp_path / "doc.tex"

        stale_data = {
            "hostname": socket.gethostname(),
            "pid": 999999999,
            "source": "/old/source.tex",
            "mode": "watch",
            "created": time.time() - 7200,
        }
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text(json.dumps(stale_data))

        with patch("ktisma.infra.locks._pid_exists", return_value=False):
            lock_mgr.acquire(lock_file, source, "build")

        data = json.loads(lock_file.read_text())
        assert data["source"] == str(source)
        assert data["mode"] == "build"
        assert data["pid"] == os.getpid()


# ---------------------------------------------------------------------------
# Contention on live lock
# ---------------------------------------------------------------------------


class TestLiveContention:
    def test_live_lock_same_host_raises(
        self, tmp_path: Path, lock_mgr: FileLockManager
    ) -> None:
        """A lock from the same host with a live PID should raise LockContention."""
        lock_file = tmp_path / ".ktisma.lock"
        source = tmp_path / "doc.tex"

        live_data = {
            "hostname": socket.gethostname(),
            "pid": os.getpid(),  # our own PID, definitely alive
            "source": str(source),
            "mode": "build",
            "created": time.time(),
        }
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text(json.dumps(live_data))

        with pytest.raises(LockContention) as exc_info:
            lock_mgr.acquire(lock_file, source, "build")
        assert "lock" in str(exc_info.value).lower() or "held" in str(exc_info.value).lower()

    def test_lock_from_different_host_raises(
        self, tmp_path: Path, lock_mgr: FileLockManager
    ) -> None:
        """A lock from a different host should raise LockContention (cannot recover)."""
        lock_file = tmp_path / ".ktisma.lock"
        source = tmp_path / "doc.tex"

        remote_data = {
            "hostname": "remote-server-xyz.example.com",
            "pid": 12345,
            "source": str(source),
            "mode": "build",
            "created": time.time(),
        }
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text(json.dumps(remote_data))

        with pytest.raises(LockContention) as exc_info:
            lock_mgr.acquire(lock_file, source, "build")
        assert "remote-server-xyz" in str(exc_info.value)

    def test_contention_message_includes_owner_info(
        self, tmp_path: Path, lock_mgr: FileLockManager
    ) -> None:
        lock_file = tmp_path / ".ktisma.lock"
        source = tmp_path / "doc.tex"

        existing_data = {
            "hostname": "build-machine",
            "pid": 42,
            "source": "/some/paper.tex",
            "mode": "watch",
            "created": time.time(),
        }
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text(json.dumps(existing_data))

        with pytest.raises(LockContention) as exc_info:
            lock_mgr.acquire(lock_file, source, "build")
        msg = str(exc_info.value)
        assert "42" in msg
        assert "build-machine" in msg
        assert "watch" in msg

    def test_unreadable_lock_raises_contention(
        self, tmp_path: Path, lock_mgr: FileLockManager
    ) -> None:
        """A lock file that cannot be parsed as JSON should raise LockContention."""
        lock_file = tmp_path / ".ktisma.lock"
        source = tmp_path / "doc.tex"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text("this is not json")

        with pytest.raises(LockContention) as exc_info:
            lock_mgr.acquire(lock_file, source, "build")
        assert "cannot be read" in str(exc_info.value).lower() or "remove" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# _pid_exists helper
# ---------------------------------------------------------------------------


class TestPidExists:
    def test_current_pid_exists(self) -> None:
        assert _pid_exists(os.getpid()) is True

    def test_zero_pid_does_not_exist(self) -> None:
        assert _pid_exists(0) is False

    def test_negative_pid_does_not_exist(self) -> None:
        assert _pid_exists(-1) is False

    def test_nonexistent_pid(self) -> None:
        """A very large PID should not exist."""
        # Use a PID that's extremely unlikely to exist
        with patch("os.kill", side_effect=ProcessLookupError):
            assert _pid_exists(999999999) is False

    def test_permission_error_means_exists(self) -> None:
        """PermissionError means the process exists but we cannot signal it."""
        with patch("os.kill", side_effect=PermissionError):
            assert _pid_exists(12345) is True


# ---------------------------------------------------------------------------
# Mocked hostname/PID scenarios
# ---------------------------------------------------------------------------


class TestMockedScenarios:
    def test_stale_lock_with_mocked_hostname_and_pid(
        self, tmp_path: Path, lock_mgr: FileLockManager
    ) -> None:
        """Use mocked hostname and PID to verify stale detection logic."""
        lock_file = tmp_path / ".ktisma.lock"
        source = tmp_path / "doc.tex"

        stale_data = {
            "hostname": "test-host",
            "pid": 55555,
            "source": str(source),
            "mode": "build",
            "created": time.time() - 1000,
        }
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text(json.dumps(stale_data))

        with (
            patch("socket.gethostname", return_value="test-host"),
            patch("ktisma.infra.locks._pid_exists", return_value=False),
            patch("os.getpid", return_value=99999),
        ):
            lock_mgr.acquire(lock_file, source, "build")

        data = json.loads(lock_file.read_text())
        # PID in the new lock should be whatever os.getpid() returned at write time
        assert data["hostname"] == "test-host"

    def test_contention_with_mocked_hostname_live_pid(
        self, tmp_path: Path, lock_mgr: FileLockManager
    ) -> None:
        """Same host, live PID = genuine contention."""
        lock_file = tmp_path / ".ktisma.lock"
        source = tmp_path / "doc.tex"

        existing_data = {
            "hostname": "test-host",
            "pid": 77777,
            "source": str(source),
            "mode": "build",
            "created": time.time(),
        }
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.write_text(json.dumps(existing_data))

        with (
            patch("socket.gethostname", return_value="test-host"),
            patch("ktisma.infra.locks._pid_exists", return_value=True),
        ):
            with pytest.raises(LockContention):
                lock_mgr.acquire(lock_file, source, "build")


# ---------------------------------------------------------------------------
# Acquire-release cycle
# ---------------------------------------------------------------------------


class TestAcquireReleaseCycle:
    def test_acquire_release_reacquire(
        self, tmp_path: Path, lock_mgr: FileLockManager
    ) -> None:
        """After release, the same lock can be re-acquired."""
        lock_file = tmp_path / ".ktisma.lock"
        source = tmp_path / "doc.tex"

        lock_mgr.acquire(lock_file, source, "build")
        lock_mgr.release(lock_file)
        lock_mgr.acquire(lock_file, source, "watch")

        data = json.loads(lock_file.read_text())
        assert data["mode"] == "watch"
