"""The one spec clause the logic gate cannot express.

"No login of a natural person appears in any output" is a property of emitted
strings, not of a numeric datum, so no oracle in the contract DSL can hold it.
This test holds it instead: it walks every key and value of a produced dataset
and fails if a human account name survives anywhere.
"""
from __future__ import annotations

import json

from pr_fanout.bots import is_agent, is_bot
from pr_fanout.metrics import Window

HUMANS = ["alice", "bob-dev", "Carol_Q", "ok-contributor"]
MACHINES = ["dependabot[bot]", "renovate", "Copilot"]


def _build() -> Window:
    w = Window("privacy", threshold=2)
    for human in HUMANS:
        for repo in ("curl/curl", "golang/go", "django/django"):
            for _ in range(3):
                w.add_opened(human, repo)
    for machine in MACHINES:
        w.add_opened(machine, "curl/curl")
    return w


def _walk(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield str(key)
            yield from _walk(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item)
    else:
        yield str(node)


def test_no_human_login_appears_in_any_output():
    w = _build()
    payload = {
        "summary": w.summary(),
        "sweep": w.sweep_thresholds(),
        "histogram": w.repos_per_actor_histogram(),
        "watchlist": w.watchlist_rows(min_cell=1),
        "top_repos": w.top_repos(min_prs=1, min_cell=1),
        "busiest": w.busiest_repos(min_cell=1),
        "bots": w.top_bot_logins(),
        "agents": w.top_agent_logins(),
    }
    blob = json.dumps(payload)
    for human in HUMANS:
        assert human not in blob, f"human login {human!r} leaked into output"
    # round-trip every token as well, so a nested structure cannot hide one
    tokens = set(_walk(payload))
    assert not (tokens & set(HUMANS))


def test_machine_accounts_are_the_only_names_published():
    w = _build()
    published = {row["login"] for row in w.top_bot_logins()} | {
        row["login"] for row in w.top_agent_logins()
    }
    assert published, "the bot/agent breakdown must not be silently empty"
    for login in published:
        assert is_bot(login) or is_agent(login), f"{login!r} is not a machine account"
