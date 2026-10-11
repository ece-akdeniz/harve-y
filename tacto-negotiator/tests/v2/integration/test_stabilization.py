"""Sanitized failure attribution and derived structured-output compatibility."""

import json
from dataclasses import replace

import httpx
import pytest

from negotiator.v2.adapters.chat_completions import ChatCompletionsTransport, messages_for, response_format
from negotiator.v2.core import models as m
from negotiator.v2.core.diagnostics import rejection
from negotiator.v2.orchestration.offline import OfflineDecisionTrace
from tests.v2.integration.test_grounded_model import Transport, draft, interpreter, setup
from tests.v2.integration.test_hosted_readiness import request_budget


@pytest.mark.parametrize('fault,category,stage', [
    ('json', 'invalid_json', 'format'), ('missing', 'missing_field', 'schema'),
    ('type', 'invalid_type', 'schema'), ('enum', 'invalid_enum', 'schema'),
    ('extra', 'schema_mismatch', 'schema'), ('quote', 'invalid_quote', 'grounding'),
    ('meaning', 'semantic_relationship', 'grounding'), ('privacy', 'disclosure_violation', 'format'),
])
@pytest.mark.asyncio
async def test_precise_rejection_survives_consumer_and_trace(relationship, fault, category, stage):
    inputs, snapshot, coordinator, clock, _, config = setup(relationship)
    raw = json.loads(draft(snapshot).model_dump_json())
    if fault == 'missing':
        del raw['observations'][0]['summary']
    elif fault == 'type':
        raw['observations'][0]['citations'] = 5
    elif fault == 'enum':
        raw['observations'][0]['kind'] = 'invented'
    elif fault == 'extra':
        raw['untrusted-field-do-not-persist-12345'] = 'supplied-value'
    elif fault == 'quote':
        raw['observations'][0]['citations'][0]['quote'] = 'X' * len(snapshot.conversation.messages[0].body)
    elif fault == 'meaning':
        raw['observations'][0]['kind'] = 'refusal'
    elif fault == 'privacy':
        raw['observations'][0]['summary'] = 'api_key=credential-do-not-persist-12345'
    raw = '{' if fault == 'json' else json.dumps(raw)
    coordinator.interpreter = interpreter(clock, None, config, Transport(raw))
    coordinator.model_token_limit = 2048
    trace = await coordinator.run_once(snapshot)
    restored = OfflineDecisionTrace.model_validate_json(trace.model_dump_json())
    restored.verify()
    call = restored.model_calls[0]
    assert call.result_kind == 'success' and call.consumer_admitted is False
    assert call.fallback_used and call.fallback_reason
    assert (call.diagnostic.category, call.diagnostic.stage) == (category, stage)
    assert call.permitted_raw_response is None
    assert 'credential-do-not-persist' not in trace.model_dump_json()
    assert 'untrusted-field-do-not-persist' not in trace.model_dump_json()
    assert next(s for s in trace.stages if s.name == 'interpretation').issues
    assert trace.validation.kind == 'valid'


@pytest.mark.parametrize('reason,category', [
    ('invalid_schema: selected ID outside exact approved batch', 'candidate_id_mismatch'),
    ('missing_source: excluded evidence', 'missing_evidence'),
    ('ungrounded_output: conditional constraint lost its antecedent', 'semantic_relationship'),
    ('ungrounded_output: uncalibrated or unsupported hypothesis', 'unsupported_economics'),
    ('unsupported_claim: invented claim', 'unsupported_claim'),
    ('ungrounded_output: departure lacks a commercial reason', 'grounding_failure'),
])
def test_bounded_contract_categories(reason, category):
    from negotiator.v2.core.errors import ContractViolation
    assert rejection(ContractViolation(reason), 'grounding').category == category


@pytest.fixture
def dataset():
    from tests.v2.integration.test_hosted_readiness import ROOT
    return json.loads((ROOT / 'experiments/v2/p10-offline-input.json').read_text())


def test_structured_schema_derived_from_dtos_and_versioned_prompt(dataset):
    request, _, config = request_budget(dataset)
    request = request.model_copy(update={'prompt_version': 'grounded-supplier-v2'})
    config = replace(config, structured_output=True)
    response = response_format(request, config)
    schema = response['json_schema']['schema']
    assert response['type'] == 'json_schema' and response['json_schema']['strict']
    assert set(schema['properties']) == set(m.AssessmentDraft.model_json_schema()['properties'])
    for obj in (schema, *schema['$defs'].values()):
        if 'properties' in obj:
            assert set(obj['required']) == set(obj['properties']) and obj['additionalProperties'] is False
    prompt = messages_for(request, config)[0]['content']
    assert 'condition_observation_refs' in prompt and 'supplier_reported' in prompt
    assert 'package_fingerprint=null' in prompt and 'not AssessmentDraft fields' in prompt


