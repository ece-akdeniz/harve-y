"""`negotiator.prewarm`: idempotent, decision-neutral, degrades gracefully, no package IO on the first decision."""

import asyncio
import builtins
import io
import json
import os
from pathlib import Path

import pytest

from negotiator import context as context_mod
from negotiator import dossiers as D
from negotiator import prewarm as P
from negotiator.agent import configured_agent
from negotiator.policy import PolicyConfig
from negotiator.runner import propose

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "configs/score-push-v3-run.json").read_text())


class Trace:
    def __init__(self):
        self.rows = []

    def log(self, event, **fields):
        self.rows.append({"event": event, **fields})

    def events(self, name):
        return [r for r in self.rows if r["event"] == name]


@pytest.fixture(scope="module")
def pkg():
    try:
        return D.load_package()
    except FileNotFoundError:
        pytest.skip("data package not available")


def cases():
    return {c["case_id"]: c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())
            if c.get("hosted")}


def agent(trace=None, **policy):
    pol = {**CONFIG["policy_config"], **policy}
    pol.pop("package_advice_types", None)
    return configured_agent(pol, tracer=trace, estimates={}, meso=False)


def opening_threads(case):
    """A supplier opening message per thread, as the sim/hosted session shows it before our first move."""
    price = round((case["buyer"].get("current_unit_price") or case["buyer"]["fallback_unit_price"]) * 1.08, 2)
    return {sid: [{"from": f"sales@{sid[4:]}", "status": "open", "subject": case["title"], "body": "Our quote.",
                   "attachments": [], "term_sheets": [{"term_sheet_id": f"offer:{sid[4:]}-0",
                                                       "terms": {"unit_price": price}}]}]
            for sid in case["suppliers"]}


# -- package cache --------------------------------------------------------------------------------


def test_load_package_is_shared_and_reloads_when_the_files_change(tmp_path, monkeypatch):
    (tmp_path / "facts.json").write_text(json.dumps({"news:1": {"supplier": "sup:a", "topic": "x"}}))
    monkeypatch.setenv("ARENA_DATA", str(tmp_path))
    first = D.load_package()
    assert D.load_package() is first
    (tmp_path / "facts.json").write_text(json.dumps({"news:1": {"supplier": "sup:a", "topic": "y"}}))
    stamp = tmp_path / "facts.json"
    os.utime(stamp, ns=(stamp.stat().st_atime_ns, stamp.stat().st_mtime_ns + 1_000_000))
    second = D.load_package()
    assert second is not first and second.facts["news:1"]["topic"] == "y"


def test_package_scan_is_cached_and_returns_copies(pkg):
    a = context_mod.package_scan(pkg.root, pkg.release)
    b = context_mod.package_scan(pkg.root, pkg.release)
    assert a == b and a[0] is not b[0]
    a[0]["x"] = "mutated"
    assert "x" not in context_mod.package_scan(pkg.root, pkg.release)[0]


# -- prewarm() ------------------------------------------------------------------------------------


def test_prewarm_is_idempotent_and_shares_the_lazy_loaders_objects(pkg):
    trace = Trace()
    first = P.prewarm(tracer=trace, force=True)
    assert not first["errors"] and first["suppliers"] > 0 and first["facts"] == len(pkg.facts)
    assert first["cache_sizes"]["packages"] >= 1 and first["cache_sizes"]["dossiers"] > 0
    package = D.load_package()
    dossier = D.build_one(package, "sup:70110")
    second = P.prewarm(tracer=trace)
    assert second["cached"] is True and second["suppliers"] == first["suppliers"]
    assert D.load_package() is package  # the lazy loaders get the pre-warmed objects
    assert D.build_one(package, "sup:70110") is dossier
    assert second["cache_sizes"] == first["cache_sizes"]
    rows = trace.events("prewarm")
    assert len(rows) == 2 and rows[1]["cached"] is True  # launch hooks always leave a row
    assert {"seconds", "suppliers", "cases", "cache_sizes"} <= set(rows[0])
    assert len(Trace().events("prewarm")) == 0
    quiet = Trace()
    P.prewarm(tracer=quiet, quiet_cached=True)  # per-case callers: no row when nothing was done
    assert quiet.events("prewarm") == []


