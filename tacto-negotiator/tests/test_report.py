import json
import math

from negotiator.report import summarise, to_markdown
from negotiator.trace import Tracer


def _synthetic(run_dir):
    tr = Tracer(run_dir)
    tr.log("run", cmd="run", arena="http://127.0.0.1:8030", agent="PackageAgent-test")
    tr.log("session", case="case:S01", session="0123456789abcdef")
    for price, c in ((15.0, 100.0), (15.5, 104.0)):
        tr.log("decision", case="case:S01", kind="offer", supplier="sup:A",
               terms={"unit_price": price, "payment_days": 90}, c=c, c_alt=math.inf, reason="schedule",
               claims=["idx:STEEL@2026-09"])
    tr.log("decision", case="case:S01", kind="offer", supplier="sup:B", terms={"unit_price": 16.0}, c=110.0,
           c_alt=math.inf, reason="rfq")
    tr.log("guard", case="case:S01", supplier="sup:A", check="must_haves", ok=True)
    tr.log("decision", case="case:S01", kind="accept", supplier="sup:A", c=104.0, c_alt=math.inf,
           sheet="offer:A-2", reason="supplier agreed", guard="passed")
    tr.log("result", case="case:S01", result={
        "deal": True, "supplier_id": "sup:A", "terms": {"unit_price": 15.5, "payment_days": 90},
        "c_open": 120.0, "c_deal": 104.0, "c_best": 100.0, "score": 0.8,
        "cost_breakdown": {"price": 100.0, "payment_terms": -1.0, "freight": 5.0}})
    tr.log("decision", case="case:S02", kind="walk_away", supplier="sup:C", c_alt=50.0, reason="no moves left")
    tr.log("result", case="case:S02", result={"deal": False, "c_open": 60.0, "c_deal": 50.0, "c_best": 40.0,
                                               "score": 0.5})
    tr.log("result", case="case:S03", result="ReadTimeout('timed out')")
    return tr.path


def test_summarise_cases_and_aggregate(tmp_path):
    _synthetic(tmp_path)
    s = summarise(tmp_path)
    assert set(s["cases"]) == {"case:S01", "case:S02", "case:S03"}
    c1 = s["cases"]["case:S01"]
    assert c1["score"] == 0.8 and c1["deal"] is True and c1["supplier"] == "sup:A"
    assert c1["terms"] == {"unit_price": 15.5, "payment_days": 90}
    assert c1["gap"] == 4.0
    assert c1["components"]["freight"] == 5.0 and c1["components_src"].startswith("trace.jsonl#L")
    assert c1["rounds"] == 2 and c1["offers_per_supplier"] == {"sup:A": 2, "sup:B": 1}
    assert c1["decision_counts"] == {"offer": 3, "accept": 1}
    assert len(c1["guards"]) == 2 and {g.get("outcome") for g in c1["guards"]} >= {"passed"}
    assert len(c1["claims_used"]) == 2
    assert c1["session"] == "0123456789abcdef" and c1["replay_url"] == "/replay/0123456789abcdef"
    assert math.isinf(c1["c_alt"])
    assert s["cases"]["case:S02"]["deal"] is False
    c3 = s["cases"]["case:S03"]
    assert c3["error"].startswith("ReadTimeout") and c3["timeouts"] == 1 and c3["score"] is None
    a = s["aggregate"]
    assert a["n_cases"] == 3 and a["n_scored"] == 2
    assert abs(a["mean"] - 0.65) < 1e-9 and a["min"] == 0.5 and a["worst_case"] == "case:S02"
    assert a["deals"] == 1 and a["no_deals"] == 1 and a["failures"] == ["case:S03"] and a["timeouts"] == 1


def test_markdown_lists_every_case(tmp_path):
    _synthetic(tmp_path)
    md = to_markdown(summarise(tmp_path))
    assert "mean 65.0, min 50.0 (case:S02)" in md
    for case in ("case:S01", "case:S02", "case:S03"):
        assert f"| {case} |" in md
    assert "∞" in md and "freight 5" in md and "ReadTimeout" in md


def test_hosted_dump_fills_components_and_session(tmp_path):
    run = tmp_path / "20261010-120000"
    tr = Tracer(run)
    tr.log("decision", case="case:D01", kind="accept", supplier="sup:X", c=10.0, c_alt=12.0, reason="ok")
    tr.log("result", case="case:D01", result={"deal": True, "supplier_id": "sup:X", "c_open": 12.0,
                                               "c_deal": 10.0, "c_best": 9.0, "score": 2 / 3})
    state = {"session_id": "feedfacefeedface", "case_id": "case:D01", "rounds": 3, "replay_url": "/replay/feedface",
             "result": {"cost_breakdown": {"price": 9.5, "quality": 0.5}, "c_alt": 12.0}}
    threads = {"sup:X": {"messages": [], "timeouts": [{"round": 2}]}}
    (run / "hosted-feedfacefeedface.json").write_text(json.dumps({"state": state, "threads": threads}))
    c = summarise(tmp_path)["cases"]["case:D01"]
    assert c["session"] == "feedfacefeedface" and c["rounds"] == 3 and c["timeouts"] == 1
    assert c["components"] == {"price": 9.5, "quality": 0.5} and c["components_src"].startswith("hosted-")


def test_session_from_sibling_log(tmp_path):
    run = tmp_path / "practice_P01" / "20261010-133901"
    tr = Tracer(run)
    tr.log("result", case="case:P01", result={"deal": True, "score": 0.5})
    (tmp_path / "practice_P01.log").write_text("13:39:03 session fa0dc70ffaaf6025\n")
    s = summarise(tmp_path / "practice_P01")
    assert s["sessions"] == ["fa0dc70ffaaf6025"]
    assert s["cases"]["case:P01"]["session"] == "fa0dc70ffaaf6025"
