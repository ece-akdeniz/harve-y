import json
from pathlib import Path

import pytest
from arena_kit.cost import total_cost

from negotiator.optimizer import best_terms
from negotiator.policy import PolicyConfig


def case(cid):
    cases = json.loads((Path(__file__).parent / "fixtures/practice_cases.json").read_text())
    return next(c for c in cases if c["case_id"] == cid)


def test_longer_tenor_tie_keeps_cost():
    c = case("case:P07")
    legacy = best_terms(c, 5.4)
    longer = best_terms(c, 5.4, prefer_longer_tenor=True)
    assert total_cost(c, longer) == pytest.approx(total_cost(c, legacy), abs=1e-6)
    assert longer["contract_months"] >= legacy["contract_months"]


def test_configs_load_and_extend_candidate():
    base = json.loads(Path("configs/candidate.json").read_text())
    for name, key, val in (("p07-longer-tenor", "longer_tenor_types", ["bundling"]),
                           ("p01-standard-payment", "standard_payment_types", ["price_increase"])):
        assert json.loads(Path(f"configs/{name}.json").read_text()) == {**base, key: val}
        assert getattr(PolicyConfig.load(f"configs/{name}.json"), key) == tuple(val)


@pytest.mark.parametrize("key", ["longer_tenor_types", "standard_payment_types"])
def test_unknown_type_rejected(tmp_path, key):
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"version": 1, key: ["nope"]}))
    with pytest.raises(ValueError):
        PolicyConfig.load(p)
