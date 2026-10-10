import json
from types import SimpleNamespace

import pytest
from test_lab_workspace import saved

from negotiator.lab.learning import LearningStore
from negotiator.lab.loop_store import LoopStore
from negotiator.lab.models import Run
from negotiator.lab.store import Store
from negotiator.lab.supplier_graph import catalog, fact_state, graph, packages
from negotiator.lab.workspace import records

pytest_plugins = ["test_lab_server"]


def register(store, version="b", *, supplier="sup:A", day="10", conflict=False):
    LearningStore(store.path)
    body = {"data_sha256": version * 64, "ingested_at": f"2026-10-{day}T12:00:00+00:00",
            "checked_at": f"2026-10-{day}T12:00:00+00:00", "label": f"Release {version}",
            "manifest": {"conflicts": {"news:collision": {
                "base": {"supplier": supplier, "headline": "Old"},
                "release": {"supplier": supplier, "headline": "Changed"}}} if conflict else {}},
            "facts": {"news:1": {"supplier": supplier, "date": "2026-10-09", "headline": f"{version} update"},
                      "quote:1": {"supplier": supplier, "part": "part:NEW", "price": 55}},
            "sources": {"news:1": "release", "quote:1": "base"},
            "entities": {"suppliers": [{"id": supplier, "name": f"Company {version}"}],
                         "parts": [{"id": "part:NEW", "description": "New part"}]}}
    with store._connect() as db:
        db.execute("INSERT INTO learning_data VALUES(?,?,?)",
                   (body["data_sha256"], json.dumps(body), body["ingested_at"]))
    return body


def all_records(store):
    return records(store, LoopStore(store.path))


