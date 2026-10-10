import json
import os
from pathlib import Path

import pytest

from negotiator import bundle_volume
from negotiator.agent import PackageAgent
from negotiator.policy import PolicyConfig

DATA = Path(os.environ.get("ARENA_DATA", "data/package"))


def case(cid):
    cases = json.loads((Path(__file__).parent / "fixtures/practice_cases.json").read_text())
    return next(c for c in cases if c["case_id"] == cid)


def test_kit_quantities_parse_memo_lines():
    text = "- 19 x Hex bolt M12 (part:1)\n- 6 x Bolt (part:2)\n- 3 x Other (part:9)"
    assert bundle_volume.kit_quantities(text, ["part:1", "part:2"]) == {"part:1": 19, "part:2": 6}


def test_config_only_adds_bundle_volume():
    base = json.loads(Path("configs/candidate.json").read_text())
    cfg = json.loads(Path("configs/p07-bundle-volume.json").read_text())
    assert cfg == {**base, "bundle_volume_types": ["bundling"]}
    assert PolicyConfig.load("configs/p07-bundle-volume.json").bundle_volume_types == ("bundling",)


def test_unknown_type_rejected(tmp_path):
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"version": 1, "bundle_volume_types": ["nope"]}))
    with pytest.raises(ValueError):
        PolicyConfig.load(p)


@pytest.mark.skipif(not (DATA / "facts.json").is_file(), reason="data package not present")
def test_p07_text_only_changes_body_and_refs(monkeypatch):
    monkeypatch.setenv("ARENA_DATA", str(DATA))
    c = case("case:P07")
    sid = c["suppliers"][0]
    m0 = {"from": "sales", "status": "open", "attachments": [], "body": "",
          "term_sheets": [{"term_sheet_id": "offer:0",
                           "terms": {"unit_price": 5.74, "payment_days": 30, "contract_months": 12}}]}
    moves = {}
    for cfg in ("configs/candidate.json", "configs/p07-bundle-volume.json"):
        agent = PackageAgent(policy=PolicyConfig.load(cfg), claims=False)
        moves[cfg] = agent.propose(c, {sid: [m0]}, sid)["message"]
    base, new = moves["configs/candidate.json"], moves["configs/p07-bundle-volume.json"]
    assert base["term_sheets"] == new["term_sheets"]
    assert new["body"].startswith(base["body"])
    assert "1308000 pieces a year" in new["body"]
    assert 0 < len(new["refs"]) <= 3
    assert all(r in new["body"] for r in new["refs"])


def test_rounds_by_type_validated_and_scoped():
    cfg = PolicyConfig.from_dict({"version": 1, "rounds_by_type": {"bundling": 3}})
    assert cfg.rounds_by_type == {"bundling": 3}
    assert PolicyConfig.from_dict({"version": 1}).rounds_by_type == {}
    for bad in ({"bundling": 0}, {"bundling": 2.5}, {"nope": 3}, [3]):
        try:
            PolicyConfig.from_dict({"version": 1, "rounds_by_type": bad})
        except ValueError:
            continue
        raise AssertionError(bad)


def test_rounds_by_type_used_only_for_listed_type():
    agent = PackageAgent(policy=PolicyConfig.from_dict({"version": 1, "rounds_by_type": {"bundling": 3}}))
    assert agent._rounds({"type": "bundling"}) == 3
    assert agent._rounds({"type": "renewal"}) == agent.rounds
