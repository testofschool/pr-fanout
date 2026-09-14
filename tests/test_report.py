import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from pr_fanout.cli import main
from pr_fanout.report import ComparisonInvalidError, build_report

ROOT = Path(__file__).resolve().parents[1]
CHARTS = [f"{metric}-{theme}.svg" for metric in ("agents", "fanout") for theme in ("light", "dark")]


def day(date, full=True):
    return {
        "date": date,
        "all_hours_full_schema": full,
        "hours_collected": 12,
        "suppressed_rows": 0,
        "summary": {
            "human_prs_opened": 10,
            "bot_prs_opened": 2,
            "agent_prs_opened": 1,
            "pct_prs_by_agents": 7.69,
            "pct_human_prs_from_fanout": 20.0,
            "pct_actors_fanout": 10.0,
        },
    }


@pytest.mark.parametrize("flag", [False, None, "true", 1])
def test_report_rejects_unverified_schema_before_creating_output(tmp_path, flag):
    out = tmp_path / "report"
    unverified = day("2026-09-09", flag)
    if flag is None:
        del unverified["all_hours_full_schema"]
    with pytest.raises(ComparisonInvalidError, match="COMPARISON_INVALID.*2026-09-09"):
        build_report([day("2025-09-10"), unverified], out)
    assert not out.exists()


def test_rejection_preserves_existing_artifacts_and_mtimes(tmp_path):
    for name in [*CHARTS, "summary.json", "summary-table.md"]:
        (tmp_path / name).write_text(f"previous {name}")
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()}
    with pytest.raises(ComparisonInvalidError):
        build_report([day("2025-09-10"), day("2026-09-09", False)], tmp_path)
    after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()}
    assert after == before


def test_degraded_only_input_is_not_silently_accepted(tmp_path):
    with pytest.raises(ComparisonInvalidError, match="COMPARISON_INVALID"):
        build_report([day("2026-09-09", False)], tmp_path / "report")


@pytest.mark.parametrize("override", [False, True])
def test_cli_comparison_guard_and_warned_override(tmp_path, capsys, override):
    for item in [day("2025-09-10"), day("2026-09-09", False)]:
        (tmp_path / f"day-{item['date']}.json").write_text(json.dumps(item))
    out = tmp_path / "report"
    args = ["report", "--inputs", str(tmp_path / "day-*.json"), "--out", str(out)]
    result = main(args + (["--allow-degraded"] if override else []))
    captured = capsys.readouterr()
    assert captured.err.startswith("COMPARISON_INVALID")
    assert "2026-09-09" in captured.err
    if not override:
        assert result == 2
        assert captured.out == ""
        assert not out.exists()
        return

    assert result == 0
    assert f"-> {out}" in captured.out
    assert (out / "summary-table.md").read_text().startswith("> **COMPARISON_INVALID")
    rows = json.loads((out / "summary.json").read_text())
    assert [row["date"] for row in rows] == ["2025-09-10", "2026-09-09"]
    assert [row["schema"] for row in rows] == ["full", "TRIMMED"]
    assert all(row["comparison_status"] == "COMPARISON_INVALID" for row in rows)
    assert all(row["comparison_warning"].startswith("COMPARISON_INVALID") for row in rows)
    for name in CHARTS:
        svg = ET.parse(out / name).getroot()
        text = [node.text or "" for node in svg.iter("{http://www.w3.org/2000/svg}text")]
        assert text[0].startswith("COMPARISON_INVALID")
        assert any("do not infer a trend" in label for label in text)
        assert {"2025", "2026"} <= set(text)
        assert svg.attrib["aria-label"].startswith("COMPARISON_INVALID")


def test_full_schema_chart_outputs_are_unchanged(tmp_path, capsys):
    results = [json.loads(p.read_text()) for p in sorted((ROOT / "data").glob("day-*.json"))]
    full = [r for r in results if r["all_hours_full_schema"] is True]
    build_report(full, tmp_path)
    assert capsys.readouterr().err == ""
    for name in CHARTS:
        assert (tmp_path / name).read_bytes() == (ROOT / "docs" / name).read_bytes()
    assert "COMPARISON_INVALID" not in (tmp_path / "summary-table.md").read_text()
    rows = json.loads((tmp_path / "summary.json").read_text())
    assert len(rows) == len(full)
    assert all("comparison_status" not in row for row in rows)


def test_warned_single_year_report_removes_stale_charts(tmp_path, capsys):
    for name in CHARTS:
        (tmp_path / name).write_text("old unmarked chart")
    build_report([day("2026-09-02"), day("2026-09-09", False)], tmp_path, allow_degraded=True)
    assert capsys.readouterr().err.startswith("COMPARISON_INVALID")
    assert all(not (tmp_path / name).exists() for name in CHARTS)
    assert (tmp_path / "summary-table.md").read_text().startswith("> **COMPARISON_INVALID")
