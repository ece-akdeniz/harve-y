import copy
import json
import threading
import time
from pathlib import Path

import pytest
from arena_kit.cost import total_cost
from test_final_robust import FakeTable
from test_package_advisor import fixture

from negotiator.advice import (
    AdviceCompletion,
    AdviceExecutionBlocked,
    CapacityAdvisor,
    candidates,
    commercial_changes,
)
from negotiator.agent import PackageAgent
from negotiator.play import guarded_decision, play_case
from negotiator.policy import PolicyConfig


def response(context, *, field="contract_months", value=36, kind="objection"):
    source = context["supplier_messages"][-1]
    selected = next(k for k, t in context["approved_packages"].items() if t.get(field) == value)
    fields = [f for f, v in context["approved_packages"][selected].items()
              if v != context["scheduled_terms"].get(f)]
    return {"selected_id": selected, "support_index": 0, "acknowledgement": "consideration",
            "observations": [{"kind": kind, "message_index": source["message_index"], "quote": source["body"],
                              "public_note_id": None, "addressed_fields": fields}]}


def keep(*_):
    return {"selected_id": "keep", "support_index": -1, "acknowledgement": "none", "observations": []}


def agent_for(case, threads, fn=keep, **limits):
    agent = PackageAgent(policy=PolicyConfig(package_advice_types=("capacity",),
                                            package_advice_mode="guarded-v1", cost_neutral_lead_time=True))
    agent.package_advisor = CapacityAdvisor(fn, **limits)
    agent.package_notes[case["suppliers"][0]] = []
    agent.trades.deadlines[case["suppliers"][0]] = time.time() + 60
    return agent


def test_joint_conditional_offer_and_cost_envelope():
    case, threads, move = fixture()
    sid = move["supplier_id"]
    terms = move["message"]["term_sheets"][0]["terms"]
    conditional = {**terms, "lead_time_days": 56, "contract_months": 36}
    threads[sid][-1]["body"] = "We can accept this price only if delivery is 56 days and the contract is 36 months."
    threads[sid][-1]["term_sheets"] = [{"terms": conditional}]
    small, _ = candidates(case, threads[sid], terms, None, .01)
    large, ceiling = candidates(case, threads[sid], terms, None, .03)
    assert conditional not in small.values() and conditional in large.values()
    assert all(total_cost(case, t) <= ceiling for t in large.values())
    def choose(context, _):
        answer = response(context, field="lead_time_days", value=56, kind="conditional_trade")
        answer["selected_id"] = next(k for k, t in context["approved_packages"].items() if t == conditional)
        answer["observations"][0]["addressed_fields"] = ["lead_time_days", "contract_months"]
        return answer
    changed, trace = CapacityAdvisor(choose, concession=.03).select(case, threads, move, remaining_s=60)
    assert trace["changed"] and trace["observations"][0]["quote"] == threads[sid][-1]["body"]
    assert changed["message"]["term_sheets"][0]["terms"] == conditional
    assert "56" in changed["message"]["body"] and "36" in changed["message"]["body"]
    assert "only if" not in changed["message"]["body"]  # model evidence is never outgoing prose


def test_paired_current_constraints_select_different_complete_trades():
    case, base_threads, move = fixture()
    sid = move["supplier_id"]
    cases = [
        ("We need a longer contract commitment to allocate capacity.", "contract_months", 36),
        ("We need more delivery time to handle the schedule.", "lead_time_days", 56),
    ]
    selected = []
    for body, field, value in cases:
        threads = copy.deepcopy(base_threads)
        threads[sid][-1]["body"] = body
        def choose(context, _, chosen_field=field, chosen_value=value):
            raw = response(context, field=chosen_field, value=chosen_value)
            raw["selected_id"] = next(k for k, t in context["approved_packages"].items()
                                      if t.get(chosen_field) == chosen_value
                                      and t["unit_price"] == context["scheduled_terms"]["unit_price"]
                                      and sum(t.get(f) != context["scheduled_terms"].get(f)
                                              for f in context["scheduled_terms"] if f != "unit_price") == 1)
            raw["observations"][0]["addressed_fields"] = [chosen_field]
            return raw
        result, trace = CapacityAdvisor(choose, concession=.03).select(
            case, threads, move, remaining_s=60)
        assert trace["admitted"] and trace["changed"]
        selected.append(result["message"]["term_sheets"][0]["terms"])
    assert selected[0]["contract_months"] == 36
    assert selected[1]["lead_time_days"] == 56
    assert selected[0] != selected[1]


