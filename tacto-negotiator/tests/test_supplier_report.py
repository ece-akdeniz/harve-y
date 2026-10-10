import copy

from test_lab_workspace import saved
from test_supplier_graph import register

from negotiator.lab.loop_store import LoopStore
from negotiator.lab.models import Run
from negotiator.lab.store import Store
from negotiator.lab.supplier_graph import graph
from negotiator.lab.supplier_report import build_report, session_brief
from negotiator.lab.workspace import records


def keep(store, name, *, version="b", env="practice", sid="sup:A", status="completed"):
    run = saved(name, env=env, sid=sid, status=status)
    run["provenance"]["data_sha256"] = version * 64 if version else None
    run["started_at"] = run["updated_at"] = f"2026-10-11T00:{int(name):02}:00+00:00"
    return run


def report(store, supplier="sup:A", dataset="latest"):
    return graph(store, records(store, LoopStore(store.path)), supplier=supplier, dataset=dataset)["report"]


def test_report_summarizes_offers_and_links_original_messages(tmp_path):
    store = Store(tmp_path / "lab.db")
    register(store)
    run = keep(store, "1")
    run["attempts"][0]["threads"]["sup:A"]["messages"] = [
        {"from": "sup:A", "body": "We need binding volume before changing the price.",
         "term_sheets": [{"terms": {"unit_price": 100, "payment_days": 30}}]},
        {"from": "buyer", "body": "We propose 90 days.", "term_sheets": [{"terms": {"payment_days": 90}}]},
        {"from": "sup:A", "body": "We can accept 90-day payment terms with a binding volume commitment.",
         "term_sheets": [{"terms": {"unit_price": 95, "payment_days": 90}}]},
    ]
    store.upsert(Run.model_validate(run))
    before = copy.deepcopy(store.get("1"))
    result = report(store)
    p = result["partitions"][0]
    assert p["stats"]["valid_deals"] == 1
    assert len(p["latest"]["changes"]) == 2
    assert "payment 90 days" in p["latest"]["summary"][1]["text"]
    assert p["latest"]["summary"][1]["evidence"][0]["message_index"] == 1
    volume = next(t for t in p["topics"] if t["title"] == "Volume & commitment")
    assert volume["count"] == 1
    assert volume["evidence"][0]["message_index"] == 2
    assert "binding volume" in volume["evidence"][0]["quote"]
    assert any(n["status"] == "Untested suggestion" for n in p["next_steps"])
    assert store.get("1") == before


def test_latest_failed_case_does_not_inflate_savings_with_earlier_repeats(tmp_path):
    store = Store(tmp_path / "lab.db")
    register(store)
    for name, status in [("1", "completed"), ("2", "completed"), ("3", "failed")]:
        store.upsert(Run.model_validate(keep(store, name, status=status)))
    p = report(store)["partitions"][0]
    assert p["stats"]["valid_deals"] == 2
    assert p["stats"]["sessions"] == 3
    assert p["stats"]["latest_case_reduction_eur"] is None
    assert p["stats"]["cost_coverage"] == 0
    assert p["next_steps"][0]["status"] == "Review first"
    assert p["latest"]["outcome"]["kind"] == "failed"


def test_other_supplier_deal_is_not_attributed_to_this_supplier(tmp_path):
    store = Store(tmp_path / "lab.db")
    register(store)
    run = keep(store, "1")
    run["attempts"][0]["result"]["supplier_id"] = "sup:B"
    store.upsert(Run.model_validate(run))
    p = report(store)["partitions"][0]
    assert p["stats"]["valid_deals"] == 0
    assert p["stats"]["other_selected"] == 1
    assert p["latest"]["savings"] is None


def test_report_partitions_versions_unknown_sources_and_arenas(tmp_path):
    store = Store(tmp_path / "lab.db")
    register(store)
    register(store, "c", day="11")
    for name, version, env in [("1", "b", "practice"), ("2", "c", "practice"),
                               ("3", None, "practice"), ("4", None, "practice"), ("5", "b", "sandbox")]:
        run = keep(store, name, version=version, env=env)
        store.upsert(Run.model_validate(run))
    assert report(store)["partitions"][0]["stats"]["sessions"] == 1
    assert len(report(store, dataset="history")["partitions"]) == 4
    assert len(report(store, dataset="history")["history"]) == 4
    register(store, "d", supplier="sup:NEW", day="12")
    assert report(store, "sup:NEW")["partitions"] == []
    assert report(store, "sup:NEW")["history"] == []


def test_quotes_preserve_negation_and_are_not_promoted_to_preferences(tmp_path):
    store = Store(tmp_path / "lab.db")
    register(store)
    run = keep(store, "1")
    quote = "We do not prefer longer payment terms."
    run["attempts"][0]["threads"]["sup:A"]["messages"][0]["body"] = quote
    store.upsert(Run.model_validate(run))
    p = report(store)["partitions"][0]
    assert any(quote == ref["quote"] for topic in p["topics"] for ref in topic["evidence"])
    assert not any(m["title"] == "Explicit supplier statement" for m in p["memory"])
    assert all(a["status"] == "Suggested approach" for a in p["approach"])


def test_missing_and_malformed_optional_message_fields_remain_unknown():
    run = saved()
    run["attempts"][0]["threads"]["sup:A"]["messages"] = [
        {"from": "sup:A", "term_sheets": "unavailable", "body": None},
        {"from": "buyer", "term_sheets": [{"terms": None}]},
    ]
    run["attempts"][0]["result"] = {}
    record = {"id": "session-record", "run": run, "attempt": run["attempts"][0]}
    brief = session_brief(record, "sup:A")
    assert brief["outcome"]["kind"] == "unknown"
    assert brief["changes"] == []
    assert len(brief["summary"]) == 1
    assert build_report([record], "sup:A", [])["partitions"][0]["stats"]["valid_deals"] == 0
