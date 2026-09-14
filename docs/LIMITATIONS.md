# Limitations

Read this before citing any number here. Each entry states what could make the
headline wrong and what would settle it.

## 1. Fan-out is a proxy, not a diagnosis

A fan-out account is not proven to be an agent, and a non-fan-out account is not
proven to be a person. The metric bounds a *behaviour*, not an author. Anyone using
it to accuse a specific contributor is misusing it, and the per-repository tables
deliberately publish counts, never account names.

**Known false positives:** release engineers synchronising a change across an
organisation's repositories; monorepo-adjacent contributors; people doing genuine
multi-project work such as a security fix applied upstream in several places;
Hacktoberfest-style event weeks.

**Known false negatives:** an operator who paces submissions to one repository per
day, or spreads them across accounts. Both cost throughput, which is the point — but
they do mean the numbers here are a **floor**, not a ceiling.

## 2. Sampling

Twelve hours of each of three Wednesdays per year is a sample, not a census. Weekday
and month are held fixed, which controls the largest sources of composition drift,
and three days per year gives a visible spread — but three points is a **range, not a
confidence interval**, and none of these numbers should be quoted with an implied
one.

That the third day matters is not hypothetical. On **2025-09-10**, `dependabot[bot]`
opened **15,885 pull requests across 15,782 distinct repositories in a single hour** —
one security advisory fanning out across the ecosystem. The same hour on the
Wednesdays either side of it carried 893 and 2,226. A one-day sample that happened to
land there would have reported bots overtaking humans; three days show that day as the
outlier it is. Any single-day figure from this dataset is untrustworthy by
construction.

*What would settle it:* consecutive-day collection (a full week per reference point)
and a bootstrap over hours. `make collect` already supports `--every 1`; the cost is
time and bandwidth, not new code.

## 3. Account classification is a name heuristic

`is_bot()` catches the `[bot]` suffix — authoritative for GitHub Apps — plus a
hand-maintained list of well-known automation accounts. `is_agent()` holds a
hand-maintained list of coding agents, which is where the heuristic is weakest: it
can only ever name the agents that already exist and announce themselves, so **the
agent share is a floor that will always lag reality**, and a new agent moves the
number the day it is added to the list rather than the day it starts submitting.

An agent driven from an ordinary personal access token is classified as human. That
is intentional — it is the population metric 2 exists for — but it means any shift in
how automation authenticates moves both numbers for reasons unrelated to behaviour.

An earlier revision missed this entirely: GitHub's Copilot coding agent posts under
the plain login `Copilot` with no `[bot]` suffix, so it was being counted as a human
contributor at roughly a thousand pull requests a day.

## 4. The threshold is a choice

Three repositories per day is a cut, not a law of nature. The published sweep shows
the share at 2, 3, 4, 5 and 10 repositories, and it falls steeply as the threshold
rises. Anyone who prefers a stricter cut can read their number straight off the
sweep — but they should read the trend at *their* threshold, not mix thresholds
across years.

## 5. The 2026 archive is not usable here

Archive hours sampled from 2026 arrive with a trimmed payload (no
`author_association`, no `merged`) and with total event volumes several times lower
than adjacent years. That is an artefact of the archive pipeline, not a collapse in
GitHub activity. Any 2026 row in `data/` is published for transparency and is
**excluded from the chart and from every claim**, and the collector marks it
`"all_hours_full_schema": false` so the exclusion is mechanical rather than a
judgement call.

## 6. Suppressed rows are invisible by design — and the floor has been wrong once

Repository rows with fewer than `--min-cell` distinct human actors are withheld, so
the per-repository tables systematically omit small projects — which are also the
projects most exposed to a single spraying account. The count of withheld rows is
published, but their contents are not recoverable from this dataset, and no claim
here covers them.

This floor has already failed once: it was applied in two of the three emitting
functions and missed in the third, and the first published dataset carried 205
below-floor rows. If you are reviewing this repository for privacy, the emitters —
not the documentation — are where to look, and `tests/test_metrics.py` parametrises
over all of them.

## 7. What would falsify the headline

Any claim about direction between years would be falsified by:

- the same measurement over full weeks showing the yearly differences inside normal
  week-to-week variation;
- the rise disappearing once event-week repositories (Hacktoberfest and similar) are
  excluded;
- the rise being carried by a handful of accounts whose removal flattens it — the
  published `fanout_actors` counts are there so this can be checked;
- the rise appearing equally at threshold 10, which would suggest a change in
  *legitimate* multi-repository work rather than mass submission.

If any of these turn out to be true, that belongs in this file, not in a footnote.
