import dataclasses
import json
from pathlib import Path

import arena_kit
import pytest

from negotiator import claims as C
from negotiator import dossiers as D

SIM = Path(arena_kit.__file__).parent / "sim_cases"
P01_LETTER = "doc:20260911-70110-P01"
P01_STATED = "LCI-C rose 2.7 % in twelve months and is 30 % of our cost; PPI-C241 rose 6.5 % and is 24 %"


@pytest.fixture(scope="module")
def pkg():
    try:
        return D.load_package()
    except FileNotFoundError:
        pytest.skip("data package not available")


def p01_case(pkg) -> dict:
    letter = pkg.lookup(P01_LETTER)
    part = next(r["part_ids"] for r in pkg.query("SELECT part_ids FROM documents WHERE id = ?", (P01_LETTER,)))
    return {"case_id": "case:P01", "type": "price_increase", "parts": [part], "suppliers": [letter["supplier"]],
            "trigger_doc": P01_LETTER, "refs": [P01_LETTER],
            "buyer": {"current_unit_price": 126.53, "category_goal": "stabilise", "reference_payment_days": 60}}


def sim(name: str) -> dict:
    return json.loads((SIM / f"{name}.json").read_text())


def test_p01_bank_index_claims(pkg):
    bank = C.build_bank(p01_case(pkg), pkg)
    idx = {c.subject: c for c in bank if c.kind == "index_change" and not c.cherry_picked}
    assert idx["PPI-C241"].ids == ("idx:PPI-C241@2025-08", "idx:PPI-C241@2026-08")
    assert idx["PPI-C241"].figure == pytest.approx(6.5, abs=0.05) and not idx["PPI-C241"].supports_buyer
    assert idx["LCI-C"].ids == ("idx:LCI-C@2025-06", "idx:LCI-C@2026-06")  # series ends 2026-06
    assert idx["LCI-C"].figure == pytest.approx(2.7, abs=0.05)
    assert idx["PPI-D351"].figure == pytest.approx(-3.7, abs=0.05) and idx["PPI-D351"].supports_buyer
    for c in bank:
        assert all(i in pkg.facts for i in c.ids)
        assert all(i in c.sentence for i in c.ids)
        assert C.verify(c, C.case_facts(p01_case(pkg), pkg))


def test_p01_default_pick_is_buyer_side(pkg):
    case = p01_case(pkg)
    bank = C.build_bank(case, pkg)
    picked = C.pick(bank, set(), supplier_id="sup:70110", case_type=case["type"])
    assert 0 < len(picked) <= 3
    assert all(c.supports_buyer and c.disclosure in C.DEFAULT_DISCLOSURE and not c.cherry_picked for c in picked)
    ids = [i for c in picked for i in c.ids]
    assert len(ids) == len(set(ids))
    assert "idx:PPI-C241@2026-08" not in ids  # adverse: kept internal
    assert {"notice", "index_change"} <= {c.kind for c in picked}


def test_pick_never_reuses_ids(pkg):
    case = p01_case(pkg)
    bank = C.build_bank(case, pkg)
    used: set[str] = set()
    seen = []
    for _ in range(4):
        msg = C.pick(bank, used, supplier_id="sup:70110", case_type="price_increase", allow_adverse=True)
        for c in msg:
            assert not (C.claim_keys(c) & used)
            used |= C.claim_keys(c)
        seen += msg
    ids = [i for c in seen for i in c.ids]
    assert len(ids) == len(set(ids))
    assert C.pick(bank, set(), max_claims=10, allow_adverse=True) and len(
        C.pick(bank, set(), max_claims=10, allow_adverse=True)) <= 3


def test_verify_tolerance_and_rules(pkg):
    facts = C.case_facts(p01_case(pkg), pkg)
    c = next(c for c in C.build_bank(p01_case(pkg), pkg) if c.subject == "PPI-D351")
    assert C.verify(dataclasses.replace(c, figure=c.figure + 0.4), facts)
    assert not C.verify(dataclasses.replace(c, figure=c.figure + 0.6), facts)
    long = dataclasses.replace(c, ids=("idx:PPI-D351@2025-01", "idx:PPI-D351@2026-08"),
                               sentence="idx:PPI-D351@2025-01 idx:PPI-D351@2026-08")
    assert C.check(long, facts) == "window longer than 12 months"
    old = dataclasses.replace(c, ids=("idx:PPI-D351@2024-01", "idx:PPI-D351@2025-01"),
                              sentence="idx:PPI-D351@2024-01 idx:PPI-D351@2025-01")
    assert C.check(old, facts) == "window ends too early"
    assert C.check(dataclasses.replace(c, ids=("idx:NOPE@2026-08", c.ids[1])), facts) == "unknown id"
    sc = next(c for c in C.build_bank(p01_case(pkg), pkg) if c.kind == "scorecard_otd")
    assert sc.figure == 85.2 and C.verify(sc, facts)
    assert not C.verify(dataclasses.replace(sc, figure=86.0), facts)


