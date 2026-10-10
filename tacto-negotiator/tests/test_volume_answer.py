import json
import os
from pathlib import Path

import pytest

from negotiator import volume_answer
from negotiator.agent import PackageAgent
from negotiator.policy import PolicyConfig

DATA = Path(os.environ.get("ARENA_DATA", "data/package"))


def case(cid):
    cases = json.loads((Path(__file__).parent / "fixtures/practice_cases.json").read_text())
    return next(c for c in cases if c["case_id"] == cid)


def test_config_only_adds_volume_answer():
    base = json.loads(Path("configs/score-push-v2.json").read_text())
    cfg = json.loads(Path("configs/rawmat-volume-answer.json").read_text())
    assert cfg == {**base, "volume_answer_types": ["raw_material"]}
    assert PolicyConfig.load("configs/rawmat-volume-answer.json").volume_answer_types == ("raw_material",)


def test_unknown_type_rejected(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"version": 1, "volume_answer_types": ["nope"]}))
    with pytest.raises(ValueError):
        PolicyConfig.load(p)


def test_paragraph_cites_forecast_once_and_respects_room():
    p = {"part": "part:1", "volume": 1000, "quota": 60.0,
         "forecast": ("fc:1@2026-09", {"volume_per_year": 1200, "change_pct": 1.9})}
    text, ids = volume_answer.paragraph(p, 24, first=True, room=True, threshold=2.0)
    assert ids == ["fc:1@2026-09"] and "+1.9 %" in text and "2000 kg in total" in text
    assert "pricing committee" in text
    assert volume_answer.paragraph(p, 24, first=False, room=True)[1] == []
    assert volume_answer.paragraph(p, 24, first=True, room=False)[1] == []
    assert volume_answer.checked_claims(["idx:A@1", "idx:A@2", "fc:x"]) == 2


@pytest.mark.skipif(not (DATA / "facts.json").is_file(), reason="data package not present")
def test_p08_text_only_changes_body_and_refs(monkeypatch):
    monkeypatch.setenv("ARENA_DATA", str(DATA))
    c = case("case:P08")
    sid = c["suppliers"][0]
    m0 = {"from": "sales", "status": "open", "attachments": [], "body": "",
          "term_sheets": [{"term_sheet_id": "offer:0", "terms": {
              "unit_price": 5.72, "payment_days": 30, "contract_months": 12, "index_clause": None}}]}
    moves = {}
    for name in ("v2", "answer"):
        agent = PackageAgent(policy=PolicyConfig.load(
            "configs/score-push-v2.json" if name == "v2" else "configs/rawmat-volume-answer.json"), claims=False)
        moves[name] = agent.propose(c, {sid: [m0]}, sid)["message"]
    assert moves["v2"]["term_sheets"] == moves["answer"]["term_sheets"]
    assert "commit bindingly" in moves["answer"]["body"]
    assert "commit bindingly" not in moves["v2"]["body"]


@pytest.mark.skipif(not (DATA / "facts.json").is_file(), reason="data package not present")
def test_specific_hedge_scopes_generic_remark(monkeypatch):
    monkeypatch.setenv("ARENA_DATA", str(DATA))
    from negotiator import claims
    from negotiator.dossiers import load_package

    pk = load_package()
    c = case("case:P08")
    series = ["AS-14404", "PPI-C2431", "LCI-C"]
    assert claims.hedged_series(c, pk, series) == set(series)  # default: generic remark fails closed
    assert claims.hedged_series(c, pk, series, specific=True) == {"AS-14404"}  # letter names alloys only
    assert PolicyConfig.load("configs/rawmat-specific-hedge.json").specific_hedge_types == ("raw_material",)
