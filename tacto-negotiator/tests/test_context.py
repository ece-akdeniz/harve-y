import copy
import json
from types import SimpleNamespace

from negotiator.context import build_context
from negotiator.evidence import EvidencePolicy


def fixture():
    facts = {
        "doc:n": {"supplier": "sup:F", "days": 30, "asked_pct": 9, "date": "2026-09-01", "part": "part:1"},
        "ctr:F": {"supplier": "sup:F", "days": 60, "part": "part:1",
                  "valid_from": "2026-01-01", "valid_to": "2026-12-31"},
        "idx:ENERGY@2025-08": {"value": 100, "month": "2025-08", "unit": "index points"},
        "idx:ENERGY@2026-08": {"value": 90, "month": "2026-08", "unit": "index points"},
        "sc:F@2026Q3": {"supplier": "sup:F", "otd_pct": 85, "ppm": 1200},
        "cost:1": {"part": "part:1", "unit_cost": 12},
        "sc:OTHER": {"supplier": "sup:OTHER", "otd_pct": 70},
    }
    case = {"case_id": "case:T", "type": "price_increase", "parts": ["part:1"],
            "suppliers": ["sup:F"], "trigger_doc": "doc:n", "refs": ["idx:ENERGY@2026-08"],
            "buyer": {"current_unit_price": 15, "reservation_price": 999}}
    return case, SimpleNamespace(facts=facts, db=None)


def test_snapshot_sources_units_private_candidates_and_no_reservations(tmp_path):
    case, package = fixture()
    before = copy.deepcopy((case, package.facts))
    context = build_context(case, package)
    assert (case, package.facts) == before
    assert context.version == build_context(case, package).version
    assert "sc:OTHER" not in context.facts
    assert "reservation_price" not in context.to_json()
    assert context.sources["sc:F@2026Q3"]["units"]["otd_pct"] == "%"
    assert any(c.disclosure == "internal" for c in context.candidates)
    policy = EvidencePolicy(package)
    assert policy.context_for(case).version == context.version
    assert policy.reserved == {}
    dest = tmp_path / "context.json"
    context.export(dest)
    assert json.loads(dest.read_text())["version"] == context.version


def test_overlay_changes_version_and_has_explicit_gaps():
    case, package = fixture()
    old = build_context(case, package)
    case["facts"] = {"sc:F@2026Q3": {"supplier": "sup:F", "otd_pct": 84}}
    case["refs"].append("doc:missing")
    new = build_context(case, package)
    assert old.version != new.version
    assert new.sources["sc:F@2026Q3"]["layer"] == "case"
    assert new.facts["sc:F@2026Q3"]["otd_pct"] == 84
    assert any(g.get("id") == "doc:missing" for g in new.gaps)
    assert any(g.get("kind") == "scorecard_ppm" for g in new.gaps)


def test_failed_checks_are_exported(monkeypatch):
    from dataclasses import replace

    case, package = fixture()
    claim = build_context(case, package).candidates[0]
    monkeypatch.setattr("negotiator.context.build_bank", lambda *_: [replace(claim, figure=999)])
    context = build_context(case, package)
    assert context.candidates == []
    assert context.failed_checks[0]["ids"] == list(claim.ids)


def test_trace_links_selected_claims_to_context_and_resume():
    case, package = fixture()
    records = []
    tracer = SimpleNamespace(log=lambda event, **fields: records.append({"event": event, **fields}))
    policy = EvidencePolicy(package, tracer)
    move = {"supplier_id": "sup:F", "message": {"body": "Our offer.",
            "term_sheets": [{"terms": {"unit_price": 15, "payment_days": 30}}]}}
    context = policy.context_for(case)
    out = policy.enrich(case, {}, "sup:F", move, context=context)
    assert out["message"]["term_sheets"] == move["message"]["term_sheets"]
    assert "cost:1" not in out["message"]["body"]
    assert "999" not in out["message"]["body"]
    selected = next(r for r in records if r["event"] == "evidence")
    assert selected["context_version"] == context.version
    assert all(ref in context.sources for c in selected["claims"] for ref in c["ids"])
    history = {"sup:F": [{**out["message"], "from": "buyer"}]}
    resumed = EvidencePolicy(package).enrich(case, history, "sup:F", move)
    assert not set(resumed.get("message", {}).get("refs", [])) & set(out["message"]["refs"])


