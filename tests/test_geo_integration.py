"""Integration-style tests: GeoInfo round-trips through JSON and str."""
from __future__ import annotations

import json

import pytest

from portwatch.geo import GeoInfo, enrich_with_geoip


class TestGeoInfoSerialization:
    def test_full_roundtrip_via_json(self):
        original = GeoInfo(ip="203.0.113.1", country="JP", city="Tokyo", asn="2497")
        serialized = json.dumps(original.to_dict())
        restored = GeoInfo.from_dict(json.loads(serialized))
        assert restored.ip == original.ip
        assert restored.country == original.country
        assert restored.city == original.city
        assert restored.asn == original.asn

    def test_partial_roundtrip_missing_optional(self):
        original = GeoInfo(ip="198.51.100.5")
        serialized = json.dumps(original.to_dict())
        restored = GeoInfo.from_dict(json.loads(serialized))
        assert restored.ip == "198.51.100.5"
        assert restored.country is None

    def test_str_representation_stable(self):
        g = GeoInfo(ip="1.2.3.4", country="US", city="Denver", asn="701")
        s = str(g)
        # All meaningful parts should appear
        assert "1.2.3.4" in s
        assert "US" in s
        assert "Denver" in s
        assert "AS:701" in s


class TestEnrichPipeline:
    def test_enrich_then_serialize(self):
        info = enrich_with_geoip("8.8.4.4")
        d = info.to_dict()
        assert d["ip"] == "8.8.4.4"
        # Stub path: optional fields are None but keys exist
        assert "country" in d
        assert "city" in d

    def test_multiple_ips_independent(self):
        ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
        results = [enrich_with_geoip(ip) for ip in ips]
        returned_ips = [r.ip for r in results]
        assert returned_ips == ips
