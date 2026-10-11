import base64
import json
from pathlib import Path

import pytest

from negotiator import fixed_volume
from negotiator.dossiers import load_package

CASES = json.loads((Path(__file__).parent / "fixtures" / "practice_cases.json").read_text())


def _case(cid):
    for c in CASES if isinstance(CASES, list) else CASES.get("cases", []):
        if c.get("case_id") == cid:
            return c
    pytest.skip(f"{cid} not in fixtures")


@pytest.fixture(scope="module")
def package():
    try:
        return load_package()
    except FileNotFoundError:
        pytest.skip("data package not available")


def test_plan_needs_fixed_volume_and_forecast(package):
    case = _case("case:P08")
    p = fixed_volume.plan(case, package, "sup:70710")
    assert p and p["volume"] == 94800 and p["fc"].startswith("fc:370010@")
    no_vol = {**case, "fixed_terms": {k: v for k, v in case["fixed_terms"].items() if k != "volume_per_year"}}
    assert fixed_volume.plan(no_vol, package, "sup:70710") is None
    assert fixed_volume.plan({**case, "parts": ["part:1", "part:2"]}, package, "sup:70710") is None


def test_attachment_is_public_monthly_csv_with_committed_share(package):
    p = fixed_volume.plan(_case("case:P08"), package, "sup:70710")
    att = fixed_volume.attachment(p)
    assert att["type"] == "csv" and att["name"].endswith(".csv")
    csv = base64.b64decode(att["content_b64"]).decode()
    rows = [r for r in csv.splitlines() if r and not r.startswith("#")]
    assert rows[0].startswith("forecast_id,part,month,")
    assert len(rows) == 1 + len(p["lines"]) and all(p["fc"] in r for r in rows[1:])
    assert f"binding annual volume under this contract: {p['volume']}" in csv


def test_first_paragraph_cites_the_forecast_once_and_states_the_term_total(package):
    p = fixed_volume.plan(_case("case:P08"), package, "sup:70710")
    text, ids = fixed_volume.first_paragraph(p, {"contract_months": 24})
    assert ids == [p["fc"]] and text.count(p["fc"]) == 1
    assert "94800" in text and str(94800 * 2) in text and "24 months" in text
    assert "budget" not in text.lower() and "walk" not in text.lower()


def test_reminder_only_after_the_supplier_asks():
    assert fixed_volume.asked_for_volume([{"from": "sup:x", "body": "Which volume can you commit to?"}])
    assert not fixed_volume.asked_for_volume([{"from": "buyer", "body": "Which volume can you commit to?"}])
    assert not fixed_volume.asked_for_volume([{"from": "sup:x", "body": "Our price follows AS-14404."}])


def test_p08_opening_adds_volume_paragraph_forecast_file_and_fc_ref(monkeypatch, package):
    from negotiator.agent import PackageAgent
    from negotiator.policy import PolicyConfig

    c = _case("case:P08")
    sid = c["suppliers"][0]
    m0 = {"from": "sales", "status": "open", "attachments": [], "body": "Which volume can you commit to?",
          "term_sheets": [{"term_sheet_id": "offer:0",
                           "terms": {"unit_price": 6.05, "payment_days": 30, "contract_months": 12,
                                     "index_clause": None}}]}
    base = PackageAgent(policy=PolicyConfig.load("configs/score-push-v2.json"), claims=False)
    new = PackageAgent(policy=PolicyConfig.load("configs/breakthrough-ladder.json"), claims=False)
    b = base.propose(c, {sid: [m0]}, sid)["message"]
    n = new.propose(c, {sid: [m0]}, sid)["message"]
    assert "94800" in n["body"] and "fc:370010@" in n["body"]
    assert n["refs"] and all(r.startswith("fc:") for r in n["refs"])
    assert n["attachments"][0]["type"] == "csv"
    assert "attachments" not in b or not b.get("attachments")
    # the deeper raw-material anchor (0.19 below the quote) replaces the agent default
    assert n["term_sheets"][0]["terms"]["unit_price"] < b["term_sheets"][0]["terms"]["unit_price"]
    assert abs(n["term_sheets"][0]["terms"]["unit_price"] - 6.05 * 0.81) < 0.03
    # second buyer offer: only a one-line reminder when the supplier asked again, no second file
    ours = {"from": "buyer", "body": n["body"], "term_sheets": [{"terms": n["term_sheets"][0]["terms"]}]}
    m1 = {**m0, "body": "Which volume can you commit to?",
          "term_sheets": [{"term_sheet_id": "offer:1", "terms": {**m0["term_sheets"][0]["terms"], "unit_price": 5.6}}]}
    n2 = new.propose(c, {sid: [m0, ours, m1]}, sid)["message"]
    assert "binding quantity is 94800" in n2["body"] and not n2.get("attachments")
