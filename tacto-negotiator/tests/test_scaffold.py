import pytest

from negotiator import client, guards, optimizer, traits


@pytest.mark.parametrize(
    "path", ["/v1/events", "/v1/events/stream", "/screen", "/v1/leaderboard?set=final", "/results/team-x"]
)
def test_forbidden_paths_blocked(path):
    with pytest.raises(client.ForbiddenEndpoint):
        client.assert_allowed(path)


@pytest.mark.parametrize("path", ["/v1/cases?set=final", "/v1/sessions/s1", "/v1/me"])
def test_allowed_paths(path):
    client.assert_allowed(path)


def test_leak_guard():
    assert guards.leaks("We have no alternative and need this urgently.")
    assert not guards.leaks("Thank you for your offer. Could you send a cost breakdown?")


def test_payment_breakeven():
    case = {"buyer": {"interest_rate": 0.08}}
    assert optimizer.payment_breakeven_pct(case, 60, 14) == pytest.approx(1.0222, abs=1e-3)


def test_trait_patterns_match_templates():
    samples = {
        "pricing_committee": "price changes above 2 % need the approval of their pricing committee",
        "liquidity_crisis": "said the bank is watching every month",
        "hedged_inputs": "they bought their electricity forward until December 2028",
    }
    for trait, text in samples.items():
        assert traits.NOTE_TRAITS[trait].search(text), trait
