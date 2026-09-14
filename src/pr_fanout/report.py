"""Rendering: a markdown table and two static SVG charts (light + dark).

Why two static SVGs instead of one theme-aware file: GitHub renders README
images through a sanitising proxy that strips ``<style>`` blocks and ignores
``prefers-color-scheme`` inside an ``<img>``. The portable pattern is a
``<picture>`` element with two sources, so we emit both files with their colours
baked in. Values come from the reference palette (categorical slot 1, blue).
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path


# --- palette (reference instance, categorical slot 1) --------------------
@dataclass(frozen=True)
class Theme:
    name: str
    surface: str
    text_primary: str
    text_secondary: str
    grid: str
    series: str


LIGHT = Theme("light", "#fcfcfb", "#0b0b0b", "#52514e", "#e5e4e0", "#2a78d6")
DARK = Theme("dark", "#1a1a19", "#ffffff", "#c3c2b7", "#333331", "#3987e5")

W, H = 720, 360
PAD_L, PAD_R, PAD_T, PAD_B = 62, 52, 58, 56

INVALID_BANNER = "COMPARISON_INVALID: degraded archive data included"


class ComparisonInvalidError(ValueError):
    """Report inputs include an archive day without a verified full schema."""


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def chart_svg(
    points: list[tuple[str, float, float, float]],
    theme: Theme,
    title: str,
    subtitle: str,
    unit: str = "%",
    warning: str | None = None,
) -> str:
    """One line through the yearly means, with the observed range as a whisker.

    Each point is ``(label, mean, low, high)``. The whisker is the whole point:
    three sampled days per year is a *range*, not a confidence interval, and a
    bare mean would imply a precision this sample does not have.
    """
    if len(points) < 2:
        raise ValueError("need at least two points")
    values = [hi for _, _, _, hi in points]
    vmax = max(values)
    # Round the axis up to a friendly ceiling so the line never touches the top.
    step = 0.5 if vmax <= 2 else 2.0
    ceiling = (int(vmax / step) + 1) * step
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B

    def x(i: int) -> float:
        return PAD_L + (plot_w * i / (len(points) - 1))

    def y(v: float) -> float:
        return PAD_T + plot_h * (1 - v / ceiling)

    ticks = [0.0, ceiling / 2, ceiling]
    parts: list[str] = []
    banner_height = 32 if warning else 0
    height = H + banner_height
    accessible_title = f"{warning}. {title}" if warning else title
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" '
        f'viewBox="0 0 {W} {height}" role="img" aria-label="{_esc(accessible_title)}">'
    )
    parts.append(f'<rect width="{W}" height="{height}" fill="{theme.surface}"/>')
    if warning:
        parts.append(
            f'<text x="16" y="22" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="13" font-weight="700" fill="{theme.text_primary}">{_esc(warning)}</text>'
        )
        parts.append(f'<g transform="translate(0 {banner_height})">')
    parts.append(
        f'<text x="{PAD_L}" y="28" font-family="Helvetica,Arial,sans-serif" font-size="17" '
        f'font-weight="600" fill="{theme.text_primary}">{_esc(title)}</text>'
    )
    parts.append(
        f'<text x="{PAD_L}" y="46" font-family="Helvetica,Arial,sans-serif" font-size="12" '
        f'fill="{theme.text_secondary}">{_esc(subtitle)}</text>'
    )
    # recessive gridlines + y labels
    for t in ticks:
        yy = round(y(t), 1)
        parts.append(
            f'<line x1="{PAD_L}" y1="{yy}" x2="{W - PAD_R}" y2="{yy}" stroke="{theme.grid}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{PAD_L - 10}" y="{yy + 4}" text-anchor="end" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="11" fill="{theme.text_secondary}">{t:g}{unit}</text>'
        )
    # x labels
    for i, (label, _, _, _) in enumerate(points):
        parts.append(
            f'<text x="{round(x(i), 1)}" y="{H - PAD_B + 22}" text-anchor="middle" '
            f'font-family="Helvetica,Arial,sans-serif" font-size="11.5" '
            f'fill="{theme.text_secondary}">{_esc(label)}</text>'
        )
    # observed range per year, drawn under the line so the mean stays readable
    for i, (_, _, lo, hi) in enumerate(points):
        if hi - lo < 1e-9:
            continue
        xx = round(x(i), 1)
        parts.append(
            f'<line x1="{xx}" y1="{round(y(lo), 1)}" x2="{xx}" y2="{round(y(hi), 1)}" '
            f'stroke="{theme.series}" stroke-width="2" stroke-opacity="0.35" stroke-linecap="round"/>'
        )
    # the line
    d = " ".join(
        ("M" if i == 0 else "L") + f"{round(x(i), 1)},{round(y(v), 1)}"
        for i, (_, v, _, _) in enumerate(points)
    )
    parts.append(
        f'<path d="{d}" fill="none" stroke="{theme.series}" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    )
    # markers with a 2px surface ring so overlaps stay readable
    for i, (_, v, _, _) in enumerate(points):
        parts.append(
            f'<circle cx="{round(x(i), 1)}" cy="{round(y(v), 1)}" r="4.5" fill="{theme.series}" '
            f'stroke="{theme.surface}" stroke-width="2"/>'
        )
    # selective direct labels: first and last only
    for i in (0, len(points) - 1):
        v = points[i][1]
        anchor = "start" if i == 0 else "end"
        dx = 10 if i == 0 else -10
        label = f"{v:.2f}{unit}" if v >= 0.1 else f"{v:.3f}{unit}"
        parts.append(
            f'<text x="{round(x(i) + dx, 1)}" y="{round(y(points[i][3]) - 14, 1)}" text-anchor="{anchor}" '
            f'font-family="Helvetica,Arial,sans-serif" font-size="13" font-weight="600" '
            f'fill="{theme.text_primary}">{label}</text>'
        )
    if warning:
        parts.append("</g>")
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def markdown_table(rows: list[dict], columns: list[tuple[str, str]]) -> str:
    head = "| " + " | ".join(h for _, h in columns) + " |"
    sep = "|" + "|".join("---" for _ in columns) + "|"
    body = []
    for r in rows:
        cells = []
        for key, _ in columns:
            v = r.get(key)
            cells.append("—" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v)))
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([head, sep, *body])


def build_report(results: list[dict], out_dir: Path, *, allow_degraded: bool = False) -> None:
    """Reject non-full inputs before writing; overrides keep every input visibly marked.

    Missing or non-boolean schema flags are unverified, rather than evidence of a
    full schema. This check also protects callers that bypass the CLI.
    """
    degraded = [r for r in results if r.get("all_hours_full_schema") is not True]
    warning = None
    if degraded:
        dates = ", ".join(str(r.get("date", "unknown date")) for r in degraded)
        warning = f"COMPARISON_INVALID: non-full archive schema for {dates}; these metrics are not comparable."
        if not allow_degraded:
            raise ComparisonInvalidError(f"{warning} Use --allow-degraded only for warned inspection.")
        print(warning, file=sys.stderr)
    out_dir.mkdir(parents=True, exist_ok=True)

    def by_year(key: str) -> list[tuple[str, float, float, float]]:
        buckets: dict[str, list[float]] = {}
        for r in sorted(results, key=lambda r: r["date"]):
            value = r["summary"].get(key)
            if value is None:
                continue
            buckets.setdefault(r["date"][:4], []).append(value)
        return [
            (year, sum(vals) / len(vals), min(vals), max(vals))
            for year, vals in sorted(buckets.items())
        ]

    charts = [
        (
            "agents",
            "pct_prs_by_agents",
            "Share of public GitHub pull requests opened by declared coding agents",
            "Self-identifying agent accounts. Mean of 3 matched Wednesdays; the bar is the observed range.",
        ),
        (
            "fanout",
            "pct_human_prs_from_fanout",
            "Share of human pull requests opened by fan-out accounts",
            "Accounts opening PRs to 3+ distinct repos the same day. Bots and agents excluded.",
        ),
    ]
    for name, key, title, sub in charts:
        points = by_year(key)
        if len(points) < 2:
            # An older chart must not survive as if it represented this report.
            for theme in (LIGHT, DARK):
                (out_dir / f"{name}-{theme.name}.svg").unlink(missing_ok=True)
            continue
        banner = INVALID_BANNER if warning else None
        subtitle = "Inspection only. Archive data is not comparable; do not infer a trend." if warning else sub
        (out_dir / f"{name}-light.svg").write_text(chart_svg(points, LIGHT, title, subtitle, warning=banner))
        (out_dir / f"{name}-dark.svg").write_text(chart_svg(points, DARK, title, subtitle, warning=banner))

    summary_rows = [
        {
            **({"comparison_status": "COMPARISON_INVALID", "comparison_warning": warning} if warning else {}),
            "date": r["date"],
            "hours": r["hours_collected"],
            "human_prs_opened": r["summary"]["human_prs_opened"],
            "bot_prs_opened": r["summary"]["bot_prs_opened"],
            "agent_prs_opened": r["summary"].get("agent_prs_opened"),
            "pct_prs_by_agents": r["summary"].get("pct_prs_by_agents"),
            "suppressed_rows": r.get("suppressed_rows"),
            "pct_human_prs_from_fanout": r["summary"]["pct_human_prs_from_fanout"],
            "pct_actors_fanout": r["summary"]["pct_actors_fanout"],
            "schema": "full" if r.get("all_hours_full_schema") is True else "TRIMMED",
        }
        for r in sorted(results, key=lambda r: r["date"])
    ]
    md = markdown_table(
        summary_rows,
        [
            ("date", "UTC day"),
            ("hours", "hours sampled"),
            ("human_prs_opened", "human PRs"),
            ("bot_prs_opened", "bot PRs"),
            ("agent_prs_opened", "agent PRs"),
            ("pct_prs_by_agents", "% PRs by agents"),
            ("pct_human_prs_from_fanout", "% human PRs from fan-out accounts"),
            ("pct_actors_fanout", "% accounts that fan out"),
            ("suppressed_rows", "repos below floor"),
            ("schema", "archive schema"),
        ],
    )
    if warning:
        md = f"> **{INVALID_BANNER}** — these metrics are not comparable.\n\n" + md
    (out_dir / "summary-table.md").write_text(md + "\n")
    (out_dir / "summary.json").write_text(json.dumps(summary_rows, indent=2) + "\n")
