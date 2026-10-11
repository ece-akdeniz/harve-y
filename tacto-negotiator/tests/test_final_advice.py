"""Final-offer review tests use public terms and synthetic supplier replies only."""

import copy
import json
import time
from pathlib import Path
from types import SimpleNamespace

from negotiator.advice import AdviceExecutionBlocked, CapacityAdvisor
from negotiator.agent import PackageAgent
from negotiator.final_advice import FinalOfferAdvisor, counter_menu
from negotiator.policy import PolicyConfig

ROOT = Path(__file__).resolve().parents[1]
QUOTE = "A lead time of 42 days necessitates a premium."


def p10(*, outside=False):
    case = next(c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())
                if c["case_id"] == "case:P10")
    case = copy.deepcopy(case)
    if outside:
        case["buyer"]["alternative"] = {
            "kind": "quote", "terms": {"unit_price": 36.0, "volume_per_year": 23400,
                                       "contract_months": 24, "lead_time_days": 42}}
    sid = case["suppliers"][0]
    opening = {"unit_price": 32.2, "volume_per_year": 19890,
               "contract_months": 12, "lead_time_days": 54}
    buyer = {"unit_price": 28.34, "volume_per_year": 23400,
             "contract_months": 24, "lead_time_days": 42}
    standing = {**buyer, "unit_price": 33.8}
    variant = {**standing, "unit_price": 31.9, "lead_time_days": 54}
    events = [
        {"from": "supplier", "status": "open", "body": "We have limited capacity.",
         "term_sheets": [{"term_sheet_id": "opening", "terms": opening}]},
        {"from": "buyer", "body": "Our first proposal.", "term_sheets": [{"terms": buyer}]},
        {"from": "supplier", "status": "final_offer", "body": QUOTE + " We can offer 54 days at EUR 31.90.",
         "term_sheets": [{"term_sheet_id": "final", "terms": standing},
                         {"term_sheet_id": "final-a", "terms": variant}]},
    ]
    return case, {sid: events}, sid


def choose(context, _):
    assert context["latest_supplier_message"]["body"].startswith(QUOTE)
    selected = next(iter(context["approved_packages"]))
    return {"selected_id": selected, "message_index": 2, "quote": QUOTE}


def test_menu_normalizes_supplier_variant_to_legal_buyer_counter():
    case, threads, sid = p10()
    menu, standing_cost = counter_menu(case, threads[sid])
    assert len(menu) == 1 and standing_cost > next(iter(menu.values()))["cost"]
    terms = next(iter(menu.values()))["terms"]
    assert terms["lead_time_days"] == 56 and terms["unit_price"] == 31.9


def test_shadow_reads_scoped_ingested_context_and_retains_p10_offer():
    case, threads, sid = p10()
    notes = [{"id": "doc:own", "supplier_id": sid, "text": "Capacity is constrained.",
              "date": "2026-10-01"},
             {"id": "doc:other", "supplier_id": "sup:other", "text": "Private rival detail."}]

    def inspect(context, timeout):
        assert [n["id"] for n in context["public_dossier_notes"]] == ["doc:own"]
        assert "Private rival detail" not in json.dumps(context)
        assert context["prior_assessment"][0]["quote"] == "Capacity is constrained."
        assert context["public_dossier_facts"]["master"] == {"standard_lead_time_days": 42}
        return choose(context, timeout)

    prior = [{"kind": "objection", "span": {"quote": "Capacity is constrained."},
              "fields": ["volume_per_year"], "lifecycle": "active"}]
    adviser = FinalOfferAdvisor(inspect, mode="shadow-v1")
    dossier = SimpleNamespace(master={"standard_lead_time_days": 42, "name": "scoped"},
                              scorecard={}, news=[], history=[])
    result, trace = adviser.select(case, threads, sid, dossier=dossier, notes=notes, prior=prior,
                                   remaining_s=60, walk_bound=.2)
    assert result is None and trace["status"] == "ok"
    assert trace["risk"]["reason"] == "no_comparable_executable_alternative"
    assert adviser.metrics()["calls"] == 1


