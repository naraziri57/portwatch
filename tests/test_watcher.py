"""Tests for portwatch.watcher."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from portwatch.scanner import PortEntry
from portwatch.alerter import Alerter, ChangeEvent
from portwatch.watcher import Watcher


@pytest.fixture()
def snapshot_file(tmp_path: Path) -> Path:
    return tmp_path / "snapshot.json"


@pytest.fixture()
def sample_ports() -> frozenset[PortEntry]:
    return frozenset([
        PortEntry(proto="tcp", local_addr="0.0.0.0", port=22, pid=1, process="sshd"),
        PortEntry(proto="tcp", local_addr="0.0.0.0", port=80, pid=2, process="nginx"),
    ])


def _make_watcher(snapshot_file: Path, ports, alerter=None) -> tuple[Watcher, MagicMock]:
    mock_alerter = alerter or MagicMock(spec=Alerter)
    w = Watcher(snapshot_path=snapshot_file, interval=1, alerter=mock_alerter)
    return w, mock_alerter


class TestWatcherFirstRun:
    def test_no_events_on_first_run(self, snapshot_file, sample_ports):
        with patch("portwatch.watcher.scan_ports", return_value=sample_ports):
            w, alerter = _make_watcher(snapshot_file, sample_ports)
            events = w.run_once()

        assert events == []
        alerter.emit.assert_not_called()

    def test_snapshot_created_on_first_run(self, snapshot_file, sample_ports):
        with patch("portwatch.watcher.scan_ports", return_value=sample_ports):
            w, _ = _make_watcher(snapshot_file, sample_ports)
            w.run_once()

        assert snapshot_file.exists()
        data = json.loads(snapshot_file.read_text())
        assert len(data) == 2


class TestWatcherSubsequentRuns:
    def test_opened_port_detected(self, snapshot_file, sample_ports):
        new_port = PortEntry(proto="tcp", local_addr="0.0.0.0", port=8080, pid=99, process="app")
        extended = sample_ports | {new_port}

        with patch("portwatch.watcher.scan_ports", return_value=sample_ports):
            w, alerter = _make_watcher(snapshot_file, sample_ports)
            w.run_once()  # baseline

        with patch("portwatch.watcher.scan_ports", return_value=extended):
            events = w.run_once()

        assert len(events) == 1
        assert events[0].kind == "opened"
        assert events[0].port == new_port
        alerter.emit.assert_called_once()

    def test_closed_port_detected(self, snapshot_file, sample_ports):
        port_to_close = next(iter(sample_ports))
        reduced = sample_ports - {port_to_close}

        with patch("portwatch.watcher.scan_ports", return_value=sample_ports):
            w, alerter = _make_watcher(snapshot_file, sample_ports)
            w.run_once()

        with patch("portwatch.watcher.scan_ports", return_value=reduced):
            events = w.run_once()

        assert len(events) == 1
        assert events[0].kind == "closed"
        alerter.emit.assert_called_once()

    def test_no_events_when_unchanged(self, snapshot_file, sample_ports):
        with patch("portwatch.watcher.scan_ports", return_value=sample_ports):
            w, alerter = _make_watcher(snapshot_file, sample_ports)
            w.run_once()
            events = w.run_once()

        assert events == []
        alerter.emit.assert_not_called()
