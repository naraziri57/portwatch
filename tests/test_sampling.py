"""Unit tests for portwatch.sampling."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from portwatch.sampling import SamplePoint, SampleStore
from portwatch.scanner import PortEntry


def _entry(port: int, proto: str = "tcp", process: str = "test") -> PortEntry:
    return PortEntry(port=port, proto=proto, address="0.0.0.0", process=process)


# ---------------------------------------------------------------------------
# SamplePoint
# ---------------------------------------------------------------------------

class TestSamplePoint:
    def test_capture_sets_port_count(self):
        ports = [_entry(80), _entry(443)]
        sp = SamplePoint.capture(ports)
        assert sp.port_count == 2

    def test_capture_timestamp_recent(self):
        before = time.time()
        sp = SamplePoint.capture([])
        assert sp.timestamp >= before

    def test_to_dict_roundtrip(self):
        sp = SamplePoint.capture([_entry(22)])
        d = sp.to_dict()
        sp2 = SamplePoint.from_dict(d)
        assert sp2.port_count == sp.port_count
        assert sp2.timestamp == pytest.approx(sp.timestamp)

    def test_ports_contain_expected_keys(self):
        sp = SamplePoint.capture([_entry(8080, proto="udp", process="svc")])
        assert sp.ports[0] == {"port": 8080, "proto": "udp", "process": "svc"}


# ---------------------------------------------------------------------------
# SampleStore
# ---------------------------------------------------------------------------

@pytest.fixture()
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "samples.json"


class TestSampleStore:
    def test_zero_max_samples_raises(self, store_path):
        with pytest.raises(ValueError):
            SampleStore(path=store_path, max_samples=0)

    def test_record_creates_file(self, store_path):
        s = SampleStore(path=store_path)
        s.record([])
        assert store_path.exists()

    def test_record_returns_sample_point(self, store_path):
        s = SampleStore(path=store_path)
        sp = s.record([_entry(80)])
        assert isinstance(sp, SamplePoint)
        assert sp.port_count == 1

    def test_multiple_records_accumulate(self, store_path):
        s = SampleStore(path=store_path)
        s.record([_entry(80)])
        s.record([_entry(443)])
        assert len(s.all_samples()) == 2

    def test_max_samples_respected(self, store_path):
        s = SampleStore(path=store_path, max_samples=3)
        for i in range(5):
            s.record([_entry(i + 1)])
        assert len(s.all_samples()) == 3

    def test_latest_returns_last_recorded(self, store_path):
        s = SampleStore(path=store_path)
        s.record([_entry(80)])
        s.record([_entry(443), _entry(8080)])
        assert s.latest().port_count == 2

    def test_average_port_count(self, store_path):
        s = SampleStore(path=store_path)
        s.record([_entry(80)])
        s.record([_entry(443), _entry(8080)])
        assert s.average_port_count() == pytest.approx(1.5)

    def test_persists_across_instances(self, store_path):
        s1 = SampleStore(path=store_path)
        s1.record([_entry(22)])
        s2 = SampleStore(path=store_path)
        assert len(s2.all_samples()) == 1

    def test_average_empty_returns_zero(self, store_path):
        s = SampleStore(path=store_path)
        assert s.average_port_count() == 0.0