def test_bounded_menu_keeps_relevant_delivery_and_other_issue_coverage():
    case, threads, move = fixture()
    sid = move["supplier_id"]
    case["term_options"]["contract_months"] = list(range(12, 84, 6))
    case["term_options"]["lead_time_days"] = list(range(35, 119, 7))
    threads[sid][-1]["body"] = "We need more delivery time to handle the schedule."
    menu, _ = candidates(case, threads[sid], move["message"]["term_sheets"][0]["terms"],
                         None, .03)
    assert len(menu) == 16
    assert any(terms["lead_time_days"] > 42 for terms in menu.values())
    assert any(terms["contract_months"] != 24 for terms in menu.values())


def test_price_only_concessions_excluded_and_alternative_remains_independent(monkeypatch):
    case, threads, move = fixture()
    terms = move["message"]["term_sheets"][0]["terms"]
    packages, _ = candidates(case, threads[move["supplier_id"]], terms, None, .01)
    assert packages and all(any(t.get(f) != v for f, v in terms.items() if f != "unit_price")
                            for t in packages.values())
    baseline = total_cost(case, terms)
    monkeypatch.setattr("negotiator.advice.alternative_cost", lambda _: baseline - 1000)
    packages, _ = candidates(case, threads[move["supplier_id"]], terms, None, .03)
    assert all(total_cost(case, t) < baseline - 1000 for t in packages.values())


def test_supplier_price_only_sheet_cannot_bypass_exchange_requirement():
    case, threads, move = fixture()
    sid = move["supplier_id"]
    terms = move["message"]["term_sheets"][0]["terms"]
    price_only = {**terms, "unit_price": 28.48}
    threads[sid][-1]["term_sheets"] = [{"terms": price_only}]
    packages, _ = candidates(case, threads[sid], terms, None, .01)
    assert price_only not in packages.values()


@pytest.mark.parametrize("fault", ["unrelated_field", "partial_joint", "quote_only", "foreign_note"])
def test_exact_citation_without_relevant_trade_support_falls_back(fault):
    case, threads, move = fixture()
    def model(context, _):
        raw = response(context)
        if fault == "unrelated_field":
            raw["observations"][0]["addressed_fields"] = ["unit_price"]
        elif fault == "partial_joint":
            raw["selected_id"] = next(k for k, t in context["approved_packages"].items()
                                      if t["contract_months"] == 36 and t["lead_time_days"] == 56)
        elif fault == "quote_only":
            raw["observations"][0]["kind"] = "stated_terms"
        else:
            raw["observations"].append({**raw["observations"][0], "message_index": -1,
                                        "public_note_id": "doc:other-supplier"})
        return raw
    actual, trace = CapacityAdvisor(model, concession=.03).select(case, threads, move, remaining_s=60)
    assert actual == move and trace["status"] == "fallback"
    assert trace["reason"] == {"unrelated_field": "unsupported_trade_fields",
                               "partial_joint": "unsupported_trade_fields",
                               "quote_only": "quotation_without_trade_evidence",
                               "foreign_note": "foreign_or_invalid_citation"}[fault]


@pytest.mark.parametrize("kind,admitted", [("objection", False), ("conditional_trade", True)])
def test_price_increase_needs_explicit_complete_supplier_exchange(kind, admitted):
    case, threads, move = fixture()
    sid = move["supplier_id"]
    terms = move["message"]["term_sheets"][0]["terms"]
    exchange = {**terms, "unit_price": 28.48, "contract_months": 36}
    threads[sid][-1].update(body="We can reserve capacity only with a 36-month contract at EUR 28.48.",
                            term_sheets=[{"terms": exchange}])
    actual, trace = CapacityAdvisor(lambda c, _: response(c, kind=kind), concession=.01).select(
        case, threads, move, remaining_s=60)
    assert trace["admitted"] is admitted
    assert actual["message"]["term_sheets"][0]["terms"] == (exchange if admitted else terms)


