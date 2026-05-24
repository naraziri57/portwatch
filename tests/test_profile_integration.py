"""Integration tests: save a profile then check drift against it."""
from __future__ import annotations

from pathlib import Path

from portwatch.profile import PortProfile, diff_profile, load_profile, save_profile
from portwatch.scanner import PortEntry


def _e(port: int, proto: str = "tcp", process: str = "svc") -> PortEntry:
    return PortEntry(port=port, proto=proto, address="0.0.0.0", process=process)


class TestProfileDriftDetection:
    def test_no_drift_when_ports_unchanged(self, tmp_path: Path):
        ports = [_e(80), _e(443)]
        profile = PortProfile(name="baseline", ports=ports)
        save_profile(profile, tmp_path / "baseline.json")
        loaded = load_profile(tmp_path / "baseline.json")
        delta = diff_profile(loaded, ports)
        assert delta["added"] == []
        assert delta["removed"] == []

    def test_new_port_detected_as_added(self, tmp_path: Path):
        original = [_e(80)]
        profile = PortProfile(name="p", ports=original)
        save_profile(profile, tmp_path / "p.json")
        loaded = load_profile(tmp_path / "p.json")
        delta = diff_profile(loaded, [_e(80), _e(9000)])
        assert len(delta["added"]) == 1
        assert delta["added"][0].port == 9000

    def test_closed_port_detected_as_removed(self, tmp_path: Path):
        original = [_e(80), _e(22)]
        profile = PortProfile(name="p", ports=original)
        save_profile(profile, tmp_path / "p.json")
        loaded = load_profile(tmp_path / "p.json")
        delta = diff_profile(loaded, [_e(80)])
        assert len(delta["removed"]) == 1
        assert delta["removed"][0].port == 22

    def test_process_change_counts_as_drift(self, tmp_path: Path):
        original = [PortEntry(port=80, proto="tcp", address="0.0.0.0", process="nginx")]
        profile = PortProfile(name="p", ports=original)
        save_profile(profile, tmp_path / "p.json")
        loaded = load_profile(tmp_path / "p.json")
        current = [PortEntry(port=80, proto="tcp", address="0.0.0.0", process="apache")]
        delta = diff_profile(loaded, current)
        # different process means different PortEntry hash → shows as add+remove
        assert len(delta["added"]) == 1
        assert len(delta["removed"]) == 1

    def test_multiple_profiles_independent(self, tmp_path: Path):
        for name, port in (("web", 80), ("db", 5432)):
            p = PortProfile(name=name, ports=[_e(port)])
            save_profile(p, tmp_path / f"{name}.json")
        web = load_profile(tmp_path / "web.json")
        db = load_profile(tmp_path / "db.json")
        assert web.ports[0].port == 80
        assert db.ports[0].port == 5432
