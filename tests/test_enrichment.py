"""Tests for portwatch.enrichment."""

from __future__ import annotations

import pytest

from portwatch.scanner import PortEntry
from portwatch.alerter import ChangeEvent
from portwatch.tags import TagSet, TagRule
from portwatch.severity import SeverityRule, Level
from portwatch.enrichment import EnrichedEvent, enrich


def _entry(port: int = 8080, proto: str = "tcp", process: str = "nginx") -> PortEntry:
    return PortEntry(port=port, proto=proto, address="127.0.0.1", process=process)


def _event(kind: str = "opened", port: int = 8080) -> ChangeEvent:
    return ChangeEvent(kind=kind, entry=_entry(port=port))


# ---------------------------------------------------------------------------
# EnrichedEvent basics
# ---------------------------------------------------------------------------

class TestEnrichedEventDefaults:
    def test_defaults_have_info_level(self):
        ev = EnrichedEvent(event=_event())
        assert ev.level == Level.INFO

    def test_defaults_empty_tags(self):
        ev = EnrichedEvent(event=_event())
        assert ev.tags == []

    def test_defaults_no_geo(self):
        ev = EnrichedEvent(event=_event())
        assert ev.geo is None

    def test_defaults_no_score(self):
        ev = EnrichedEvent(event=_event())
        assert ev.score is None


# ---------------------------------------------------------------------------
# enrich() pipeline
# ---------------------------------------------------------------------------

class TestEnrichFunction:
    def test_returns_enriched_event(self):
        result = enrich(_event())
        assert isinstance(result, EnrichedEvent)

    def test_score_is_populated(self):
        result = enrich(_event())
        assert result.score is not None

    def test_tags_applied_when_tagset_provided(self):
        rule = TagRule(port=8080, tag="web")
        ts = TagSet(rules=[rule])
        result = enrich(_event(port=8080), tagset=ts)
        assert "web" in result.tags

    def test_no_tags_when_no_match(self):
        rule = TagRule(port=9999, tag="other")
        ts = TagSet(rules=[rule])
        result = enrich(_event(port=8080), tagset=ts)
        assert result.tags == []

    def test_severity_rule_sets_level(self):
        rule = SeverityRule(port=8080, level=Level.HIGH)
        result = enrich(_event(port=8080), severity_rules=[rule])
        assert result.level == Level.HIGH

    def test_unmatched_severity_stays_info(self):
        rule = SeverityRule(port=9999, level=Level.HIGH)
        result = enrich(_event(port=8080), severity_rules=[rule])
        assert result.level == Level.INFO

    def test_geo_skipped_when_flag_false(self):
        result = enrich(_event(), resolve_geo=False)
        assert result.geo is None


# ---------------------------------------------------------------------------
# to_dict / __str__
# ---------------------------------------------------------------------------

class TestEnrichedEventSerialization:
    def test_to_dict_contains_event_key(self):
        result = enrich(_event())
        d = result.to_dict()
        assert "event" in d

    def test_to_dict_contains_level(self):
        result = enrich(_event())
        d = result.to_dict()
        assert "level" in d

    def test_to_dict_tags_list(self):
        rule = TagRule(port=8080, tag="web")
        ts = TagSet(rules=[rule])
        result = enrich(_event(port=8080), tagset=ts)
        assert result.to_dict()["tags"] == ["web"]

    def test_str_contains_level(self):
        result = enrich(_event())
        assert "level=" in str(result)

    def test_str_contains_tags_when_present(self):
        rule = TagRule(port=8080, tag="web")
        ts = TagSet(rules=[rule])
        result = enrich(_event(port=8080), tagset=ts)
        assert "tags=" in str(result)
