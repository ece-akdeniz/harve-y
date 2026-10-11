"""All-case prose writing keeps commercial decisions in the existing agent."""

import asyncio
import copy
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from negotiator import cli
from negotiator.advice import AdviceCompletion, digest
from negotiator.agent import configured_agent
from negotiator.message_prose import checked_body
from negotiator.package_advisor import ModelResponseError, complete, failure_reason
from negotiator.play import play_case
from negotiator.policy import PolicyConfig
from negotiator.response_writer import ResponseWriter
from negotiator.runner import CaseRunner, Clock
from negotiator.state import CaseState, Journal, ThreadState
from negotiator.trace import Tracer

ROOT = Path(__file__).resolve().parents[1]
CASES = {c["type"]: c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())}
CONFIG = json.loads((ROOT / "configs/score-push-v6-all-cases.json").read_text())
BODY = "Thank you for clarifying your position. We propose the attached terms as one package. Could you review them?"


def test_writer_rejects_unsupported_non_numeric_claims_and_commitments():
    terms = {"unit_price": 10, "volume_per_year": 100}
    for candidate in (
        "Your production capacity is stable. We propose the attached terms as one package.",
        "We will purchase additional volume. We propose the attached terms as one package.",
        "We can buy more units later. We propose the attached terms as one package.",
        "Your team has been very reliable. We propose the attached terms as one package.",
    ):
        assert checked_body(candidate, terms) is None
    assert checked_body(BODY, terms) == BODY


def test_writer_preserves_prepared_question_and_condition():
    terms = {"unit_price": 10}
    prepared = ("We propose the attached terms as one package. "
                "These terms are conditional on agreement to the complete attached package. "
                "Could you confirm the attached package or quote your best complete alternative?")
    assert checked_body(BODY, terms, prepared_body=prepared) is None
    assert checked_body(prepared, terms, prepared_body=prepared) == prepared


def test_writer_usage_is_included_in_role_metrics():
    case, sid, events, message = sample("quality")
    writer = ResponseWriter(lambda *_: AdviceCompletion({"body": BODY},
                              {"prompt_tokens": 40, "completion_tokens": 12}))
    assert writer.write(case, events, sid, message, remaining_s=60)[0] == BODY
    assert writer.metrics()["reported_input_tokens"] == 40
    assert writer.metrics()["reported_output_tokens"] == 12