def test_active_counter_needs_finite_outside_and_code_owned_risk_gate():
    case, threads, sid = p10(outside=True)
    adviser = FinalOfferAdvisor(choose, mode="select-v1")
    result, trace = adviser.select(case, threads, sid, remaining_s=60, walk_bound=.2)
    assert result["lead_time_days"] == 56 and result["unit_price"] == 31.9
    assert trace["changed"] and trace["risk"]["admitted"]
    again, trace = adviser.select(case, threads, sid, remaining_s=60, walk_bound=.2)
    assert again is None and trace["reason"] == "admission_closed"


def test_malformed_citation_and_provider_failure_keep_closing():
    case, threads, sid = p10(outside=True)
    bad = FinalOfferAdvisor(lambda context, timeout: {
        **choose(context, timeout), "quote": "Missing from supplier message"}, mode="select-v1")
    assert bad.select(case, threads, sid, remaining_s=60, walk_bound=.2)[0] is None
    assert bad.metrics()["outcomes"][0]["reason"] == "unsupported_citation"

    def fail(*_):
        raise TimeoutError("provider late")

    timed = FinalOfferAdvisor(fail, mode="select-v1")
    result, trace = timed.select(case, threads, sid, remaining_s=60, walk_bound=.2)
    assert result is None and trace["reason"] == "timeout" and timed.disabled


def test_supplier_alternative_can_support_a_legal_normalized_counter():
    case, threads, sid = p10()
    quote = "Alternatively, with Lieferzeit 54 days: a price of EUR 31.90 per unit."
    threads[sid][-1]["body"] = "This is our last offer. " + quote

    def select(context, _timeout):
        return {"selected_id": next(iter(context["approved_packages"])),
                "message_index": 2, "quote": quote}

    terms, trace = FinalOfferAdvisor(select, mode="explore-v1").select(
        case, threads, sid, remaining_s=60, walk_bound=.2, max_loss_fraction=.4)
    assert trace["status"] == "ok" and trace["changed"]
    assert terms["lead_time_days"] == 56 and terms["unit_price"] == 31.9


def test_validation_model_repairs_final_quote_then_risk_gate_still_applies():
    case, threads, sid = p10()

    def bad(context, timeout):
        return {**choose(context, timeout), "quote": "Invented supplier promise."}

    def validation(context, timeout):
        assert context["rejection_reason"] == "unsupported_citation"
        return choose(context["source_context"], timeout)

    terms, trace = FinalOfferAdvisor(bad, repair_fn=validation, mode="explore-v1").select(
        case, threads, sid, remaining_s=60, walk_bound=.2, max_loss_fraction=.4)
    assert terms["lead_time_days"] == 56 and trace["changed"] and trace["repaired"]
    assert trace["risk"]["admitted"] and trace["repair"]["status"] == "ok"

    held, denied = FinalOfferAdvisor(bad, repair_fn=validation, mode="select-v1").select(
        case, threads, sid, remaining_s=60, walk_bound=.2)
    assert held is None and not denied["changed"] and not denied["risk"]["admitted"]


def test_validator_can_take_over_final_after_primary_provider_timeout():
    case, threads, sid = p10()

    def timeout(*_):
        raise TimeoutError("primary provider late")

    def validation(context, limit):
        assert context["rejected_response"] is None
        assert context["rejection_reason"] == "timeout"
        return choose(context["source_context"], limit)

    adviser = FinalOfferAdvisor(timeout, repair_fn=validation, mode="explore-v1")
    terms, trace = adviser.select(case, threads, sid, remaining_s=60,
                                  walk_bound=.2, max_loss_fraction=.4)
    assert trace["status"] == "ok" and trace["changed"] and trace["repaired"]
    assert adviser.disabled and terms["lead_time_days"] == 56