def saved_p10():
    return json.loads(Path("tests/fixtures/p10-capacity-advice-repair.json").read_text())


def delivery_trade(context, _):
    raw = response(context, field="lead_time_days", value=56, kind="stated_terms")
    note = next(n for n in context["public_dossier_notes"] if n["id"].endswith("-P10"))
    raw["observations"].append({"kind": "objection", "message_index": -1,
                                "public_note_id": note["id"], "quote": note["text"],
                                "addressed_fields": ["lead_time_days"]})
    return raw


def test_saved_p10_opening_exposes_costed_delivery_trade_with_scoped_evidence():
    case, _, _ = fixture()
    saved = saved_p10()
    sid, move = saved["supplier_id"], saved["scheduled_move"]
    threads = {sid: saved["messages"][:1]}
    notes = copy.deepcopy(saved["public_notes"])
    notes[0].update(full_cost=987654, reservation_cost=987654)
    notes.append({"id": "doc:foreign", "supplier_id": "sup:other", "text": "Secret foreign conditions."})
    seen = []
    def model(context, timeout):
        seen.append(context)
        return delivery_trade(context, timeout)
    actual, trace = CapacityAdvisor(model, concession=.01).select(
        case, threads, move, public_notes=notes, remaining_s=60)
    assert trace["admitted"] and trace["changed"]
    terms = actual["message"]["term_sheets"][0]["terms"]
    assert terms == {"unit_price": 27.62, "volume_per_year": 23400,
                     "contract_months": 24, "lead_time_days": 56}
    from arena_kit.docs import standard_terms

    assert total_cost(case, terms, standard_terms(threads[sid])) <= total_cost(
        case, move["message"]["term_sheets"][0]["terms"], standard_terms(threads[sid]))
    context = seen[0]
    assert context["response_contract"] == "capacity-advice-v2"
    assert context["case_requirements"]["must_haves"] == [
        {"field": "volume_per_year", "op": ">=", "value": 22230}]
    assert context["case_requirements"]["preferred_lead_time_days"] == 42
    assert all(n["supplier_id"] == sid and n.get("date") for n in context["public_dossier_notes"])
    text = json.dumps(context)
    assert all(secret not in text for secret in ("987654", "reservation_cost", "doc:foreign", "c_best"))
    assert "pricing committee" not in actual["message"]["body"]


def test_current_resolution_supersedes_historical_delivery_constraint():
    case, _, _ = fixture()
    saved = saved_p10()
    sid, move = saved["supplier_id"], saved["scheduled_move"]
    threads = {sid: copy.deepcopy(saved["messages"][:1])}
    threads[sid][-1]["body"] = "Delivery is now stable; we can meet the original schedule."
    actual, trace = CapacityAdvisor(delivery_trade, concession=.01).select(
        case, threads, move, public_notes=saved["public_notes"], remaining_s=60)
    assert actual == move and trace["reason"] == "historical_constraint_resolved"


def test_cited_note_must_independently_support_its_claimed_trade_field():
    case, _, _ = fixture()
    saved = saved_p10()
    sid, move = saved["supplier_id"], saved["scheduled_move"]
    threads = {sid: copy.deepcopy(saved["messages"][:1])}
    notes = [{"id": "doc:unrelated", "supplier_id": sid,
              "text": "Our payment processing is slow this month."}]
    def choose(context, _):
        answer = response(context, field="lead_time_days", value=56, kind="stated_terms")
        answer["observations"].append({"kind": "objection", "message_index": -1,
                                       "public_note_id": "doc:unrelated", "quote": notes[0]["text"],
                                       "addressed_fields": ["lead_time_days"]})
        return answer
    actual, trace = CapacityAdvisor(choose, concession=.01).select(
        case, threads, move, public_notes=notes, remaining_s=60)
    assert actual == move and trace["reason"] == "historical_support_not_admitted"


