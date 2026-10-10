"""Load executable negotiation guidance from the installed package, independent of cwd."""

import hashlib
import json
import math
import re
from dataclasses import dataclass
from importlib.resources import files


@dataclass(frozen=True)
class RuntimeGuidance:
    settings: dict
    sha256: str

    @classmethod
    def load(cls):
        raw = files("negotiator").joinpath("AGENTS.md").read_bytes()
        blocks = re.findall(r"^```runtime-settings\s*\n(.*?)^```\s*$", raw.decode(), re.M | re.S)
        if len(blocks) != 1:
            raise ValueError("runtime AGENTS.md requires exactly one runtime-settings block")
        settings = json.loads(blocks[0])
        expected = {"version", "anchor", "rounds", "close_gap", "final_hold_s", "p_walk", "conditional_exchange"}
        if not isinstance(settings, dict) or set(settings) != expected:
            raise ValueError("invalid runtime guidance fields")
        if type(settings["version"]) is not int or settings["version"] != 1:
            raise ValueError("unsupported runtime guidance version")
        if type(settings["rounds"]) is not int or not 1 <= settings["rounds"] <= 100:
            raise ValueError("runtime rounds must be an integer between 1 and 100")
        if type(settings["conditional_exchange"]) is not bool:
            raise ValueError("conditional_exchange must be boolean")
        for key, low, high in (
            ("anchor", 0, 1), ("close_gap", 0, 1), ("p_walk", 0, 1), ("final_hold_s", 0, 3600),
        ):
            value = settings[key]
            if type(value) not in (int, float) or not math.isfinite(value) or not low <= value < high:
                raise ValueError(f"invalid runtime {key}")
        return cls(settings, hashlib.sha256(raw).hexdigest())

    def new_agent(self, *, tracer=None, policy=None, memory=None):
        from .agent import PackageAgent

        agent = PackageAgent(tracer=tracer, policy=policy, memory=memory, **{
            k: v for k, v in self.settings.items() if k not in ("version", "conditional_exchange")
        })
        agent.conditional_exchange = self.settings["conditional_exchange"]
        agent.runtime_guidance = self.record()
        return agent

    def record(self):
        return {"resource": "negotiator/AGENTS.md", "sha256": self.sha256, "settings": dict(self.settings)}