def test_final_review_preserves_condition_and_rejects_refusal():
    case, threads, sid = p10(outside=True)
    conditional = "If you allow 56 delivery days, we can reduce the price."
    threads[sid][-1]["body"] = conditional

    def cite(context, timeout):
        return {"selected_id": next(iter(context["approved_packages"])),
                "message_index": 2, "quote": conditional}

    # The cited condition remains part of the source-linked observation.
    admitted, trace = FinalOfferAdvisor(cite, mode="select-v1").select(
        case, threads, sid, remaining_s=60, walk_bound=.2)
    assert admitted is not None and trace["evidence_id"].startswith("sha256:")
    refusal = "We cannot accept 56 delivery days."
    threads[sid][-1]["body"] = refusal

    def cite_refusal(context, timeout):
        return {"selected_id": next(iter(context["approved_packages"])),
                "message_index": 2, "quote": refusal}

    result, trace = FinalOfferAdvisor(cite_refusal, mode="select-v1").select(
        case, threads, sid, remaining_s=60, walk_bound=.2)
    assert result is None and trace["reason"] == "no_legal_cheaper_counter"


def test_agent_routes_final_review_before_legacy_accept():
    case, threads, sid = p10(outside=True)
    policy = PolicyConfig.from_dict({"version": 1, "package_advice_types": ["capacity"],
                                     "package_advice_mode": "select-v1",
                                     "final_advice_mode": "select-v1",
                                     "final_review_max_walk_probability": .2})
    agent = PackageAgent(policy=policy)
    agent.final_advisor = FinalOfferAdvisor(choose, mode="select-v1")
    agent.package_notes[sid] = []
    agent.trades.deadlines[sid] = time.time() + 60
    move = agent.decide(case, threads)
    assert move["message"]["term_sheets"][0]["terms"]["lead_time_days"] == 56
    assert "action" not in move["message"]
    agent.validate_decision(case, threads, move)
    assert agent.final_counters[sid] == 1


def test_p10_without_outside_option_reviews_then_accepts():
    case, threads, sid = p10()
    policy = PolicyConfig.from_dict({"version": 1, "package_advice_types": ["capacity"],
                                     "package_advice_mode": "select-v1",
                                     "final_advice_mode": "select-v1",
                                     "final_review_max_walk_probability": .2})
    agent = PackageAgent(policy=policy)
    agent.final_advisor = FinalOfferAdvisor(choose, mode="select-v1")
    agent.package_notes[sid] = []
    agent.trades.deadlines[sid] = time.time() + 60
    move = agent.decide(case, threads)
    assert move["message"]["action"] == {"type": "accept", "term_sheet_id": "final"}
    outcome = agent.experiment_metrics()["final_advice"]["outcomes"][0]
    assert outcome["selected_id"].startswith("counter_")
    assert outcome["reason"] == "no_comparable_executable_alternative"


def test_exploratory_p10_sends_one_sourced_counter_with_explicit_no_deal_downside():
    case, threads, sid = p10()
    policy = PolicyConfig.from_dict({"version": 1, "package_advice_types": ["capacity"],
                                     "package_advice_mode": "select-v1",
                                     "package_advice_max_calls": 0,
                                     "package_advice_total_s": 0,
                                     "final_advice_mode": "explore-v1",
                                     "final_explore_max_loss_fraction": .4,
                                     "final_review_max_walk_probability": .2})
    agent = PackageAgent(policy=policy)
    agent.final_advisor = FinalOfferAdvisor(choose, mode="explore-v1")
    agent.package_notes[sid] = []
    agent.trades.deadlines[sid] = time.time() + 60
    move = agent.decide(case, threads)
    terms = move["message"]["term_sheets"][0]["terms"]
    assert terms["unit_price"] == 31.9 and terms["lead_time_days"] == 56
    assert "action" not in move["message"]
    agent.validate_decision(case, threads, move)
    outcome = agent.experiment_metrics()["final_advice"]["outcomes"][0]
    assert outcome["reason"] == "exploratory_no_alt_counter" and outcome["changed"]
    assert outcome["risk"]["no_deal_scenario_cost"] == 2_185_560
    assert outcome["risk"]["walk_probability"] == "unknown"
    assert 0 < outcome["risk"]["break_even_walk_probability"] < .1
    assert agent.final_counters[sid] == 1
    again = agent.decide(case, threads)
    assert again["message"]["action"] == {"type": "accept", "term_sheet_id": "final"}


