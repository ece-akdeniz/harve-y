"""Offline fixtures only. These tests were prepared, not executed during setup."""

import copy
import json

import httpx
import pytest

from negotiator.inference import InferenceConnection, InferenceProbeAgent


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_BASE_URL", "https://inference.example/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_API_KEY", "fixture-secret")


def test_configuration_and_factory_never_send_requests(credentials, monkeypatch):
    monkeypatch.setattr(httpx, "Client", lambda **_: pytest.fail("unexpected request during construction"))
    from negotiator.lab.runner import agent_factory

    factory = agent_factory("negotiator.inference:InferenceProbeAgent", {"claims": False})
    assert factory().experiment_metrics()["inference_probe"]["calls"] == 0
    monkeypatch.delenv("LLM_BASE_URL")
    with pytest.raises(ValueError, match="configure LLM_BASE_URL"):
        InferenceConnection()


def test_chat_request_uses_separate_key_and_fixed_prompt(credentials, monkeypatch):
    def route(request):
        assert str(request.url) == "https://inference.example/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer fixture-secret"
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        assert "fixture-secret" not in json.dumps(body)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"style":"concise"}'}}]})

    client = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: client(transport=httpx.MockTransport(route), **kwargs)
    )
    assert InferenceConnection().choose_style() == "concise"


@pytest.mark.parametrize("choice", ["collaborative", "invented numeric claim", None])
def test_probe_preserves_terms_refs_and_calls_once(monkeypatch, choice):
    calls = []
    agent = InferenceProbeAgent(complete=lambda: calls.append(1) or choice, claims=False)
    case = {"case_id": "case:T"}
    move = {"supplier_id": "sup:F", "message": {"body": "Approved facts and offer.", "refs": ["doc:fact"],
            "term_sheets": [{"terms": {"unit_price": 15, "payment_days": 30}}]}}
    monkeypatch.setattr(agent, "_propose", lambda *_: copy.deepcopy(move))
    first = agent.propose(case, {}, "sup:F")
    second = agent.propose(case, {}, "sup:F")
    assert first == second
    assert len(calls) == 1
    assert first["message"]["term_sheets"] == move["message"]["term_sheets"]
    assert first["message"]["refs"] == move["message"]["refs"]
    if choice != "collaborative":
        assert first == move
    assert agent.experiment_metrics()["inference_probe"]["fallbacks"] == int(choice != "collaborative")


def test_probe_never_calls_model_for_close(monkeypatch):
    agent = InferenceProbeAgent(complete=lambda: pytest.fail("model called for close"), claims=False)
    close = {"message": {"action": {"type": "walk_away"}}}
    monkeypatch.setattr(agent, "_propose", lambda *_: close)
    assert agent.propose({"case_id": "case:T"}, {}, "sup:F") == close
