"""Opt-in `cost_breakdown_request`: ask once early, parse the XLSX, rank index claims by the supplier's own
cost shares, one ID-free arithmetic sentence; off = byte-identical messages."""

import copy
import json
from pathlib import Path

import pytest
from arena_kit.docs import read_document

from negotiator import cost_breakdown as cb
from negotiator.agent import configured_agent
from negotiator.claims import _pct, case_facts, index_relevance, recent_index_claims, series_values
from negotiator.dossiers import load_package
from negotiator.guards import leaks
from negotiator.policy import PolicyConfig

ROOT = Path(__file__).resolve().parents[1]
KIT_FIXTURE = (ROOT.parent / "negotiation-arena-kit/negotiation-arena-kit/starter-kit/tests/fixtures"
               / "cost-breakdown.xlsx")
CASE = next(c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())
            if c["case_id"] == "case:P18")
THREAD = json.loads((ROOT / "tests/fixtures/p18_retained_thread.json").read_text())
SID = THREAD["supplier_id"]
RUN = json.loads((ROOT / "configs/fresh-h1h2-run.json").read_text())
RUN_CB = json.loads((ROOT / "configs/fresh-h1h2-cb-run.json").read_text())

# `arena_kit.docs.read_document` of the kit's cost-breakdown.xlsx (formulas as written; no saved hosted
# run carries a cost breakdown - every saved XLSX attachment is a delivery schedule).
KIT_TEXT = ("[Cost breakdown]\nElement | EUR per unit | Share of price\nMaterial | 14.1 | =B2/B6\n"
            "Conversion | 19.6 | =B3/B6\nOverhead | 6.3 | =B4/B6\nMargin | 3.2 | =B5/B6\n"
            "Unit price | =SUM(B2:B5) | =SUM(C2:C5)")


def _sheet(material, drawing, labour=0.30, energy=0.25, overhead=0.40, margin=0.20, material_name="Material"):
    rows = [(material_name, material), ("Cold drawing", drawing), ("Labour", labour), ("Energy", energy),
            ("Overhead", overhead), ("Margin", margin)]
    body = "\n".join(f"{n} | {v:.2f} | =B{i}/B8" for i, (n, v) in enumerate(rows, 2))
    return f"[Cost breakdown]\nElement | EUR per unit | Share of price\n{body}\nUnit price | =SUM(B2:B7) | =SUM(C2:C7)"


def _attach(message, text, name="cost-breakdown.xlsx"):
    out = copy.deepcopy(message)
    out["attachments"] = [*(out.get("attachments") or []),
                          {"attachment_id": "att:cb", "name": name, "type": "xlsx", "text": text}]
    return out


@pytest.fixture(scope="module")
def package():
    try:
        return load_package()
    except FileNotFoundError:
        pytest.skip("data package not available")


def _agent(run):
    agent = configured_agent(**run)
    agent.conditional_exchange = True
    return agent


def _replay(run, messages=None):
    messages = messages if messages is not None else THREAD["messages"]
    agent, sent = _agent(run), []
    for i, message in enumerate(messages):
        if message.get("from") != "buyer":
            continue
        it = iter(sent)
        history = [next(it) if e.get("from") == "buyer" else e for e in messages[:i]]
        move = agent.decide(CASE, {SID: history})["message"]
        sent.append({"from": "buyer", **move})
    return sent


# ---------------------------------------------------------------- parse


def test_parse_kit_rendered_breakdown_recomputes_shares_from_eur():
    if KIT_FIXTURE.is_file():
        assert read_document("cost-breakdown.xlsx", KIT_FIXTURE.read_bytes()) == KIT_TEXT
    parsed = cb.parse(KIT_TEXT)
    assert [e["name"] for e in parsed["elements"]] == ["Material", "Conversion", "Overhead", "Margin"]
    assert parsed["total_eur_per_unit"] == 43.2
    assert parsed["elements"][0] == {"name": "Material", "eur_per_unit": 14.1, "share": round(14.1 / 43.2, 4)}
    assert abs(sum(e["share"] for e in parsed["elements"]) - 1) < 1e-3
    assert parsed["material_share"] == round(14.1 / 43.2, 4) and parsed["energy_share"] is None
    assert parsed["labour_share"] == round(19.6 / 43.2, 4)  # conversion is the labour-side element
    assert parsed["margin_share"] == round(3.2 / 43.2, 4)


def test_parse_tolerates_rows_percent_shares_and_numeric_totals():
    rows = [["Cost element", "EUR/unit", "Share"], ["Raw material", "2,60", "46 %"], ["Energy", 0.25, 0.044],
            ["Labour", "EUR 0.30", None], ["Total", 3.15, 1.0]]
    parsed = cb.parse(rows)
    assert parsed["total_eur_per_unit"] == 3.15 and parsed["material_share"] == round(2.6 / 3.15, 4)
    assert parsed["energy_share"] == round(0.25 / 3.15, 4) and parsed["labour_share"] == round(0.3 / 3.15, 4)
    assert cb.parse("") is None and cb.parse("[Cost breakdown]\nElement | EUR per unit\nMaterial | 1.0") is None
    assert cb.parse("Material | abc | x\nLabour | =B2 | y\nTotal | 1 | 1") is None


