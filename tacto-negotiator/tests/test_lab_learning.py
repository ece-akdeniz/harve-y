import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from test_lab_loop_store import checkpoint, finish
from test_lab_server import snapshot

from negotiator.lab.knowledge import export_graph
from negotiator.lab.learning import LearningStore
from negotiator.lab.loop_store import LoopStore
from negotiator.lab.models import Run
from negotiator.lab.policy import default_suite
from negotiator.lab.store import Conflict, Store

pytest_plugins = ["test_lab_server"]


def test_supplied_data_rebuilds_facts_without_changing_message_identity(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    (data / "facts.json").write_text("{}")
    state = {"date": "2026-10-10", "contact": "person:1"}

    def package(*_):
        return SimpleNamespace(
            facts={"news:1": {"supplier": "sup:A", "date": state["date"], "headline": "Update"},
                   "contact:1": {"supplier": "sup:A", "contact_id": state["contact"]}},
            sources={"news:1": "base", "contact:1": "base"},
            manifest={"sha256": state["date"]}, conflicts=[], warnings=[], db=None,
        )

    monkeypatch.setattr("negotiator.lab.learning.load_package", package)
    learning = LearningStore(tmp_path / "lab.db")
    legacy = snapshot("legacy-no-provenance", status="completed", score=0.4)
    legacy.update(status="completed", source="imported", provenance=None)
    Store(learning.path).upsert(Run.model_validate(legacy))
    first = learning.ingest(data)
    run = snapshot("prior", status="completed", score=0.6)
    run["attempts"][0].update(session_id="session-a", result={"ended": True, "deal": True},
                              threads={"sup:A": [{"from": "sup:A", "body": "Hello"}]})
    Store(learning.path).upsert(Run.model_validate(run))
    old = learning.graph(first["data_sha256"])
    (data / "update.txt").write_text("new release")
    state.update(date="2026-10-11", contact="person:2")
    second = learning.ingest(data)
    new = learning.graph(second["data_sha256"])
    assert first["data_sha256"] != second["data_sha256"]
    assert {n["id"] for n in old["nodes"] if n["kind"] == "message"} == {
        n["id"] for n in new["nodes"] if n["kind"] == "message"
    }
    assert {n["id"] for n in old["nodes"] if n["kind"] == "public_fact"} != {
        n["id"] for n in new["nodes"] if n["kind"] == "public_fact"
    }
    assert any(e["relation"] == "has_news_fact" for e in new["edges"])
    assert any(e["relation"] == "has_contact" for e in new["edges"])


def test_terminal_feedback_is_retryable_and_does_not_rewrite_original(tmp_path):
    learning = LearningStore(tmp_path / "lab.db")
    run = snapshot("terminal", status="completed", score=0.3)
    run["status"] = "completed"
    run["agent"] = "package"
    run["attempts"][0].update(session_id="session-a", timeouts=2,
                              result={"ended": True, "deal": True, "must_haves_ok": True,
                                      "agent_metrics": {"model": {"calls": 2, "fallbacks": 1,
                                                                  "latency_s": [0.2, 0.3],
                                                                  "input_tokens": 100,
                                                                  "output_tokens": 40},
                                                        "package_advice": {"calls": 1, "fallbacks": 0,
                                                                           "reported_input_tokens": 80,
                                                                           "reported_output_tokens": 12,
                                                                           "usage_reported_calls": 1,
                                                                           "unknown_usage_calls": 0,
                                                                           "latency_s": [0.4]}}})
    Store(learning.path).upsert(Run.model_validate(run))
    before = Store(learning.path).get("terminal")
    report = learning.review("terminal")
    assert learning.status("terminal")["state"] == "ready"
    assert report == learning.report("terminal")
    assert len(report["proposed_experiments"]) == 1
    assert report["model_calls"] == 2 and report["model_usage"]["fallbacks"] == 1
    assert report["model_usage"]["unknown_usage_calls"] == 2
    assert report["package_advice_usage"]["calls"] == 1
    assert report["package_advice_usage"]["reported_input_tokens"] == 80
    assert any(item.get("code") == "low_score" and item["category"] == "test"
               for item in report["findings"])
    assert learning.review("terminal")["proposed_experiments"] == report["proposed_experiments"]
    assert Store(learning.path).get("terminal") == before
    assert report["missing_evidence"] == ["matching_public_data_unavailable"]


def test_no_deal_feedback_cites_original_attempt_without_inventing_cause(tmp_path):
    learning = LearningStore(tmp_path / "lab.db")
    run = snapshot("no-deal", status="completed", score=0.0)
    run["status"] = "completed"
    run["attempts"][0].update(session_id="session-a", result={"deal": False})
    Store(learning.path).upsert(Run.model_validate(run))
    findings = learning.review("no-deal")["findings"]
    no_deal = next(item for item in findings if item.get("code") == "no_deal")
    assert no_deal["evidence"] == [{"run_id": "no-deal", "attempt_id": run["attempts"][0]["attempt_id"]}]
    assert "not causal proof" in no_deal["confidence_basis"]


def test_stronger_anchor_proposal_requires_two_valid_price_dominated_cases(tmp_path):
    learning = LearningStore(tmp_path / "lab.db")
    run = snapshot("weak-deals", status="completed", score=0.4)
    run.update(status="completed", agent="package", source="tracked")
    first = run["attempts"][0]
    first.update(status="completed", score=0.4, timeouts=0,
                 result={"deal": True, "must_haves_ok": True, "c_deal": 100,
                         "cost_breakdown": {"price": 90}})
    second = deepcopy(first)
    second.update(attempt_id="second", case_id="case:D02", score=0.3)
    run["cases"].append("case:D02")
    run["attempts"].append(second)
    Store(learning.path).upsert(Run.model_validate(run))
    report = learning.review("weak-deals")
    proposal = next(p for p in report["proposed_experiments"]
                    if p["kind"] == "stronger_opening_anchor")
    assert proposal["config_patch"] == {"anchor": 0.16}
    assert {e["case_id"] for e in proposal["evidence"]} == {"case:D01", "case:D02"}
    second["result"]["must_haves_ok"] = False
    assert not any(p["kind"] == "stronger_opening_anchor"
                   for p in learning._proposals(run, report))


def test_feedback_reads_only_prior_same_version_episodic_observations(tmp_path):
    learning = LearningStore(tmp_path / "lab.db")
    for name, version, date in (("prior", "b" * 64, "2026-10-10T11:00:00+00:00"),
                                ("other-case", "b" * 64, "2026-10-10T11:00:00+00:00"),
                                ("other-version", "c" * 64, "2026-10-10T11:00:00+00:00"),
                                ("current", "b" * 64, "2026-10-10T12:00:00+00:00")):
        run = snapshot(name, status="completed", score=0.5)
        run.update(status="completed", started_at=date, updated_at=date)
        if name == "other-case":
            run["attempts"][0]["case_id"] = "case:D02"
            run["cases"] = ["case:D02"]
        run["provenance"]["data_sha256"] = version
        run["attempts"][0].update(session_id="session-" + name,
                                  result={"ended": True, "deal": True, "must_haves_ok": True},
                                  threads={"sup:A": [{"from": "sup:A", "body": "We prefer faster payment."}]})
        Store(learning.path).upsert(Run.model_validate(run))
    report = learning.review("current")
    assert len(report["episodic_context"]) == 1
    assert report["episodic_context"][0]["citation"]["run_id"] == "prior"
    assert "excerpt" not in report["episodic_context"][0]
    scope = {"supplier": "sup:A", "case_id": "case:D01", "arena_url": "https://arena.tacto.ai",
             "environment": "sandbox", "data_sha256": "b" * 64,
             "before": "2026-10-10T12:00:00+00:00"}
    assert len(learning.context(**scope, purpose="feedback", limit=1)["episodic_observations"]) == 1
    assert learning.context(**scope, purpose="live")["episodic_observations"] == []
    different = learning.context(**{**scope, "data_sha256": "c" * 64})["episodic_observations"]
    assert len(different) == 1 and different[0]["citation"]["run_id"] == "other-version"


def test_learning_candidate_requires_review_before_promotion(tmp_path):
    path = tmp_path / "lab.db"
    learning = LearningStore(path)
    loop = LoopStore(path)
    base = checkpoint("base")
    candidate = deepcopy(checkpoint("candidate"))
    candidate["parent_id"] = "base"
    candidate["config"]["final_hold_s"] = 20.0
    loop.write("checkpoint", base)
    loop.write("checkpoint", candidate)
    loop.write("suite", default_suite())
    loop.write("family", {"family_id": "family", "max_sessions": 12})
    loop.write("seed", {"suite_id": default_suite()["suite_id"], "checkpoint_id": "base", "author": "tester"})
    proposal = {"proposal_id": "proposal-1", "status": "draft", "config_patch": {"final_hold_s": 20.0}}
    with learning._connect() as db:
        db.execute("INSERT INTO learning_proposals VALUES(?,?)", ("proposal-1", json.dumps(proposal)))
    loop.write("learning-register", {"proposal_id": "proposal-1", "checkpoint_id": "candidate"})
    campaign = loop.write("campaign", {"campaign_id": "comparison", "family_id": "family",
                                       "suite_id": default_suite()["suite_id"], "baseline_id": "base",
                                       "candidate_id": "candidate", "generation": 1, "seed": 1,
                                       "author": "tester", "hypothesis": "shorter hold"})
    finish(loop, campaign)
    assert loop.write("complete", {"campaign_id": "comparison"})["status"] == "awaiting_review"
    assert loop.read("recommended", default_suite()["suite_id"])["checkpoint_id"] == "base"
    with pytest.raises(ValueError, match="different author"):
        loop.write("learning-review", {"proposal_id": "proposal-1", "campaign_id": "comparison",
                                       "author": "tester", "approve": True})
    decision = {"proposal_id": "proposal-1", "campaign_id": "comparison", "author": "reviewer", "approve": True}
    assert loop.write("learning-review", decision)["status"] == "approved"
    assert loop.write("learning-review", decision)["status"] == "approved"
    assert loop.read("recommended", default_suite()["suite_id"])["checkpoint_id"] == "candidate"


def test_failed_comparison_marks_registered_proposal_evaluated(tmp_path):
    path = tmp_path / "lab.db"
    learning, loop = LearningStore(path), LoopStore(path)
    base = checkpoint("base")
    candidate = deepcopy(checkpoint("candidate"))
    candidate["parent_id"] = "base"
    candidate["config"]["final_hold_s"] = 20.0
    loop.write("checkpoint", base)
    loop.write("checkpoint", candidate)
    suite = default_suite()
    loop.write("suite", suite)
    loop.write("family", {"family_id": "family", "max_sessions": 12})
    loop.write("seed", {"suite_id": suite["suite_id"], "checkpoint_id": "base", "author": "tester"})
    proposal = {"proposal_id": "proposal-1", "status": "draft", "config_patch": {"final_hold_s": 20.0}}
    with learning._connect() as db:
        db.execute("INSERT INTO learning_proposals VALUES(?,?)", ("proposal-1", json.dumps(proposal)))
    loop.write("learning-register", {"proposal_id": "proposal-1", "checkpoint_id": "candidate"})
    campaign = loop.write("campaign", {"campaign_id": "comparison", "family_id": "family",
                                       "suite_id": suite["suite_id"], "baseline_id": "base",
                                       "candidate_id": "candidate", "generation": 1, "seed": 1,
                                       "author": "tester", "hypothesis": "shorter hold"})
    for attempt in campaign["attempts"]:
        loop.write("attempt-start", {"attempt_id": attempt["attempt_id"], "worker_id": "laptop",
                                     "key_id": "shared"})
        loop.write("attempt-result", {"attempt_id": attempt["attempt_id"],
                                      "checkpoint_id": attempt["checkpoint_id"],
                                      "session_id": attempt["attempt_id"], "status": "completed",
                                      "score": 0.4 if attempt["arm"] == "candidate" else 0.6,
                                      "timeouts": 0, "result": {"deal": True, "must_haves_ok": True,
                                                              "ended": True}, "threads": {}, "elapsed_s": 1.0})
    assert loop.write("complete", {"campaign_id": "comparison"})["status"] == "rejected"
    assert loop.read("recommended", suite["suite_id"])["checkpoint_id"] == "base"
    saved = learning.proposals()[0]
    assert saved["status"] == "evaluated_rejected"
    assert saved["campaign_id"] == "comparison"
    assert saved["evaluation_status"] == "rejected"
    # A campaign completed by an older lab revision can be repaired idempotently.
    with learning._connect() as db:
        db.execute("UPDATE learning_proposals SET body=? WHERE proposal_id=?",
                   (json.dumps({**saved, "status": "registered"}), "proposal-1"))
    assert loop.write("complete", {"campaign_id": "comparison"})["status"] == "rejected"
    assert learning.proposals()[0]["status"] == "evaluated_rejected"


def test_stale_feedback_cannot_register_a_checkpoint(tmp_path):
    path = tmp_path / "lab.db"
    learning, loop = LearningStore(path), LoopStore(path)
    run = snapshot("stale", status="completed", score=0.4)
    run.update(status="completed", agent="package")
    run["attempts"][0].update(session_id="session-a", timeouts=1,
                              result={"ended": True, "deal": True, "must_haves_ok": True})
    Store(path).upsert(Run.model_validate(run))
    proposal = learning.review("stale")["proposed_experiments"][0]
    base, candidate = checkpoint("base"), deepcopy(checkpoint("candidate"))
    candidate["parent_id"] = "base"
    candidate["config"].update(proposal["config_patch"])
    loop.write("checkpoint", base)
    loop.write("checkpoint", candidate)
    run["revision"] = 2
    run["updated_at"] = "2026-10-10T12:01:00+00:00"
    Store(path).upsert(Run.model_validate(run))
    with pytest.raises(Conflict, match="source changed"):
        loop.write("learning-register", {"proposal_id": proposal["proposal_id"],
                                         "checkpoint_id": "candidate"})


def test_public_graph_does_not_infer_contact_identity_from_names():
    package = SimpleNamespace(manifest={"sha256": "version", "conflicts": {
                                  "sc:1": {"base": {"otd_pct": 80}, "release": {"otd_pct": 90}}
                              }}, sources={"contact:1": "release"},
                              facts={"contact:1": {"supplier": "sup:A", "name": "Alex",
                                                    "authority": "unknown"}})
    graph = export_graph([], package=package)
    assert any(e["relation"] == "has_contact_fact" for e in graph["edges"])
    assert not any(n["kind"] == "current_contact" for n in graph["nodes"])
    conflict = next(n for n in graph["nodes"] if n["kind"] == "public_conflict")
    assert conflict["data"]["versions"]["release"]["otd_pct"] == 90


def test_terminal_upload_projects_feedback_and_retry_preserves_original(dashboard, monkeypatch):
    client, store = dashboard
    client.headers["Authorization"] = "Bearer test-token"
    body = snapshot("learned", status="completed", score=0.5)
    body["status"] = "completed"
    body["agent"] = "package"
    body["attempts"][0].update(session_id="session-learned", timeouts=1,
                               result={"ended": True, "deal": True, "must_haves_ok": True})
    original = LearningStore._proposals

    def fail(*_):
        raise RuntimeError("synthetic feedback failure")

    monkeypatch.setattr(LearningStore, "_proposals", staticmethod(fail))
    assert client.put("/api/runs/learned", json=body).json()["accepted"]
    assert client.get("/api/learning/status/learned").json()["state"] == "failed"
    assert client.get("/api/feedback/learned").status_code == 503
    saved = store.get("learned")
    monkeypatch.setattr(LearningStore, "_proposals", staticmethod(original))
    assert client.post("/api/learning/retry/learned", json={}).json()["state"] == "ready"
    assert client.get("/api/feedback/learned").json()["run_id"] == "learned"
    assert len(client.get("/api/learning/proposals").json()["proposals"]) == 1
    assert client.get("/api/learning/graph").status_code == 200
    assert client.get("/api/learning/context", params={
        "supplier": "sup:A", "case_id": "case:D01", "arena_url": "https://arena.tacto.ai",
        "environment": "sandbox", "data_sha256": "b" * 64,
        "before": "2026-10-10T12:00:00+00:00", "purpose": "live",
    }).json()["episodic_observations"] == []
    assert store.get("learned") == saved
