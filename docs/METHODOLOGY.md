# Methodology

## The question

Maintainers report that agent-written pull requests have made review unaffordable.
The obvious way to measure that — classify each pull request as AI-written — is a
dead end, and maintainers said so themselves before anyone tried it:

> "any detector good enough to matter just trains undetectable output"
> — GitHub Community Discussion #185387, *Exploring Solutions to Tackle Low-Quality Contributions on GitHub*

So this project measures two things that need no detector at all.

## Metric 1 — declared coding agents

Some agents announce themselves. GitHub's Copilot coding agent opens pull requests
under the plain login `Copilot`; Devin, Cursor, OpenHands and others use equally
identifiable accounts. `bots.py` keeps them in `KNOWN_AGENT_LOGINS`, **separate from
ordinary automation**, because a maintainer reviewing a Dependabot version bump and
a maintainer reviewing an agent's patch are not doing the same work. Every run
reports opened pull requests split three ways: human, dependency/infrastructure bot,
declared coding agent.

Note the one thing this cannot see: an agent driven from a personal access token
looks exactly like its owner. That is the floor, and metric 2 exists because of it.

## Metric 2 — fan-out

Within one UTC day, an account is a **fan-out submitter** if it opens pull requests
against **3 or more distinct repositories**. The headline is the share of
human-opened pull requests that come from such accounts.

Opening many pull requests is not suspicious; maintainers do it constantly. Opening
them across *unfamiliar* codebases is the hard part: reading three strange projects
in a day and producing a correct patch for each is near the limit of what a person
does, and trivially what an agent loop does. Fan-out separates breadth from depth
without ever looking at a diff, and it is expensive to evade while keeping the
payoff — spreading across days or accounts costs exactly the throughput that made
mass submission attractive.

Both the threshold and the window are parameters. Every run also prints a threshold
sweep (2, 3, 4, 5, 10 repositories) and the full distribution of distinct
repositories per account, so a reader can see how much of the result depends on the
cut rather than taking 3 on faith.

### Correction, 2026-09-14

The `--min-cell` floor was applied in two of the three functions that emit a
per-repository row and missed in the third. The first published dataset therefore
carried **205 rows below the floor out of 300, 172 of them with a single
contributor** — a repository name plus a pull-request count for one person, which
is close enough to naming them. The floor now lives in one helper that every
emitter calls, a parametrised test covers all three emitters so a fourth cannot be
added without one, and all ten datasets were re-collected.

The privacy test did not catch this: it searches emitted output for *account names*,
and a single-actor row contains none. Re-identification through a small cell is a
different failure from a leaked login, and it now has its own test.

### Correction, 2026-09-13

An earlier revision of `metrics.py` computed this share from *distinct repositories
per actor* rather than *pull requests per actor*, which systematically discounted
exactly the behaviour the metric exists to surface (40 pull requests to each of 3
repositories reported 2.5%, not 100%). It is fixed, the regression is pinned in
`tests/test_metrics.py::test_numerator_counts_pull_requests_not_repositories`, and
every dataset in `data/` was re-collected afterwards. No number published before
that fix should be cited.

## What is never published

- **No login of a natural person**, anywhere in any output. GitHub's
  [Acceptable Use Policies](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies)
  permit research use of "public, **non-personal** information … only if any
  publications resulting from that research are open access". Aggregates qualify;
  per-contributor behaviour does not. Enforced by `tests/test_privacy.py`, which
  walks every key and value of a produced dataset and fails on any human name.
- **No repository row below `--min-cell` distinct human actors** (default 5). With
  three contributors in a window, a per-repository count is close enough to naming
  them. The count of excluded repositories is published as `suppressed_rows` — hiding the
  withholding would be worse than the withholding. Note what that number counts:
  **every** repository the floor removed while the tables were built, not only the
  ones that would have reached the published top-N. Most repositories see a pull
  request from one person on a given day, so it runs in the tens of thousands. It
  describes the shape of GitHub, not the size of a secret.
- **No repository ranked by rejection rate.** A league table of who rejects most
  would punish maintainers for the coping strategy the flood forced on them.
- **No score, gate, or auto-close.** Fan-out is an observation, not a verdict on a
  contributor, and this repository proposes no mechanism that would keep a
  first-time contributor out.

## Data source

[GH Archive](https://www.gharchive.org/) hourly dumps of the public GitHub event
stream — anonymous, rate-limit-free, and reproducible by anyone auditing this
repository. The GitHub REST API was rejected because it requires per-repository
authorisation a reader cannot replicate.

Sampling: every second hour (12 hours) of three Wednesdays per reference year,
holding weekday and calendar month fixed so weekday and seasonal composition do not
move between comparison points. Three days per year is what makes a year-over-year
statement legible at all — a single day can be moved 20 points by one event, and one
was.

## Two field-tested traps, encoded in the code

1. **User-Agent.** The archive CDN answers the default `Python-urllib/x.y`
   User-Agent with HTTP 403. `archive.py` always sends a descriptive one.
2. **Schema drift.** Some recent archive hours ship a trimmed payload with
   `author_association` and `merged` removed. Computing association metrics on those
   hours silently returns zeros that look like a finding. `schema_probe()` detects it
   per hour, the collector records `full_schema` for every hour, and the report
   refuses to plot any day that is not full-schema throughout.

## Reproducing

```
make collect   # re-measures every reference day from the archive
make report    # rebuilds docs/ from data/
make test
```

CI re-runs a spot collection weekly and fails if the archive schema changes, so this
repository finds out its dataset went stale before a reader does.

The behaviour contract the collector implements — states, ownership rules, and the
replayed traces — is in [`PRODUCT_LOGIC_SPEC.md`](../PRODUCT_LOGIC_SPEC.md).
