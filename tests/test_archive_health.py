import argparse
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

import pytest

SPEC = importlib.util.spec_from_file_location(
    "archive_health", Path(__file__).resolve().parents[1] / "scripts" / "archive_health.py"
)
health = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(health)


def range_response(monkeypatch, *, status=206, content_range="bytes 0-0/1234", body=b"x", **headers):
    response = MagicMock()
    response.status = status
    response.headers = {"Content-Range": content_range, **headers}
    response.read.return_value = body
    response.__enter__.return_value = response
    opener = MagicMock(return_value=response)
    monkeypatch.setattr(health.urllib.request, "urlopen", opener)
    return response, opener


def test_fetches_only_one_byte_with_descriptive_headers(monkeypatch):
    response, opener = range_response(monkeypatch, **{"Content-Length": "1"})
    assert health.gzip_size("2025-09-10-15") == 1234
    request = opener.call_args.args[0]
    assert request.full_url == "https://data.gharchive.org/2025-09-10-15.json.gz"
    assert request.get_method() == "GET"
    assert request.get_header("Range") == "bytes=0-0"
    assert request.get_header("Accept-encoding") == "identity"
    assert "pr-fanout archive health check" in request.get_header("User-agent")
    response.read.assert_called_once_with(1)
    opener.assert_called_once()
    response.__exit__.assert_called_once()


def test_refuses_ignored_range_without_reading_full_body(monkeypatch):
    response, opener = range_response(monkeypatch, status=200)
    with pytest.raises(health.RangeResponseError, match="expected HTTP 206, received HTTP 200"):
        health.gzip_size("2025-09-10-15")
    response.read.assert_not_called()
    opener.assert_called_once()


@pytest.mark.parametrize("content_range", ["", "bytes 0-1/1234", "bytes 1-1/1234", "bytes 0-0/*", "bytes 0-0/0"])
def test_refuses_invalid_content_range(monkeypatch, content_range):
    response, _ = range_response(monkeypatch, content_range=content_range)
    with pytest.raises(health.RangeResponseError, match="invalid Content-Range"):
        health.gzip_size("2025-09-10-15")
    response.read.assert_not_called()


@pytest.mark.parametrize("headers", [{"Content-Length": "1234"}, {"Content-Encoding": "gzip"}])
def test_refuses_non_identity_or_non_range_body(monkeypatch, headers):
    response, _ = range_response(monkeypatch, **headers)
    with pytest.raises(health.RangeResponseError):
        health.gzip_size("2025-09-10-15")
    response.read.assert_not_called()


def test_refuses_empty_one_byte_response(monkeypatch):
    range_response(monkeypatch, body=b"")
    with pytest.raises(health.RangeResponseError, match="one-byte response was empty"):
        health.gzip_size("2025-09-10-15")


def test_cli_uses_network_sizes_and_first_hour_baseline(monkeypatch, capsys):
    sizes = dict(zip(health.DEFAULT_HOURS, (1000, 600, 80)))
    getter = MagicMock(side_effect=sizes.__getitem__)
    monkeypatch.setattr(health, "gzip_size", getter)
    assert health.main([]) == 0
    output = capsys.readouterr().out
    rows = [line.split() for line in output.splitlines() if line.startswith(("2025-", "2026-"))]
    assert rows == [
        ["2025-09-10-15", "1000", "100.0%", "BASELINE"],
        ["2026-06-10-15", "600", "60.0%", "NO_SIZE_ALERT"],
        ["2026-09-09-15", "80", "8.0%", "POSSIBLE_DEGRADATION"],
    ]
    assert "threshold: <50.0%" in output
    assert "does not prove schema degradation" in output
    assert getter.call_count == 3


def test_cli_accepts_custom_hours_baseline_and_threshold(monkeypatch, capsys):
    sizes = {"2025-01-01-9": 300, "2025-01-02-9": 1000}
    monkeypatch.setattr(health, "gzip_size", sizes.__getitem__)
    assert health.main([
        "2025-01-01-09", "2025-01-02-9", "--baseline", "2025-01-02-09", "--size-threshold", "0.2"
    ]) == 0
    output = capsys.readouterr().out
    assert "30.0%  NO_SIZE_ALERT" in output
    assert "Baseline: 2025-01-02-9" in output


@pytest.mark.parametrize("hour", ["2025-02-29-1", "2025-09-10-24", "2025-9-10-15", "../2025-09-10-15"])
def test_invalid_dates_are_rejected(hour):
    with pytest.raises(argparse.ArgumentTypeError):
        health.archive_hour(hour)


def test_cli_refuses_baseline_outside_input_without_network(monkeypatch):
    getter = MagicMock()
    monkeypatch.setattr(health, "gzip_size", getter)
    with pytest.raises(SystemExit) as exc:
        health.main(["2025-09-10-15", "--baseline", "2026-09-09-15"])
    assert exc.value.code == 2
    getter.assert_not_called()


def test_cli_fails_clearly_without_inventing_measurements(monkeypatch, capsys):
    monkeypatch.setattr(health, "gzip_size", MagicMock(side_effect=health.RangeResponseError("HTTP 200")))
    assert health.main([]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "archive_health: HTTP 200\n"