def test_combined_agent_loads_supplier_notes_and_preserves_final_closing(monkeypatch):
    from types import SimpleNamespace

    case, _, _ = fixture()
    saved = saved_p10()
    sid = saved["supplier_id"]
    threads = {sid: saved["messages"][:1]}
    calls = []
    monkeypatch.setattr("negotiator.dossiers.load_package", lambda: object())
    def build(package, supplier):
        calls.append(supplier)
        return SimpleNamespace(notes=list(reversed(saved["public_notes"])))
    monkeypatch.setattr("negotiator.dossiers.build_one", build)
    agent = agent_for(case, threads, delivery_trade)
    del agent.package_notes[sid]
    selected = agent.decide(case, threads)
    agent.validate_decision(case, threads, selected)
    assert calls == [sid] and selected["message"]["term_sheets"][0]["terms"]["lead_time_days"] == 56
    # Replay the actual final history, not a fictional response to the changed opening.
    final_threads = {sid: saved["messages"]}
    baseline = PackageAgent(policy=PolicyConfig(cost_neutral_lead_time=True))
    baseline.trades.deadlines[sid] = time.time() + 60
    candidate = agent_for(case, final_threads, lambda *_: pytest.fail("final must bypass advice"))
    assert candidate.decide(case, final_threads) == baseline.decide(case, final_threads)


def test_relationship_costs_are_checked_without_inverse_search(monkeypatch):
    case, threads, move = fixture()
    supplier = {"full_cost": 24.31, "interest_rate": .08, "standard": {}}
    monkeypatch.setattr("negotiator.package_advisor.price_for_cost", lambda *_: pytest.fail("inverse search"))
    terms = move["message"]["term_sheets"][0]["terms"]
    packages, ceiling = candidates(case, threads[move["supplier_id"]], terms, supplier, .03)
    assert all(total_cost(case, t, supplier=supplier) <= ceiling for t in packages.values())


@pytest.mark.parametrize("fault", ["foreign", "buyer_citation", "unknown_package", "extra", "bad_type", "no_support"])
def test_rejected_advice_preserves_exact_move(fault):
    case, threads, move = fixture()
    sid = move["supplier_id"]
    threads[sid].insert(0, {"from": "buyer", "body": "We need a longer contract commitment to allocate capacity."})
    before = copy.deepcopy(move)
    def bad(context, _):
        raw = response(context)
        if fault == "foreign":
            raw["observations"][0]["quote"] = "Different supplier's conditions."
        elif fault == "buyer_citation":
            raw["observations"][0]["message_index"] = 0
        elif fault == "unknown_package":
            raw["selected_id"] = "invented"
        elif fault == "extra":
            raw["body"] = "We promise exclusivity."
        elif fault == "bad_type":
            raw["support_index"] = True
        else:
            raw["observations"] = []
        return raw
    advisor = CapacityAdvisor(bad)
    selected, trace = advisor.select(case, threads, move, remaining_s=60)
    assert selected == before == move and trace["status"] == "fallback" and not trace["admitted"]
    assert advisor.metrics()["outcomes"][0]["reason"] == trace["reason"]


def test_refused_acknowledged_package_is_excluded_and_history_not_truncated():
    case, threads, move = fixture()
    sid = move["supplier_id"]
    rejected = {**move["message"]["term_sheets"][0]["terms"], "contract_months": 36}
    threads[sid].insert(0, {"from": "buyer", "term_sheets": [{"terms": rejected}]})
    threads[sid][-1]["body"] = "We refuse the 36-month commitment; keep a 24-month contract."
    def inspect(context, _):
        assert rejected not in context["approved_packages"].values()
        assert context["supplier_messages"][-1]["body"] == threads[sid][-1]["body"]
        return keep()
    assert CapacityAdvisor(inspect).select(case, threads, move, remaining_s=60)[0] == move
    threads[sid][0]["from"] = sid
    threads[sid][0]["body"] = "Earlier refusal " * 4000
    selected, trace = CapacityAdvisor(lambda *_: pytest.fail("oversized context")).select(
        case, threads, move, remaining_s=60)
    assert selected == move and trace["reason"] == "context_bound"