def test_find_latest_supplier_breakdown_only():
    events = [{"from": "sales@x", "attachments": [{"name": "quote-offer-1.pdf", "text": "Unit price (EUR) 5"}]},
              {"from": "buyer", "attachments": [{"name": "cost-breakdown.xlsx", "text": KIT_TEXT}]}]
    assert cb.find(events) is None and not cb.received(events)
    events.append({"from": "sales@x", "attachments": [{"attachment_id": "a", "name": "cost-breakdown.xlsx",
                                                       "type": "xlsx"}]})
    assert cb.received(events) and cb.find(events) is None  # bytes not yet read: no parse, no request
    events.append({"from": "sales@x", "attachments": [{"name": "cost-breakdown.xlsx", "text": _sheet(3.0, 1.5)}]})
    assert cb.find(events)["total_eur_per_unit"] == 5.65


# ---------------------------------------------------------------- request


def test_request_sentence_names_part_and_passes_leaks():
    text = cb.request_sentence("Round bar 1.4404 dia 30 mm, peeled")
    assert text == ("Could you share your cost breakdown for Round bar 1.4404 dia 30 mm, peeled (material, energy,"
                    " labour, overhead and margin per unit) so we can align the price with the cost elements"
                    " that actually moved?")
    assert not leaks(text) and "idx:" not in text
    assert cb.request_sentence(None).startswith("Could you share your cost breakdown for this part (")


def test_request_once_in_first_offer_and_moves_identical_to_flag_off(package):
    off, on = _replay(RUN), _replay(RUN_CB)
    assert len(off) == len(on) == 5
    for a, b in zip(off, on, strict=True):
        assert a.get("term_sheets") == b.get("term_sheets") and a.get("action") == b.get("action")
        assert a.get("refs") == b.get("refs")
    asked = [m for m in on if cb._REQUEST_MARK in (m.get("body") or "").lower()]
    assert asked == [on[0]] and cb.requested(on)
    assert not leaks(on[0]["body"])
    assert on[0]["body"].count(cb.REQUEST.split(" for ")[0]) == 1
    request = cb.request_sentence("Round bar 1.4404 dia 30 mm, peeled")
    assert on[0]["body"] == off[0]["body"].replace("\n\nThe AS-14404", f"\n\n{request}\n\nThe AS-14404")
    assert [m.get("body") for m in off[1:]] == [m.get("body") for m in on[1:]]
    # The default (flag omitted) is the flag set to false.
    assert PolicyConfig.from_dict(RUN["policy_config"]) == PolicyConfig.from_dict(
        {**RUN["policy_config"], "cost_breakdown_request": False})


def test_request_in_second_offer_when_first_could_not_ask_never_after_breakdown_or_final(package):
    messages = copy.deepcopy(THREAD["messages"])
    # First offer did not carry the request (e.g. sent by an older build): the second one asks.
    on = _replay(RUN_CB, messages)
    agent = _agent(RUN_CB)
    first = {k: v for k, v in on[0].items() if k != "from"}
    first["body"] = first["body"].replace("\n\n" + cb.request_sentence("Round bar 1.4404 dia 30 mm, peeled"), "")
    assert not cb.requested([{"from": "buyer", **first}])
    second = agent.decide(CASE, {SID: [messages[0], {"from": "buyer", **first}, messages[2]]})["message"]
    assert cb._REQUEST_MARK in second["body"].lower()
    # Two offers already sent: no request, even without a breakdown.
    third = agent.decide(CASE, {SID: [messages[0], {"from": "buyer", **first}, messages[2],
                                      {"from": "buyer", **first}, messages[4]]})["message"]
    assert cb._REQUEST_MARK not in third["body"].lower()
    # A breakdown attached to the opening: no request at all.
    opening = _attach(messages[0], _sheet(2.0, 1.5))
    move = _agent(RUN_CB).decide(CASE, {SID: [opening]})["message"]
    assert cb._REQUEST_MARK not in move["body"].lower()
    # Final offer: the counter never asks.
    final = _agent(RUN_CB).decide(CASE, {SID: [messages[0]] + [{**messages[8], "status": "final_offer"}]})
    assert cb._REQUEST_MARK not in (final["message"].get("body") or "").lower()


def test_policy_flag_validation():
    with pytest.raises(ValueError):
        PolicyConfig.from_dict({"version": 1, "cost_breakdown_request": "yes"})
    assert PolicyConfig.from_dict({"version": 1, "cost_breakdown_request": True}).cost_breakdown_request is True
    assert json.loads((ROOT / "configs/fresh-h1h2-cb.json").read_text()) == {
        **json.loads((ROOT / "configs/fresh-h1h2.json").read_text()), "cost_breakdown_request": True}
    assert RUN_CB == {"policy_config": json.loads((ROOT / "configs/fresh-h1h2-cb.json").read_text()),
                      "estimates": {}, "meso": False}


