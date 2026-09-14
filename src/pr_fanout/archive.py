"""Fetching and decoding GH Archive hourly dumps.

GH Archive (https://www.gharchive.org/) publishes one gzipped JSON-lines file
per hour containing every public GitHub event. We read it directly rather than
using the GitHub REST API because the API requires per-repository authorisation
and heavy rate-limit budget, while the archive is anonymous, complete for the
hours it covers, and reproducible by anyone auditing this repository.

Two field-tested gotchas are encoded here:

1. The CDN rejects the default ``Python-urllib/x.y`` User-Agent with HTTP 403.
   A descriptive User-Agent is required, so we always send one.
2. The archive's payload schema is **not stable across years**. Older hours
   embed the full ``pull_request`` object (including ``author_association`` and
   ``merged``); some recent hours ship a trimmed payload with only
   ``base``/``head``/``id``/``number``/``url``. Callers must check
   :func:`schema_probe` before trusting association-derived numbers.
"""
from __future__ import annotations

import gzip
import http.client
import io
import json
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://data.gharchive.org"
USER_AGENT = "pr-fanout/0.1 (+https://github.com/testofschool/pr-fanout)"


class ArchiveError(RuntimeError):
    """Raised when an hour cannot be fetched after retries."""


@dataclass(frozen=True)
class Hour:
    """One archive hour, addressable as ``YYYY-MM-DD-H``."""

    year: int
    month: int
    day: int
    hour: int

    @classmethod
    def parse(cls, tag: str) -> Hour:
        y, m, d, h = tag.split("-")
        return cls(int(y), int(m), int(d), int(h))

    @property
    def tag(self) -> str:
        # GH Archive uses a non-padded hour, e.g. 2025-09-13-9.
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}-{self.hour}"

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.tag}.json.gz"

    def as_datetime(self) -> datetime:
        return datetime(self.year, self.month, self.day, self.hour, tzinfo=timezone.utc)


def day_hours(date: str, every: int = 1) -> list[Hour]:
    """All hours of ``date`` (``YYYY-MM-DD``), optionally every ``every``-th hour."""
    y, m, d = (int(p) for p in date.split("-"))
    return [Hour(y, m, d, h) for h in range(0, 24, every)]


def fetch(hour: Hour, cache_dir: Path | None = None, retries: int = 3) -> bytes:
    """Download one archive hour, with on-disk caching and bounded retries."""
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached = cache_dir / f"{hour.tag}.json.gz"
        if cached.exists() and cached.stat().st_size > 0:
            return cached.read_bytes()

    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(hour.url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = resp.read()
            if cache_dir is not None:
                (cache_dir / f"{hour.tag}.json.gz").write_bytes(raw)
            return raw
        except urllib.error.HTTPError as exc:  # pragma: no cover - network
            last = exc
            if exc.code == 404:
                raise ArchiveError(f"{hour.tag}: not published (404)") from exc
            time.sleep(2 ** attempt)
        except (
            urllib.error.URLError,
            http.client.HTTPException,
            TimeoutError,
            OSError,
        ) as exc:  # pragma: no cover - network
            # Deliberately broad across transport failures: a DNS blip, a reset
            # connection, a truncated body and a read timeout all mean the same
            # thing here - retry this hour, and if the retry budget runs out let
            # the run fail rather than emit a day built from a partial sample.
            #
            # http.client.HTTPException is listed explicitly because it is NOT an
            # OSError: a 100 MB archive hour that stops short raises
            # http.client.IncompleteRead, which an OSError-only clause lets
            # escape and crashes the run. Observed on a 2023 hour while tightening
            # this very clause for a linter.
            last = exc
            time.sleep(2 ** attempt)
    raise ArchiveError(f"{hour.tag}: giving up after {retries} attempts ({last})")


def iter_events(raw: bytes, event_type: str | None = None) -> Iterator[dict]:
    """Yield decoded events from a gzipped JSON-lines blob.

    A cheap bytes-level prefilter avoids JSON-decoding the ~90% of lines that
    are PushEvents; on a 130 MB hour this is the difference between seconds and
    minutes.
    """
    needle = f'"{event_type}"'.encode() if event_type else None
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as fh:
        for line in fh:
            if needle is not None and needle not in line:
                continue
            try:
                event = json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if event_type is not None and event.get("type") != event_type:
                continue
            yield event


def schema_probe(raw: bytes, sample: int = 400) -> dict:
    """Report which pull-request fields this hour actually carries.

    Returns counts so a caller can refuse to compute association-based metrics
    on a trimmed hour instead of silently reporting zeros.
    """
    seen = has_assoc = has_merged = 0
    for event in iter_events(raw, "PullRequestEvent"):
        pr = event.get("payload", {}).get("pull_request") or {}
        seen += 1
        has_assoc += 1 if pr.get("author_association") else 0
        has_merged += 1 if "merged" in pr else 0
        if seen >= sample:
            break
    return {
        "sampled": seen,
        "with_author_association": has_assoc,
        "with_merged_flag": has_merged,
        "full_schema": bool(seen) and has_assoc / seen > 0.5,
    }
