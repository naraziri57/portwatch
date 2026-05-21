"""Tests for portwatch.scanner module."""

import pytest
from unittest.mock import patch, MagicMock
from portwatch.scanner import scan_ports, PortEntry, _parse_ss_line


SAMPLE_SS_OUTPUT = """tcp   LISTEN 0  128  0.0.0.0:22   0.0.0.0:*  users:(("sshd",pid=1234,fd=3))
tcp   LISTEN 0  128  0.0.0.0:80   0.0.0.0:*  users:(("nginx",pid=5678,fd=6))
udp   UNCONN 0  0    0.0.0.0:5353 0.0.0.0:*
tcp6  LISTEN 0  128  [::]:443     [::]:*     users:(("nginx",pid=5678,fd=7))
"""


class TestPortEntry:
    def test_str_with_process(self):
        entry = PortEntry(protocol="tcp", port=22, pid=1234, process_name="sshd")
        assert str(entry) == "TCP:22 (sshd/1234)"

    def test_str_without_process(self):
        entry = PortEntry(protocol="udp", port=5353)
        assert str(entry) == "UDP:5353"

    def test_frozen(self):
        entry = PortEntry(protocol="tcp", port=80)
        with pytest.raises(Exception):
            entry.port = 443  # type: ignore

    def test_hashable(self):
        e1 = PortEntry(protocol="tcp", port=80)
        e2 = PortEntry(protocol="tcp", port=80)
        assert e1 == e2
        assert len({e1, e2}) == 1


class TestParseSsLine:
    def test_parse_tcp_with_pid(self):
        line = 'tcp   LISTEN 0  128  0.0.0.0:22   0.0.0.0:*  users:(("sshd",pid=1234,fd=3))'
        entry = _parse_ss_line(line)
        assert entry is not None
        assert entry.protocol == "tcp"
        assert entry.port == 22
        assert entry.pid == 1234
        assert entry.process_name == "sshd"

    def test_parse_udp_no_process(self):
        line = "udp   UNCONN 0  0    0.0.0.0:5353 0.0.0.0:*"
        entry = _parse_ss_line(line)
        assert entry is not None
        assert entry.protocol == "udp"
        assert entry.port == 5353
        assert entry.pid is None

    def test_parse_tcp6_normalized(self):
        line = 'tcp6  LISTEN 0  128  [::]:443     [::]:*     users:(("nginx",pid=5678,fd=7))'
        entry = _parse_ss_line(line)
        assert entry is not None
        assert entry.protocol == "tcp"  # tcp6 -> tcp
        assert entry.port == 443

    def test_parse_invalid_line(self):
        assert _parse_ss_line("") is None
        assert _parse_ss_line("not enough") is None


class TestScanPorts:
    @patch("portwatch.scanner.subprocess.run")
    def test_scan_returns_port_entries(self, mock_run):
        mock_run.return_value = MagicMock(stdout=SAMPLE_SS_OUTPUT, returncode=0)
        ports = scan_ports()
        assert len(ports) >= 3
        port_numbers = {e.port for e in ports}
        assert 22 in port_numbers
        assert 80 in port_numbers
        assert 5353 in port_numbers

    @patch("portwatch.scanner.subprocess.run")
    def test_scan_falls_back_to_netstat(self, mock_run):
        mock_run.side_effect = [FileNotFoundError, MagicMock(stdout="", returncode=0)]
        ports = scan_ports()
        assert isinstance(ports, set)

    @patch("portwatch.scanner.subprocess.run")
    def test_scan_empty_output(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        ports = scan_ports()
        assert ports == set()
