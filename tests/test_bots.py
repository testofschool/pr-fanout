from pr_fanout.bots import is_agent, is_bot


def test_app_suffix_is_authoritative():
    assert is_bot("dependabot[bot]")
    assert is_bot("some-random-name[bot]")


def test_known_logins_without_suffix():
    assert is_bot("renovate")
    assert is_bot("Dependabot")  # case-insensitive


def test_humans_are_not_bots():
    for login in ("torvalds", "robotnik", "bottomley", "abbott"):
        assert not is_bot(login), login


def test_missing_login():
    assert not is_bot(None)
    assert not is_bot("")



def test_copilot_is_an_agent_not_a_plain_bot():
    assert is_agent("Copilot")
    assert is_agent("copilot-swe-agent[bot]")
    assert not is_agent("dependabot[bot]")


def test_agents_and_bots_are_disjoint_for_known_logins():
    assert not is_agent("renovate")
    assert is_bot("renovate")
