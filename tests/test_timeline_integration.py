"""Integration tests: timeline persists and queries correctly end-to-end."""

from __future__ import annotations

from datetime import datetime, timezone

from portwatch.scanner import PortEntry
from portwatch.alerter import ChangeEvent
from portwatch.timeline import append_events, load_timeline, query_range


def _pe(port: int, process: str = "svc") -> PortEntry:
    return PortEntry(port=port, proto="tcp", address="0.0.0.0", process=process)


def _ev(kind: str, port: int) -> ChangeEvent:
    return ChangeEvent(kind=kind, entry=_pe(port))


class TestTimelineIntegration:
    def test_events_persist_and_reload(self, tmp_path):
        p = tmp_path / "tl.json"
        append_events(p, [_ev("opened", 80), _ev("opened", 443)])
        loaded = load_timeline(p)
        assert len(loaded) == 2
        ports = {e.port for e in loaded}
        assert ports == {80, 443}

    def test_multiple_appends_accumulate(self, tmp_path):
        p = tmp_path / "tl.json"
        for port in [22, 80, 443, 8080]:
            append_events(p, [_ev("opened", port)])
        assert len(load_timeline(p)) == 4

    def test_query_range_end_to_end(self, tmp_path):
        p = tmp_path / "tl.json"
        append_events(p, [_ev("opened", 80), _ev("closed", 80)])
        entries = load_timeline(p)
        # all entries are recent, so no filtering expected
        result = query_range(
            entries,
            since=datetime(2000, 1, 1, tzinfo=timezone.utc),
        )
        assert len(result) == 2

    def test_kind_roundtrip_preserved(self, tmp_path):
        p = tmp_path / "tl.json"
        append_events(p, [_ev("opened", 22), _ev("closed", 22)])
        kinds = {e.kind for e in load_timeline(p)}
        assert kinds == {"opened", "closed"}

    def test_empty_file_safe(self, tmp_path):
        p = tmp_path / "tl.json"
        assert load_timeline(p) == []
        append_events(p, [])
        assert load_timeline(p) == []