def test_provider_failure_codes_distinguish_refusal_empty_and_bad_json(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://model.invalid/v1")

    class Client:
        def __init__(self, payload, **_):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def post(self, *_args, **_kwargs):
            return self

        def raise_for_status(self):
            pass

        def json(self):
            return self.payload

    context = {"response_contract": "buyer-response-v1", "skill_sha256":
               ResponseWriter(lambda *_: None).skill.sha256}
    for payload, expected in (
        ({"choices": [{"message": {"refusal": "no", "content": ""}}]}, "provider_refusal"),
        ({"choices": [{"message": {"content": ""}}]}, "empty_output"),
        ({"choices": [{"message": {"content": "{bad"}}]}, "invalid_json"),
    ):
        monkeypatch.setattr("negotiator.package_advisor.httpx.Client",
                            lambda payload=payload, **kwargs: Client(payload, **kwargs))
        with pytest.raises(ModelResponseError) as caught:
            complete(context, 2)
        assert failure_reason(caught.value) == expected


def sample(kind):
    case = CASES[kind]
    sid = case["suppliers"][0]
    events = [{"from": "supplier", "status": "open", "body": "We need a workable complete offer.",
               "term_sheets": [{"term_sheet_id": "supplier:0", "terms": {"unit_price": 11.0}}]}]
    message = {"subject": "Offer", "body": "We propose the attached package.",
               "term_sheets": [{"terms": {"unit_price": 10.0}}]}
    return case, sid, events, message


@pytest.mark.parametrize("kind", sorted(CASES))
def test_all_seven_case_types_can_use_scoped_model_prose(kind):
    case, sid, events, message = sample(kind)
    brief = {"supplier_id": sid, "status": "extractive", "excerpts": [{"source_id": "doc:own"}]}

    def complete(context, timeout):
        assert context["case_type"] == kind and context["supplier_id"] == sid
        assert context["approved_terms"] == message["term_sheets"][0]["terms"]
        assert context["supplier_brief"] == brief
        assert context["latest_supplier_message"]["body"] == events[0]["body"]
        assert timeout <= 6
        return {"body": BODY}

    writer = ResponseWriter(complete)
    body, trace = writer.write(case, events, sid, message, brief=brief, remaining_s=60)
    assert body == BODY and trace["body_source"] == "model"
    assert writer.metrics()["calls"] == 1


def test_disclosed_claims_and_unsafe_prose_keep_original_message():
    case, sid, events, message = sample("quality")
    writer = ResponseWriter(lambda *_: {"body": "We propose EUR 1.00 and guarantee the attached terms."})
    body, trace = writer.write(case, events, sid, message, remaining_s=60)
    assert body is None and trace["reason"] == "invalid_prose"
    assert trace["prose_check"] in {"unsafe_content", "numeric_mismatch"}
    message["refs"] = ["sc:own"]
    body, trace = writer.write(case, events, sid, message, remaining_s=60)
    assert body is None and trace["reason"] == "ineligible"
    assert writer.metrics()["calls"] == 1


def test_all_case_config_keeps_existing_strategy_and_final_choice_scope():
    policy = PolicyConfig.from_dict(CONFIG)
    assert policy.llm_response_mode == "all-v1"
    assert set(policy.package_advice_types) == {"capacity", "renewal"}
    agent = configured_agent(CONFIG, estimates={}, meso=False)
    assert agent.package_advisor.write_response is False
    assert agent.final_advisor.write_response is False
    assert agent.response_writer is not None


def test_serial_handoff_rehashes_guarded_permit_without_changing_terms(monkeypatch):
    case, sid, events, message = sample("capacity")
    agent = configured_agent(CONFIG, estimates={}, meso=False)
    agent.response_writer = ResponseWriter(lambda *_: {"body": BODY})
    agent.trades.deadlines[sid] = time.time() + 60
    monkeypatch.setattr(agent, "_supplier_brief", lambda *_args, **_kw: None)
    move = {"supplier_id": sid, "message": copy.deepcopy(message)}
    original_terms = copy.deepcopy(message["term_sheets"])
    agent._advice_pending = {"payload": digest(move)}
    changed = agent.rewrite_response(case, {sid: events}, move)
    assert changed["message"]["body"] == BODY
    assert changed["message"]["term_sheets"] == original_terms
    assert agent._advice_pending["payload"] == digest(changed)
    assert move["message"]["body"] == message["body"]


def test_serial_runner_dispatches_model_prose_for_quality(monkeypatch):
    case, sid, events, message = sample("quality")
    agent = configured_agent(CONFIG, estimates={}, meso=False)
    agent.response_writer = ResponseWriter(lambda *_: {"body": BODY})
    monkeypatch.setattr(agent, "_supplier_brief", lambda *_args, **_kw: None)
    monkeypatch.setattr(agent, "decide", lambda *_: {"supplier_id": sid,
                                                     "message": copy.deepcopy(message)})
    sent = []

    class Table:
        case = None

        def open(self, _case_id):
            return case, {sid: copy.deepcopy(events)}

        def send(self, _sid, outgoing):
            sent.append(outgoing)
            return {"result": {"ended": True, "deal": True, "score": .5}}

    result = play_case(Table(), case["case_id"], agent)
    assert result["ended"] and sent[0]["body"] == BODY
    assert sent[0]["term_sheets"] == message["term_sheets"]


def test_serial_writer_uses_run_directory_budget(monkeypatch, tmp_path):
    case, sid, events, message = sample("quality")
    agent = configured_agent(CONFIG, estimates={}, meso=False)
    agent.tracer = Tracer(tmp_path)
    agent.response_writer.complete_fn = lambda *_: {"body": BODY}
    monkeypatch.setattr(agent, "_supplier_brief", lambda *_args, **_kw: None)
    monkeypatch.setattr(agent, "decide", lambda *_: {"supplier_id": sid,
                                                     "message": copy.deepcopy(message)})

    class Table:
        session_id = "session:local"
        client = SimpleNamespace()

        def open(self, _case_id):
            return case, {sid: copy.deepcopy(events)}

        def send(self, _sid, outgoing):
            return {"result": {"ended": True, "deal": True, "score": .5}}

    assert play_case(Table(), case["case_id"], agent)["ended"]
    assert agent.model_budget.metrics()["by_role"]["buyer-response-v1"]["calls"] == 1
    restored = type(agent.model_budget)()
    restored.bind("session:local", tmp_path / "trace.jsonl")
    assert restored.metrics()["calls"] == 1


def test_async_preview_can_write_rfq_without_mutating_live_agent(monkeypatch):
    case, sid, events, message = sample("rfq")
    agent = configured_agent(CONFIG, estimates={}, meso=False)
    agent.response_writer = ResponseWriter(lambda *_: {"body": BODY})
    monkeypatch.setattr(agent, "_supplier_brief", lambda *_args, **_kw: None)
    monkeypatch.setattr(type(agent), "propose", lambda self, _case, _threads, _sid,
                        **_kw: {"supplier_id": _sid, "message": copy.deepcopy(message)})
    before = copy.deepcopy(agent.prev)
    prepared = agent.prepare_response(case, {sid: events}, sid, remaining_s=60)
    assert prepared["original"] == message and prepared["body"] == BODY
    assert agent.prev == before


def test_short_deadline_avoids_model_call():
    case, sid, events, message = sample("raw_material")
    writer = ResponseWriter(lambda *_: pytest.fail("provider must not be called"))
    assert writer.write(case, events, sid, message, remaining_s=23)[0] is None


def test_provider_uses_strict_body_schema_and_packaged_skill(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://model.invalid/v1")
    sent = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": json.dumps({"body": BODY})}}]}

    class Client:
        def __init__(self, **_):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def post(self, _url, **kwargs):
            sent.append(kwargs["json"])
            return Response()

    monkeypatch.setattr("negotiator.package_advisor.httpx.Client", Client)
    case, sid, events, message = sample("quality")
    body, trace = ResponseWriter(complete).write(case, events, sid, message, remaining_s=60)
    assert body == BODY and trace["body_source"] == "model"
    assert sent[0]["max_completion_tokens"] == 1200
    assert sent[0]["response_format"]["json_schema"]["schema"]["required"] == ["body"]
    assert "# Buyer response writer" in sent[0]["messages"][0]["content"]


def test_cli_launches_all_case_writer_and_records_resource(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "load_env", lambda: None)
    monkeypatch.setattr(cli, "_run_dir", lambda: tmp_path)
    monkeypatch.setattr(cli, "ArenaClient", lambda: type("Client", (), {"practice_remaining": None})())
    monkeypatch.setattr(cli, "RemoteTable", lambda _: object())
    agents = []

    def play(_table, _case_id, agent):
        agents.append(agent)
        return {"ended": True, "deal": True, "score": .5}

    monkeypatch.setattr(cli, "play_case", play)
    assert cli.main(["play", "case:P11", "--runner", "serial", "--policy-config",
                     str(ROOT / "configs/score-push-v6-all-cases.json")]) == 0
    assert agents[0].response_writer is not None
    trace = [json.loads(row) for row in (tmp_path / "trace.jsonl").read_text().splitlines()]
    launch = next(row for row in trace if row["event"] == "run")
    assert launch["response_skill"]["sha256"] == agents[0].response_writer.skill.sha256
    assert launch["effective_capabilities"]["response_writer"] is True
    assert launch["effective_capabilities"]["advice_case_types"] == ["capacity", "renewal"]


@pytest.mark.asyncio
async def test_async_rfq_worker_dispatches_prepared_model_prose(tmp_path, monkeypatch):
    case, sid, events, message = sample("rfq")
    agent = SimpleNamespace(
        response_writer=object(), model_assist=None, trades=None,
        prepare_response=lambda *_args, **_kw: {"original": copy.deepcopy(message), "body": BODY})
    worker = CaseRunner(object(), case["case_id"], agent, Journal(tmp_path / "rfq.jsonl"))
    worker.st = CaseState(case, "session:local", threads={
        sid: ThreadState(sid, events, deadline_utc=time.time() + 60)})
    monkeypatch.setattr("negotiator.runner.propose",
                        lambda *_args: ("send", copy.deepcopy(message)))
    sent = []

    async def send(_sid, _intent, outgoing, _t0):
        sent.append(outgoing)
        worker.st.threads[sid].closed = "ended"

    monkeypatch.setattr(worker, "_send", send)
    await asyncio.wait_for(worker._worker(sid), timeout=2)
    assert len(sent) == 1 and sent[0]["body"] == BODY
    assert sent[0]["term_sheets"] == message["term_sheets"]


@pytest.mark.asyncio
async def test_async_rfq_simulator_sends_model_prose_without_timeouts(tmp_path):
    from test_runner import SimArena, timeouts

    clock = Clock()
    arena = SimArena(clock)
    agent = configured_agent(CONFIG, estimates={}, meso=False)
    agent.response_writer = ResponseWriter(lambda *_: {"body": BODY})
    result = await CaseRunner(arena, "case:S02", agent, Journal(tmp_path / "rfq-sim.jsonl"),
                              clock=clock).run()
    assert result["ended"] and any(message.get("body") == BODY for _, _, message in arena.posts)
    assert set(timeouts(arena, result["session_id"]).values()) == {0}
