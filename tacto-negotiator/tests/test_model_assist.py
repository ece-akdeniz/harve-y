import json
from datetime import UTC, datetime, timedelta
from importlib.resources import files

from arena_kit.cost import total_cost
from test_runner import ScaledClock, SimArena

from negotiator.agent import PackageAgent
from negotiator.evidence import EvidencePolicy
from negotiator.model_assist import ModelAssist, approved_lessons
from negotiator.replies import evidence_constraints
from negotiator.runner import CaseRunner
from negotiator.state import Journal

pytest_plugins = ["test_evidence"]


def test_model_observations_require_verbatim_source_and_do_not_create_terms():
    case = {"type": "renewal", "term_options": {"payment_days": [30, 60]}}
    events = [{"from": "supplier", "body": "We can do 30 days, but need director approval.",
               "term_sheets": [{"terms": {"payment_days": 60, "unit_price": 20}}]}]
    answer = {"signals": [{"kind": "authority_constraint", "quote": "need director approval"},
                          {"kind": "index_objection", "quote": "We are hedged"}],
              "terms": [{"field": "payment_days", "value": 30, "quote": "30 days"},
                        {"field": "unit_price", "value": 1, "quote": "€1"}],
              "questions": [{"quote": "Do you agree?"}], "memory_refs": []}
    result = ModelAssist(complete=lambda prompt: json.dumps(answer)).read(case, events, "sup:A")
    assert [s["kind"] for s in result["signals"]] == ["authority_constraint", "authority_constraint"]
    assert result["terms"] == [{"field": "payment_days", "value": 30, "quote": "30 days", "message_index": 0,
                                "status": "prose_only_unverified", "allowed_option": True}]
    assert result["questions"] == []
    assert result["source"] == "model"


def test_model_timeout_falls_back_to_rules_and_only_cited_signal_vetoes_argument():
    def fail(_prompt):
        raise TimeoutError

    events = [{"from": "supplier", "body": "We are hedged."}]
    result = ModelAssist(complete=fail).read({"type": "renewal"}, events, "sup:A")
    assert result["source"] == "rules"
    assert "index_change" in evidence_constraints(events, result)[1]
    assert result["terms"] == []


