"""Command line interface.

    python -m pr_fanout collect --date 2025-09-13 --every 3 --out data/2025-09.json
    python -m pr_fanout report  --inputs data/*.json --out docs/
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

from . import __version__
from .archive import ArchiveError, day_hours, fetch, iter_events, schema_probe
from .metrics import AssociationCounts, Window


def collect(args: argparse.Namespace) -> int:
    hours = day_hours(args.date, every=args.every)
    window = Window(label=args.label or args.date[:7], threshold=args.threshold)
    assoc = AssociationCounts()
    cache = Path(args.cache) if args.cache else None
    hours_done: list[dict] = []

    for hour in hours:
        try:
            raw = fetch(hour, cache_dir=cache)
        except ArchiveError as exc:
            print(f"  ! {hour.tag}: {exc}", file=sys.stderr)
            hours_done.append({"hour": hour.tag, "ok": False, "error": str(exc)})
            continue

        probe = schema_probe(raw)
        opened = closed = 0
        for event in iter_events(raw, "PullRequestEvent"):
            payload = event["payload"]
            action = payload.get("action")
            if action == "opened":
                window.add_opened(event["actor"]["login"], event["repo"]["name"])
                opened += 1
            elif action in ("closed", "merged") and probe["full_schema"]:
                pr = payload.get("pull_request") or {}
                association = pr.get("author_association")
                merged = bool(pr.get("merged")) or action == "merged"
                assoc.add_closed(association, merged)
                window.add_closed(event["repo"]["name"], association, merged)
                closed += 1
        hours_done.append(
            {
                "hour": hour.tag,
                "ok": True,
                "pr_opened": opened,
                "pr_closed_scored": closed,
                "full_schema": probe["full_schema"],
            }
        )
        print(f"  . {hour.tag}  opened={opened:>6}  schema={'full' if probe['full_schema'] else 'TRIMMED'}", flush=True)
        if cache is None:
            del raw

    ok_hours = [h for h in hours_done if h.get("ok")]
    result = {
        "tool": f"pr-fanout/{__version__}",
        "date": args.date,
        "hours_requested": len(hours),
        "hours_collected": len(ok_hours),
        "all_hours_full_schema": all(h.get("full_schema") for h in ok_hours) if ok_hours else False,
        "summary": window.summary(),
        "threshold_sweep": window.sweep_thresholds(),
        "association": assoc.summary(),
        "repos_per_actor_histogram": window.repos_per_actor_histogram(),
        "top_agent_logins": window.top_agent_logins(limit=25),
        "top_bot_logins": window.top_bot_logins(limit=25),
        "watchlist": window.watchlist_rows(min_cell=args.min_cell),
        "most_fanout_exposed_repos": window.top_repos(limit=args.top, min_cell=args.min_cell),
        "busiest_repos": window.busiest_repos(limit=args.top, min_cell=args.min_cell),
        "min_cell": args.min_cell,
        "suppressed_rows": window.suppressed_row_count(),
        "hours": hours_done,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result["summary"], indent=2))
    print(f"-> {out}")
    return 0


def report(args: argparse.Namespace) -> int:
    from .report import ComparisonInvalidError, build_report

    paths: list[Path] = []
    for pattern in args.inputs:
        paths.extend(Path(p) for p in sorted(glob.glob(pattern)))
    if not paths:
        print("no input files matched", file=sys.stderr)
        return 2
    try:
        build_report(
            [json.loads(p.read_text()) for p in paths], Path(args.out), allow_degraded=args.allow_degraded
        )
    except ComparisonInvalidError as exc:
        print(exc, file=sys.stderr)
        return 2
    print(f"-> {args.out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pr-fanout", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    c = sub.add_parser("collect", help="measure one calendar day of GH Archive")
    c.add_argument("--date", required=True, help="YYYY-MM-DD (UTC)")
    c.add_argument("--every", type=int, default=1, help="sample every Nth hour (default: all 24)")
    c.add_argument("--threshold", type=int, default=3, help="distinct repos that define fan-out")
    c.add_argument("--top", type=int, default=30, help="repositories to list")
    c.add_argument("--min-cell", type=int, default=5,
                   help="withhold any repository row with fewer than this many distinct human actors")
    c.add_argument("--label", default=None)
    c.add_argument("--cache", default=None, help="directory to keep downloaded hours")
    c.add_argument("--out", required=True)
    c.set_defaults(func=collect)

    r = sub.add_parser("report", help="render markdown + svg from collected files")
    r.add_argument("--inputs", nargs="+", required=True)
    r.add_argument("--out", required=True)
    r.add_argument(
        "--allow-degraded", action="store_true",
        help="include non-full archive days for inspection, keeping COMPARISON_INVALID warnings",
    )
    r.set_defaults(func=report)

    args = parser.parse_args(argv)
    return args.func(args)
