"""Bot-account classification.

Deliberately conservative and *transparent*: every rule is a plain string
predicate you can read, argue with, and override. We would rather
under-classify (leave a bot in the human pool) than silently invent a
category, because the headline metric is a share of *human* pull requests.

A GitHub App posts under a login ending in ``[bot]``; that is the only
authoritative marker. Everything else is a heuristic over well-known
automation accounts, kept in one list so it can be audited in a diff.
"""
from __future__ import annotations

#: Well-known automation accounts that do not always carry the ``[bot]`` suffix.
KNOWN_BOT_LOGINS: frozenset[str] = frozenset(
    {
        "allcontributors",
        "codecov",
        "copybara",
        "dependabot",
        "dependabot-preview",
        "greenkeeper",
        "imgbot",
        "mergify",
        "pull",
        "pyup-bot",
        "renovate",
        "restyled-io",
        "semantic-release-bot",
        "snyk-bot",
        "stale",
        "step-security-bot",
        "whitesource-bolt-for-github",
    }
)

#: Substrings that only ever appear in automation account names.
BOT_SUBSTRINGS: tuple[str, ...] = ("dependabot", "renovate", "greenkeeper")

#: Suffixes/prefixes conventionally used by automation accounts.
BOT_SUFFIXES: tuple[str, ...] = ("[bot]", "-bot", "_bot")
BOT_PREFIXES: tuple[str, ...] = ("bot-",)


def is_bot(login: str | None) -> bool:
    """Return True when ``login`` is an automation account.

    >>> is_bot("dependabot[bot]")
    True
    >>> is_bot("torvalds")
    False
    >>> is_bot(None)
    False
    """
    if not login:
        return False
    low = login.lower()
    if low in KNOWN_BOT_LOGINS:
        return True
    if any(low.endswith(s) for s in BOT_SUFFIXES):
        return True
    if any(low.startswith(p) for p in BOT_PREFIXES):
        return True
    return any(sub in low for sub in BOT_SUBSTRINGS)


#: Accounts that are *coding agents* — they author code changes, unlike a
#: dependency updater or a fork-sync bot. Kept separate from KNOWN_BOT_LOGINS
#: because lumping them together answers the wrong question: a maintainer
#: reviewing a Dependabot version bump and a maintainer reviewing an agent's
#: patch are not doing the same work.
#:
#: GitHub's own Copilot coding agent opens pull requests under the plain login
#: ``Copilot`` with no ``[bot]`` suffix, so name-suffix rules miss it entirely.
KNOWN_AGENT_LOGINS: frozenset[str] = frozenset(
    {
        "codegen-sh",
        "copilot",
        "copilot-swe-agent",
        "cursoragent",
        "cursor-com",
        "devin-ai-integration",
        "factory-droid",
        "openhands-agent",
        "sweep-ai",
    }
)

AGENT_SUBSTRINGS: tuple[str, ...] = ("copilot-swe", "devin-ai", "openhands", "cursoragent")


def is_agent(login: str | None) -> bool:
    """Return True when ``login`` is a known code-writing agent account.

    >>> is_agent("Copilot")
    True
    >>> is_agent("dependabot[bot]")
    False
    """
    if not login:
        return False
    low = login.lower().removesuffix("[bot]")
    if low in KNOWN_AGENT_LOGINS:
        return True
    return any(sub in low for sub in AGENT_SUBSTRINGS)
