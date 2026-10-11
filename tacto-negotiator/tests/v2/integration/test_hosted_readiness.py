"""Local HTTP/provider framing and P10 rehearsal; no hosted calls or Arena sessions."""

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import httpx
import pytest

from experiments.v2.run_p10_llm import authorization_template, check_authorization, run
from negotiator.v2.adapters.chat_completions import (
    ChatCompletionConfig,
    ChatCompletionsTransport,
    input_token_upper_bound,
    messages_for,
)
from negotiator.v2.adapters.p10 import recorded_p10
from negotiator.v2.core import models as m
from negotiator.v2.core.serialization import semantic_hash
from negotiator.v2.orchestration.offline import OfflineDecisionTrace

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def dataset():
    return json.loads((ROOT / "experiments/v2/p10-offline-input.json").read_text())


def request_budget(dataset):
    inputs = recorded_p10(dataset, message=dataset["supplier_messages"][0], now=datetime.now(UTC))
    config = ChatCompletionConfig(
        base_url="https://provider.example/v1", provider_id="approved-provider", model_id="exact-model"
    )
    projection = m.InterpretInput(
        kind="interpret",
        snapshot=m.SnapshotRef(
            run_id=inputs.state.run_id,
            session_id=inputs.server.session_id,
            state_version=0,
            context_version="context:test",
            config_hash=inputs.state.config_hash,
            case_contract_hash=inputs.case.contract_hash,
        ),
        supplier_id=inputs.target_supplier_id,
        conversation=inputs.server.threads[0].conversation,
        evidence=(),
    )
    request = m.ModelRequest(
        call_id=UUID(int=1),
        correlation_id=UUID(int=1),
        task="interpret",
        input=projection,
        task_schema_version="assessment-draft-v1",
        prompt_version="grounded-supplier-v1",
        provider_id=config.provider_id,
        model_id=config.model_id,
        protocol_id=config.protocol_id,
        output_schema_hash=semantic_hash(m.AssessmentDraft.model_json_schema()),
    )
    budget = m.ModelBudget(
        deadline_at=datetime.now(UTC) + timedelta(seconds=8),
        time_limit_s=Decimal("8"),
        max_tokens=16384,
        max_calls=1,
        retry_limit=0,
    )
    return request, budget, config


@pytest.mark.asyncio
async def test_actual_p10_local_rehearsal_cost_parity_and_variation(dataset, tmp_path):
    raw = json.loads((ROOT / "tests/fixtures/v2/p10.json").read_text())
    assert dataset["case"] == raw["case"] and dataset["case"]["set"] == "practice"
    result = await run(tmp_path)
    assert result["evidence"] == "local fake HTTP rehearsal; no hosted inference" and result["calls"] == 4
    assert all(row["validation"] == "valid" and row["fallback_code"] is None for row in result["results"])
    traces = [
        OfflineDecisionTrace.model_validate_json((tmp_path / f"message-{i}-model.json").read_text()) for i in (0, 1)
    ]
    for trace in traces:
        trace.verify()
        assert trace.model_calls[0].charged_tokens == 1400
        assert trace.assessment.model_call_id == str(trace.model_calls[0].request.call_id)
        for i, golden in zip(
            (i for i in trace.evaluations.items if i.economic), raw["official_cost_goldens"], strict=True
        ):
            assert i.economic[0].nominal_cost.amount == Decimal(str(golden["total_cost"]))
        for call in trace.model_calls:
            serialized = call.request.input.model_dump_json()
            assert not any(
                key in serialized for key in ("fallback_price", "relationship_eur_per_point", "late_cost_per_day")
            )
    assert traces[0].rendered.payload.packages != traces[1].rendered.payload.packages
    assert traces[1].decision.citations[0].quote == dataset["supplier_messages"][1]
    assert traces[0].validation.action.economic_fingerprint == traces[1].validation.action.economic_fingerprint
    assert json.loads((tmp_path / "authorization-template.json").read_text())["authorized"] is False


