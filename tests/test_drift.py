"""Tests for portwatch.drift and portwatch.commands.drift_cmd."""

from __future__ import annotations

import argparse
import json
from unittest.mock import patch

import pytest

from portwatch.drift import DriftResult, detect_drift
from portwatch.scanner import PortEntry


def _e(port: int, proto: str = "tcp", process: str | None = "svc") -> PortEntry:
    return PortEntry(port=port, proto=proto, address="0.0.0.0", process=process)


# ---------------------------------------------------------------------------
# DriftResult
# ---------------------------------------------------------------------------

class TestDriftResult:
    def test_clean_when_empty(self):
        r = DriftResult()
        assert r.is_clean

    def test_not_clean_when_added(self):
        r = DriftResult(added=frozenset([_e(8080)]))
        assert not r.is_clean

    def test_not_clean_when_removed(self):
        r = DriftResult(removed=frozenset([_e(22)]))
        assert not r.is_clean

    def test_summary_clean(self):
        assert DriftResult().summary() == "No drift detected."

    def test_summary_added(self):
        r = DriftResult(added=frozenset([_e(8080)]))
        assert "+1 opened" in r.summary()
        assert "8080" in r.summary()

    def test_summary_removed(self):
        r = DriftResult(removed=frozenset([_e(22)]))
        assert "-1 closed" in r.summary()
        assert "22" in r.summary()

    def test_to_dict_keys(self):
        r = DriftResult(added=frozenset([_e(9000)]), removed=frozenset([_e(22)]))
        d = r.to_dict()
        assert "added" in d and "removed" in d and "clean" in d
        assert 9000 in d["added"]
        assert 22 in d["removed"]
        assert d["clean"] is False


# ---------------------------------------------------------------------------
# detect_drift
# ---------------------------------------------------------------------------

class TestDetectDrift:
    def test_no_change_is_clean(self):
        ports = {_e(22), _e(80)}
        result = detect_drift(ports, ports)
        assert result.is_clean

    def test_new_port_detected_as_added(self):
        ref = {_e(22)}
        cur = {_e(22), _e(8080)}
        result = detect_drift(ref, cur)
        assert any(e.port == 8080 for e in result.added)
        assert not result.removed

    def test_closed_port_detected_as_removed(self):
        ref = {_e(22), _e(80)}
        cur = {_e(22)}
        result = detect_drift(ref, cur)
        assert any(e.port == 80 for e in result.removed)
        assert not result.added

    def test_proto_distinguishes_ports(self):
        ref = {_e(53, proto="tcp")}
        cur = {_e(53, proto="udp")}
        result = detect_drift(ref, cur)
        assert result.added and result.removed


# ---------------------------------------------------------------------------
# drift_cmd
# ---------------------------------------------------------------------------

def _args(**kwargs) -> argparse.Namespace:
    defaults = {
        "baseline": ".portwatch_baseline.json",
        "json": False,
        "fail_on_drift": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_drift_cmd_returns_1_when_baseline_missing(tmp_path):
    from portwatch.commands.drift_cmd import cmd_drift
    args = _args(baseline=str(tmp_path / "no_baseline.json"))
    assert cmd_drift(args) == 1


def test_drift_cmd_returns_0_on_clean(tmp_path):
    from portwatch.baseline import save_baseline
    from portwatch.commands.drift_cmd import cmd_drift

    bl = tmp_path / "baseline.json"
    ports = [_e(22)]
    save_baseline(ports, str(bl))

    with patch("portwatch.commands.drift_cmd.scan_ports", return_value=ports):
        assert cmd_drift(_args(baseline=str(bl))) == 0


def test_drift_cmd_returns_2_on_drift_with_fail_flag(tmp_path):
    from portwatch.baseline import save_baseline
    from portwatch.commands.drift_cmd import cmd_drift

    bl = tmp_path / "baseline.json"
    save_baseline([_e(22)], str(bl))

    with patch("portwatch.commands.drift_cmd.scan_ports", return_value=[_e(22), _e(9000)]):
        assert cmd_drift(_args(baseline=str(bl), fail_on_drift=True)) == 2


def test_drift_cmd_json_output(tmp_path, capsys):
    from portwatch.baseline import save_baseline
    from portwatch.commands.drift_cmd import cmd_drift

    bl = tmp_path / "baseline.json"
    save_baseline([_e(22)], str(bl))

    with patch("portwatch.commands.drift_cmd.scan_ports", return_value=[_e(22), _e(443)]):
        cmd_drift(_args(baseline=str(bl), json=True))

    out = capsys.readouterr().out
    data = json.loads(out)
    assert "added" in data
    assert 443 in data["added"]
