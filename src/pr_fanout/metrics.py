"""The fan-out metric.

Definition
----------
Within a fixed observation window, an account is a **fan-out submitter** if it
opens pull requests against at least ``threshold`` *distinct* repositories.
The headline number is the share of human-opened pull requests that come from
such accounts.

Why this shape
--------------
Maintainers have repeatedly said that AI-text detection is a dead end: any
detector good enough to matter trains undetectable output. So this metric never
inspects the content of a contribution. It measures a property of the
*submission pattern* that is expensive to fake while staying a genuine
contributor — breadth without depth — and that a human contributor rarely
exhibits, because reading three unfamiliar codebases in one hour is hard and
generating three patches for them is not.

The threshold and window are parameters, not truths. Both are reported
alongside every number, and :func:`sweep_thresholds` exists precisely so a
reader can see how much the headline depends on the cut.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from .bots import is_agent, is_bot
from .watchlist import canonical

OUTSIDE_ASSOCIATIONS = frozenset({"NONE", "FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER", "CONTRIBUTOR"})
INSIDE_ASSOCIATIONS = frozenset({"MEMBER", "OWNER", "COLLABORATOR"})


@dataclass
class Window:
    """Mutable accumulator for one observation window."""

    label: str
    threshold: int = 3
    human_prs: int = 0
    bot_prs: int = 0
    _actor_repos: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    _repo_actors: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    _repo_prs: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _watch_closed: dict[str, AssociationCounts] = field(default_factory=dict)
    _bot_logins: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _suppressed: int = 0
    _agent_prs: int = 0
    _agent_logins: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _actor_prs: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def add_opened(self, actor: str, repo: str) -> None:
        if is_agent(actor):
            self._agent_prs += 1
            self._agent_logins[actor] += 1
            return
        if is_bot(actor):
            self.bot_prs += 1
            self._bot_logins[actor] += 1
            return
        self.human_prs += 1
        self._actor_prs[actor] += 1
        self._actor_repos[actor].add(repo)
        self._repo_actors[repo].add(actor)
        self._repo_prs[repo] += 1

    def repos_per_actor_histogram(self) -> dict[str, int]:
        """How many human accounts opened PRs to exactly N distinct repos today.

        This is the distribution the headline share is a single cut of. It is
        published because the cut is arbitrary and the shape is not.
        """
        hist: dict[str, int] = defaultdict(int)
        for repos in self._actor_repos.values():
            n = len(repos)
            key = str(n) if n < 10 else ("10-19" if n < 20 else ("20-49" if n < 50 else "50+"))
            hist[key] += 1
        return dict(sorted(hist.items(), key=lambda kv: (len(kv[0]), kv[0])))

    def top_agent_logins(self, limit: int = 20) -> list[dict]:
        rows = sorted(self._agent_logins.items(), key=lambda kv: -kv[1])[:limit]
        return [{"login": k, "prs_opened": v} for k, v in rows]

    def _withheld(self, actors: set[str], min_cell: int) -> bool:
        """Return True when this repository row must be withheld.

        Every function that emits a per-repository row calls this. It exists
        because the floor was once applied in two of the three emitters and
        missed in the third, and the published dataset carried 205 rows below
        the floor — 172 of them with a single contributor, which is close
        enough to naming that person.
        """
        if len(actors) < min_cell:
            self._suppressed += 1
            return True
        return False

    def suppressed_row_count(self) -> int:
        """Repositories excluded by the small-cell floor in this window.

        This counts every repository the floor removed while building the
        per-repository tables, not only the ones that would have made the
        published top-N. Most repositories receive a pull request from a single
        person on a given day, so this number is large by nature — it is the
        shape of GitHub, not a measure of how much was hidden from you.
        """
        return self._suppressed

    def top_bot_logins(self, limit: int = 20) -> list[dict]:
        """Which automation accounts actually produce the bot pull requests.

        Published because "bots opened more PRs than people" is meaningless
        without it: a dependency updater and a coding agent are both bots and
        mean opposite things for a maintainer.
        """
        rows = sorted(self._bot_logins.items(), key=lambda kv: -kv[1])[:limit]
        total = self.bot_prs
        return [
            {"login": login, "prs_opened": n, "pct_of_bot_prs": _pct(n, total)}
            for login, n in rows
        ]

    def add_closed(self, repo: str, association: str | None, merged: bool) -> None:
        """Record a close/merge outcome for a watchlist repository."""
        name = canonical(repo)
        if name is None:
            return
        self._watch_closed.setdefault(name, AssociationCounts()).add_closed(association, merged)

    def watchlist_rows(self, min_cell: int = 5) -> list[dict]:
        """One row per watched repository seen in this window.

        Rows whose distinct-actor count is below ``min_cell`` are withheld:
        with two or three contributors in a window, a per-repository count is
        close enough to naming them. :meth:`suppressed_row_count` reports how
        many were withheld, because hiding the withholding is worse than the
        withholding.
        """
        multi = self.fanout_actors()
        rows = []
        for repo, actors in self._repo_actors.items():
            name = canonical(repo)
            if name is None:
                continue
            hit = sorted(a for a in actors if a in multi)
            closed = self._watch_closed.get(name)
            if self._withheld(actors, min_cell):
                continue
            rows.append(
                {
                    "repo": name,
                    "human_prs_opened": self._repo_prs[repo],
                    "distinct_human_actors": len(actors),
                    "fanout_actors": len(hit),
                    "pct_actors_fanout": _pct(len(hit), len(actors)),
                    "outside_prs_closed": closed.outside_closed if closed else 0,
                    "outside_merge_rate": closed.summary()["outside_merge_rate"] if closed else None,
                }
            )
        rows.sort(key=lambda r: -r["human_prs_opened"])
        return rows

    # -- derived -------------------------------------------------------
    def fanout_actors(self, threshold: int | None = None) -> dict[str, set[str]]:
        t = self.threshold if threshold is None else threshold
        return {a: r for a, r in self._actor_repos.items() if len(r) >= t}

    def summary(self, threshold: int | None = None) -> dict:
        t = self.threshold if threshold is None else threshold
        multi = self.fanout_actors(t)
        prs_from_multi = sum(self._actor_prs[a] for a in multi)
        return {
            "label": self.label,
            "threshold_repos": t,
            "human_prs_opened": self.human_prs,
            "bot_prs_opened": self.bot_prs,
            "agent_prs_opened": self._agent_prs,
            "pct_prs_by_agents": _pct(self._agent_prs, self.human_prs + self.bot_prs + self._agent_prs),
            "pct_prs_by_bots": _pct(self.bot_prs, self.human_prs + self.bot_prs + self._agent_prs),
            "human_actors": len(self._actor_repos),
            "fanout_actors": len(multi),
            "pct_human_prs_from_fanout": _pct(prs_from_multi, self.human_prs),
            "pct_actors_fanout": _pct(len(multi), len(self._actor_repos)),
        }

    def sweep_thresholds(self, thresholds: Iterable[int] = (2, 3, 4, 5, 10)) -> list[dict]:
        return [self.summary(t) for t in thresholds]

    def top_repos(self, limit: int = 25, min_prs: int = 20, min_cell: int = 5) -> list[dict]:
        """Per-repository fan-out exposure, most-exposed first.

        ``fanout_prs`` counts pull requests this repository received from
        accounts that were, in the same window, also opening pull requests
        elsewhere.
        """
        multi = self.fanout_actors()
        rows = []
        for repo, actors in self._repo_actors.items():
            total = self._repo_prs[repo]
            if total < min_prs or self._withheld(actors, min_cell):
                continue
            hit = sum(1 for a in actors if a in multi)
            rows.append(
                {
                    "repo": repo,
                    "human_prs_opened": total,
                    "distinct_human_actors": len(actors),
                    "fanout_actors": hit,
                    "pct_actors_fanout": _pct(hit, len(actors)),
                }
            )
        rows.sort(key=lambda r: (-r["pct_actors_fanout"], -r["human_prs_opened"]))
        return rows[:limit]

    def busiest_repos(self, limit: int = 25, min_cell: int = 5) -> list[dict]:
        """Repositories receiving the most human pull requests in the window."""
        multi = self.fanout_actors()
        rows = []
        for repo, total in self._repo_prs.items():
            actors = self._repo_actors[repo]
            if self._withheld(actors, min_cell):
                continue
            hit = sum(1 for a in actors if a in multi)
            rows.append(
                {
                    "repo": repo,
                    "human_prs_opened": total,
                    "distinct_human_actors": len(actors),
                    "fanout_actors": hit,
                    "pct_actors_fanout": _pct(hit, len(actors)),
                }
            )
        rows.sort(key=lambda r: -r["human_prs_opened"])
        return rows[:limit]


@dataclass
class AssociationCounts:
    """Merge outcomes split by author association (full-schema hours only)."""

    outside_closed: int = 0
    outside_merged: int = 0
    inside_closed: int = 0
    inside_merged: int = 0

    def add_closed(self, association: str | None, merged: bool) -> None:
        if association in OUTSIDE_ASSOCIATIONS:
            self.outside_closed += 1
            self.outside_merged += 1 if merged else 0
        elif association in INSIDE_ASSOCIATIONS:
            self.inside_closed += 1
            self.inside_merged += 1 if merged else 0

    def summary(self) -> dict:
        return {
            "outside_prs_closed": self.outside_closed,
            "outside_merge_rate": _pct(self.outside_merged, self.outside_closed),
            "inside_prs_closed": self.inside_closed,
            "inside_merge_rate": _pct(self.inside_merged, self.inside_closed),
        }


def _pct(numerator: int, denominator: int) -> float | None:
    if not denominator:
        return None
    return round(100.0 * numerator / denominator, 2)
