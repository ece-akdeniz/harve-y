"""Every model call inside the move loop ends within a hard wall-clock bound, with a deterministic fallback."""

import json
import threading
import time

import pytest
from arena_kit.sim import load_cases

from negotiator import budget
from negotiator.budget import HARD_TIMEOUT_S, bounded
from negotiator.inference import InferenceProbeAgent
from negotiator.model_assist import ModelAssist
from negotiator.package_advisor import PackageAdvisor


def test_bounded_returns_results_and_raises_on_a_stall():
    assert bounded(lambda x: x + 1, 1.0, 1) == 2
    with pytest.raises(TimeoutError):
        bounded(time.sleep, 0.05, 5)
    with pytest.raises(ValueError):
        bounded(lambda: json.loads("nope"), 1.0)


def test_bounded_caps_every_timeout_at_the_hard_ceiling(monkeypatch):
    seen = {}

    class Fut:
        def set_result(self, *_):
            pass

        def set_exception(self, *_):
            pass

        def result(self, timeout=None):
            seen["timeout"] = timeout
            return "x"

    monkeypatch.setattr(budget, "Future", Fut)
    monkeypatch.setattr(threading, "Thread", lambda **kw: type("T", (), {"start": lambda self: None})())
    assert bounded(lambda: "x", 60.0) == "x" and seen["timeout"] == HARD_TIMEOUT_S == 8.0


def test_model_assist_stall_falls_back_to_rules_within_its_budget():
    release = threading.Event()

    def stall(prompt):
        release.wait(5)
        return "{}"

    model = ModelAssist(complete=stall, timeout_s=0.2)
    assert model.timeout_s == 0.2
    events = [{"from": "sales", "status": "open", "body": "We can offer better payment terms.", "term_sheets": []}]
    t0 = time.monotonic()
    result = model.read({"case_id": "c", "type": "rfq"}, events, "sup:A")
    assert time.monotonic() - t0 < 2.0
    assert result["source"] == "rules" and model.metrics()["fallbacks"] == 1
    release.set()
    assert ModelAssist(complete=stall, timeout_s=99).timeout_s == 3.0  # ceiling documented in the module


def test_inference_probe_stall_keeps_the_deterministic_move(monkeypatch):
    monkeypatch.setattr(budget, "HARD_TIMEOUT_S", 0.2)
    from negotiator import inference

    monkeypatch.setattr(inference, "HARD_TIMEOUT_S", 0.2)
    release = threading.Event()
    agent = InferenceProbeAgent(complete=lambda: release.wait(5) or "concise")
    case = load_cases()["case:S01"]
    events = [{"from": "sales", "status": "open", "body": "quote",
               "term_sheets": [{"term_sheet_id": "offer:A-0", "terms": {"unit_price": 10.0}}]}]
    t0 = time.monotonic()
    move = agent.propose(case, {"sup:70270": events}, "sup:70270")
    assert time.monotonic() - t0 < 2.0
    assert move["message"]["term_sheets"] and "closing style" not in move["message"]["body"]
    assert agent.experiment_metrics()["inference_probe"]["fallbacks"] == 1
    release.set()


def test_package_advisor_timeout_is_capped_at_eight_seconds():
    assert PackageAdvisor(timeout_s=30).timeout_s == 8.0
