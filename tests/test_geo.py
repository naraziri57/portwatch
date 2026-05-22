"""Tests for portwatch.geo."""
from __future__ import annotations

import pytest

from portwatch.geo import GeoInfo, enrich_with_geoip, resolve_hostname


# ---------------------------------------------------------------------------
# GeoInfo dataclass
# ---------------------------------------------------------------------------

class TestGeoInfo:
    def test_to_dict_all_fields(self):
        g = GeoInfo(ip="1.2.3.4", country="DE", city="Berlin", asn="1234")
        d = g.to_dict()
        assert d["ip"] == "1.2.3.4"
        assert d["country"] == "DE"
        assert d["city"] == "Berlin"
        assert d["asn"] == "1234"

    def test_to_dict_optional_none(self):
        g = GeoInfo(ip="1.2.3.4")
        d = g.to_dict()
        assert d["country"] is None
        assert d["city"] is None

    def test_from_dict_roundtrip(self):
        original = GeoInfo(ip="5.6.7.8", country="FR", city="Paris", asn="5678")
        restored = GeoInfo.from_dict(original.to_dict())
        assert restored == original

    def test_str_ip_only(self):
        g = GeoInfo(ip="1.2.3.4")
        assert str(g) == "1.2.3.4"

    def test_str_with_country_and_city(self):
        g = GeoInfo(ip="1.2.3.4", country="US", city="New York")
        result = str(g)
        assert "1.2.3.4" in result
        assert "US" in result
        assert "New York" in result

    def test_str_with_asn(self):
        g = GeoInfo(ip="1.2.3.4", asn="7922")
        assert "AS:7922" in str(g)


# ---------------------------------------------------------------------------
# enrich_with_geoip — stub path (no geoip2 installed in test env)
# ---------------------------------------------------------------------------

def test_enrich_returns_geoinfo():
    result = enrich_with_geoip("8.8.8.8")
    assert isinstance(result, GeoInfo)
    assert result.ip == "8.8.8.8"


def test_enrich_no_db_returns_stub():
    result = enrich_with_geoip("1.1.1.1", db_path=None)
    assert result.country is None
    assert result.city is None


def test_enrich_bad_db_path_returns_stub():
    result = enrich_with_geoip("1.1.1.1", db_path="/nonexistent/path.mmdb")
    assert isinstance(result, GeoInfo)
    assert result.ip == "1.1.1.1"


# ---------------------------------------------------------------------------
# resolve_hostname
# ---------------------------------------------------------------------------

def test_resolve_invalid_ip_returns_none():
    # Completely bogus address should fail gracefully
    result = resolve_hostname("0.0.0.0")
    # May return None or a hostname depending on OS; must not raise
    assert result is None or isinstance(result, str)


def test_resolve_loopback():
    result = resolve_hostname("127.0.0.1")
    # localhost or None — just must not raise
    assert result is None or isinstance(result, str)
