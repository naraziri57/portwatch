"""Unit tests for portwatch.checkpoint."""

from __future__ import annotations

import json
import time

import pytest

from portwatch.checkpoint import (
    Checkpoint,
    list_checkpoints,
    load_checkpoint,
    save_checkpoint,
)
from portwatch.scanner import PortEntry


@pytest.fixture()
def sample_ports():
    return [
        PortEntry(port=22, proto="tcp", address="0.0.0.0", process="sshd"),
        PortEntry(port=80, proto="tcp", address="0.0.0.0", process="nginx"),
    ]


@pytest.fixture()
def cp_path(tmp_path):
    return tmp_path / "checkpoint_test.json"


class TestCheckpointSerialisation:
    def test_to_dict_contains_timestamp(self, sample_ports):
        cp = Checkpoint(timestamp=1_000_000.0, ports=sample_ports)
        assert cp.to_dict()["timestamp"] == 1_000_000.0

    def test_to_dict_contains_ports(self, sample_ports):
        cp = Checkpoint(timestamp=1.0, ports=sample_ports)
        assert len(cp.to_dict()["ports"]) == 2

    def test_to_dict_contains_label(self, sample_ports):
        cp = Checkpoint(timestamp=1.0, ports=sample_ports, label="before-deploy")
        assert cp.to_dict()["label"] == "before-deploy"

    def test_roundtrip(self, sample_ports):
        cp = Checkpoint(timestamp=999.5, ports=sample_ports, label="x")
        restored = Checkpoint.from_dict(cp.to_dict())
        assert restored.timestamp == cp.timestamp
        assert restored.label == cp.label
        assert len(restored.ports) == len(cp.ports)
        assert restored.ports[0].port == 22

    def test_from_dict_missing_process(self):
        data = {
            "timestamp": 1.0,
            "label": "",
            "ports": [{"port": 443, "proto": "tcp", "address": "0.0.0.0"}],
        }
        cp = Checkpoint.from_dict(data)
        assert cp.ports[0].process is None


class TestSaveLoadCheckpoint:
    def test_save_creates_file(self, cp_path, sample_ports):
        save_checkpoint(cp_path, sample_ports)
        assert cp_path.exists()

    def test_save_valid_json(self, cp_path, sample_ports):
        save_checkpoint(cp_path, sample_ports)
        data = json.loads(cp_path.read_text())
        assert "timestamp" in data
        assert "ports" in data

    def test_load_returns_checkpoint(self, cp_path, sample_ports):
        save_checkpoint(cp_path, sample_ports, label="test")
        cp = load_checkpoint(cp_path)
        assert cp is not None
        assert cp.label == "test"
        assert len(cp.ports) == 2

    def test_load_missing_returns_none(self, tmp_path):
        assert load_checkpoint(tmp_path / "nope.json") is None

    def test_save_timestamp_is_recent(self, cp_path, sample_ports):
        before = time.time()
        cp = save_checkpoint(cp_path, sample_ports)
        assert cp.timestamp >= before


class TestListCheckpoints:
    def test_empty_directory_returns_empty(self, tmp_path):
        assert list_checkpoints(tmp_path) == []

    def test_returns_sorted_checkpoints(self, tmp_path, sample_ports):
        for label in ("a", "b", "c"):
            save_checkpoint(tmp_path / f"checkpoint_{label}.json", sample_ports, label=label)
        cps = list_checkpoints(tmp_path)
        assert [c.label for c in cps] == ["a", "b", "c"]

    def test_ignores_non_checkpoint_files(self, tmp_path, sample_ports):
        (tmp_path / "other.json").write_text("{}")
        save_checkpoint(tmp_path / "checkpoint_x.json", sample_ports)
        assert len(list_checkpoints(tmp_path)) == 1
