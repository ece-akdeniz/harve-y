"""Behavior and safety checks for the opt-in skill-guided decision layer."""

import copy
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import pytest
from test_package_advisor import fixture

from negotiator import cli
from negotiator.advice import AdviceExecutionBlocked
from negotiator.agent import PackageAgent, configured_agent
from negotiator.model_budget import SessionModelBudget
from negotiator.policy import PolicyConfig
from negotiator.skill_docs import load_skill
from negotiator.strategy_advisor import NegotiationSkill, StrategyAdvisor

ROOT = Path(__file__).resolve().parents[1]
QUOTE = "We need a longer contract commitment to allocate capacity."


def choice(context, _timeout):
    assert context["deterministic_move"]["terms"]["contract_months"] == 24
    selected = next(key for key, terms in context["approved_packages"].items()
                    if terms["contract_months"] == 36
                    and terms["unit_price"] == context["deterministic_move"]["terms"]["unit_price"])
    return {"selected_id": selected, "message_index": 0,
            "quote": QUOTE, "kind": "objection"}


def test_skill_is_packaged_and_strategy_changes_a_legal_complete_move():
    case, threads, move = fixture()
    notes = [{"id": "doc:own", "supplier_id": move["supplier_id"],
              "text": "Capacity is scarce.", "private_cost": 100000},
             {"id": "doc:foreign", "supplier_id": "sup:other", "text": "Do not disclose."}]

    def inspect(context, timeout):
        assert context["skill_sha256"] == NegotiationSkill.load().sha256
        assert [n["id"] for n in context["public_dossier_notes"]] == ["doc:own"]
        assert "private_cost" not in json.dumps(context) and "Do not disclose" not in json.dumps(context)
        assert "buyer_cost_change_eur" not in context
        assert context["commercial_changes"]
        return choice(context, timeout)

    adviser = StrategyAdvisor(inspect)
    original = copy.deepcopy(move)
    changed, trace = adviser.select(case, threads, move, public_notes=notes, remaining_s=60)
    terms = changed["message"]["term_sheets"][0]["terms"]
    assert terms["contract_months"] == 36 and terms["unit_price"] == 28.34
    assert trace["status"] == "ok" and trace["changed"] and trace["evidence_id"].startswith("sha256:")
    assert move == original and QUOTE not in changed["message"]["body"]
    assert adviser.metrics()["skill_sha256"] == NegotiationSkill.load().sha256


def test_skill_writes_buyer_email_using_scoped_context_and_approved_numbers():
    case, threads, move = fixture()
    brief = {"supplier_id": move["supplier_id"], "status": "model",
             "excerpts": [{"source_id": "doc:capacity", "text": "Capacity is constrained."}]}

    def write(context, _timeout):
        assert context["write_response"] is True
        assert context["supplier_brief"] == brief
        assert context["deterministic_move"]["terms"]["unit_price"] == 28.34
        assert context["commercial_changes"]
        return {**choice(context, _timeout), "body": (
            "Thank you for clarifying your position. We propose the attached terms as one package. "
            "These terms are offered together as one conditional package. "
            "Could you confirm the attached package or quote your best complete alternative?"
        )}

    selected, trace = StrategyAdvisor(write, write_response=True).select(
        case, threads, move, brief=brief, remaining_s=60)
    assert selected["message"]["body"].startswith("Thank you for clarifying your position")
    assert selected["message"]["term_sheets"][0]["terms"]["contract_months"] == 36
    assert trace["body_source"] == "model"


def test_unsafe_model_prose_falls_back_without_changing_approved_choice():
    case, threads, move = fixture()

    def write(context, _timeout):
        return {**choice(context, _timeout), "body": (
            "We propose the attached 36-month package and guarantee 99 percent savings."
        )}

    selected, trace = StrategyAdvisor(write, write_response=True).select(
        case, threads, move, remaining_s=60)
    assert trace["status"] == "ok" and trace["body_source"] == "deterministic_fallback"
    assert selected["message"]["term_sheets"][0]["terms"]["contract_months"] == 36
    assert selected["message"]["body"].startswith("Thank you") or "attached terms" in selected["message"]["body"]


