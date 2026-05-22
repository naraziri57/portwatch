"""Tests for portwatch.commands.tags_cmd."""
import argparse
import json
from unittest.mock import patch

import pytest

from portwatch.scanner import PortEntry
from portwatch.commands.tags_cmd import cmd_tags, register_subcommands


def _entry(port=80, proto="tcp", process="nginx"):
    return PortEntry(port=port, proto=proto, local_addr="0.0.0.0", process=process)


def _args(rules_file=None):
    ns = argparse.Namespace()
    ns.rules_file = rules_file
    return ns


class TestCmdTags:
    def test_returns_zero_on_success(self):
        with patch("portwatch.commands.tags_cmd.scan_ports", return_value=[_entry()]):
            assert cmd_tags(_args()) == 0

    def test_returns_one_on_scan_failure(self):
        with patch("portwatch.commands.tags_cmd.scan_ports", side_effect=RuntimeError("fail")):
            assert cmd_tags(_args()) == 1

    def test_no_ports_prints_message(self, capsys):
        with patch("portwatch.commands.tags_cmd.scan_ports", return_value=[]):
            rc = cmd_tags(_args())
        assert rc == 0
        assert "no open ports" in capsys.readouterr().out

    def test_output_contains_port(self, capsys):
        with patch("portwatch.commands.tags_cmd.scan_ports", return_value=[_entry(port=8080)]):
            cmd_tags(_args())
        assert "8080" in capsys.readouterr().out

    def test_tags_applied_from_rules_file(self, tmp_path, capsys):
        rules_file = tmp_path / "rules.json"
        rules_file.write_text(json.dumps({"rules": [{"tag": "web", "port": 80}]}))
        with patch("portwatch.commands.tags_cmd.scan_ports", return_value=[_entry(port=80)]):
            rc = cmd_tags(_args(rules_file=str(rules_file)))
        assert rc == 0
        assert "web" in capsys.readouterr().out

    def test_no_matching_tag_shows_none(self, tmp_path, capsys):
        rules_file = tmp_path / "rules.json"
        rules_file.write_text(json.dumps({"rules": [{"tag": "db", "port": 5432}]}))
        with patch("portwatch.commands.tags_cmd.scan_ports", return_value=[_entry(port=80)]):
            cmd_tags(_args(rules_file=str(rules_file)))
        assert "(none)" in capsys.readouterr().out

    def test_bad_rules_file_returns_one(self):
        with patch("portwatch.commands.tags_cmd.scan_ports", return_value=[_entry()]):
            assert cmd_tags(_args(rules_file="/nonexistent/rules.json")) == 1

    def test_register_adds_tags_subcommand(self):
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers()
        register_subcommands(sub)
        ns = parser.parse_args(["tags"])
        assert hasattr(ns, "func")
