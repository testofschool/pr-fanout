# Launch

## Hacker News

**Title** (76 chars, no colon-clickbait, the number does the work):

> AI agents open 1.4% of public GitHub pull requests. Two years ago: 0.02%

**First comment** (post it yourself, immediately, as the author):

> Author here. I got tired of arguing about the AI-slop-on-GitHub question with
> anecdotes, so I measured it off GH Archive.
>
> Two numbers, and they cut against each other:
>
> - Pull requests opened by accounts that *announce themselves* as coding agents went
>   from 0.020% (2023) to 1.40% (2025). Roughly 70x.
> - That is still about 1 in 70 pull requests. Almost all of it is one account —
>   Copilot, 1,097 of 1,175 agent PRs on the day I sampled.
>
> The obvious objection is that agents running under a personal token look like
> humans, so I also measured a behavioural proxy that needs no detector: accounts
> opening PRs to 3+ distinct repos in one day. That rose 2023→2024 and has been flat
> since — it is *not* still climbing.
>
> Things I got wrong and fixed before publishing, both in the repo: the fan-out share
> was initially computed from distinct repos instead of PRs (a 40x understatement in
> the worst case), and GitHub's Copilot agent has no `[bot]` suffix so it was being
> counted as a human at ~1,000 PRs/day.
>
> No logins of real people anywhere in the output, rows below 5 distinct actors are
> withheld, and the withheld count is published. `make all` reproduces every number.
> Limitations are the part I'd actually like torn apart: three days a year is a
> range, not a confidence interval.

**When**: 12–17 UTC is the measured-best window (that's 21:00–02:00 KST). Post at the
start of it, not the end, and be at the keyboard for the two hours after — the first
comments decide the thread.

**Do not**: use the "Show HN" prefix. Measured effect on stars was not significant
(−119 at 48h, p=0.39).

## Elsewhere

- **r/programming** and **r/ExperiencedDevs** — same title, drop the "Author here",
  lead with the 1-in-70 framing rather than the 70x. Reddit punishes hype openings.
- **LinkedIn** — this is the one that carries your name in Korea. Lead with the
  method, not the number: "나는 AI 슬롭 논쟁을 일화 말고 숫자로 보고 싶었다" and link the repo.
- **Do not** submit to any "awesome-" list until the repo has independent issues.
  Self-added list entries are the first thing that reads as astroturf.

## The asset still missing

A ~10s terminal GIF at the top of the README, showing `collect` running and printing
hours, then the summary. Record with `asciinema rec` + `agg`, cap at 800px wide and
under 2 MB, no music, no zoom. This is the single highest-leverage README asset and
costs about 20 minutes; a rendered video is not worth building before there is
traffic to justify it.
