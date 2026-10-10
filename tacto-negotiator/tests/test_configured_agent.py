import json
from pathlib import Path

import pytest

from negotiator.agent import PackageAgent, configured_agent
from negotiator.lab.runner import agent_factory
from negotiator.policy import PolicyConfig

CONFIGS = Path(__file__).parents[1] / "configs"


@pytest.mark.parametrize("name", ["cost-neutral-delivery.json", "package-advice.json"])
def test_configured_agent_matches_policy_file(name):
    path = CONFIGS / name
    agent = configured_agent(json.loads(path.read_text()), estimates={}, meso=False)
    assert isinstance(agent, PackageAgent)
    assert agent.policy == PolicyConfig.load(path)
    assert agent.meso is False


def test_configured_agent_rejects_unknown_fields():
    with pytest.raises(ValueError):
        configured_agent({"version": 1, "bogus": True})


def test_lab_factory_path_and_trace_dir(tmp_path):
    config = {
        "policy_config": json.loads((CONFIGS / "cost-neutral-delivery.json").read_text()),
        "estimates": {},
        "meso": False,
        "trace_dir": str(tmp_path),
    }
    agent = agent_factory("negotiator.agent:configured_agent", config)()
    assert agent.policy.cost_neutral_lead_time is True
    assert agent.tracer is not None and Path(agent.tracer.path).parent == tmp_path
