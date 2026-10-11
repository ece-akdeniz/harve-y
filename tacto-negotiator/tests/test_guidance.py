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
    # Final defaults to the measured v5 policy, which runs without the conditional-exchange wording.
    assert observed[0].conditional_exchange is False
    assert observed[0].runtime_guidance == RuntimeGuidance.load().record()
    assert RuntimeGuidance.load().sha256 in (tmp_path / "trace.jsonl").read_text()
    import json

    rows = [json.loads(line) for line in (tmp_path / "trace.jsonl").read_text().splitlines()]
    assert "memory" not in next(row for row in rows if row.get("event") == "run")
    assert next(row for row in rows if row.get("event") == "run")["conditional_exchange"] is False
    observed.clear()
    assert cli.main(["run", "--set", "sandbox", "--runner", "async"]) == 0
    assert observed[0].conditional_exchange is True  # no policy: packaged guidance as written


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


@pytest.fixture
def memory(tmp_path):
    from test_lab_memory import add_run, build

    path = tmp_path / 'memory.sqlite'
    for name, case in [('A', 'case:one'), ('B', 'case:one'), ('C', 'case:two')]:
        add_run(path, name, supplier='sup:' + name, case=case)
    return build(path)


@pytest.mark.parametrize('runner', ['serial', 'async'])
def test_final_cli_pins_saved_memory_in_every_agent_and_trace(monkeypatch, tmp_path, runner, memory):
    import json

    source = tmp_path / 'memory.json'
    source.write_text(json.dumps(memory))
    monkeypatch.setattr(cli, 'load_env', lambda: None)
    monkeypatch.setattr(cli, '_run_dir', lambda: tmp_path)
    monkeypatch.setattr(cli, 'ArenaClient', lambda: type('Client', (), {'practice_remaining': None})())
    observed = []

    def run(factory):
        source.write_text('{}')  # Changes on disk after launch must not refresh memory.
        observed.extend([factory(), factory()])
        return {'case:T': {'score': 0.5, 'deal': True, 'ended': True}}

    monkeypatch.setattr(cli, 'play_waves', lambda client, factory, *args: run(factory))
    monkeypatch.setattr(cli, 'run_async', lambda args, factory, *rest: run(factory))
    assert cli.main(['run', '--set', 'final', '--runner', runner, '--memory-file', str(source)]) == 0
    assert len(observed) == 2
    assert all(agent.memory == memory for agent in observed)
    observed[0].memory['lessons'].clear()
    assert observed[1].memory == memory
    trace = [json.loads(line) for line in (tmp_path / 'trace.jsonl').read_text().splitlines()]
    assert next(row for row in trace if row.get('event') == 'run')['memory'] == memory


@pytest.mark.parametrize('payload', ['{}', '[]', '{invalid', ' ' * 65537])
def test_invalid_memory_file_stops_before_dispatch(monkeypatch, tmp_path, payload, capsys):
    source = tmp_path / 'memory.json'
    source.write_text(payload)
    monkeypatch.setattr(cli, 'load_env', lambda: None)
    monkeypatch.setattr(cli, '_run_dir', lambda: tmp_path)
    monkeypatch.setattr(cli, 'ArenaClient', lambda: pytest.fail('invalid memory must stop before client creation'))
    monkeypatch.setattr(cli, 'run_async', lambda *args: pytest.fail('must not dispatch'))
    with pytest.raises(SystemExit) as exc:
        cli.main(['play', 'case:T', '--runner', 'async', '--memory-file', str(source)])
    assert exc.value.code == 2
    assert 'unrecognized arguments' not in capsys.readouterr().err


def test_runtime_guidance_passes_detached_memory(memory):
    agent = RuntimeGuidance.load().new_agent(memory=memory)
    memory['lessons'].clear()
    assert agent.memory['lessons']
