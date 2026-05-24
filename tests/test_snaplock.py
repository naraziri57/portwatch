"""Tests for portwatch.snaplock."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from portwatch.snaplock import LockInfo, LockTimeout, acquire_lock, is_locked


@pytest.fixture()
def snap(tmp_path: Path) -> Path:
    return tmp_path / "snapshot.json"


# ---------------------------------------------------------------------------
# LockInfo
# ---------------------------------------------------------------------------

class TestLockInfo:
    def test_age_increases_over_time(self, snap: Path) -> None:
        info = LockInfo(path=snap)
        time.sleep(0.05)
        assert info.age_seconds() >= 0.04

    def test_to_dict_has_required_keys(self, snap: Path) -> None:
        info = LockInfo(path=snap)
        d = info.to_dict()
        assert "path" in d
        assert "pid" in d
        assert "age_seconds" in d

    def test_pid_matches_current_process(self, snap: Path) -> None:
        import os
        info = LockInfo(path=snap)
        assert info.pid == os.getpid()


# ---------------------------------------------------------------------------
# acquire_lock — basic behaviour
# ---------------------------------------------------------------------------

def test_acquire_yields_lock_info(snap: Path) -> None:
    with acquire_lock(snap) as info:
        assert isinstance(info, LockInfo)


def test_lock_file_removed_after_context(snap: Path) -> None:
    with acquire_lock(snap):
        pass
    assert not is_locked(snap)


def test_lock_file_removed_on_exception(snap: Path) -> None:
    with pytest.raises(RuntimeError):
        with acquire_lock(snap):
            raise RuntimeError("boom")
    assert not is_locked(snap)


def test_is_locked_true_inside_context(snap: Path) -> None:
    with acquire_lock(snap):
        assert is_locked(snap)


def test_is_locked_false_outside_context(snap: Path) -> None:
    assert not is_locked(snap)


# ---------------------------------------------------------------------------
# acquire_lock — contention
# ---------------------------------------------------------------------------

def test_timeout_raises_when_already_locked(snap: Path) -> None:
    results: list[Exception] = []

    def _hold() -> None:
        with acquire_lock(snap, timeout=2.0):
            time.sleep(0.5)

    holder = threading.Thread(target=_hold, daemon=True)
    holder.start()
    time.sleep(0.05)  # let holder grab the lock

    with pytest.raises(LockTimeout):
        acquire_lock(snap, timeout=0.1).__enter__()

    holder.join(timeout=1.0)


def test_sequential_locks_succeed(snap: Path) -> None:
    with acquire_lock(snap):
        pass
    with acquire_lock(snap):
        pass  # should not raise