def test_agent_obtains_context_and_preserves_offer_and_close(monkeypatch):
    from negotiator.agent import PackageAgent

    case, package = fixture()
    move = {"supplier_id": "sup:F", "message": {"body": "Offer.",
            "term_sheets": [{"terms": {"unit_price": 15}}]}}
    agent = PackageAgent(claims=True)
    agent.evidence.package = package
    monkeypatch.setattr(agent, "_propose", lambda *_: copy.deepcopy(move))
    out = agent.propose(case, {}, "sup:F")
    assert out["message"]["term_sheets"] == move["message"]["term_sheets"]
    assert agent.evidence.contexts[case["case_id"]]
    close = {"supplier_id": "sup:F", "message": {"action": {"type": "walk_away"}}}
    monkeypatch.setattr(agent, "_propose", lambda *_: close)
    assert agent.propose(case, {}, "sup:F") == close


def test_case_only_and_malformed_data_fallback():
    case, package = fixture()
    assert any(g["area"] == "package" for g in build_context(case, None).gaps)
    package.facts["idx:ENERGY@2025-08"]["value"] = 0
    context = build_context(case, package)
    assert not any(c.kind == "index_yoy" for c in context.candidates)
    assert any(c.kind == "scorecard_otd" for c in context.candidates)


def test_p01_context_preserves_existing_bank_and_selection():
    from pathlib import Path

    from negotiator.claims import build_bank, pick
    from negotiator.dossiers import load_package

    package = load_package()
    case = next(c for c in json.loads(Path("tests/fixtures/practice_cases.json").read_text())
                if c["case_id"] == "case:P01")
    context = build_context(case, package)
    bank = build_bank(case, package)
    assert context.candidates == bank
    selected = pick(context.candidates, set(), supplier_id="sup:70110", case_type="price_increase")
    assert selected == pick(bank, set(), supplier_id="sup:70110", case_type="price_increase")
    notice = next(c for c in context.candidates if c.kind == "notice")
    assert notice.figure == 51
    assert context.facts[notice.ids[1]]["days"] == 90
    indices = {c.subject: c for c in context.candidates if c.kind == "index_change" and not c.cherry_picked}
    assert indices["PPI-D351"].figure == -3.7
    assert indices["LCI-C"].figure == 2.7
    assert indices["PPI-C241"].figure == 6.5
    assert next(c for c in context.candidates if c.kind == "scorecard_otd").figure == 85.2
    assert next(c for c in context.candidates if c.kind == "scorecard_ppm").figure == 712
    assert {"notice", "index_change", "scorecard_otd"} == {c.kind for c in selected}
    assert context.signals
    assert all(ref in context.sources for signal in context.signals for ref in signal["source_ids"])


def test_policy_rebuild_keeps_reservations_and_rejects_wrong_scope():
    case, package = fixture()
    policy = EvidencePolicy(package)
    old = policy.context_for(case)
    policy.reserved[case["case_id"]] = {"doc:n"}
    package.facts["sc:F@2026Q3"]["otd_pct"] = 84
    new = policy.context_for(case)
    assert new.version != old.version
    assert old.facts["sc:F@2026Q3"]["otd_pct"] == 85
    assert policy.reserved[case["case_id"]] == {"doc:n"}
    move = {"message": {"body": "Offer", "term_sheets": [{"terms": {"unit_price": 15}}]}}
    assert policy.enrich({**case, "parts": ["part:OTHER"]}, {}, "sup:F", move, context=new) == move


def test_release_provenance_and_hashes(tmp_path):
    from arena_kit.data import DataPackage

    case, package = fixture()
    base = tmp_path / "base"
    release = tmp_path / "release"
    base.mkdir()
    release.mkdir()
    (base / "facts.json").write_text(json.dumps(package.facts))
    (release / "facts.json").write_text(json.dumps({"sc:F@2026Q3": {"supplier": "sup:F", "otd_pct": 84}}))
    context = build_context(case, DataPackage(base, release))
    assert context.sources["sc:F@2026Q3"]["layer"] == "release"
    assert context.sources["doc:n"]["layer"] == "base"
    assert context.sources["sc:F@2026Q3"]["path"] == str(release / "facts.json")
    assert str(release / "facts.json") in context.data_version["files"]
