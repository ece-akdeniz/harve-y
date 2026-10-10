from dataclasses import replace

import pytest

from negotiator.evidence import evidence_for_offer, index_claims


def fixture():
    facts = {f"idx:ENERGY@{month}": {"series": "ENERGY", "month": month, "value": value}
             for month, value in [("2025-08", 100), ("2026-08", 96.3)]}
    case = {"type": "price_increase", "refs": list(facts), "facts": facts}
    return case, facts


def test_verified_sentence_and_tamper_rejection():
    case, facts = fixture()
    claim = index_claims(case, facts)[0]
    assert "-3.70%" in claim.sentence(facts)
    with pytest.raises(ValueError, match="unsupported"):
        replace(claim, change_pct=12).sentence(facts)
    with pytest.raises(ValueError):
        claim.sentence({})


@pytest.mark.parametrize("value", [0, -10, float("nan"), float("inf"), True, "100"])
def test_bad_values_never_become_claims(value):
    case, facts = fixture()
    facts["idx:ENERGY@2025-08"]["value"] = value
    assert index_claims(case, facts) == []


def test_requires_exact_calendar_window_and_matching_metadata():
    case, facts = fixture()
    facts["idx:ENERGY@2025-08"]["month"] = "2025-07"
    assert index_claims(case, facts) == []


def test_unrelated_series_stale_data_and_other_case_types_are_excluded():
    case, facts = fixture()
    assert index_claims({**case, "refs": []}, facts) == []
    assert index_claims({**case, "type": "quality"}, facts) == []
    facts["idx:OTHER@2027-09"] = {"series": "OTHER", "month": "2027-09", "value": 100}
    assert index_claims(case, facts) == []


def test_case_overlay_wins_and_sent_history_prevents_reuse_across_suppliers():
    case, facts = fixture()
    base = {ref: {**fact, "value": 100} for ref, fact in facts.items()}
    selected = evidence_for_offer(case, base, {})
    assert "-3.70%" in selected[0][1]
    # A decision is not a sent message: repeat calls are stable, including retries.
    assert selected == evidence_for_offer(case, base, {})
    for message in [{"refs": [selected[0][0].refs[0]]}, {"body": selected[0][1]}]:
        assert evidence_for_offer(case, base, {"other": [{"from": "buyer", **message}]}) == []
    assert evidence_for_offer(case, base, {"other": [{"from": "sales", "body": selected[0][1]}]})


def test_at_most_two_claims_and_deterministic_order():
    case, facts = fixture()
    for series in ("B", "C"):
        for month in ("2025-08", "2026-08"):
            ref = f"idx:{series}@{month}"
            facts[ref] = {"series": series, "month": month, "value": 100}
            case["refs"].append(ref)
    selected = evidence_for_offer(case, {}, {}, limit=99)
    assert len(selected) == 2
    assert selected[0][0].refs[0].startswith("idx:ENERGY")


def test_agent_evidence_is_opt_in_and_does_not_change_terms():
    import json
    from importlib.resources import files

    from negotiator.agent import PackageAgent

    case = json.loads(files("arena_kit").joinpath("sim_cases/S01.json").read_text())
    evidence_case, _ = fixture()
    case.update({"refs": evidence_case["refs"], "facts": evidence_case["facts"]})
    sid = case["suppliers"][0]
    threads = {sid: [{"from": "sales", "status": "open", "attachments": [],
                     "term_sheets": [{"term_sheet_id": "offer:a", "terms": {"unit_price": 17}}]}]}
    baseline = PackageAgent().decide(case, threads)["message"]
    agent = PackageAgent(evidence=True)
    candidate = agent.decide(case, threads)["message"]
    assert baseline["term_sheets"] == candidate["term_sheets"]
    assert "refs" not in baseline
    assert "-3.70%" in candidate["body"]
    assert candidate["refs"] == evidence_case["refs"]
    threads[sid].extend([{"from": "buyer", **candidate}, threads[sid][0]])
    assert "refs" not in agent.decide(case, threads)["message"]


def test_hosted_case_uses_only_its_own_cost_driver_series():
    case, facts = fixture()
    case.update(refs=[], parts=["part:ours"])
    links = {"part:other": {"ENERGY"}}
    assert evidence_for_offer(case, facts, {}, series_by_part=links) == []
    links["part:ours"] = {"ENERGY"}
    selected = evidence_for_offer(case, facts, {}, series_by_part=links)
    assert len(selected) == 1
    assert "-3.70%" in selected[0][1]