@pytest.mark.asyncio
async def test_strict_provider_format_and_independent_consumer_admission(dataset):
    request, budget, config = request_budget(dataset)
    request = request.model_copy(update={'prompt_version': 'grounded-supplier-v2'})
    config = replace(config, structured_output=True)
    async def mock(wire):
        body = json.loads(wire.content)
        assert body['response_format']['type'] == 'json_schema'
        return httpx.Response(200, json={
            'model': config.model_id, 'choices': [{'finish_reason': 'stop', 'message': {'content': '{'}}],
            'usage': {'prompt_tokens': 20, 'completion_tokens': 1},
        })
    async with httpx.AsyncClient(transport=httpx.MockTransport(mock)) as client:
        result = await ChatCompletionsTransport(config=config, api_key='local-only', client=client)(request, budget)
    # Provider transport success never certifies schema/semantics, even in strict mode.
    assert result.kind == 'success'
    with pytest.raises(ValueError) as error:
        m.AssessmentDraft.model_validate_json(result.raw_response_json)
    assert rejection(error.value, 'schema').category == 'invalid_json'


@pytest.mark.asyncio
async def test_legacy_trace_digest_and_unknown_admission_are_preserved(relationship):
    from negotiator.v2.core.serialization import semantic_hash
    _, snapshot, coordinator, clock, _, config = setup(relationship)
    coordinator.interpreter = interpreter(clock, None, config, Transport(draft(snapshot).model_dump_json()))
    coordinator.model_token_limit = 2048
    trace = await coordinator.run_once(snapshot)
    historic = json.loads(trace.model_dump_json())
    for call in historic['model_calls']:
        for key in ('consumer_admitted', 'fallback_used', 'fallback_reason', 'diagnostic'):
            del call[key]
    historic['trace_hash'] = semantic_hash({k: v for k, v in historic.items() if k != 'trace_hash'})
    restored = OfflineDecisionTrace.model_validate_json(json.dumps(historic))
    restored.verify()
    assert restored.model_calls[0].consumer_admitted is None
    assert restored.model_calls[0].diagnostic is None  # Historical exact cause is unattributable.
    assert json.loads(restored.model_dump_json()) == historic
    OfflineDecisionTrace.model_validate_json(restored.model_dump_json()).verify()


@pytest.mark.parametrize('fault,category', [
    ('forged', 'candidate_id_mismatch'), ('quote', 'invalid_quote'),
    ('edited', 'schema_mismatch'), ('private', 'disclosure_violation'),
    ('json', 'invalid_json'), ('transport_failure', 'execution_failure'),
])
@pytest.mark.asyncio
async def test_selection_rejections_are_attributed_without_raw_output(relationship, fault, category):
    from tests.v2.integration.test_grounded_selection import decision
    trace, _ = await decision(relationship, 'We prefer delivery in 49 days.', choice='delivery', fault=fault)
    call = trace.model_calls[-1]
    assert call.consumer_admitted is False and call.fallback_used
    assert call.diagnostic.category == category and call.permitted_raw_response is None
    assert trace.decision.fallback_code and trace.validation.kind == 'valid'


def test_structured_schema_is_counted_once_in_conservative_input_budget(dataset):
    from negotiator.v2.adapters.chat_completions import input_token_upper_bound
    request, _, config = request_budget(dataset)
    request = request.model_copy(update={'prompt_version': 'grounded-supplier-v2'})
    config = replace(config, structured_output=True)
    messages = messages_for(request, config)
    output_format = response_format(request, config)
    bound = input_token_upper_bound(messages, config.framing_token_reserve, output_format)
    format_size = len(json.dumps(output_format, separators=(',', ':'), ensure_ascii=False).encode())
    assert bound == input_token_upper_bound(messages, config.framing_token_reserve) + format_size
    assert bound < 16384 and '$defs' not in messages[0]['content']
    # Decimal serialization is a wire string, matching the strict consumer's Decimal rule.
    assert output_format['json_schema']['schema']['$defs']['EstimatedEffect']['properties']['low']['type'] == 'string'