def test_skilled_final_reviewer_writes_counter_email_before_dispatch():
    case, threads, sid = p10()
    policy = PolicyConfig.from_dict({"version": 1, "package_advice_types": ["capacity"],
                                     "package_advice_mode": "strategy-v1",
                                     "llm_response_mode": "skill-v1",
                                     "final_advice_mode": "explore-v1",
                                     "final_explore_max_loss_fraction": .4,
                                     "final_review_max_walk_probability": .2})
    agent = PackageAgent(policy=policy)

    def write(context, timeout):
        assert context["write_response"] is True
        assert context["standing_terms"]["unit_price"] == 33.8
        assert context["latest_supplier_message"]["body"].startswith(QUOTE)
        return {**choose(context, timeout), "body": (
            "Thank you for clarifying your position. We propose the attached terms as one package. "
            "These terms are offered together as one conditional package. "
            "Could you confirm the attached package or quote your best complete alternative?"
        )}

    agent.final_advisor = FinalOfferAdvisor(write, mode="explore-v1", write_response=True)
    agent.package_notes[sid] = []
    agent.trades.deadlines[sid] = time.time() + 60
    move = agent.decide(case, threads)
    assert move["message"]["body"].startswith("Thank you for clarifying your position")
    assert move["message"]["term_sheets"][0]["terms"]["lead_time_days"] == 56
    agent.validate_decision(case, threads, move)
    assert agent.final_advisor.metrics()["outcomes"][0]["body_source"] == "model"


def test_invalid_final_email_uses_safe_prepared_body():
    case, threads, sid = p10()

    def write(context, timeout):
        return {**choose(context, timeout), "body": "We accept your offer and guarantee 50 percent savings."}

    adviser = FinalOfferAdvisor(write, mode="explore-v1", write_response=True)
    terms, trace = adviser.select(case, threads, sid, remaining_s=60,
                                  walk_bound=.2, max_loss_fraction=.4)
    assert terms["lead_time_days"] == 56
    assert trace["body_source"] == "deterministic_fallback" and "body" not in trace


def test_written_body_rejects_unsupported_numeric_and_spelled_claims():
    from negotiator.message_prose import checked_body

    terms = {"unit_price": 31.9, "lead_time_days": 56, "volume_per_year": 23400}
    assert checked_body("We propose the attached EUR 31.90 package for 23,400 units.", terms)
    for body in (
        "We propose the attached package and guarantee 99 percent savings.",
        "We propose the attached package with delivery within two weeks.",
        "We propose the attached package with a 56-month contract.",
        "We propose the attached package with a 31.90-day lead time.",
        "We propose the attached package with a private budget allowance.",
        "We propose the attached package based on news:unapproved evidence.",
    ):
        assert checked_body(body, terms) is None


def test_exploration_still_requires_case_priced_downside_and_explicit_limit():
    case, threads, sid = p10()
    case["buyer"]["fallback_risk_pct"] = -1
    adviser = FinalOfferAdvisor(choose, mode="explore-v1")
    result, trace = adviser.select(case, threads, sid, remaining_s=60,
                                   walk_bound=.2, max_loss_fraction=.4)
    assert result is None and trace["reason"] == "no_comparable_executable_alternative"
    case, threads, sid = p10()
    adviser = FinalOfferAdvisor(choose, mode="explore-v1")
    result, trace = adviser.select(case, threads, sid, remaining_s=60,
                                   walk_bound=.2, max_loss_fraction=.3)
    assert result is None and trace["reason"] == "exploratory_loss_limit"


