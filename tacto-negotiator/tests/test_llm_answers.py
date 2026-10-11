"""`model_answers`: direct supplier questions answered from an allowlist; the validator is the gate."""

import json
import os
from pathlib import Path

import pytest

from negotiator import llm_answers
from negotiator.agent import PackageAgent
from negotiator.llm import LlmClient
from negotiator.policy import PolicyConfig

DATA = Path(os.environ.get("ARENA_DATA", "data/package"))
needs_data = pytest.mark.skipif(not (DATA / "facts.json").is_file(), reason="data package not present")


def case(cid):
    cases = json.loads((Path(__file__).parent / "fixtures/practice_cases.json").read_text())
    return next(c for c in cases if c["case_id"] == cid)


def stub(answer):
    def fn(context, timeout_s):
        if isinstance(answer, BaseException):
            raise answer
        return json.loads(json.dumps(answer))
    return fn


P07_EVENTS = [
    {"from": "sales", "status": "open", "body": "Dear customer, we can offer €5.74 per unit, Zahlungsziel 30 days.",
     "term_sheets": [{"term_sheet_id": "offer:0", "terms": {"unit_price": 5.74, "payment_days": 30,
                                                           "contract_months": 12}}]},
    {"from": "buyer", "body": "Thank you for your offer. To go ahead we propose the attached terms: unit price EUR "
                              "5.05, payment days 90, contract months 24.\n\nThe kit puts the whole annual volume of "
                              "all 4 parts with one supplier: 2070000 pieces a year, of which 1308000 pieces a year "
                              "are delivered by other suppliers today. Our forecast fc:360012@2026-09 for part:360012 "
                              "is 654000 pieces a year.",
     "refs": ["fc:360012@2026-09"],
     "term_sheets": [{"terms": {"unit_price": 5.05, "payment_days": 90, "contract_months": 24}}]},
    {"from": "sales", "status": "open",
     "body": "We checked the volume change data you cited; it holds. Our current Angebot is €5.59 per unit, "
             "Zahlungsziel 90 days net, 24 months. Alternatively, with Zahlungsziel 30 days net: €5.52 per unit. "
             "Our standard Zahlungsziel is 30 days net. A binding higher volume would help us and can improve the "
             "price. Which volume can you commit to? Which figures is that based on? Please send us the data. "
             "Please do not hesitate to reach out if you have any questions.",
     "term_sheets": [{"term_sheet_id": "offer:1", "terms": {"unit_price": 5.59, "payment_days": 90,
                                                           "contract_months": 24}}]},
]
OFFERED = {"unit_price": 5.16, "payment_days": 90, "contract_months": 24}
FACTS = {"kit_total_pieces_per_year": 2070000, "pieces_per_year_moved_from_other_suppliers": 1308000,
         "binding_kits_per_year": 30000, "kits_over_full_term": 60000, "supplier_pricing_committee_threshold_pct": 2.0}


def p07_case():
    c = case("case:P07")
    return {**c, "fixed_terms": {**(c.get("fixed_terms") or {}), "volume_per_year": 30000}}


def allow():
    return llm_answers.allowlist(p07_case(), P07_EVENTS, OFFERED, FACTS)


def test_detects_direct_questions_and_ignores_pleasantries():
    qs = llm_answers.questions(P07_EVENTS[-1]["body"])
    assert qs == ["Which volume can you commit to?", "Which figures is that based on?"]
    assert llm_answers.questions("Thank you for your order. Please decide.") == []


def test_allowlist_separates_term_figures_from_public_thread_figures():
    a = allow()
    assert {5.16, 90, 24, 30000, 60000, 2070000, 1308000, 2.0} <= a["term_numbers"]
    assert 5.59 in a["numbers"] and 5.59 not in a["term_numbers"]  # supplier's price: public, not our term
    assert "fc:360012@2026-09" in a["ids"] and a["facts"]["offered_terms"] == OFFERED
    assert a["facts"]["supplier_latest_quote"]["unit_price"] == 5.59


@pytest.mark.parametrize("text,why", [
    ("We commit to 35000 kits a year for 24 months.", "unknown number"),
    ("We can accept 30 days payment at EUR 5.16.", "unit figure"),  # 30 is public but not our offered term
    ("Our budget allows EUR 5.16 at 90 days.", "internal"),
    ("Our target is 5.16; our alternative supplier quotes less.", "internal"),
    ("The price is based on our estimate of your costs.", "internal"),
    ("See forecast fc:360030@2026-09 for the figures.", "unknown id"),
    ("Yes. We commit. To 30000 kits. For 24 months. Fine.", "too many sentences"),
    ("Dear Mr Stadler, we commit to 30000 kits a year.", "padding"),
    ("No figures for PPI-C2611 are available to share.", "admits a gap"),
    ("", "empty"),
])
def test_validator_rejects_unknown_numbers_internal_values_and_padding(text, why):
    ok, reason = llm_answers.validate(text, allow())
    assert not ok, (text, reason)


