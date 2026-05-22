"""Tests for portwatch.fingerprint."""

from __future__ import annotations

import pytest

from portwatch.scanner import PortEntry
from portwatch.fingerprint import (
    Fingerprint,
    fingerprint_entry,
    fingerprint_all,
    changed_fingerprints,
    _compute_digest,
)


def _entry(port: int = 8080, proto: str = "tcp", process: str | None = "nginx") -> PortEntry:
    return PortEntry(port=port, proto=proto, process=process)


class TestFingerprint:
    def test_to_dict_contains_all_keys(self):
        fp = Fingerprint(port=80, proto="tcp", process="nginx", digest="abc123def456")
        d = fp.to_dict()
        assert d["port"] == 80
        assert d["proto"] == "tcp"
        assert d["process"] == "nginx"
        assert d["digest"] == "abc123def456"

    def test_from_dict_roundtrip(self):
        fp = Fingerprint(port=443, proto="tcp", process="apache", digest="deadbeef1234")
        assert Fingerprint.from_dict(fp.to_dict()) == fp

    def test_str_contains_port_and_process(self):
        fp = Fingerprint(port=22, proto="tcp", process="sshd", digest="aabbcc112233")
        s = str(fp)
        assert "22" in s
        assert "sshd" in s
        assert "aabbcc112233" in s

    def test_frozen(self):
        fp = Fingerprint(port=80, proto="tcp", process="nginx", digest="abc")
        with pytest.raises(Exception):
            fp.port = 9999  # type: ignore[misc]


class TestComputeDigest:
    def test_digest_is_12_chars(self):
        entry = _entry()
        assert len(_compute_digest(entry)) == 12

    def test_same_entry_same_digest(self):
        e1 = _entry()
        e2 = _entry()
        assert _compute_digest(e1) == _compute_digest(e2)

    def test_different_process_different_digest(self):
        e1 = _entry(process="nginx")
        e2 = _entry(process="apache")
        assert _compute_digest(e1) != _compute_digest(e2)

    def test_none_process_treated_as_empty_string(self):
        e1 = _entry(process=None)
        e2 = _entry(process="")
        assert _compute_digest(e1) == _compute_digest(e2)


class TestFingerprintEntry:
    def test_returns_fingerprint_instance(self):
        fp = fingerprint_entry(_entry())
        assert isinstance(fp, Fingerprint)

    def test_port_and_proto_match(self):
        entry = _entry(port=3306, proto="tcp")
        fp = fingerprint_entry(entry)
        assert fp.port == 3306
        assert fp.proto == "tcp"


class TestFingerprintAll:
    def test_returns_dict_keyed_by_proto_port(self):
        entries = [_entry(port=80), _entry(port=443)]
        result = fingerprint_all(entries)
        assert ("tcp", 80) in result
        assert ("tcp", 443) in result

    def test_empty_input_returns_empty_dict(self):
        assert fingerprint_all([]) == {}


class TestChangedFingerprints:
    def test_no_changes_when_identical(self):
        entries = [_entry(port=80)]
        old = fingerprint_all(entries)
        new = fingerprint_all(entries)
        assert changed_fingerprints(old, new) == []

    def test_detects_process_change(self):
        old_entry = _entry(port=80, process="nginx")
        new_entry = _entry(port=80, process="apache")
        old = fingerprint_all([old_entry])
        new = fingerprint_all([new_entry])
        changes = changed_fingerprints(old, new)
        assert len(changes) == 1
        old_fp, new_fp = changes[0]
        assert old_fp.process == "nginx"
        assert new_fp.process == "apache"

    def test_new_port_not_reported_as_change(self):
        old = fingerprint_all([_entry(port=80)])
        new = fingerprint_all([_entry(port=80), _entry(port=443)])
        assert changed_fingerprints(old, new) == []