def test_timeout_quarantines_late_output_and_keeps_reservation():
    case, threads, move = fixture()
    release, completed = threading.Event(), threading.Event()
    def slow(context, _):
        release.wait(1)
        context["scheduled_terms"]["unit_price"] = -100
        completed.set()
        return keep()
    advisor = CapacityAdvisor(slow, timeout_s=.02)
    original = copy.deepcopy(move)
    try:
        selected, trace = advisor.select(case, threads, move, remaining_s=60)
        assert selected == original and trace["reason"] == "timeout"
        assert advisor.disabled and advisor.calls == 1 and advisor.reserved_s == .02
    finally:
        release.set()
    assert completed.wait(1) and move == original
    threads[move["supplier_id"]][-1]["body"] += " New reply."
    assert advisor.select(case, threads, move, remaining_s=60)[1]["reason"] == "admission_closed"


def test_once_per_update_total_call_limit_and_reserved_seconds():
    case, threads, move = fixture()
    advisor = CapacityAdvisor(keep, max_calls=1, total_s=1)
    advisor.select(case, threads, move, remaining_s=60)
    advisor.select(case, threads, move, remaining_s=60)
    threads[move["supplier_id"]][-1]["body"] += " New update."
    advisor.select(case, threads, move, remaining_s=60)
    assert advisor.calls == 1 and advisor.reserved_s == 1


def test_stale_and_expired_advice_cannot_enter_generic_send_fallback():
    case, threads, move = fixture()
    now = [0.0]
    def stale(context, _):
        threads[move["supplier_id"]][-1]["body"] += " Changed while waiting."
        return response(context)
    with pytest.raises(AdviceExecutionBlocked):
        guarded_decision(None, case, threads,
                         lambda: CapacityAdvisor(stale).select(case, threads, move, remaining_s=60))
    def expired(*_):
        now[0] = 50
        return keep()
    with pytest.raises(AdviceExecutionBlocked):
        CapacityAdvisor(expired, clock=lambda: now[0]).select(case, threads, move, remaining_s=30)


def test_final_and_short_deadline_bypass_inference():
    case, threads, move = fixture()
    advisor = CapacityAdvisor(lambda *_: pytest.fail("must skip"))
    assert advisor.select(case, threads, move, remaining_s=19)[0] == move
    threads[move["supplier_id"]][-1]["status"] = "final_offer"
    assert advisor.select(case, threads, move, remaining_s=60)[0] == move


def test_single_call_draft_isolation_evidence_once_and_predispatch_tampering():
    case, threads, move = fixture()
    sid = move["supplier_id"]
    calls = []
    agent = agent_for(case, threads)
    def choose(context, _):
        assert agent.prev == {} and agent.final_counters == {}
        calls.append(context)
        return response(context)
    agent.package_advisor.complete_fn = choose
    class Reader:
        def read(self, *_):
            pytest.fail("separate reader must not run")
    agent.model_assist = Reader()
    decorated = []
    class Evidence:
        def eligible(self, *_):
            return True
        def context_for(self, *_):
            return None
        def enrich(self, case, threads, sid, move, **_):
            decorated.append(copy.deepcopy(move))
            return {**move, "message": {**move["message"], "refs": ["verified:fixture"]}}
    agent.evidence = Evidence()
    agent.prepare_email(case, threads, sid)  # same entry as serial runner
    selected = agent.decide(case, threads)
    assert len(calls) == len(decorated) == 1
    assert selected["message"]["term_sheets"][0]["terms"]["contract_months"] == 36
    assert agent.prev == {}
    assert agent.final_counters == {}  # discarded baseline's mutation is absent
    tampered = copy.deepcopy(selected)
    tampered["message"]["body"] += " We promise exclusivity."
    with pytest.raises(AdviceExecutionBlocked):
        agent.validate_decision(case, threads, tampered)
    agent.validate_decision(case, threads, selected)
    assert agent.prev[sid]["contract_months"] == 36
    assert agent._advice_pending is None


