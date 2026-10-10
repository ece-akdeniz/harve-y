from copy import deepcopy

from test_lab_server import snapshot

from negotiator.lab.feedback import FeedbackAgent, review_store
from negotiator.lab.knowledge import SnapshotMemory, export_graph
from negotiator.lab.models import Run
from negotiator.lab.store import Store


def recorded(name, *, version="b" * 64, date="2026-10-10T12:00:00+00:00"):
    run = snapshot(name, status="failed")
    run.update(status="failed", started_at=date, updated_at=date)
    run["provenance"]["data_sha256"] = version
    run["attempts"][0].update(session_id=name, result={"reconciled_result": {"score": 0.9}},
                              threads={"sup:A": [{"from": "supplier", "body": "Our energy is hedged.",
                                                  "term_sheets": [{"term_sheet_id": "ts:1",
                                                                   "terms": {"unit_price": 12}}]}]})
    return run


def test_graph_is_stable_and_keeps_failure_and_claims_attributed():
    first, second = recorded("a"), recorded("b")
    graph = export_graph([first, second])
    assert graph == export_graph([deepcopy(second), deepcopy(first)])
    assert len([n for n in graph["nodes"] if n["kind"] == "supplier"]) == 1
    attempts = [n for n in graph["nodes"] if n["kind"] == "attempt"]
    assert all(n["data"]["status"] == "failed" and n["data"]["score"] is None for n in attempts)
    assert all(n["data"]["result"]["reconciled_result"]["score"] == .9 for n in attempts)
    message = next(n for n in graph["nodes"] if n["kind"] == "message")
    assert message["data"]["from"] == "supplier" and message["provenance"]["message_index"] == 0
    assert all(n["scope"] == "evaluation_only" for n in graph["nodes"])
    ids = {n["id"] for n in graph["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in graph["edges"])


def test_memory_is_version_scoped_asof_bounded_and_unavailable_to_live_play():
    current = recorded("current", date="2026-10-10T13:00:00+00:00")
    runs = [recorded("prior"), recorded("unknown", version=None), recorded("different", version="c" * 64),
            recorded("future", date="2026-10-10T14:00:00+00:00"), current]
    memory = SnapshotMemory(export_graph(runs))
    found = memory.supplier_history(current, "sup:A", purpose="feedback", limit=1)
    assert [n["provenance"]["run_id"] for n in found] == ["prior"]
    assert memory.supplier_history(current, "sup:A", purpose="live") == []
    assert memory.supplier_history(recorded("unknown2", version=None), "sup:A", purpose="feedback") == []


def test_feedback_uses_shared_history_and_graph_ignores_stale_reports(tmp_path):
    store = Store(tmp_path / "lab.db")
    for body in [recorded("prior"), recorded("current", date="2026-10-10T13:00:00+00:00")]:
        store.upsert(Run.model_validate(body))
    reports = review_store(store)["reports"]
    current = next(r for r in reports if r["run_id"] == "current")
    finding = next(f for f in current["findings"] if "Shared memory" in f["observation"])
    assert finding["evidence"][-1]["run_id"] == "prior"
    graph = export_graph(store.all(), reports)
    assert any(n["kind"] == "observation" for n in graph["nodes"])
    observation = next(n for n in graph["nodes"] if n["kind"] == "observation" and
                       "Shared memory" in n["data"]["observation"])
    evidence_ids = {e["target"] for e in graph["edges"] if e["source"] == observation["id"] and
                    e["relation"] == "supported_by"}
    assert {n["provenance"]["run_id"] for n in graph["nodes"] if n["id"] in evidence_ids} == {"prior", "current"}
    changed = recorded("current")
    stale = FeedbackAgent().review(changed)
    changed["attempts"][0]["timeouts"] = 2
    assert not any(n["kind"] == "observation" for n in export_graph([changed], [stale])["nodes"])


def test_historical_math_does_not_use_unmatched_data(monkeypatch):
    checked = []
    monkeypatch.setattr("negotiator.lab.feedback.evaluate", lambda *args: checked.append(args))
    run = recorded("recorded")
    run["attempts"][0]["threads"]["sup:A"][0]["from"] = "buyer"
    case = {"case:D01": {"case_id": "case:D01"}}
    report = FeedbackAgent().review(run, case, data_sha256="c" * 64)
    assert not checked and report["package_validation"].startswith("skipped")
    FeedbackAgent().review(run, case, data_sha256="b" * 64)
    assert len(checked) == 1
