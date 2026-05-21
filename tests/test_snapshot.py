"""Tests for portwatch.snapshot."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from portwatch.scanner import PortEntry
from portwatch.snapshot import diff_snapshots, load_snapshot, save_snapshot


@pytest.fixture()
def tmp_snapshot(tmp_path: Path) -> Path:
    return tmp_path / "snapshot.json"


@pytest.fixture()
def sample_ports() -> set[PortEntry]:
    return {
        PortEntry(proto="tcp", local_addr="0.0.0.0", local_port=22, pid=1001, process="sshd"),
        PortEntry(proto="tcp", local_addr="0.0.0.0", local_port=80, pid=1234, process="nginx"),
    }


def test_save_creates_file(tmp_snapshot, sample_ports):
    save_snapshot(sample_ports, tmp_snapshot)
    assert tmp_snapshot.exists()


def test_save_valid_json(tmp_snapshot, sample_ports):
    save_snapshot(sample_ports, tmp_snapshot)
    data = json.loads(tmp_snapshot.read_text())
    assert "timestamp" in data
    assert "ports" in data
    assert len(data["ports"]) == 2


def test_roundtrip(tmp_snapshot, sample_ports):
    save_snapshot(sample_ports, tmp_snapshot)
    result = load_snapshot(tmp_snapshot)
    assert result is not None
    ts, loaded = result
    assert isinstance(ts, datetime)
    assert loaded == sample_ports


def test_load_missing_returns_none(tmp_snapshot):
    assert load_snapshot(tmp_snapshot) is None


def test_diff_appeared_disappeared():
    old = {
        PortEntry(proto="tcp", local_addr="0.0.0.0", local_port=22, pid=1, process="sshd"),
        PortEntry(proto="tcp", local_addr="0.0.0.0", local_port=8080, pid=2, process="old-app"),
    }
    new = {
        PortEntry(proto="tcp", local_addr="0.0.0.0", local_port=22, pid=1, process="sshd"),
        PortEntry(proto="tcp", local_addr="0.0.0.0", local_port=443, pid=3, process="nginx"),
    }
    appeared, disappeared = diff_snapshots(old, new)
    assert any(p.local_port == 443 for p in appeared)
    assert any(p.local_port == 8080 for p in disappeared)


def test_diff_no_changes(sample_ports):
    appeared, disappeared = diff_snapshots(sample_ports, sample_ports)
    assert appeared == set()
    assert disappeared == set()