@pytest.mark.parametrize("fn", [keep, lambda *_: {"malformed": True}])
def test_combined_keep_and_failure_match_prepared_v5_baseline(fn):
    case, threads, move = fixture()
    sid = move["supplier_id"]
    baseline = PackageAgent(policy=PolicyConfig(cost_neutral_lead_time=True))
    baseline.trades.deadlines[sid] = time.time() + 60
    expected = baseline.decide(case, threads)
    candidate = agent_for(case, threads, fn)
    actual = candidate.decide(case, threads)
    candidate.validate_decision(case, threads, actual)
    assert actual == expected and candidate.prev == baseline.prev
    assert candidate.final_counters == baseline.final_counters


def test_supplied_mode_is_opt_in_and_bad_limits_fail():
    base = json.loads(Path("configs/score-push-v6.json").read_text())
    config = json.loads(Path("configs/score-push-v6-guarded.json").read_text())
    assert PolicyConfig.from_dict(base).package_advice_mode == "legacy"
    assert isinstance(PackageAgent(policy=config).package_advisor, CapacityAdvisor)
    for key, value in [("package_advice_mode", "unknown"),
                       ("package_advice_max_calls", True), ("package_advice_total_s", -1),
                       ("package_advice_types", ["rfq"])]:
        with pytest.raises(ValueError):
            PolicyConfig.from_dict({**config, key: value})


def test_commercial_labels_do_not_invent_supplier_value():
    effects = commercial_changes({"payment_days": 30, "contract_months": 12},
                                 {"payment_days": 60, "contract_months": 36})
    assert effects["payment_days"]["direction"] == "buyer_requests"
    assert effects["contract_months"]["direction"] == "unknown"


def test_advice_metrics_distinguish_reported_usage_from_unknown():
    case, threads, move = fixture()
    agent = agent_for(case, threads, lambda *_: AdviceCompletion(keep(),
                      {"prompt_tokens": 120, "completion_tokens": 25}))
    agent.decide(case, threads)
    metrics = agent.experiment_metrics()["package_advice"]
    assert metrics["calls"] == metrics["admitted"] == metrics["usage_reported_calls"] == 1
    assert metrics["changed"] == metrics["unknown_usage_calls"] == 0
    assert metrics["reported_input_tokens"] == 120
    unknown = agent_for(case, threads)
    unknown.decide(case, threads)
    assert unknown.experiment_metrics()["package_advice"]["unknown_usage_calls"] == 1


def test_restart_does_not_refund_or_repeat_an_unknown_attempt(tmp_path):
    case, threads, move = fixture()
    first = CapacityAdvisor(keep)
    first.attach("session:one", tmp_path / "serial.jsonl")
    first.select(case, threads, move, remaining_s=60)
    assert first.calls == 1
    resumed = CapacityAdvisor(lambda *_: pytest.fail("same update must not call provider"))
    resumed.attach("session:one", tmp_path / "serial.jsonl")
    selected, trace = resumed.select(case, threads, move, remaining_s=60)
    assert selected == move and trace["reason"] == "admission_closed"
    assert resumed.calls == 1 and resumed.reserved_s == first.reserved_s


