from pathlib import Path

import pytest

from pr_fanout.archive import Hour, day_hours, iter_events, schema_probe
from pr_fanout.metrics import Window

FIXTURE = Path(__file__).parent / "fixtures" / "sample-hour.json.gz"


def test_hour_tag_is_not_zero_padded():
    # GH Archive publishes 2025-09-10-9.json.gz, not ...-09.json.gz
    assert Hour(2025, 9, 10, 9).tag == "2025-09-10-9"
    assert Hour.parse("2025-09-10-9").url.endswith("2025-09-10-9.json.gz")


def test_day_hours_sampling():
    assert len(day_hours("2025-09-10")) == 24
    assert [h.hour for h in day_hours("2025-09-10", every=6)] == [0, 6, 12, 18]


def test_iter_events_skips_other_types_and_broken_lines():
    raw = FIXTURE.read_bytes()
    events = list(iter_events(raw, "PullRequestEvent"))
    assert len(events) == 10
    assert all(e["type"] == "PullRequestEvent" for e in events)


def test_schema_probe_detects_full_schema():
    probe = schema_probe(FIXTURE.read_bytes())
    assert probe["full_schema"] is True


def test_end_to_end_on_fixture():
    raw = FIXTURE.read_bytes()
    w = Window("fixture", threshold=3)
    for event in iter_events(raw, "PullRequestEvent"):
        if event["payload"].get("action") == "opened":
            w.add_opened(event["actor"]["login"], event["repo"]["name"])
    s = w.summary()
    assert s["human_prs_opened"] == 6
    assert s["bot_prs_opened"] == 1
    assert s["fanout_actors"] == 1
    assert s["pct_human_prs_from_fanout"] == pytest.approx(66.67, abs=0.01)


def test_retry_clause_covers_truncated_transfers():
    """Regression: narrowing the retry clause to (URLError, TimeoutError, OSError)
    for a linter let http.client.IncompleteRead escape — and a 100 MB archive hour
    that stops short raises exactly that. It is an HTTPException, not an OSError,
    so the narrow clause crashed the run instead of retrying. Observed live."""
    import http.client
    import inspect
    import urllib.error

    from pr_fanout import archive

    err = http.client.IncompleteRead(b"partial")
    assert not isinstance(err, OSError)
    assert not isinstance(err, urllib.error.URLError)

    source = inspect.getsource(archive.fetch)
    assert "http.client.HTTPException" in source, (
        "fetch() must retry truncated transfers, not crash on them"
    )
