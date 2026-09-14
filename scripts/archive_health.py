#!/usr/bin/env python3
"""Compare GH Archive gzip sizes using one-byte HTTP Range requests only."""

import argparse
import http.client
import math
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

DEFAULT_HOURS = ("2025-09-10-15", "2026-06-10-15", "2026-09-09-15")
USER_AGENT = "pr-fanout archive health check (https://github.com/testofschool/pr-fanout)"
DEFAULT_SIZE_THRESHOLD = 0.5


class RangeResponseError(ValueError):
    """The archive server did not honor the one-byte request."""


def archive_hour(value: str) -> str:
    """Validate a UTC hour and use GH Archive's unpadded hour naming."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}-\d{1,2}", value):
        raise argparse.ArgumentTypeError("use an archive hour such as 2025-09-10-15 (UTC)")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d-%H").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid archive hour: {value}") from exc
    return f"{parsed:%Y-%m-%d}-{parsed.hour}"


def size_threshold(value: str) -> float:
    try:
        threshold = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("size threshold must be a number between 0 and 1") from exc
    if not math.isfinite(threshold) or not 0 < threshold < 1:
        raise argparse.ArgumentTypeError("size threshold must be a number between 0 and 1")
    return threshold


def gzip_size(hour: str, *, timeout: float = 30) -> int:
    """Read one response byte, taking the complete gzip size from Content-Range."""
    request = urllib.request.Request(
        f"https://data.gharchive.org/{hour}.json.gz",
        headers={"Range": "bytes=0-0", "User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 206:
            raise RangeResponseError(f"{hour}: expected HTTP 206, received HTTP {response.status}; body not read")
        content_range = response.headers.get("Content-Range", "")
        match = re.fullmatch(r"bytes 0-0/([1-9]\d*)", content_range)
        if not match:
            raise RangeResponseError(f"{hour}: invalid Content-Range {content_range!r}; body not read")
        content_length = response.headers.get("Content-Length")
        if content_length is not None and content_length != "1":
            raise RangeResponseError(f"{hour}: expected Content-Length 1, received {content_length!r}; body not read")
        content_encoding = response.headers.get("Content-Encoding", "identity")
        if content_encoding.lower() != "identity":
            raise RangeResponseError(f"{hour}: unexpected Content-Encoding {content_encoding!r}; body not read")
        if len(response.read(1)) != 1:
            raise RangeResponseError(f"{hour}: the one-byte response was empty")
        return int(match.group(1))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hours", nargs="*", type=archive_hour, help="UTC archive hours (default: three sample hours)")
    parser.add_argument("--baseline", type=archive_hour, help="baseline hour from the input list (default: first hour)")
    parser.add_argument(
        "--size-threshold", type=size_threshold, default=DEFAULT_SIZE_THRESHOLD,
        help="flag a gzip size below this fraction of the baseline (default: 0.5)",
    )
    args = parser.parse_args(argv)
    hours = args.hours or list(DEFAULT_HOURS)
    baseline = args.baseline or hours[0]
    if baseline not in hours:
        parser.error("--baseline must be one of the input hours")
    measured_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        sizes = {hour: gzip_size(hour) for hour in dict.fromkeys(hours)}
    except (RangeResponseError, urllib.error.URLError, OSError, http.client.HTTPException) as exc:
        print(f"archive_health: {exc}", file=sys.stderr)
        return 1

    print(f"Measured at (UTC): {measured_at}")
    print(f"Baseline: {baseline}; possible degradation threshold: <{args.size_threshold:.1%} of baseline gzip size")
    print("Signal is relative gzip size only; a smaller file alone does not prove schema degradation.")
    print("hour           gzip_bytes  baseline_pct  size_signal")
    for hour in hours:
        ratio = sizes[hour] / sizes[baseline]
        signal = "BASELINE" if hour == baseline else (
            "POSSIBLE_DEGRADATION" if ratio < args.size_threshold else "NO_SIZE_ALERT"
        )
        print(f"{hour:<14} {sizes[hour]:>10}  {ratio * 100:>11.1f}%  {signal}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
