import copy

# Imported pytest fixture is intentionally requested by name.
# ruff: noqa: F811
from test_lab_server import dashboard, snapshot  # noqa: F401

from negotiator.lab.loop_store import LoopStore
from negotiator.lab.models import Run
from negotiator.lab.workspace import detail, directory, records, savings


def saved(name="one", *, status="completed", env="practice", sid="sup:A", price=80):
    r = snapshot(name, status=status, score=0.7 if status == "completed" else None)
    r.update(status="completed" if status == "completed" else "running", environment=env)
    a = r["attempts"][0]
    a.update(session_id=name, result={"ended": True, "deal": True, "supplier_id": sid,
        "must_haves_ok": True, "c_open": 100, "c_deal": price, "terms": {"payment_days": 30}},
        threads={sid: {"messages": [{"from": "sales@A", "from_name": "Supplier A", "body": "We prefer faster payment.",
                    "term_sheets": [{"terms": {"payment_days": 30}}]}]}})
    return r


def test_savings_requires_valid_original_complete_deal_and_keeps_losses():
    r = saved(price=120)
    record = {"run": r, "attempt": r["attempts"][0]}
    assert savings(record)["change_eur"] == -20
    for changes in ({"must_haves_ok": None}, {"deal": False}, {"ended": False}, {"c_open": 0},
                    {"c_deal": True}, {"c_deal": float("nan")}):
        a = copy.deepcopy(record)
        a["attempt"]["result"].update(changes)
        assert savings(a) is None
    record["attempt"]["status"] = "failed"
    assert savings(record) is None


def test_latest_case_savings_not_sum_of_repeated_experiments(dashboard):
    _, store = dashboard
    for i, price in enumerate([80, 90]):
        r = saved(str(i), price=price)
        r["started_at"] = r["updated_at"] = f"2026-10-10T12:0{i}:00+00:00"
        store.upsert(Run.model_validate(r))
    data = directory(records(store, LoopStore(store.path)), "practice")
    assert data["summary"]["sessions"] == 2
    assert data["summary"]["savings_eur"] == 10
    assert data["summary"]["savings_covered"] == 1
    assert directory(records(store, LoopStore(store.path)), "sandbox")["summary"]["savings_eur"] is None


def test_latest_failed_attempt_does_not_fall_back_to_older_success(dashboard):
    _, store = dashboard
    store.upsert(Run.model_validate(saved()))
    r = saved("later", status="failed")
    r["updated_at"] = r["started_at"] = "2026-10-10T13:00:00+00:00"
    store.upsert(Run.model_validate(r))
    assert directory(records(store, LoopStore(store.path)), "practice")["summary"]["savings_covered"] == 0


def test_workspace_auth_routes_and_no_record_mutation(dashboard):
    client, store = dashboard
    store.upsert(Run.model_validate(saved()))
    before = store.get("one")
    assert client.get("/api/workspace").status_code == 401
    assert client.get("/api/workspace/suppliers/anything").status_code == 401
    client.post("/api/login", json={"password": "test-password"})
    listing = client.get("/api/workspace").json()
    key = listing["suppliers"][0]["key"]
    d = client.get(f"/api/workspace/suppliers/{key}").json()
    assert d["supplier_id"] == "sup:A"
    assert d["messages"][0]["body"] == "We prefer faster payment."
    assert client.get(f"/api/workspace/suppliers/{key}?negotiation=missing").status_code == 404
    assert client.get("/api/workspace?environment=production").status_code == 400
    assert store.get("one") == before
    for path in ("/workspace", "/workspace.js", "/workspace.css"):
        assert client.get(path).status_code == 200


def test_losing_supplier_not_assigned_case_score_or_cost(dashboard):
    _, store = dashboard
    r = saved()
    r["attempts"][0]["threads"]["sup:B"] = {"messages": []}
    store.upsert(Run.model_validate(r))
    all_records = records(store, LoopStore(store.path))
    suppliers = directory(all_records, "practice")["suppliers"]
    b = next(s for s in suppliers if s["supplier_id"] == "sup:B")
    d = detail(store, all_records, b["key"])
    assert d["negotiation"]["score"] is None
    assert d["negotiation"]["savings"] is None
    assert d["result"] == {}


def test_memory_isolated_by_arena_environment_case_and_data(dashboard):
    _, store = dashboard
    for name, env, data, case in [("one", "practice", "b", "case:D01"),
                                  ("two", "sandbox", "b", "case:D01"),
                                  ("three", "practice", "c", "case:D01"),
                                  ("four", "practice", "b", "case:D02")]:
        r = saved(name, env=env)
        r["provenance"]["data_sha256"] = data * 64
        r["cases"] = [case]
        r["attempts"][0]["case_id"] = case
        store.upsert(Run.model_validate(r))
    all_records = records(store, LoopStore(store.path))
    s = directory(all_records, "practice")["suppliers"][0]
    n = next(n for n in s["negotiations"] if n["session_id"] == "one")
    d = detail(store, all_records, s["key"], n["id"])
    assert d["memory"]["observations"]
    assert {o["citation"]["session_id"] for o in d["memory"]["observations"]} == {"one"}


def test_campaign_duplicate_import_counts_once(dashboard):
    from test_lab_loop_store import campaign, checkpoint

    from negotiator.lab.policy import default_suite

    _, store = dashboard
    loop = LoopStore(store.path)
    for name in ("base", "one"):
        loop.write("checkpoint", checkpoint(name))
    loop.write("suite", default_suite())
    loop.write("family", {"family_id": "f", "max_sessions": 12})
    loop.write("seed", {"suite_id": default_suite()["suite_id"], "checkpoint_id": "base", "author": "tester"})
    c = campaign(loop)
    a = c["attempts"][0]
    loop.write("attempt-start", {"attempt_id": a["attempt_id"], "worker_id": "test", "key_id": "test"})
    assert directory(records(store, loop), "sandbox")["summary"]["running"] == 1
    r = saved("owned", env="sandbox")
    outcome = r["attempts"][0]
    loop.write("attempt-result", {"attempt_id": a["attempt_id"], "checkpoint_id": a["checkpoint_id"],
        "session_id": "owned", "status": "completed", "score": 0.7, "result": outcome["result"],
        "threads": outcome["threads"]})
    r["source"] = "imported"
    store.upsert(Run.model_validate(r))
    rows = records(store, loop)
    assert len(rows) == 1
    assert rows[0]["run"]["source"] == "campaign"