def test_renewal_uses_complete_costed_menu_and_current_conditional_evidence():
    case = next(c for c in json.loads(Path("tests/fixtures/practice_cases.json").read_text())
                if c["case_id"] == "case:P04")
    sid = case["suppliers"][0]
    body = "We can offer a longer term if you agree to a 36-month contract."
    threads = {sid: [{"from": "sales@70620", "status": "open", "body": body,
                      "term_sheets": [{"terms": {"unit_price": 4.8, "payment_days": 30,
                                                 "contract_months": 12}}]}]}
    terms = {"unit_price": 4.5, "payment_days": 30, "contract_months": 24}
    move = {"supplier_id": sid, "message": {"subject": "Offer", "body": "Our proposal follows.",
            "term_sheets": [{"terms": terms}], "refs": []}}

    def choose(context, _):
        assert len(context["approved_packages"]) <= 16
        selected = next(key for key, package in context["approved_packages"].items()
                        if package == {**terms, "contract_months": 36})
        return {"selected_id": selected, "support_index": 0, "acknowledgement": "consideration",
                "observations": [{"kind": "conditional_trade", "message_index": 0,
                                  "public_note_id": None, "quote": body,
                                  "addressed_fields": ["contract_months"]}]}

    advisor = CapacityAdvisor(choose, case_types=("capacity", "renewal"))
    actual, trace = advisor.select(case, threads, move, remaining_s=60)
    assert trace["admitted"] and trace["changed"]
    assert actual["message"]["term_sheets"][0]["terms"] == {**terms, "contract_months": 36}
    shadow = CapacityAdvisor(choose, case_types=("capacity", "renewal"), shadow=True)
    same, trace = shadow.select(case, threads, move, remaining_s=60)
    assert same == move and trace["admitted"] and not trace["changed"]
    assert trace["shadow_selected_id"].startswith("package_")


@pytest.mark.parametrize("mode", ["select", "invalid", "stale"])
def test_serial_runner_sends_one_validated_move_or_blocks_stale_state(mode, monkeypatch):
    case, threads, move = fixture()
    monkeypatch.setattr("negotiator.prewarm.prewarm_case", lambda *_: None)
    def model(context, _):
        if mode == "stale":
            threads[move["supplier_id"]][-1]["body"] += " Updated terms."
        return {} if mode == "invalid" else response(context)
    agent = agent_for(case, threads, model)
    table = FakeTable(case, threads, replies=[{"result": {"ended": True}}])
    if mode == "stale":
        with pytest.raises(AdviceExecutionBlocked):
            play_case(table, case["case_id"], agent)
        assert not table.sent and not table.closed and agent.prev == {}
    else:
        assert play_case(table, case["case_id"], agent) == {"ended": True}
        assert len(table.sent) == 1 and not table.closed and agent._advice_pending is None
        if mode == "select":
            assert table.sent[0][1]["term_sheets"][0]["terms"]["contract_months"] == 36


def test_expired_predispatch_and_changed_estimates_do_not_commit_draft_state(monkeypatch):
    case, threads, move = fixture()
    agent = agent_for(case, threads, lambda c, _: response(c))
    selected = agent.decide(case, threads)
    agent._advice_pending["deadline"] = time.monotonic() - 1
    with pytest.raises(AdviceExecutionBlocked):
        agent.validate_decision(case, threads, selected)
    assert agent.prev == {}
    agent._advice_pending["deadline"] = time.monotonic() + 60
    monkeypatch.setattr("negotiator.agent.total_cost", lambda *_: float("inf"))
    with pytest.raises(AdviceExecutionBlocked):
        agent.validate_decision(case, threads, selected)
    assert agent.prev == {}


def test_transport_uses_combined_schema_and_reports_usage(monkeypatch):
    from negotiator.package_advisor import complete

    monkeypatch.setenv("LLM_API_KEY", "test-only-key")
    monkeypatch.setenv("LLM_MODEL", "test-only-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://model.invalid/v1")
    requests = []
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"choices": [{"message": {"content": json.dumps(keep())}}],
                    "usage": {"prompt_tokens": 40, "completion_tokens": 20}}
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
    case, threads, move = fixture()
    advisor = CapacityAdvisor(complete)
    assert advisor.select(case, threads, move, remaining_s=60)[1]["admitted"]
    assert len(requests) == 1
    schema = requests[0]["response_format"]["json_schema"]["schema"]
    assert "observations" in schema["required"] and "supporting_quote" not in schema["properties"]
    assert advisor.metrics()["reported_input_tokens"] == 40