def test_shared_memory_combines_cases_and_contributors_with_citations(tmp_path):
    store = Store(tmp_path / "lab.db")
    register(store)
    for i in range(3):
        run = saved(str(i))
        run.update(agent="naive" if i == 0 else "package", author=f"Author {i}")
        run["attempts"][0]["case_id"] = f"case:D0{i + 1}"
        run["cases"] = [f"case:D0{i + 1}"]
        store.upsert(Run.model_validate(run))
    g = graph(store, all_records(store), supplier="sup:A")
    assert g["coverage"]["sessions"] == 3
    assert g["coverage"]["contributors"] == 3
    statement = next(n for n in g["nodes"]
                     if n["kind"] == "observation" and n["values"]["kind"] == "supplier_statement")
    assert statement["values"]["session_count"] == 3
    assert {e["case_id"] for e in statement["evidence"]} == {"case:D01", "case:D02", "case:D03"}
    ids = {n["id"] for n in g["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in g["edges"])
    assert g["freshness"]["external_news_connected"] is False


def test_new_release_reused_ids_do_not_inherit_old_runs_or_facts(tmp_path):
    store = Store(tmp_path / "lab.db")
    register(store)
    store.upsert(Run.model_validate(saved()))
    before = store.get("one")
    register(store, "c", day="11")
    register(store, "d", supplier="sup:UNSEEN", day="12")
    c = catalog(store, all_records(store))
    assert any(s["id"] == "sup:UNSEEN" and not s["has_history"] for s in c["suppliers"])
    unseen = graph(store, all_records(store), supplier="sup:UNSEEN")
    assert unseen["name"] == "Company d" and unseen["coverage"]["source_facts"] == 2
    assert unseen["coverage"]["sessions"] == 0
    new = graph(store, all_records(store), supplier="sup:A", dataset="c" * 64)
    assert new["name"] == "Company c"
    assert new["coverage"]["sessions"] == new["coverage"]["shared_observations"] == 0
    assert not any(n["label"] == "b update" for n in new["nodes"])
    assert store.get("one") == before
    old = graph(store, all_records(store), supplier="sup:A", dataset="b" * 64)
    assert old["coverage"]["sessions"] == 1
    assert {n["id"] for n in old["nodes"] if n["kind"] == "source_fact"}.isdisjoint(
        n["id"] for n in new["nodes"] if n["kind"] == "source_fact")


def test_history_keeps_unknown_versions_arenas_and_environments_separate(tmp_path):
    store = Store(tmp_path / "lab.db")
    for name, version, env, arena in [("one", None, "practice", "https://arena.tacto.ai"),
                                     ("two", None, "practice", "https://arena.tacto.ai"),
                                     ("other", "b", "practice", "https://other.example"),
                                     ("sandbox", "b", "sandbox", "https://arena.tacto.ai")]:
        run = saved(name, env=env)
        run["arena_url"] = arena
        if version is None:
            run["provenance"] = None
        store.upsert(Run.model_validate(run))
    g = graph(store, all_records(store), supplier="sup:A", dataset="history", arena="https://arena.tacto.ai")
    assert g["coverage"]["sessions"] == 2
    statements = [n for n in g["nodes"]
                  if n["kind"] == "observation" and n["values"]["kind"] == "supplier_statement"]
    assert len(statements) == 2
    assert all(n["values"]["session_count"] == 1 for n in statements)
    assert len({n["values"]["dataset"] for n in statements}) == 2


def test_conflicts_and_dates_remain_explicit(tmp_path):
    store = Store(tmp_path / "lab.db")
    register(store, conflict=True)
    for i, message in enumerate(["We prefer faster payment.", "We prefer later payment."]):
        run = saved(str(i))
        run["attempts"][0]["threads"]["sup:A"]["messages"][0]["body"] = message
        store.upsert(Run.model_validate(run))
    g = graph(store, all_records(store), supplier="sup:A")
    assert len([n for n in g["nodes"] if n["group"] == "conflicts"]) == 2
    assert not any(n["kind"] == "source_fact" and n["label"] == "news:collision" for n in g["nodes"])
    assert fact_state({"date": "2099-01-01"}, "2026-10-11") == "future dated"
    assert fact_state({"valid_to": "2020-01-01"}, "2026-10-11") == "expired"
    assert fact_state({}, "2026-10-11") == "date unknown"


def test_ingestion_hashes_discovered_overlay_and_recheck_does_not_activate_old_data(tmp_path, monkeypatch):
    base, overlay = tmp_path / "data", tmp_path / "release"
    base.mkdir()
    overlay.mkdir()
    (base / "facts.json").write_text("{}")
    (overlay / "facts.json").write_text("{}")
    state = {"release": None, "sha": "base"}

    def package(*_):
        return SimpleNamespace(release=state["release"], facts={}, sources={}, db=None,
                               manifest={"sha256": state["sha"]}, warnings=[], conflicts=[])

    monkeypatch.setattr("negotiator.lab.learning.load_package", package)
    learning = LearningStore(tmp_path / "lab.db")
    first = learning.ingest(base, label="Initial")
    state.update(release=overlay, sha="overlay")
    second = learning.ingest(base, label="Release")
    assert first["data_sha256"] != second["data_sha256"]
    state.update(release=None, sha="base")
    learning.ingest(base)
    data = packages(Store(learning.path))
    assert data[0]["data_sha256"] == second["data_sha256"]
    assert data[1]["label"] == "Initial"
    assert data[1]["checked_at"] >= data[1]["ingested_at"]


def test_knowledge_routes_auth_and_scope(dashboard):
    client, store = dashboard
    register(store)
    store.upsert(Run.model_validate(saved()))
    assert client.get("/api/workspace/knowledge?supplier=sup:A").status_code == 401
    client.post("/api/login", json={"password": "test-password"})
    assert client.get("/knowledge.js").status_code == 200
    result = client.get("/api/workspace/knowledge?supplier=sup:A").json()
    assert result["graph"]["coverage"]["sessions"] == 1
    assert result["catalog"]["external_news_connected"] is False
    assert client.get("/api/workspace/knowledge?supplier=missing").status_code == 404
    assert client.get("/api/workspace/knowledge?supplier=sup:A&dataset=missing").status_code == 404
    assert client.get("/api/workspace/knowledge?environment=production").status_code == 400


def test_explicit_missing_release_is_not_silently_ingested_as_base(tmp_path, monkeypatch):
    base = tmp_path / "data"
    base.mkdir()
    (base / "facts.json").write_text("{}")
    monkeypatch.setattr("negotiator.lab.learning.load_package",
                        lambda *_: SimpleNamespace(release=None, db=None))
    learning = LearningStore(tmp_path / "lab.db")
    with pytest.raises(ValueError, match="configured release"):
        learning.ingest(base, tmp_path / "missing-release")
    assert packages(Store(learning.path)) == []