def test_prewarm_degrades_when_the_package_is_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("ARENA_DATA", str(tmp_path / "nowhere"))
    trace = Trace()
    out = P.prewarm(tracer=trace)
    assert out["suppliers"] == 0 and any(e.startswith("package:") for e in out["errors"])
    assert trace.events("prewarm")[0]["errors"] == out["errors"]
    case = cases()["case:P01"]
    a = agent(trace)
    assert P.prewarm_case(a, case) is not None  # logged, no raise
    kind, _what = propose(a, case, opening_threads(case), case["suppliers"][0], case["suppliers"])
    assert kind in ("send", "close", "hold", "park")  # the lazy path still decides without the package


def test_prewarm_degrades_when_a_release_is_broken(tmp_path, monkeypatch):
    (tmp_path / "facts.json").write_text(json.dumps({"news:1": {"supplier": "sup:a"}}))
    rel = tmp_path / "release-sunday"
    rel.mkdir()
    (rel / "facts.json").write_text("[not an object]")
    monkeypatch.setenv("ARENA_DATA", str(tmp_path))
    out = P.prewarm()
    assert out["errors"] and out["suppliers"] == 0


# -- prewarm_case() -------------------------------------------------------------------------------


def test_prewarm_case_builds_the_context_the_opened_case_will_hit(pkg):
    case = cases()["case:P01"]
    listing = {**case, "wave": 1, "open": True, "seconds_left": 480.0, "theme": "x"}
    opened = {k: v for k, v in case.items() if k != "hosted"}
    trace = Trace()
    a = agent(trace)
    out = P.prewarm_case(a, listing, tracer=trace)
    assert out["contexts"] == 1 and out["claims"] > 0 and not out["errors"]
    before = a.evidence.contexts[case["case_id"]]
    assert a.evidence.context_for(opened) is before  # same key: no rebuild on the first decision
    assert len(trace.events("evidence_context")) == 1
    row = trace.events("prewarm_case")[0]
    assert row["case"] == "case:P01" and {"seconds", "suppliers", "contexts", "estimates", "traits"} <= set(row)
    again = P.prewarm_case(a, listing)  # idempotent: the agent's caches short-circuit, nothing is rebuilt
    assert {k: v for k, v in again.items() if k != "seconds"} == {k: v for k, v in out.items() if k != "seconds"}
    assert a.evidence.contexts[case["case_id"]] is before


def test_prewarm_case_without_a_case_or_when_disabled(pkg):
    assert P.prewarm_case(agent(), None) is None
    assert P.prewarm_case(agent(prewarm=False), cases()["case:P01"]) is None
    assert P.prewarm(agent=agent(prewarm=False))["disabled"] is True


def _guarded_open(real, root):
    def guard(file, *args, **kwargs):
        if str(file).startswith(root):
            raise AssertionError(f"first decision read the data package: {file}")
        return real(file, *args, **kwargs)

    return guard


def test_first_decision_after_prewarm_does_no_package_disk_io(pkg, monkeypatch):
    all_cases = cases()
    root = str(pkg.root)
    for cid in ("case:P01", "case:P05", "case:P18"):
        case = {k: v for k, v in all_cases[cid].items() if k != "hosted"}
        trace = Trace()
        a = agent(trace)
        P.prewarm(tracer=trace)
        P.prewarm_case(a, {**all_cases[cid], "wave": 1, "seconds_left": 480.0, "open": True}, tracer=trace)

        def no_json(*_a, **_k):
            raise AssertionError("first decision parsed JSON from disk")

        with monkeypatch.context() as mp:
            mp.setattr(builtins, "open", _guarded_open(builtins.open, root))
            mp.setattr(io, "open", _guarded_open(io.open, root))
            mp.setattr(json, "load", no_json)
            mp.setattr(json, "loads", no_json)
            mp.setattr(D, "build", lambda package: pytest.fail("dossiers rebuilt on the first decision"))
            mp.setattr(context_mod, "_scan", lambda *a: pytest.fail("package re-hashed on the first decision"))
            threads = opening_threads(case)
            kind, what = propose(a, case, threads, case["suppliers"][0], case["suppliers"])
        assert kind == "send" and what.get("term_sheets"), (cid, kind, what)


