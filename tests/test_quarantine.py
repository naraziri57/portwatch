"""Tests for portwatch.quarantine."""

import json
import time

import pytest

from portwatch.quarantine import Quarantine, QuarantineEntry
from portwatch.scanner import PortEntry


def _entry(port=8080, proto="tcp", process="nginx") -> PortEntry:
    return PortEntry(port=port, proto=proto, address="0.0.0.0", process=process)


def _qe(port=8080, proto="tcp", process=None, expires_at=0, reason="test") -> QuarantineEntry:
    return QuarantineEntry(port=port, proto=proto, process=process, expires_at=expires_at, reason=reason)


class TestQuarantineEntryMatching:
    def test_matches_port_and_proto(self):
        qe = _qe(port=8080, proto="tcp")
        assert qe.matches(_entry(port=8080, proto="tcp"))

    def test_no_match_wrong_port(self):
        qe = _qe(port=9090, proto="tcp")
        assert not qe.matches(_entry(port=8080, proto="tcp"))

    def test_no_match_wrong_proto(self):
        qe = _qe(port=8080, proto="udp")
        assert not qe.matches(_entry(port=8080, proto="tcp"))

    def test_matches_with_process_filter(self):
        qe = _qe(port=8080, proto="tcp", process="nginx")
        assert qe.matches(_entry(port=8080, proto="tcp", process="nginx"))

    def test_no_match_wrong_process(self):
        qe = _qe(port=8080, proto="tcp", process="apache")
        assert not qe.matches(_entry(port=8080, proto="tcp", process="nginx"))

    def test_none_process_matches_any_process(self):
        qe = _qe(port=8080, proto="tcp", process=None)
        assert qe.matches(_entry(port=8080, proto="tcp", process="anything"))


class TestQuarantineEntryExpiry:
    def test_never_expires_when_zero(self):
        qe = _qe(expires_at=0)
        assert not qe.is_expired()

    def test_expired_in_the_past(self):
        qe = _qe(expires_at=time.time() - 10)
        assert qe.is_expired()

    def test_not_expired_in_the_future(self):
        qe = _qe(expires_at=time.time() + 3600)
        assert not qe.is_expired()


class TestQuarantine:
    def test_is_quarantined_returns_true(self):
        q = Quarantine()
        q.add(_qe(port=8080, proto="tcp"))
        assert q.is_quarantined(_entry(port=8080, proto="tcp"))

    def test_is_quarantined_returns_false_no_match(self):
        q = Quarantine()
        q.add(_qe(port=9090, proto="tcp"))
        assert not q.is_quarantined(_entry(port=8080, proto="tcp"))

    def test_expired_entry_auto_purged(self):
        q = Quarantine()
        q.add(_qe(port=8080, proto="tcp", expires_at=time.time() - 1))
        assert not q.is_quarantined(_entry(port=8080, proto="tcp"))

    def test_active_entries_excludes_expired(self):
        q = Quarantine()
        q.add(_qe(port=8080, proto="tcp", expires_at=time.time() - 1))
        q.add(_qe(port=9090, proto="tcp", expires_at=0))
        assert len(q.active_entries()) == 1
        assert q.active_entries()[0].port == 9090

    def test_save_and_load_roundtrip(self, tmp_path):
        p = tmp_path / "quarantine.json"
        q = Quarantine()
        q.add(_qe(port=443, proto="tcp", reason="maintenance"))
        q.save(p)
        q2 = Quarantine.load(p)
        assert len(q2.active_entries()) == 1
        assert q2.active_entries()[0].port == 443
        assert q2.active_entries()[0].reason == "maintenance"

    def test_load_missing_file_returns_empty(self, tmp_path):
        q = Quarantine.load(tmp_path / "nonexistent.json")
        assert q.active_entries() == []

    def test_to_dict_from_dict_roundtrip(self):
        qe = QuarantineEntry(port=22, proto="tcp", process="sshd", expires_at=0, reason="ok")
        restored = QuarantineEntry.from_dict(qe.to_dict())
        assert restored.port == 22
        assert restored.process == "sshd"
        assert restored.reason == "ok"