def test_model_writes_keep_move_too():
    case, threads, move = fixture()
    body = "Thank you for explaining your requirements. We propose the attached terms as one package."
    adviser = StrategyAdvisor(lambda *_: {"selected_id": "keep", "message_index": -1,
                                          "quote": "", "kind": "none", "body": body},
                              write_response=True)
    selected, trace = adviser.select(case, threads, move, remaining_s=60)
    assert selected["message"]["body"] == body and trace["body_source"] == "model"
    assert selected["message"]["term_sheets"] == move["message"]["term_sheets"]


def test_skilled_config_routes_model_written_email_through_dispatch_check():
    case, threads, _ = fixture()
    config = json.loads((ROOT / "configs/score-push-v6-skilled.json").read_text())
    agent = configured_agent(config, estimates={}, meso=False)
    assert agent.package_advisor.write_response and agent.final_advisor.write_response
    sid = case["suppliers"][0]

    def write(context, timeout):
        return {**choice(context, timeout), "body": (
            "Thank you for clarifying your position. We propose the attached terms as one package. "
            "These terms are offered together as one conditional package. "
            "Could you confirm the attached package or quote your best complete alternative?"
        )}

    agent.package_advisor = StrategyAdvisor(write, write_response=True)
    agent.package_notes[sid] = []
    agent.trades.deadlines[sid] = time.time() + 60
    move = agent.decide(case, threads)
    assert move["message"]["body"].startswith("Thank you for clarifying your position")
    agent.validate_decision(case, threads, move)


def test_writing_requires_both_live_reviewers_and_stays_off_by_default():
    assert PolicyConfig().llm_response_mode == "off"
    for policy in (
        {"version": 1, "llm_response_mode": "skill-v1"},
        {"version": 1, "llm_response_mode": "skill-v1", "package_advice_mode": "strategy-v1",
         "package_advice_types": ["capacity"]},
        {"version": 1, "llm_response_mode": "other"},
    ):
        with pytest.raises(ValueError):
            PolicyConfig.from_dict(policy)


def test_question_selection_is_registered_and_attached_to_complete_package():
    case, threads, move = fixture()
    threads[move["supplier_id"]][0]["body"] = "Which contract term would help us allocate capacity?"

    def ask(context, _timeout):
        question = next(key for key, value in context["registered_questions"].items()
                        if value["field"] == "contract_months" and value["value"] == 36)
        return {"selected_id": question, "message_index": 0,
                "quote": context["supplier_messages"][-1]["body"], "kind": "question"}

    changed, trace = StrategyAdvisor(ask).select(case, threads, move, remaining_s=60)
    assert trace["question_id"] and trace["changed"]
    assert changed["message"]["term_sheets"][0]["terms"]["contract_months"] == 36
    assert "Could you confirm whether" in changed["message"]["body"]


@pytest.mark.parametrize("fault", ["quotation", "invented_terms", "foreign_quote", "provider_timeout"])
def test_bad_or_unsupported_strategy_retains_prepared_move(fault):
    case, threads, move = fixture()

    def model(context, timeout):
        answer = choice(context, timeout)
        if fault == "quotation":
            answer["quote"] = threads[move["supplier_id"]][0]["body"]
        elif fault == "invented_terms":
            answer["selected_id"] = "package_invented"
        elif fault == "foreign_quote":
            answer["quote"] = "An unrelated supplier accepts this."
        else:
            raise TimeoutError("provider late")
        return answer

    adviser = StrategyAdvisor(model)
    if fault == "quotation":
        threads[move["supplier_id"]][0]["body"] = "The contract term is 36 months."
    actual, trace = adviser.select(case, threads, move, remaining_s=60)
    assert actual == move and trace["status"] == "fallback"
    assert trace["reason"] == {
        "quotation": "quotation_without_constraint",
        "invented_terms": "unknown_choice",
        "foreign_quote": "unsupported_current_quote",
        "provider_timeout": "timeout",
    }[fault]
    assert adviser.disabled is (fault == "provider_timeout")


def test_explicit_supplier_alternative_supports_legal_buyer_counter():
    case, threads, move = fixture()
    quote = "Alternatively, we can offer a 36-month contract at EUR 31.90."
    threads[move["supplier_id"]][0]["body"] = quote

    def select(context, timeout):
        return {**choice(context, timeout), "quote": quote, "kind": "conditional_trade"}

    selected, trace = StrategyAdvisor(select).select(case, threads, move, remaining_s=60)
    assert selected["message"]["term_sheets"][0]["terms"]["contract_months"] == 36
    assert trace["status"] == "ok" and trace["changed"] and "repair" not in trace