def test_cost_pressure_estimate_p01(pkg):
    case = p01_case(pkg)
    est = C.cost_pressure_estimate(case, package=pkg, stated=P01_STATED)
    assert est["pp"] == pytest.approx(2.37, abs=0.01)
    assert est["coverage"] == pytest.approx(0.54)
    assert est["asked_pct"] == 9.5 and est["verified"] is False
    assert "2.37 percentage points" in est["sentence"] and "remainder of the requested 9.5 %" in est["sentence"]
    assert ":" not in est["sentence"].split("(")[0] and "idx:" not in est["sentence"]  # not a checked claim
    listed = C.cost_pressure_estimate(case, package=pkg)
    assert listed["coverage"] == pytest.approx(0.64) and listed["pp"] == pytest.approx(2.33, abs=0.02)


def test_parse_stated_drivers():
    rows = C.parse_stated_drivers(P01_STATED)
    assert rows == [{"series": "LCI-C", "pct": 2.7, "weight": 0.30}, {"series": "PPI-C241", "pct": 6.5, "weight": 0.24}]


@pytest.mark.parametrize("name", ["S01", "S02", "S03"])
def test_sim_cases_bank_verifies(pkg, name):
    case = sim(name)
    facts = C.case_facts(case, pkg)
    bank = C.build_bank(case, pkg)
    assert bank and all(C.verify(c, facts) for c in bank)
    assert len(C.pick(bank, set(), case_type=case["type"], allow_adverse=True)) <= 3


def test_sim_s01_cited_index_matches_refs(pkg):
    case = sim("S01")
    c = next(c for c in C.build_bank(case, pkg) if c.subject == "PPI-C2431" and not c.cherry_picked)
    assert c.ids == ("idx:PPI-C2431@2025-08", "idx:PPI-C2431@2026-08") and c.in_case_refs
    assert c.figure == pytest.approx((129.1 / 115.0 - 1) * 100, abs=0.05) and not c.supports_buyer


def test_sim_bank_from_case_facts_only():
    case = sim("S01")
    bank = C.build_bank(case)  # no package: only the case's own facts
    assert {c.kind for c in bank} == {"index_change", "scorecard_otd", "scorecard_ppm"}
    assert all(C.verify(c, case["facts"]) for c in bank)


def test_rival_quote_reveal_once_per_supplier(pkg):
    case = sim("S03")
    bank = C.build_bank(case, pkg)
    q = next(c for c in bank if c.kind == "rival_quote")
    assert q.ids == ("quote:7100042",) and q.supplier_id == "sup:70520" and q.disclosure == "reveals_rival"
    assert q not in C.pick(bank, set(), case_type="renewal", allow_adverse=True)  # not disclosed by default
    allow = C.DEFAULT_DISCLOSURE | {"reveals_rival"}
    assert q in C.pick(bank, set(), case_type="renewal", allow_adverse=True, disclosures=allow)
    assert C.claim_keys(q) == {"quote:7100042>sup:70520"}
    other = dataclasses.replace(q, supplier_id="sup:70999")
    assert C.pick([other], C.claim_keys(q), allow_adverse=True, disclosures=allow) == [other]


def test_release_overlay_shifts_latest_window(pkg, tmp_path, monkeypatch):
    rel = tmp_path / "release-sunday"
    rel.mkdir()
    (rel / "facts.json").write_text(json.dumps(
        {"idx:PPI-D351@2026-09": {"month": "2026-09", "series": "PPI-D351", "value": 120.0}}))
    monkeypatch.setenv("ARENA_RELEASE", str(rel))
    p = D.load_package(str(pkg.root))
    assert p.release == rel.resolve()
    c = next(c for c in C.build_bank(p01_case(p), p) if c.subject == "PPI-D351" and not c.cherry_picked)
    assert c.ids == ("idx:PPI-D351@2025-09", "idx:PPI-D351@2026-09")


def test_prep_writes_banks(pkg, tmp_path, monkeypatch):
    monkeypatch.delenv("ARENA_RELEASE", raising=False)
    out = tmp_path / "prep.json"
    summary = C.prep(str(pkg.root), out)
    data = json.loads(out.read_text())
    assert summary["dossiers"] == len(data["dossiers"]) > 40
    assert data["banks"]["sup:70110|part:310010"]
