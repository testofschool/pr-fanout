# Why this measurement matters now

## GitHub has acknowledged the review burden

On February 12, 2026, Ashley Wolf, GitHub's Director of Open Source Programs,
described how easier contribution creation can overwhelm maintainers' review
capacity: "The cost to create has dropped but the cost to review has not."
[GitHub's maintainer post](https://github.blog/open-source/maintainers/welcome-to-the-eternal-september-of-open-source-heres-what-we-plan-to-do-for-maintainers/)
recognizes that even contributions made in good faith can exceed that capacity.

## GitHub has introduced pull request limits

On June 18, 2026, GitHub described its newly introduced pull request limits as a
response to incoming contribution volume and low-quality noise. The post reports
about 25 million monthly merged pull requests across GitHub in January 2023,
compared with more than 90 million at publication, roughly a 3.6x increase. These
are counts of merged pull requests across GitHub, not an agent-authorship share of
public opened pull requests.
[GitHub's pull request limits announcement](https://github.blog/open-source/maintainers/how-pull-request-limits-are-cutting-down-the-noise/)

## GitHub has published review and author-side figures

On May 7, 2026, Andrea Griffiths wrote: "More than one in five code reviews on
GitHub now involve an agent."
[GitHub's guide to reviewing agent pull requests](https://github.blog/ai-and-ml/generative-ai/agent-pull-requests-are-everywhere-heres-how-to-review-them/)
describes an automated review pass. That is a reviewer-side statistic.

GitHub has also published an author-side count. In a section about Copilot coding
agent, [Octoverse 2025](https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/)
(published October 28, 2025; updated February 28, 2026) states:

> A first glimpse of coding agent shows 1+ million pull requests that were created between May 2025 and September 2025.

This is an absolute count over five months. The article includes methodology, but
does not attach a matching denominator or an executable reconstruction to this
agent count. pr-fanout adds a share with an explicit denominator and reproducible
collection method for its public sample, plus a 2023 baseline.

These figures cannot be converted into comparable rates. Octoverse's methodology
defaults to public activity unless otherwise noted; private-repository coverage
is not established for the quoted agent count. pr-fanout samples public
repositories, using its own known-agent classification and observation windows.
The article also reports a monthly average of 43.2 million **merged** pull requests
for its 2025 reporting year. Merged PRs are a different event from **opened** PRs;
that monthly average is not a denominator for either the five-month created-PR
count or pr-fanout's sampled opened PRs. No ratio or trend between these figures
is calculated here.

## pr-fanout measures declared coding-agent accounts in the public sample

pr-fanout measures the share of sampled public opened pull requests whose opening
accounts identify themselves as coding agents. This is a lower bound based on
known account identities, not a detector for all AI-written code: an agent using
an ordinary personal account can be indistinguishable from its owner. Fan-out
measures submission breadth and does not prove agent authorship.

The collection and aggregation are reproducible from public GH Archive dumps.
See the [methodology](METHODOLOGY.md) and [limitations](LIMITATIONS.md) before
citing the results.

## Repeated claims still need primary evidence

The source audit supplied for this context did not establish primary evidence for
several circulated authorship claims. It also distinguished anecdotes and forecasts
from measurements. This document omits those claims.
Repetition does not establish a denominator, a collection method, or a measured
result. The linked GitHub publications support the statements above, not a census
of agent-written contributions.

## The degraded archive sample cannot establish the effect of limits

The stored [sampled day](../data/day-2026-09-09.json) from 2026 records
`all_hours_full_schema: false`. Its hourly schema checks flag trimmed payloads;
it cannot be treated as directly comparable to the full-schema reference data.
The [archive health script](../scripts/archive_health.py) independently checks
compressed archive sizes using a minimal HTTP Range request:

```bash
python3 scripts/archive_health.py
```

The live size check found smaller archives for the newer sampled hours. File size
is a screening signal, not proof of schema completeness or event-stream
coverage. Smaller archives cannot establish a decline in GitHub activity or a
causal effect of pull request limits. The schema flag and the size check are
different observations and must be read separately.

Reports require `all_hours_full_schema` to be explicitly `true` for every input.
A degraded, missing, or unknown schema flag is rejected by default with
`COMPARISON_INVALID`. The existing `make report` and `make all` commands select the
mixed bundled files and now intentionally stop at this guard. Choose only
full-schema input files to produce a valid report.

For inspection of every bundled input, run:

```bash
PYTHONPATH=src python3 -m pr_fanout report \
  --inputs 'data/day-*.json' --out /tmp/pr-fanout-inspection --allow-degraded
```

The override includes every input and retains `COMPARISON_INVALID` in the terminal,
Markdown, SVG, and JSON outputs; it does not validate the comparison. This dataset
cannot currently answer whether pull request limits reduced unwanted submissions.
Answering that question would require comparable coverage and a suitable evaluation
design.
