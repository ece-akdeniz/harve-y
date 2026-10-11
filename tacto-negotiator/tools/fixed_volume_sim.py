"""Offline ladder check for the fixed-volume (raw_material) recipe: play the v5 agent against the
supplier replies of the breakthrough sessions S6 (P08, 0.759) and S9 (P18, 0.587) and print every
buyer move (sheet, refs, body tail). Never contacts the arena.

    uv run python tools/fixed_volume_sim.py [--config configs/score-push-v5-run.json] [--rounds N]
"""
import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from negotiator.agent import configured_agent  # noqa: E402

DB0 = {"series": "AS-14404", "material_share": 0.45, "deadband_pct": 0.0, "base_month": "2026-08"}
DB5 = {**DB0, "deadband_pct": 5.0}


def sup(sid, n, price, status="open", alt=None, body="", clause=DB0, pay=90, months=24):
    def terms(p, c):
        return {"unit_price": p, "payment_days": pay, "index_clause": c, "contract_months": months}

    sheets = [{"term_sheet_id": f"offer:{sid[4:]}-{n}", "terms": terms(price, clause)}]
    if alt is not None:
        sheets.append({"term_sheet_id": f"offer:{sid[4:]}-{n}-a", "terms": terms(alt, DB5)})
    return {"from": f"sales@{sid[4:]}", "status": status, "term_sheets": sheets, "attachments": [], "refs": [],
            "action": None, "body": body, "claim_results": []}


# supplier replies as observed (first element = its opening quote); the last is its final offer
OPEN = "AS-14404 rose 5.9 % ... PPI-C2431 rose 12.3 %"
HOLDS = "We checked the price history data you cited; it holds, but it does not change our calculation."
FINAL = "This is our final offer (letztes Angebot). Please decide."
S6_P08 = [
    sup("sup:70710", 0, 6.05, clause=None, pay=30, months=12, body=OPEN),
    sup("sup:70710", 1, 5.45, alt=5.57, body="We checked the volume change data you cited; it holds."),
    sup("sup:70710", 2, 5.31, alt=5.43, body=HOLDS),
    sup("sup:70710", 3, 5.16, alt=5.29, status="final_offer", body=FINAL),
]
S9_P18 = [
    sup("sup:70740", 0, 6.10, clause=None, pay=30, months=12, body=OPEN),
    sup("sup:70740", 1, 5.60, alt=5.70, body=HOLDS),
    sup("sup:70740", 2, 5.50, body="A binding higher volume would help us. Which volume can you commit to?"),
    sup("sup:70740", 3, 5.40, alt=5.50, body="We have verified the AS-14404 index data you provided."),
    sup("sup:70740", 4, 5.20, alt=5.30, status="final_offer", body=FINAL),
]


def play(case, sid, replies, agent):
    events = []
    out = []
    for i, reply in enumerate(replies):
        events.append(copy.deepcopy(reply))
        move = agent.decide(case, {sid: events})
        msg = move.get("message") or {}
        out.append((i, reply["status"], reply["term_sheets"][0]["terms"]["unit_price"], move))
        if msg.get("action") or not msg.get("term_sheets"):
            break
        events.append({"from": "buyer", **{k: v for k, v in msg.items() if k != "attachments"}})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/score-push-v5-run.json")
    ap.add_argument("--rounds", type=int, help="override rounds_by_type.raw_material")
    ap.add_argument("--anchor", type=float, help="override anchor_by_type.raw_material")
    args = ap.parse_args(argv)
    cfg = json.loads((ROOT / args.config).read_text())
    cfg = cfg if "policy_config" in cfg else {"policy_config": cfg}
    if args.rounds:
        cfg["policy_config"].setdefault("rounds_by_type", {})["raw_material"] = args.rounds
    if args.anchor:
        cfg["policy_config"].setdefault("anchor_by_type", {})["raw_material"] = args.anchor
    kwargs = {k: v for k, v in cfg.items() if k not in ("name", "notes", "hypothesis", "trace_dir")}
    kwargs.setdefault("estimates", {})
    kwargs.setdefault("meso", False)
    kwargs["model_assist"] = False
    cases = {c["case_id"]: c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())}
    for cid, sid, replies in (("case:P08", "sup:70710", S6_P08), ("case:P18", "sup:70740", S9_P18)):
        agent = configured_agent(**kwargs)
        print(f"===== {cid} {sid} rounds={agent._rounds(cases[cid])} anchor={agent._anchor_for(cases[cid])}")
        last = None
        for i, status, their, move in play(cases[cid], sid, replies, agent):
            msg = move.get("message") or {}
            sheets = [s["terms"] for s in msg.get("term_sheets") or []]
            price = sheets[0]["unit_price"] if sheets else None
            step = f"+{price - last:.2f}" if (price is not None and last is not None) else ""
            print(f"-- after supplier r{i} {status} {their}: ours {sheets} {step} action={msg.get('action')} "
                  f"close={move.get('close')} reason={move.get('reason')}")
            print(f"   refs={msg.get('refs')} att={[a['name'] for a in msg.get('attachments') or []]}")
            body = msg.get("body") or ""
            tail = body.split("\n\n", 1)[1] if "\n\n" in body else ""
            print("   body+: " + tail.replace("\n\n", " | ")[:600])
            if price is not None:
                last = price
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