def test_validation_model_repairs_rejected_strategy_without_bypassing_checks(tmp_path):
    case, threads, move = fixture()
    seen = []

    def bad(context, timeout):
        return {**choice(context, timeout), "quote": "A quote absent from the supplier reply."}

    def validation(context, timeout):
        seen.append(context["rejection_reason"])
        assert context["response_contract"] == "validation-repair-v1"
        return choice(context["source_context"], timeout)

    adviser = StrategyAdvisor(bad, repair_fn=validation)
    adviser.attach("session:repair", tmp_path / "serial.jsonl")
    budget = adviser.model_budget = SessionModelBudget(validation_reserve_s=6)
    budget.bind("session:repair", tmp_path / "serial.jsonl")
    selected, trace = adviser.select(
        case, threads, move, remaining_s=60)
    assert seen == ["unsupported_current_quote"]
    assert trace["status"] == "ok" and trace["changed"] and trace["repaired"]
    assert trace["repair"]["status"] == "ok"
    assert selected["message"]["term_sheets"][0]["terms"]["contract_months"] == 36
    assert budget.metrics()["by_role"]["validation-repair-v1"]["calls"] == 1

    invalid, failed = StrategyAdvisor(
        bad, repair_fn=lambda context, timeout: bad(context["source_context"], timeout)).select(
        case, threads, move, remaining_s=60)
    assert invalid == move and failed["status"] == "fallback"


def test_validator_can_take_over_after_primary_provider_timeout():
    case, threads, move = fixture()

    def timeout(*_):
        raise TimeoutError("primary provider late")

    def validation(context, limit):
        assert context["rejected_response"] is None
        assert context["rejection_reason"] == "timeout"
        return choice(context["source_context"], limit)

    adviser = StrategyAdvisor(timeout, repair_fn=validation)
    selected, trace = adviser.select(case, threads, move, remaining_s=60)
    assert trace["status"] == "ok" and trace["changed"] and trace["repaired"]
    assert adviser.disabled and selected["message"]["term_sheets"][0]["terms"]["contract_months"] == 36


def test_agent_routes_strategy_through_fresh_serial_dispatch_check():
    case, threads, _ = fixture()
    policy = PolicyConfig.from_dict({"version": 1, "package_advice_types": ["capacity"],
                                     "package_advice_mode": "strategy-v1"})
    agent = PackageAgent(policy=policy)
    assert isinstance(agent.package_advisor, StrategyAdvisor)
    agent.package_advisor = StrategyAdvisor(choice)
    sid = case["suppliers"][0]
    agent.package_notes[sid] = []
    agent.trades.deadlines[sid] = time.time() + 60
    selected = agent.decide(case, threads)
    assert selected["message"]["term_sheets"][0]["terms"]["contract_months"] == 36
    agent.validate_decision(case, threads, selected)
    assert agent.package_advisor.calls == 1


def test_restart_charges_unknown_attempt_and_shadow_does_not_change_action(tmp_path):
    case, threads, move = fixture()
    path = tmp_path / "serial.jsonl"
    first = StrategyAdvisor(choice, shadow=True)
    first.attach("session:1", path)
    actual, trace = first.select(case, threads, move, remaining_s=60)
    assert actual == move and trace["shadow_selected_id"] and not trace["changed"]
    resumed = StrategyAdvisor(choice)
    resumed.attach("session:1", path)
    assert resumed.calls == 1 and resumed.reserved_s == first.reserved_s
    assert resumed.select(case, threads, move, remaining_s=60)[1]["reason"] == "admission_closed"


def test_stale_thread_blocks_strategy_dispatch():
    case, threads, move = fixture()

    def mutate(context, timeout):
        threads[move["supplier_id"]][-1]["body"] += " New condition."
        return choice(context, timeout)

    with pytest.raises(AdviceExecutionBlocked, match="state changed"):
        StrategyAdvisor(mutate).select(case, threads, move, remaining_s=60)


