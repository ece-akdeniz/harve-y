import copy

import pytest
from test_evaluator import RFQ, msg

from negotiator import cli
from negotiator.agent import PackageAgent
from negotiator.guidance import RuntimeGuidance


def test_guidance_changes_real_offer_without_changing_validated_terms():
    guidance = RuntimeGuidance.load()
    case = copy.deepcopy(RFQ)
    sid = case["suppliers"][0]
    threads = {sid: [msg("open", ("o:0", {
        "unit_price": 20, "payment_days": 30, "lead_time_days": 21, "incoterm": "DAP",
    }))]}
    baseline = PackageAgent(meso=False, claims=False, estimates={}).propose(case, threads, sid)
    agent = guidance.new_agent()
    agent.meso = False
    agent.evidence = None
    agent._estimates = {}
    actual = agent.propose(case, threads, sid)
    assert actual["message"]["term_sheets"] == baseline["message"]["term_sheets"]
    assert "conditional on the proposed unit price" in actual["message"]["body"]
    assert "conditional on the proposed unit price" not in baseline["message"]["body"]
    adjusted = RuntimeGuidance({**guidance.settings, "anchor": 0.05}, guidance.sha256).new_agent()
    adjusted.meso = False
    adjusted.evidence = None
    adjusted._estimates = {}
    changed = adjusted.propose(case, threads, sid)
    assert changed["message"]["term_sheets"][0]["terms"]["unit_price"] > (
        actual["message"]["term_sheets"][0]["terms"]["unit_price"]
    )


@pytest.mark.parametrize("runner", ["serial", "async"])
def test_final_cli_passes_packaged_guidance_to_running_agents(monkeypatch, tmp_path, runner):
    monkeypatch.setattr(cli, "load_env", lambda: None)
    monkeypatch.setattr(cli, "_run_dir", lambda: tmp_path)
    monkeypatch.setattr(cli, "ArenaClient", lambda: type("Client", (), {"practice_remaining": None})())
    observed = []

    def run(factory):
        agent = factory()
        observed.append(agent)
        return {"case:T": {"score": 0.5, "deal": True, "ended": True}}

    monkeypatch.setattr(cli, "play_waves", lambda client, factory, *args: run(factory))
    monkeypatch.setattr(cli, "run_async", lambda args, factory, *rest: run(factory))
    monkeypatch.chdir(tmp_path)
    assert cli.main(["run", "--set", "final", "--runner", runner]) == 0
    assert observed[0].conditional_exchange is True
    assert observed[0].runtime_guidance == RuntimeGuidance.load().record()
    assert RuntimeGuidance.load().sha256 in (tmp_path / "trace.jsonl").read_text()


def test_invalid_guidance_stops_launch_before_session_dispatch(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "load_env", lambda: None)
    monkeypatch.setattr(cli, "_run_dir", lambda: tmp_path)
    monkeypatch.setattr(cli, "ArenaClient", lambda: object())

    def fail():
        raise ValueError("invalid runtime guidance")

    monkeypatch.setattr(cli.RuntimeGuidance, "load", fail)
    monkeypatch.setattr(cli, "run_async", lambda *args: pytest.fail("must not start a session"))
    with pytest.raises(SystemExit) as exc:
        cli.main(["play", "case:T", "--runner", "async"])
    assert exc.value.code == 2