# ---------------------------------------------------------------- ranking and arithmetic


def test_element_series_mapping_uses_name_stems_then_category(package):
    parsed = cb.parse(_sheet(3.0, 1.5, material_name="Material (alloy surcharge)"))
    mapping = cb.element_series(parsed, "part:370010", package)
    assert mapping == {"Material (alloy surcharge)": "AS-14404", "Cold drawing": "PPI-C2431", "Labour": "LCI-C"}
    plain = cb.element_series(cb.parse(_sheet(3.0, 1.5)), "part:370010", package)
    assert plain["Material"] == "AS-14404"  # heaviest material driver of the part
    assert cb.element_series(cb.parse(KIT_TEXT), None, package) == {}


def test_breakdown_ranks_biggest_moved_element_first(package):
    facts = case_facts(CASE, package)
    bank = recent_index_claims(CASE, package, facts)
    assert {c.subject for c in bank} == {"AS-14404", "PPI-C2431"}
    base, _ = index_relevance(bank, CASE, package, [])
    assert base["AS-14404"] < base["PPI-C2431"]
    drawing_heavy = cb.parse(_sheet(1.0, 4.0))
    ranked, reasons = index_relevance(bank, CASE, package, [], breakdown=drawing_heavy)
    assert ranked["PPI-C2431"] == -1 < ranked["AS-14404"]
    assert reasons["PPI-C2431"].startswith("supplier cost breakdown")
    material_heavy = cb.parse(_sheet(3.0, 1.5))
    ranked, _ = index_relevance(bank, CASE, package, [], breakdown=material_heavy)
    assert ranked["AS-14404"] == -1 < ranked["PPI-C2431"]
    windows = {c.subject: c.window for c in bank}
    lead = cb.lead_series(drawing_heavy, "part:370010", package, facts, windows)
    values = series_values(facts)["PPI-C2431"]
    assert lead["series"] == "PPI-C2431" and lead["element"] == "Cold drawing"
    assert lead["eur_moved"] == round(4.0 * abs(_pct(values[windows["PPI-C2431"][0]],
                                                     values[windows["PPI-C2431"][1]])) / 100, 4)


def test_arithmetic_sentence_recomputes_from_breakdown_and_facts(package):
    facts = case_facts(CASE, package)
    bank = recent_index_claims(CASE, package, facts)
    claim = next(c for c in bank if c.subject == "AS-14404")
    values = series_values(facts)["AS-14404"]
    pct = _pct(values[claim.window[0]], values[claim.window[1]])
    heavy = cb.parse(_sheet(3.0, 1.5))  # material 3.00 of 5.65 = 53 % > listed driver weight 0.43
    text = cb.arithmetic_sentence(heavy, claim, "part:370010", package, facts)
    share = heavy["elements"][0]["share"]
    assert text == (f"Your breakdown puts material at {share * 100:.0f} % of the unit cost; with the AS-14404 index"
                    f" down {abs(pct):.1f} % that alone is worth about {3.0 * abs(pct) / 100:.2f} EUR per unit.")
    assert "idx:" not in text and not leaks(text) and f"{abs(claim.figure):.1f} %" in text
    light = cb.parse(_sheet(2.0, 2.5))  # material 35 % < 0.43: no sentence
    assert cb.arithmetic_sentence(light, claim, "part:370010", package, facts) is None
    other = next(c for c in bank if c.subject == "PPI-C2431")
    assert cb.arithmetic_sentence(heavy, other, "part:370010", package, facts) is None  # 27 % < 0.36
    from dataclasses import replace

    assert cb.arithmetic_sentence(heavy, replace(claim, figure=-9.9), "part:370010", package, facts) is None
    assert cb.arithmetic_sentence(heavy, replace(claim, window=("2000-01", "2000-02")), "part:370010", package,
                                  facts) is None


def test_agent_uses_received_breakdown_for_ranking_and_sentence(package):
    opening = _attach(THREAD["messages"][0], _sheet(1.0, 4.0))
    move = _agent(RUN_CB).decide(CASE, {SID: [opening]})["message"]
    lines = move["body"].split("\n\n")[-1].splitlines()
    assert lines[0].startswith("The PPI-C2431 index fell 2.3 % between idx:PPI-C2431@")
    assert lines[1].startswith("Your breakdown puts cold drawing at 65 % of the unit cost; with the PPI-C2431 index"
                               " down 2.3 % that alone is worth about 0.09 EUR per unit.")
    assert "idx:" not in lines[1] and move["refs"] == ["idx:PPI-C2431@2026-06", "idx:PPI-C2431@2026-08"]
    assert cb._REQUEST_MARK not in move["body"].lower() and not leaks(move["body"])
    # Same breakdown, flag off: the breakdown is ignored entirely.
    plain = _agent(RUN).decide(CASE, {SID: [opening]})["message"]
    assert plain["body"].split("\n\n")[-1].startswith("The AS-14404 index fell 5.5 %")
    assert plain["term_sheets"] == move["term_sheets"]
