"""Authorization, exact mocked schedule and stop boundaries for the development evaluation."""

import json
from decimal import Decimal

import httpx
import pytest

from experiments.v2.run_hosted_comparison import SpendGuard
from experiments.v2.run_semantic_validation import MAX_USD, FixedClock, plan, public_config, run, suite


@pytest.mark.asyncio
async def test_prepare_exact_schedule_without_credentials_or_network(tmp_path, monkeypatch):
    from experiments.v2.run_semantic_validation import ChatCompletionsTransport

    for key in ('LLM_API_KEY', 'LLM_PROVIDER', 'LLM_BASE_URL', 'LLM_MODEL'):
        monkeypatch.delenv(key, raising=False)
    original = ChatCompletionsTransport.__call__

    async def local_only(self, request, budget):
        assert isinstance(self.client._transport, httpx.MockTransport)
        return await original(self, request, budget)

    monkeypatch.setattr(ChatCompletionsTransport, '__call__', local_only)
    output = tmp_path / 'prepared'
    result = await run(output)
    report = json.loads((output / 'local-preflight/report.json').read_text())
    payloads = json.loads((output / 'request-preview.json').read_text())
    assert result['status'] == 'prepared; no hosted inference'
    assert len(payloads) == report['inference']['attempts'] == 19
    assert report['interpretation']['semantic_correct'] == 14
    assert report['interpretation']['critical_review_missing'] == 14
    assert all(c['consumer_admitted'] for c in report['interpretation_calls'])
    assert all(r['final_action_valid'] and r['selection_admitted'] for r in report['selection_decisions'])
    assert [r['cost_delta'] for r in report['selection_decisions']] == ['0.0', '1262.88']
    assert all(p['response_format']['type'] == 'json_schema' for p in payloads)
    assert all(0 < p['max_completion_tokens'] <= 2048 for p in payloads)
    assert all('scripted_draft' not in p['messages'][1]['content'] for p in payloads)
    assert not (output / 'hosted-started.json').exists()
    assert result['plan']['frozen_held_out_sha256'] == report['frozen_held_out_sha256_after']
    with pytest.raises(FileExistsError):
        await run(output)


@pytest.mark.asyncio
async def test_unapproved_or_changed_plan_rejected_before_transport(tmp_path, monkeypatch):
    def never():
        raise AssertionError('configuration must not load for rejected approval')
    monkeypatch.setattr('experiments.v2.run_semantic_validation.configuration', never)
    auth = tmp_path / 'authorization.json'
    original = plan()
    for value in (original, {**original, 'authorized': True, 'token_accounting_confirmed': True,
                             'max_calls': 77},
                  {**original, 'authorized': True, 'token_accounting_confirmed': True,
                   'prompt_hashes': {}}):
        auth.write_text(json.dumps(value))
        with pytest.raises(ValueError):
            await run(tmp_path / 'not-started', auth)
        assert not (tmp_path / 'not-started').exists()


@pytest.mark.asyncio
async def test_failed_probe_stops_and_preserves_partial_report(tmp_path):
    from negotiator.v2.adapters.chat_completions import failure

    async def rejected(request, budget):
        return failure(request, 'transport_failure', 'probe rejected', Decimal('0'))
    guard = SpendGuard(rejected, max_usd=MAX_USD, max_calls=19)
    with pytest.raises(ValueError, match='connectivity failed'):
        await suite(tmp_path, public_config(), guard, FixedClock(), hosted=False)
    report = json.loads((tmp_path / 'report.json').read_text())
    assert report['inference']['attempts'] == 1
    assert report['status'].startswith('stopped')
    assert report['interpretation']['missing'] == 14
    assert report['selection_decisions'] == []


@pytest.mark.asyncio
async def test_spend_guard_charges_failure_and_refuses_twentieth_call():
    from types import SimpleNamespace
    from uuid import uuid4

    from negotiator.v2.adapters.chat_completions import failure

    request = SimpleNamespace(call_id=uuid4(), task='interpret', model_id='test')
    budget = SimpleNamespace(max_tokens=16384)
    invoked = []
    async def rejected(request, budget):
        invoked.append(request.call_id)
        return failure(request, 'transport_failure', 'rejected', Decimal('0'))
    guard = SpendGuard(rejected, max_usd=MAX_USD, max_calls=19)
    for _ in range(19):
        await guard(request, budget)
    with pytest.raises(ValueError, match='allowance exhausted'):
        await guard(request, budget)
    assert len(invoked) == 19
    assert str(guard.reserved) == '0.4980736'
