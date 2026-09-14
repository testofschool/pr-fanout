import pytest

from pr_fanout.metrics import AssociationCounts, Window


def build() -> Window:
    w = Window("test", threshold=3)
    for repo in ("org/a", "org/b", "org/c"):
        w.add_opened("sprayer", repo)
    w.add_opened("alice", "org/a")
    w.add_opened("dependabot[bot]", "org/a")
    return w


def test_bots_leave_the_human_denominator():
    w = build()
    s = w.summary()
    assert s["human_prs_opened"] == 4
    assert s["bot_prs_opened"] == 1


def test_fanout_share():
    s = build().summary()
    assert s["fanout_actors"] == 1
    assert s["pct_human_prs_from_fanout"] == 75.0


def test_threshold_is_a_parameter_not_a_truth():
    w = build()
    sweep = {row["threshold_repos"]: row["pct_human_prs_from_fanout"] for row in w.sweep_thresholds((2, 3, 4))}
    assert sweep[2] == 75.0
    assert sweep[3] == 75.0
    assert sweep[4] == 0.0


def test_repeated_prs_to_one_repo_are_not_fanout():
    w = Window("t", threshold=3)
    for _ in range(10):
        w.add_opened("busy", "org/a")
    assert w.summary()["fanout_actors"] == 0


def test_empty_window_returns_none_not_zero():
    assert Window("t").summary()["pct_human_prs_from_fanout"] is None


def test_association_counts():
    a = AssociationCounts()
    a.add_closed("NONE", False)
    a.add_closed("CONTRIBUTOR", True)
    a.add_closed("MEMBER", True)
    a.add_closed(None, True)  # trimmed schema -> ignored entirely
    s = a.summary()
    assert s["outside_prs_closed"] == 2
    assert s["outside_merge_rate"] == 50.0
    assert s["inside_prs_closed"] == 1


def test_numerator_counts_pull_requests_not_repositories():
    """Regression: the share was once computed from distinct repos per actor,
    which silently discounted exactly the mass-submission behaviour the metric
    exists to surface (40 PRs to each of 3 repos reported 2.5%, not 100%)."""
    w = Window("regression", threshold=3)
    for repo in ("org/a", "org/b", "org/c"):
        for _ in range(40):
            w.add_opened("sprayer", repo)
    s = w.summary()
    assert s["human_prs_opened"] == 120
    assert s["pct_human_prs_from_fanout"] == 100.0


def test_coding_agents_are_their_own_category():
    """Regression: GitHub's Copilot coding agent has no [bot] suffix and was
    being counted as a human contributor."""
    w = Window("agents")
    w.add_opened("Copilot", "org/a")
    w.add_opened("dependabot[bot]", "org/a")
    w.add_opened("alice", "org/a")
    s = w.summary()
    assert (s["human_prs_opened"], s["bot_prs_opened"], s["agent_prs_opened"]) == (1, 1, 1)


def test_histogram_buckets_the_tail():
    w = Window("hist")
    for i in range(3):
        w.add_opened("a", f"org/{i}")
    for i in range(25):
        w.add_opened("b", f"org/{i}")
    assert w.repos_per_actor_histogram() == {"3": 1, "20-49": 1}


def test_small_cells_are_withheld_and_counted():
    """Spec clause min-cell: a repository row with fewer than `min_cell`
    distinct human actors is close enough to naming them, so it is withheld —
    and the count of withheld rows is published rather than hidden."""
    w = Window("cells")
    for i in range(3):
        w.add_opened(f"person{i}", "curl/curl")       # 3 actors -> below the floor
    for i in range(6):
        w.add_opened(f"other{i}", "golang/go")        # 6 actors -> published
    rows = w.watchlist_rows(min_cell=5)
    assert [r["repo"] for r in rows] == ["golang/go"]
    assert w.suppressed_row_count() == 1


@pytest.mark.parametrize(
    "emitter",
    ["watchlist_rows", "top_repos", "busiest_repos"],
)
def test_every_repo_emitter_applies_the_floor(emitter):
    """Regression: the floor was applied in two emitters and missed in the
    third, and 205 of 300 published rows sat below it — 172 with a single
    contributor. Parametrised so a new emitter cannot be added without one."""
    w = Window("floor")
    for i in range(3):
        w.add_opened(f"person{i}", "curl/curl")        # 3 actors, below the floor
    for i in range(6):
        w.add_opened(f"other{i}", "golang/go")         # 6 actors, published
    kwargs = {"min_prs": 1} if emitter == "top_repos" else {}
    rows = getattr(w, emitter)(min_cell=5, **kwargs)
    assert [r["repo"] for r in rows] == ["golang/go"]
    assert all(r["distinct_human_actors"] >= 5 for r in rows)