def test_prewarmed_and_lazy_first_decisions_are_identical(pkg):
    """Same agent config, same opening; one agent pre-warmed, one loading lazily: identical moves."""
    all_cases = cases()
    for cid in ("case:P01", "case:P05", "case:P18", "case:P07", "case:P11"):
        case = {k: v for k, v in all_cases[cid].items() if k != "hosted"}
        warm, lazy = agent(), agent()
        P.prewarm_case(warm, all_cases[cid])
        threads = opening_threads(case)
        for sid in case["suppliers"]:
            a = propose(warm, case, {s: list(e) for s, e in threads.items()}, sid, case["suppliers"])
            b = propose(lazy, case, {s: list(e) for s, e in threads.items()}, sid, case["suppliers"])
            assert a == b, (cid, sid)


# -- runtime key ----------------------------------------------------------------------------------


def test_policy_prewarm_key_defaults_on_and_is_recorded():
    assert PolicyConfig.from_dict({"version": 1}).prewarm is True
    assert PolicyConfig.from_dict({"version": 1, "prewarm": False}).prewarm is False
    assert PolicyConfig.from_dict({"version": 1}).record()["config"]["prewarm"] is True
    with pytest.raises(ValueError):
        PolicyConfig.from_dict({"version": 1, "prewarm": "yes"})
    v3 = json.loads((ROOT / "configs/score-push-v3-run.json").read_text())["policy_config"]
    assert PolicyConfig.from_dict({**v3, "prewarm": True}).prewarm is True


# -- launch hooks: before the polling loop, before the session opens ------------------------------


class FakeArena:
    """`run_waves` sees one already-closed wave: the loop polls once and returns."""

    def __init__(self, trace):
        self.trace = trace

    async def cases(self, set_):
        self.trace.log("poll", set=set_)
        return [{"case_id": "case:X", "wave": 1, "open": False}]


def test_run_waves_prewarms_before_the_first_poll(tmp_path):
    from negotiator.runner import run_waves
    from negotiator.state import Journal

    trace = Trace()
    out = asyncio.run(run_waves(FakeArena(trace), lambda: agent(trace), Journal(tmp_path / "j.jsonl"), waves=1,
                                poll_s=0.0, tracer=trace))
    assert out == {}
    events = [r["event"] for r in trace.rows if r["event"] in ("prewarm", "poll")]
    assert events and events[0] == "prewarm" and "poll" in events  # the package is warm before polling


def test_play_waves_prewarms_before_the_first_poll():
    from negotiator.play import play_waves

    trace = Trace()

    class Client:
        def cases(self, set_):
            trace.log("poll", set=set_)
            return [{"case_id": "case:X", "wave": 1, "open": False}]

    out = play_waves(Client(), lambda: agent(trace), waves=1, parallel=1, poll=0.0)
    assert out == {}
    events = [r["event"] for r in trace.rows if r["event"] in ("prewarm", "poll")]
    assert events[0] == "prewarm" and "poll" in events


def test_async_play_case_prewarms_the_case_before_opening(pkg, tmp_path):
    from negotiator.runner import play_case
    from negotiator.state import Journal

    case = cases()["case:P01"]
    trace = Trace()

    class Arena:
        async def open_session(self, case_id, move_id):
            trace.log("open_session", case=case_id)
            raise RuntimeError("stop here")

    a = agent(trace)
    with pytest.raises(RuntimeError, match="stop here"):
        asyncio.run(play_case(Arena(), case["case_id"], a, Journal(tmp_path / "j.jsonl"), case=case, tracer=trace))
    order = [r["event"] for r in trace.rows if r["event"] in ("prewarm_case", "open_session")]
    assert order == ["prewarm_case", "open_session"]
    assert case["case_id"] in a.evidence.contexts


def test_serial_play_case_prewarms_the_case_before_opening(pkg):
    from negotiator.play import play_case

    case = cases()["case:P01"]
    trace = Trace()

    class Table:
        def __init__(self):
            self.case = {**case, "wave": 1, "open": True, "seconds_left": 480.0}

        def open(self, case_id):
            trace.log("open_session", case=case_id)
            raise RuntimeError("stop here")

    a = agent(trace)
    with pytest.raises(RuntimeError, match="stop here"):
        play_case(Table(), case["case_id"], a)
    order = [r["event"] for r in trace.rows if r["event"] in ("prewarm_case", "open_session")]
    assert order == ["prewarm_case", "open_session"]
