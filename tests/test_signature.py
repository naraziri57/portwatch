"""Tests for portwatch.signature."""

import pytest

from portwatch.scanner import PortEntry
from portwatch.signature import (
    PortSignature,
    SignatureChange,
    build_signature,
    detect_signature_changes,
)


def _entry(port=80, proto="tcp", address="0.0.0.0", process="nginx") -> PortEntry:
    return PortEntry(port=port, proto=proto, address=address, process=process)


# ---------------------------------------------------------------------------
# PortSignature
# ---------------------------------------------------------------------------

class TestPortSignature:
    def test_str_includes_port_and_proto(self):
        e = _entry()
        sig = build_signature(e)
        assert "tcp" in str(sig)
        assert "80" in str(sig)

    def test_str_unknown_process(self):
        e = _entry(process=None)
        sig = build_signature(e)
        assert "<unknown>" in str(sig)

    def test_to_dict_roundtrip(self):
        e = _entry()
        sig = build_signature(e)
        restored = PortSignature.from_dict(sig.to_dict())
        assert restored == sig

    def test_to_dict_has_expected_keys(self):
        sig = build_signature(_entry())
        d = sig.to_dict()
        assert set(d) == {"port", "proto", "address", "process", "digest"}

    def test_digest_is_deterministic(self):
        e = _entry()
        assert build_signature(e).digest == build_signature(e).digest

    def test_different_process_yields_different_digest(self):
        a = build_signature(_entry(process="nginx"))
        b = build_signature(_entry(process="apache2"))
        assert a.digest != b.digest

    def test_different_address_yields_different_digest(self):
        a = build_signature(_entry(address="0.0.0.0"))
        b = build_signature(_entry(address="127.0.0.1"))
        assert a.digest != b.digest


# ---------------------------------------------------------------------------
# detect_signature_changes
# ---------------------------------------------------------------------------

class TestDetectSignatureChanges:
    def test_no_changes_when_identical(self):
        e = _entry()
        known = {(e.port, e.proto): build_signature(e)}
        assert detect_signature_changes(known, [e]) == []

    def test_detects_process_change(self):
        original = _entry(process="nginx")
        updated = _entry(process="apache2")
        known = {(original.port, original.proto): build_signature(original)}
        changes = detect_signature_changes(known, [updated])
        assert len(changes) == 1
        assert "process" in changes[0].changed_fields

    def test_detects_address_change(self):
        original = _entry(address="0.0.0.0")
        updated = _entry(address="127.0.0.1")
        known = {(original.port, original.proto): build_signature(original)}
        changes = detect_signature_changes(known, [updated])
        assert len(changes) == 1
        assert "address" in changes[0].changed_fields

    def test_new_port_not_in_known_ignored(self):
        known = {}  # no prior knowledge
        changes = detect_signature_changes(known, [_entry()])
        assert changes == []

    def test_multiple_entries_only_changed_reported(self):
        stable = _entry(port=443, process="nginx")
        changed = _entry(port=80, process="nginx")
        updated = _entry(port=80, process="apache2")
        known = {
            (stable.port, stable.proto): build_signature(stable),
            (changed.port, changed.proto): build_signature(changed),
        }
        result = detect_signature_changes(known, [stable, updated])
        assert len(result) == 1
        assert result[0].port == 80

    def test_summary_mentions_port(self):
        original = _entry(process="nginx")
        updated = _entry(process="apache2")
        known = {(original.port, original.proto): build_signature(original)}
        change = detect_signature_changes(known, [updated])[0]
        assert "80" in change.summary()