def test_strict_provider_schema_reads_packaged_skill(monkeypatch):
    from negotiator.package_advisor import complete

    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://model.invalid/v1")
    sent = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": json.dumps({
                "selected_id": "keep", "message_index": -1, "quote": "", "kind": "none"})}}]}

    class Client:
        def __init__(self, **_):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def post(self, url, **kwargs):
            sent.append(kwargs["json"])
            return Response()

    monkeypatch.setattr("negotiator.package_advisor.httpx.Client", Client)
    case, threads, move = fixture()
    actual, trace = StrategyAdvisor(complete).select(case, threads, move, remaining_s=60)
    assert actual == move and trace["reason"] == "model_keep"
    assert len(sent) == 1 and sent[0]["max_completion_tokens"] == 350
    assert "# Negotiation decision skill" in sent[0]["messages"][0]["content"]
    schema = sent[0]["response_format"]["json_schema"]
    assert schema["strict"] and schema["schema"]["required"] == [
        "selected_id", "message_index", "quote", "kind"]
    StrategyAdvisor(complete, write_response=True).select(case, threads, move, remaining_s=60)
    assert sent[1]["max_completion_tokens"] == 600
    assert sent[1]["response_format"]["json_schema"]["schema"]["required"] == [
        "selected_id", "message_index", "quote", "kind", "body"]


def test_strategy_config_is_explicit_and_default_is_unchanged():
    path = ROOT / "configs/score-push-v6-strategy.json"
    agent = configured_agent(json.loads(path.read_text()), estimates={}, meso=False)
    assert isinstance(agent.package_advisor, StrategyAdvisor)
    assert agent.policy.package_advice_mode == "strategy-v1"
    default = configured_agent(json.loads((ROOT / "configs/score-push-v6.json").read_text()),
                               estimates={}, meso=False)
    assert not isinstance(default.package_advisor, StrategyAdvisor)
    with pytest.raises(ValueError):
        PolicyConfig.from_dict({"version": 1, "package_advice_mode": "strategy-v1",
                                "package_advice_types": ["rfq"]})


def test_cli_loads_opt_in_writing_and_records_packaged_skills(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "load_env", lambda: None)
    monkeypatch.setattr(cli, "_run_dir", lambda: tmp_path)
    monkeypatch.setattr(cli, "ArenaClient", lambda: type("Client", (), {"practice_remaining": None})())
    monkeypatch.setattr(cli, "RemoteTable", lambda _: object())
    observed = []

    def run(_table, _case_id, agent):
        observed.append(agent)
        return {"ended": True, "deal": True, "score": .5}

    monkeypatch.setattr(cli, "play_case", run)
    assert cli.main(["play", "case:P10", "--runner", "serial", "--policy-config",
                     str(ROOT / "configs/score-push-v6-skilled.json")]) == 0
    assert isinstance(observed[0].package_advisor, StrategyAdvisor)
    assert observed[0].package_advisor.write_response
    assert observed[0].final_advisor.write_response
    trace = [json.loads(row) for row in (tmp_path / "trace.jsonl").read_text().splitlines()]
    launch = next(row for row in trace if row["event"] == "run")
    assert launch["negotiation_skill"]["sha256"] == NegotiationSkill.load().sha256
    assert launch["final_offer_skill"]["sha256"] == load_skill("final", "final-offer-review").sha256


def test_skill_resource_loads_from_a_zipped_package(tmp_path):
    source = ROOT / "src/negotiator"
    archive = tmp_path / "negotiator.zip"
    with zipfile.ZipFile(archive, "w") as package:
        for path in source.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                package.write(path, "negotiator/" + path.relative_to(source).as_posix())
    env = {**os.environ, "PYTHONPATH": str(archive)}
    result = subprocess.run(
        [sys.executable, "-c",
         "from negotiator.strategy_advisor import NegotiationSkill; "
         "from negotiator.skill_docs import load_skill; "
         "print(NegotiationSkill.load().sha256); "
         "print(load_skill('final', 'final-offer-review').sha256); "
         "print(load_skill('brief', 'supplier-brief').sha256); "
         "print(load_skill('response', 'buyer-response-writer').sha256)"],
        cwd=tmp_path, env=env, capture_output=True, text=True, check=True,
    )
    assert result.stdout.splitlines() == [NegotiationSkill.load().sha256,
                                          load_skill("final", "final-offer-review").sha256,
                                          load_skill("brief", "supplier-brief").sha256,
                                          load_skill("response", "buyer-response-writer").sha256]