def test_validator_accepts_an_answer_built_only_from_allowlisted_facts():
    text = ("On volume: with the attached package we commit bindingly to 30,000 kits a year for the full 24 months, "
            "60000 kits in total. The figures are the kit volume of 2070000 pieces a year and our forecast "
            "fc:360012@2026-09, which you have verified; the price of EUR 5.16 reflects that volume at 90 days.")
    ok, reason = llm_answers.validate(text, allow())
    assert ok, reason


def test_draft_returns_none_on_timeout_garbage_or_invalid_answer():
    client = LlmClient(stub(TimeoutError()))
    assert llm_answers.draft(client, ["Which volume can you commit to?"], allow())[0] is None
    client = LlmClient(stub({"answer": "We commit to 99999 kits."}))
    text, reason = llm_answers.draft(client, ["Which volume can you commit to?"], allow())
    assert text is None and "unknown number" in reason
    client = LlmClient(stub({"nope": 1}))
    assert llm_answers.draft(client, ["Which volume can you commit to?"], allow())[0] is None
    assert llm_answers.draft(client, [], allow()) == (None, "no question")


@needs_data
def test_p07_later_round_uses_validated_answer_else_the_commitment_template(monkeypatch):
    monkeypatch.setenv("ARENA_DATA", str(DATA))
    c = case("case:P07")
    sid = c["suppliers"][0]
    events = [{**P07_EVENTS[0], "from": sid}, P07_EVENTS[1], {**P07_EVENTS[2], "from": sid}]
    base = {"version": 1, "bundle_volume_types": ["bundling"], "bundle_commitment_types": ["bundling"]}
    plain = PackageAgent(policy=PolicyConfig.from_dict(base), claims=False)
    template_move = plain.propose(c, {sid: list(events)}, sid)["message"]
    assert "On your question about volume: with this package we commit bindingly to 30000 kits" in template_move["body"]

    good = "On volume: with this package we commit bindingly to 30000 kits a year for the full 24 months."
    agent = PackageAgent(policy=PolicyConfig.from_dict({**base, "model_answers": ["bundling"]}), claims=False,
                         llm=stub({"answer": good}))
    move = agent.propose(c, {sid: list(events)}, sid)["message"]
    assert move["term_sheets"] == template_move["term_sheets"]  # answers never touch the sheet
    assert move["body"].endswith("\n\n" + good) and "On your question about volume" not in move["body"]

    bad = PackageAgent(policy=PolicyConfig.from_dict({**base, "model_answers": ["bundling"]}), claims=False,
                       llm=stub({"answer": "We commit to 45000 kits a year; our budget allows it."}))
    move = bad.propose(c, {sid: list(events)}, sid)["message"]
    assert move["body"] == template_move["body"]  # rejected: template kept verbatim

    down = PackageAgent(policy=PolicyConfig.from_dict({**base, "model_answers": ["bundling"]}), claims=False,
                        llm=stub(TimeoutError()))
    assert down.propose(c, {sid: list(events)}, sid)["message"]["body"] == template_move["body"]


@needs_data
def test_no_question_means_no_model_call_and_no_body_change(monkeypatch):
    monkeypatch.setenv("ARENA_DATA", str(DATA))
    c = case("case:P03")
    sid = c["suppliers"][0]
    events = [{"from": sid, "status": "open", "body": "Thank you for your enquiry. We offer €438.21 per unit.",
               "term_sheets": [{"term_sheet_id": "offer:0", "terms": {"unit_price": 438.21, "payment_days": 30,
                                                                     "contract_months": 12, "volume_per_year": 4580}}]}]
    calls = []

    def fn(context, timeout_s):
        calls.append(context)
        return {"answer": "x"}

    policy = PolicyConfig.from_dict({"version": 1, "package_types": ["renewal"], "model_answers": ["renewal"]})
    agent = PackageAgent(policy=policy, claims=False, llm=fn)
    plain = PackageAgent(policy=PolicyConfig.from_dict({"version": 1, "package_types": ["renewal"]}), claims=False)
    assert agent.propose(c, {sid: list(events)}, sid)["message"]["body"] == \
        plain.propose(c, {sid: list(events)}, sid)["message"]["body"]
    assert calls == []