def test_only_reviewed_scoped_unexpired_lessons_are_available(tmp_path):
    lesson = {"id": "l1", "approved": True, "supplier_id": "sup:A", "case_type": "renewal",
              "environment": "sandbox", "data_sha256": "hash", "avoid_claim_kind": "index_change",
              "approved_by": "reviewer", "campaign_id": "campaign-1", "confidence": 0.8,
              "valid_from": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
              "observation": "Prior cited test supports avoiding this argument.",
              "evidence": [{"run_id": "r1", "attempt_id": "a1"}],
              "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat()}
    path = tmp_path / "memory.json"
    path.write_text(json.dumps({"schema_version": 1, "lessons": [lesson, {**lesson, "id": "l2", "approved": False}]}))
    case = {"type": "renewal", "environment": "sandbox"}
    assert [x["id"] for x in approved_lessons(path, supplier="sup:A", case=case, data_sha256="hash")] == ["l1"]
    assert approved_lessons(path, supplier="sup:A", case=case, data_sha256="other") == []
    assert approved_lessons(path, supplier="sup:B", case=case, data_sha256="hash") == []


def test_model_memory_summary_cites_only_available_approved_lessons(tmp_path):
    path = tmp_path / "memory.json"
    path.write_text(json.dumps({"schema_version": 1, "lessons": [{
        "id": "l1", "approved": True, "supplier_id": "sup:A", "case_type": "renewal",
        "environment": "sandbox", "data_sha256": "hash", "avoid_claim_kind": "index_change",
        "approved_by": "reviewer", "campaign_id": "campaign-1", "confidence": 0.8,
        "valid_from": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        "observation": "Prior response challenged the index argument.",
        "evidence": [{"run_id": "r1", "attempt_id": "a1"}],
        "expires_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
    }]}))
    answer = {"signals": [], "terms": [], "questions": [], "memory_refs": ["l1", "invented"],
              "memory_summary": "Prior cited response challenged this argument."}
    result = ModelAssist(complete=lambda _: json.dumps(answer), memory_path=path, data_sha256="hash").read(
        {"type": "renewal", "set": "sandbox"}, [{"from": "supplier", "body": "Our offer stands."}], "sup:A"
    )
    assert [x["id"] for x in result["lessons"]] == ["l1"]
    assert result["memory_summary"] == answer["memory_summary"]


def test_agent_caches_model_read_and_keeps_numbers_deterministic():
    calls = []

    def complete(prompt):
        calls.append(prompt)
        return json.dumps({"signals": [{"kind": "payment_trade", "quote": "faster payment"}],
                           "terms": [], "questions": [], "memory_refs": []})

    agent = PackageAgent(model_assist=ModelAssist(complete=complete))
    case = {"case_id": "case:X", "type": "renewal"}
    threads = {"sup:A": [{"from": "supplier", "body": "We prefer faster payment.", "term_sheets": []}]}
    agent.prepare_email(case, threads, "sup:A")
    agent.prepare_email(case, threads, "sup:A")
    assert len(calls) == 1
    assert agent.model_context["sup:A"]["signals"][-1]["kind"] == "payment_trade"


def test_model_cited_objection_changes_argument_selection_without_changing_offer(context):
    case, move, package, _ = context
    events = [{"from": "supplier", "status": "open", "body": "Our hedge covers that input."}]
    model = ModelAssist(complete=lambda _: json.dumps({
        "signals": [{"kind": "index_objection", "quote": "Our hedge covers that input."}],
        "terms": [], "questions": [], "memory_refs": [],
    }))
    interpretation = model.read(case, events, "sup:F")
    assert interpretation["source"] == "model"
    policy = EvidencePolicy(package, interpretation={"sup:F": interpretation})
    result = policy.enrich(case, {"sup:F": events}, "sup:F", move)
    assert "idx:ENERGY@2026-08" not in result["message"]["refs"]
    assert "sc:F@2026Q3" in result["message"]["refs"]
    assert result["message"]["term_sheets"] == move["message"]["term_sheets"]


def test_cited_payment_request_adds_equal_cost_variant_without_model_prices():
    case = json.loads(files("arena_kit").joinpath("sim_cases/S01.json").read_text())
    supplier = case["suppliers"][0]
    events = [{"from": "supplier", "status": "open", "body": "We prefer faster payment.",
               "term_sheets": [{"term_sheet_id": "offer:1", "terms": {"unit_price": 100,
                                                                  "payment_days": 30}}]}]
    model = ModelAssist(complete=lambda _: json.dumps({
        "signals": [{"kind": "payment_trade", "quote": "faster payment"}],
        "terms": [], "questions": [], "memory_refs": [],
    }))
    agent = PackageAgent(model_assist=model, meso=False)
    agent.prepare_email(case, {supplier: events}, supplier)
    move = agent.propose(case, {supplier: events}, supplier)
    sheets = move["message"]["term_sheets"]
    assert len(sheets) > 1
    costs = [total_cost(case, sheet["terms"]) for sheet in sheets]
    assert all(cost <= costs[0] for cost in costs[1:])


async def test_async_case_completes_with_model_path_and_no_invalid_terms(tmp_path):
    calls = []

    def complete(prompt):
        calls.append(prompt)
        return json.dumps({"signals": [], "terms": [], "questions": [], "memory_refs": []})

    clock = ScaledClock()
    arena = SimArena(clock)
    agent = PackageAgent(model_assist=ModelAssist(complete=complete))
    result = await CaseRunner(arena, "case:S01", agent, Journal(tmp_path / "journal.jsonl"), clock=clock).run()
    assert result["ended"] is True and result["deal"] is True
    assert all(count == 0 for count in result["thread_timeouts"].values())
    assert calls
    assert all(not any(s.get("terms", {}).get("unit_price") == 1 for s in m.get("term_sheets", []))
               for _, _, m in arena.posts)