def test_exploratory_config_requires_loss_limit():
    base = {"version": 1, "package_advice_types": ["capacity"],
            "package_advice_mode": "select-v1", "final_advice_mode": "explore-v1"}
    for config in (base, {**base, "final_explore_max_loss_fraction": 2},
                   {**base, "final_explore_max_loss_fraction": .4,
                    "final_review_max_walk_probability": .2,
                    "final_advice_mode": "select-v1"}):
        try:
            PolicyConfig.from_dict(config)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe exploration configuration admitted")


def test_final_reservation_survives_restart_without_charging_package_advice(tmp_path):
    case, threads, sid = p10()
    path = tmp_path / "serial.jsonl"
    first = FinalOfferAdvisor(choose, mode="shadow-v1")
    first.attach("session:1", path)
    first.select(case, threads, sid, remaining_s=60, walk_bound=.2)
    resumed = FinalOfferAdvisor(choose, mode="shadow-v1")
    resumed.attach("session:1", path)
    assert resumed.calls == 1 and resumed.reserved_s == first.reserved_s
    assert resumed.select(case, threads, sid, remaining_s=60, walk_bound=.2)[0] is None
    package = CapacityAdvisor(lambda *_: None)
    package.attach("session:1", path)
    assert package.calls == 0


def test_changed_thread_during_final_review_blocks_stale_action():
    case, threads, sid = p10(outside=True)
    policy = PolicyConfig.from_dict({"version": 1, "package_advice_types": ["capacity"],
                                     "package_advice_mode": "select-v1",
                                     "final_advice_mode": "select-v1",
                                     "final_review_max_walk_probability": .2})
    agent = PackageAgent(policy=policy)

    def mutate(context, timeout):
        threads[sid][-1]["body"] += " Updated while reviewing."
        return choose(context, timeout)

    agent.final_advisor = FinalOfferAdvisor(mutate, mode="select-v1")
    agent.package_notes[sid] = []
    agent.trades.deadlines[sid] = time.time() + 60
    try:
        agent.decide(case, threads)
    except AdviceExecutionBlocked:
        pass
    else:
        raise AssertionError("stale final review was dispatched")


def test_policy_rejects_final_advice_without_supported_adviser():
    try:
        PolicyConfig.from_dict({"version": 1, "final_advice_mode": "select-v1"})
    except ValueError:
        pass
    else:
        raise AssertionError("unsupported final advice configuration admitted")


def test_default_metrics_and_closing_remain_unchanged():
    case, threads, sid = p10()
    default = PackageAgent(policy=PolicyConfig())
    assert "final_advice" not in default.experiment_metrics()
    move = default.decide(case, threads)
    assert move["message"]["action"] == {"type": "accept", "term_sheet_id": "final"}


def test_final_review_uses_small_strict_provider_contract(monkeypatch):
    from negotiator.package_advisor import complete

    monkeypatch.setenv("LLM_API_KEY", "test-only-key")
    monkeypatch.setenv("LLM_MODEL", "test-only-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://model.invalid/v1")
    requests = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": json.dumps({
                "selected_id": "keep", "message_index": -1, "quote": ""})}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 10}}

    class Client:
        def __init__(self, **_):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def post(self, url, **kwargs):
            requests.append(kwargs["json"])
            return Response()

    monkeypatch.setattr("negotiator.package_advisor.httpx.Client", Client)
    case, threads, sid = p10()
    result, trace = FinalOfferAdvisor(complete).select(case, threads, sid, remaining_s=60)
    assert result is None and trace["reason"] == "model_keep"
    assert len(requests) == 1 and requests[0]["max_completion_tokens"] == 400
    assert "# Final-offer review" in requests[0]["messages"][0]["content"]
    schema = requests[0]["response_format"]["json_schema"]
    assert schema["strict"] and schema["schema"]["required"] == ["selected_id", "message_index", "quote"]
    FinalOfferAdvisor(complete, write_response=True).select(case, threads, sid, remaining_s=60)
    assert requests[1]["max_completion_tokens"] == 650
    assert requests[1]["response_format"]["json_schema"]["schema"]["required"] == [
        "selected_id", "message_index", "quote", "body"]
