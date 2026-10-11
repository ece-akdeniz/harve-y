"""Byte-identity without a wave cap: on saved hosted transcripts (practice runs: no deadline, so
`time_left_fn` is never wired) the agent with the Live-Final safety on (time guard + compressed schedule,
the defaults) decides exactly as the same agent with both off, under score-push-v3 and fresh-h1h2, for
P01/P03/P04/P05/P08/P11/P18. Uses tools/replay_decisions.py; skipped when the saved runs are absent."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from replay_decisions import (  # noqa: E402
    DEFAULT_RUNS,
    iter_attempts,
    load_config,
    make_agent,
    replay_config,
    thread_messages,
    wants_conditional,
)

CASES = {c["case_id"]: c for c in json.loads((ROOT / "tests/fixtures/practice_cases.json").read_text())}
CASE_IDS = ["case:P01", "case:P03", "case:P04", "case:P05", "case:P08", "case:P11", "case:P18"]
CONFIGS = ["configs/score-push-v3.json", "configs/fresh-h1h2.json"]
MAX_RUNS = 1  # saved sessions per case (the fixture below covers P05 when the runs directory is absent)

pytestmark = pytest.mark.skipif(not DEFAULT_RUNS.is_dir(), reason=f"saved runs not at {DEFAULT_RUNS}")


def _attempts():
    seen = {}
    for name, _path, attempt in iter_attempts(DEFAULT_RUNS, set(CASE_IDS)):
        cid = attempt["case_id"]
        if seen.get(cid, 0) >= MAX_RUNS:
            continue
        seen[cid] = seen.get(cid, 0) + 1
        yield name, attempt


def _strip(rounds):
    return [{k: v for k, v in r.items() if k != "error"} | {"error": r.get("error") is not None} for r in rounds]


@pytest.mark.parametrize("config", CONFIGS)
def test_saved_runs_replay_byte_identical_with_the_safety_on_and_off(config):
    kwargs = load_config(ROOT / config)
    compared = 0
    for name, attempt in _attempts():
        case = CASES[attempt["case_id"]]
        saved = {sid: thread_messages(t) for sid, t in attempt["threads"].items()}
        ce = wants_conditional(saved)
        on = make_agent(kwargs, ce)
        on.compressed_schedule = True  # opt-in since codex/consolidated; the test covers both safeties on
        assert on.time_guard_rounds == 2 and on.compressed_schedule is True and on.time_left_fn is None
        assert on.time_guard() is None and on.rounds_available() is None
        off = make_agent(kwargs, ce)
        off.time_guard_rounds, off.compressed_schedule = 0, False
        rounds_on = replay_config(case, {s: list(m) for s, m in saved.items()}, on)
        rounds_off = replay_config(case, {s: list(m) for s, m in saved.items()}, off)
        assert json.dumps(_strip(rounds_on), sort_keys=True) == json.dumps(_strip(rounds_off), sort_keys=True), (
            config, name, attempt["case_id"])
        compared += len(rounds_on)
    assert compared > 0


def test_p05_fixture_replays_identically_with_and_without_the_safety():
    """Always runs: the saved 0.8136 P05 transcript shipped as a fixture."""
    saved = json.loads((ROOT / "tests/fixtures/p05_fast_payment_run.json").read_text())["threads"]
    kwargs = load_config(ROOT / "configs/score-push-v3.json")
    kwargs["policy_config"] = {**kwargs["policy_config"], "rfq_fast_payment_reanchor": True}
    on, off = make_agent(kwargs, False), make_agent(kwargs, False)
    on.compressed_schedule = True
    off.time_guard_rounds, off.compressed_schedule = 0, False
    a = replay_config(CASES["case:P05"], {s: list(m) for s, m in saved.items()}, on)
    b = replay_config(CASES["case:P05"], {s: list(m) for s, m in saved.items()}, off)
    assert json.dumps(_strip(a), sort_keys=True) == json.dumps(_strip(b), sort_keys=True)
    assert any((r["move"] or {}).get("term_sheets") for r in a)