@pytest.mark.asyncio
async def test_chat_wire_matches_prompt_schema_and_total_token_reservation(dataset):
    request, budget, config = request_budget(dataset)
    bound = input_token_upper_bound(messages_for(request, config), config.framing_token_reserve)
    config = replace(config, max_output_tokens=10000)
    seen = []

    async def handler(wire):
        seen.append(json.loads(wire.content))
        assert wire.url.path == "/v1/chat/completions"
        assert wire.headers["authorization"] == "Bearer local-only-key"
        body = seen[0]
        assert body["max_completion_tokens"] + bound == budget.max_tokens
        assert body["response_format"] == {"type": "json_object"} and body["stream"] is False
        assert "Return only JSON" in body["messages"][0]["content"]
        assert "reported_constraints" in body["messages"][0]["content"]
        assert len(body["messages"]) == 2 and json.loads(body["messages"][1]["content"])["evidence"] == []
        return httpx.Response(
            200,
            json={
                "model": config.model_id,
                "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
                "usage": {"prompt_tokens": 1000, "completion_tokens": 20},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await ChatCompletionsTransport(config=config, api_key="local-only-key", client=client)(request, budget)
    assert result.kind == "success" and result.usage.input_tokens == 1000 and result.usage.output_tokens == 20
    assert len(seen) == 1


@pytest.mark.parametrize(
    "fault",
    (
        "refusal",
        "length",
        "content_filter",
        "tools",
        "model",
        "usage",
        "json",
        "choices",
        "oversize",
        "429",
        "500",
        "timeout",
        "connect",
    ),
)
@pytest.mark.asyncio
async def test_provider_failures_do_not_retry_or_reveal_unsafe_details(dataset, fault):
    request, budget, config = request_budget(dataset)
    calls = []

    async def handler(wire):
        calls.append(wire)
        data = {
            "model": config.model_id,
            "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 20},
        }
        if fault in ("429", "500"):
            return httpx.Response(int(fault), text="secret provider response")
        if fault == "timeout":
            raise httpx.ReadTimeout("secret provider exception")
        if fault == "connect":
            raise httpx.ConnectError("secret provider exception")
        if fault == "json":
            return httpx.Response(200, content=b"{")
        if fault == "oversize":
            return httpx.Response(200, content=b"x" * (config.max_response_bytes + 1))
        if fault == "refusal":
            data["choices"][0]["message"]["refusal"] = "secret reason"
        elif fault in ("length", "content_filter"):
            data["choices"][0]["finish_reason"] = fault
        elif fault == "tools":
            data["choices"][0]["message"]["tool_calls"] = [{"function": "unsafe"}]
        elif fault == "model":
            data["model"] = "unauthorized-model"
        elif fault == "usage":
            data["usage"]["prompt_tokens"] = True
        elif fault == "choices":
            data["choices"].append(data["choices"][0])
        return httpx.Response(200, json=data)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await ChatCompletionsTransport(config=config, api_key="local-only-key", client=client)(request, budget)
    assert result.kind != "success" and len(calls) == 1
    assert "secret" not in result.model_dump_json()
    if fault == "connect":
        assert "ConnectError" in result.issues[0].detail
    elif fault == "timeout":
        assert "ReadTimeout" in result.issues[0].detail
    elif fault == "500":
        assert "status 500" in result.issues[0].detail


@pytest.mark.asyncio
async def test_total_input_bound_denies_call_before_network(dataset):
    request, budget, config = request_budget(dataset)
    budget = budget.model_copy(update={"max_tokens": 10})

    async def handler(wire):
        pytest.fail("unaffordable input reached network")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await ChatCompletionsTransport(config=config, api_key="local-only-key", client=client)(request, budget)
    assert result.kind == "capacity_unavailable"


@pytest.mark.asyncio
async def test_http_cancellation_propagates(dataset):
    request, budget, config = request_budget(dataset)
    entered = asyncio.Event()

    async def handler(wire):
        entered.set()
        await asyncio.Event().wait()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        task = asyncio.create_task(
            ChatCompletionsTransport(config=config, api_key="local-only-key", client=client)(request, budget)
        )
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.parametrize(
    "field", ("authorized", "token_accounting_confirmed", "dataset_hash", "model_id", "max_calls", "max_total_tokens")
)
def test_explicit_authorization_is_exact_and_absolute(dataset, field):
    config = ChatCompletionConfig(
        base_url="https://provider.example/v1", provider_id="approved-provider", model_id="exact-model"
    )
    auth = authorization_template(dataset)
    auth.update(
        authorized=True,
        token_accounting_confirmed=True,
        provider_id=config.provider_id,
        model_id=config.model_id,
        base_url=config.base_url,
    )
    check_authorization(auth, dataset, config)
    auth[field] = (
        False
        if field in ("authorized", "token_accounting_confirmed")
        else (0 if field.startswith("max_") else "forged")
    )
    with pytest.raises(ValueError):
        check_authorization(auth, dataset, config)


@pytest.mark.asyncio
async def test_missing_authorization_never_opens_hosted_client(dataset, tmp_path, monkeypatch):
    opened = []
    original = httpx.AsyncClient

    def guarded_client(*args, **kwargs):
        assert isinstance(kwargs.get("transport"), httpx.MockTransport)
        opened.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", guarded_client)
    with pytest.raises(ValueError, match="authorization"):
        await run(tmp_path, hosted=True)
    assert len(opened) == 2


@pytest.mark.parametrize(
    "url", ("https://user:pass@example.com", "http://remote.example", "https://example.com?token=unsafe")
)
def test_transport_rejects_unsafe_endpoint_config(url):
    with pytest.raises(ValueError):
        ChatCompletionConfig(base_url=url, provider_id="provider", model_id="exact-model").checked()


def test_dotenv_settings_consumed_without_credentials_in_plan(monkeypatch, tmp_path):
    from dotenv import load_dotenv

    from experiments.v2.run_hosted_comparison import configuration, datasets, plan

    for key in ("LLM_PROVIDER", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    env = tmp_path / ".env"
    env.write_text(
        "LLM_PROVIDER=openai\nLLM_BASE_URL=https://api.openai.com/v1\n"
        "LLM_MODEL=gpt-4.1-mini\nLLM_API_KEY=local-test-secret\n"
    )
    load_dotenv(env, override=False)
    config = configuration()
    assert config.request_model_id == "gpt-4.1-mini"
    assert config.model_id == "gpt-4.1-mini-2025-04-14"
    assert config.base_url == "https://api.openai.com/v1"
    assert "local-test-secret" not in json.dumps(plan(datasets(), config))


@pytest.mark.asyncio
async def test_explicit_openai_alias_requests_alias_and_validates_snapshot(dataset):
    from experiments.v2.run_hosted_comparison import SNAPSHOT

    request, budget, config = request_budget(dataset)
    config = replace(
        config,
        base_url="https://api.openai.com/v1",
        provider_id="openai",
        model_id=SNAPSHOT,
        request_model_id="gpt-4.1-mini",
    )
    request = request.model_copy(update={"provider_id": "openai", "model_id": SNAPSHOT})

    async def handler(wire):
        assert wire.headers["authorization"] == "Bearer local-only-key"
        assert wire.url == "https://api.openai.com/v1/chat/completions"
        assert json.loads(wire.content)["model"] == "gpt-4.1-mini"
        return httpx.Response(
            200,
            json={
                "model": SNAPSHOT,
                "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 10},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await ChatCompletionsTransport(config=config, api_key="local-only-key", client=client)(request, budget)
    assert result.kind == "success" and result.model_id == SNAPSHOT
    with pytest.raises(ValueError, match="mapping"):
        replace(config, base_url="https://different.example/v1").checked()


@pytest.mark.asyncio
async def test_dollar_guard_reserves_unknown_usage_before_call(dataset):
    from experiments.v2.run_hosted_comparison import CALL_USD, SpendGuard
    from negotiator.v2.orchestration.budgets import failure

    request, budget, _ = request_budget(dataset)
    calls = []

    async def failed(request, budget):
        calls.append(request)
        return failure(request, "timeout", "safe timeout")

    guard = SpendGuard(failed, max_usd=CALL_USD)
    assert (await guard(request, budget)).kind == "timeout"
    with pytest.raises(ValueError, match="expenditure"):
        await guard(request, budget)
    assert len(calls) == 1 and guard.report()["unknown_usage_calls"] == 1
    assert guard.reserved == CALL_USD


def test_combined_experiment_approval_is_exact_and_under_five_dollars():
    from experiments.v2.run_hosted_comparison import SNAPSHOT, approve, datasets, plan

    config = ChatCompletionConfig(
        base_url="https://api.openai.com/v1", provider_id="openai", model_id=SNAPSHOT, request_model_id="gpt-4.1-mini"
    )
    expected = plan(datasets(), config)
    assert Decimal(expected["conservative_usd_reservation"]) < Decimal("5")
    assert expected["max_calls"] == 77
    with pytest.raises(ValueError, match="approval"):
        approve(expected, expected)
    auth = {**expected, "authorized": True, "token_accounting_confirmed": True}
    approve(auth, expected)
    with pytest.raises(ValueError, match="differs"):
        approve({**auth, "max_usd": "50.00"}, expected)


@pytest.mark.asyncio
async def test_hosted_benchmark_composition_preserves_common_universe_and_validator():
    from experiments.v2.run_hosted_comparison import benchmark_decision, datasets, record
    from tests.v2.integration.test_grounded_model import success

    data = datasets()
    example = data["benchmark"]["examples"][0]
    config = ChatCompletionConfig(base_url="https://provider.example/v1", provider_id="fake", model_id="fake-model")
    seen = []

    async def transport(request, budget):
        seen.append(request)
        if request.task == "interpret":
            raw = json.dumps(
                dict(
                    observations=[], reported_constraints=[], hypotheses=[], uncertainties=[], questions=[], unknowns=[]
                )
            )
        else:
            option = min(
                (o for o in request.input.options if o.summary.startswith("Offer:")),
                key=lambda o: Decimal(o.summary.split("from cheapest=")[1].split(" ")[0]),
            )
            raw = json.dumps({"selected_id": option.candidate_id, "supporting_quote": ""})
        return success(request, raw, m.ModelUsage(input_tokens=100, output_tokens=50))

    traces = [
        await benchmark_decision(data, example, arm, config, transport) for arm in ("minimum", "direct", "grounded")
    ]
    assert len({semantic_hash(t.evaluations) for t in traces}) == 1
    assert [len(t.model_calls) for t in traces] == [0, 1, 2]
    assert all(
        record(t, example["id"], arm)["admitted"]
        for t, arm in zip(traces, ("minimum", "direct", "grounded"), strict=True)
    )
    assert len(seen) == 3
    assert all(t.decision.fallback_code is None for t in traces)


@pytest.mark.asyncio
async def test_complete_hosted_composition_uses_only_mock_http_until_approval(monkeypatch, tmp_path):
    import experiments.v2.run_hosted_comparison as experiment

    for key, value in {
        "LLM_PROVIDER": "openai",
        "LLM_BASE_URL": "https://api.openai.com/v1",
        "LLM_MODEL": "gpt-4.1-mini",
        "LLM_API_KEY": "local-secret",
    }.items():
        monkeypatch.setenv(key, value)
    expected = experiment.plan(experiment.datasets(), experiment.configuration())
    auth = tmp_path / "approved-local-test.json"
    auth.write_text(json.dumps({**expected, "authorized": True, "token_accounting_confirmed": True}))
    real_client = httpx.AsyncClient
    wires = []

    async def handler(wire):
        payload = json.loads(wire.content)
        projection = json.loads(payload["messages"][1]["content"])
        assert "admissible_actions" not in wire.content.decode()
        assert "fallback_price" not in wire.content.decode()
        assert payload["model"] == "gpt-4.1-mini"
        wires.append(payload)
        if projection["kind"] == "interpret":
            response = dict(
                observations=[], reported_constraints=[], hypotheses=[], uncertainties=[], questions=[], unknowns=[]
            )
        else:
            offers = [o for o in projection["options"] if o["summary"].startswith("Offer:")]
            option = min(offers, key=lambda o: Decimal(o["summary"].split("from cheapest=")[1].split(" ")[0]))
            response = dict(selected_id=option["candidate_id"], supporting_quote="")
        return httpx.Response(
            200,
            json={
                "model": experiment.SNAPSHOT,
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(response)}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            },
        )

    def client(**kwargs):
        if kwargs.get("transport") is None:
            kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(**kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client)
    result = await experiment.run(tmp_path / "run", auth)
    assert result["status"] == "complete"
    assert len(result["records"]) == 72 and len(result["p10"]) == 2
    assert len(wires) == 74 and result["inference"]["attempts"] == 74
    assert Decimal(result["inference"]["reserved_usd"]) < 5
    assert [(r["example_id"], r["arm"], r["fallback_code"]) for r in result["records"] if r["fallback_code"]] == [
        ("adversarial:1", "direct", "private_disclosure"),
        ("adversarial:1", "grounded", "private_disclosure"),
    ]
    assert "local-secret" not in (tmp_path / "run" / "report.json").read_text()
    with pytest.raises(FileExistsError):
        await experiment.run(tmp_path / "run", auth)
    assert len(wires) == 74
