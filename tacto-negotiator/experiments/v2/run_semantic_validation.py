"""Prepare or execute one separately authorized 19-call offline development evaluation.

Reuses the existing DTO consumers, HTTP transport, spend guard and P10 composition.
No Arena client, Lab publisher, retry or new negotiation policy.
"""

import argparse
import asyncio
import hashlib
import json
import os
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

import httpx
from dotenv import load_dotenv

from experiments.v2.evaluate_interpretation import evaluate
from experiments.v2.evaluate_stabilization import FIXTURE, FixedClock, scripted_draft
from experiments.v2.run_hosted_comparison import (
    CALL_USD,
    INPUT_RATE,
    OUTPUT_RATE,
    ROOT,
    SNAPSHOT,
    SpendGuard,
    approve,
    configuration,
)
from experiments.v2.run_p10_llm import DATASET, PER_CALL_TOKENS, Clock, LocalResponses
from negotiator.v2.adapters.chat_completions import (
    ChatCompletionConfig,
    ChatCompletionsTransport,
    input_token_upper_bound,
    response_format,
)
from negotiator.v2.adapters.model import AsyncModelGateway
from negotiator.v2.adapters.p10 import recorded_p10
from negotiator.v2.core import models as m
from negotiator.v2.core.serialization import semantic_hash
from negotiator.v2.factory import bounded_services, run_recorded_decision
from negotiator.v2.intelligence.interpreter import GroundedInterpreter, InterpreterConfig
from negotiator.v2.orchestration.budgets import DecisionModelLedger
from negotiator.v2.orchestration.metrics import decision_metrics

MAX_CALLS = 19
MAX_USD = Decimal('1.00')
REVIEW = Path(__file__).with_name('semantic-expectations-review.json')


def public_config():
    return ChatCompletionConfig(base_url='https://api.openai.com/v1', provider_id='openai',
                                model_id=SNAPSHOT, request_model_id=SNAPSHOT, structured_output=True)


def frozen_digest():
    data = json.loads((ROOT / 'tests/fixtures/v2/selection-pilot.json').read_text())
    heldout = [e for e in data['examples'] if e['split'] == 'held-out']
    digest = hashlib.sha256(json.dumps(heldout, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if digest != data['held_out_sha256']:
        raise ValueError('frozen held-out subset changed')
    return digest


def plan():
    fixture = json.loads(FIXTURE.read_text())
    if len(fixture['examples']) != 14:
        raise ValueError('exact 14-example development allowance required')
    source = sorted((ROOT / 'src/negotiator/v2').rglob('*.py'))
    source += sorted((ROOT / 'src/negotiator/v2/intelligence/prompts').glob('*.txt'))
    source += [Path(__file__), REVIEW, DATASET, FIXTURE,
               Path(__file__).with_name('evaluate_interpretation.py'),
               Path(__file__).with_name('evaluate_stabilization.py'),
               Path(__file__).with_name('run_p10_llm.py'),
               Path(__file__).with_name('run_hosted_comparison.py')]
    return {
        'authorized': False, 'token_accounting_confirmed': False,
        'experiment': 'v2-semantic-development-19-v1', 'single_run': True,
        'provider': 'OpenAI direct', 'base_url': 'https://api.openai.com/v1',
        'request_model': SNAPSHOT, 'response_model': SNAPSHOT,
        'max_calls': MAX_CALLS, 'max_usd': str(MAX_USD),
        'per_call_reserved_tokens': PER_CALL_TOKENS,
        'max_total_reserved_tokens': MAX_CALLS * PER_CALL_TOKENS,
        'max_output_tokens_per_call': 2048,
        'conservative_usd_reservation': str(MAX_CALLS * CALL_USD),
        'input_usd_per_million': str(INPUT_RATE), 'output_usd_per_million': str(OUTPUT_RATE),
        'token_accounting': 'utf8-byte-upper-bound-v1; messages + strict schema + 256 framing',
        'retry_limit': 0, 'interpretation_time_limit_s': 8, 'selection_time_limit_s': 4,
        'decision_call_limit': 2, 'decision_reserved_tokens': 32768,
        'schedule': ['one strict selection connectivity probe',
                     '14 interpretation-only development examples', 'two P10 decisions, two calls each'],
        'dataset_hashes': {'development': semantic_hash(fixture),
                           'p10': semantic_hash(json.loads(DATASET.read_text())),
                           'semantic_review': semantic_hash(json.loads(REVIEW.read_text()))},
        'frozen_held_out_sha256': frozen_digest(), 'held_out_calls': 0,
        'prompt_hashes': {name: hashlib.sha256(files('negotiator.v2.intelligence').joinpath(
            'prompts', name + '.txt').read_bytes()).hexdigest()
            for name in ('grounded-supplier-v2', 'grounded-selection-v2')},
        'provider_schema_hashes': {task: semantic_hash(response_format(SimpleNamespace(task=task), public_config()))
                                   for task in ('interpret', 'select')},
        'dto_schema_hashes': {name: semantic_hash(dto.model_json_schema())
                              for name, dto in [('interpret', m.AssessmentDraft), ('select', m.SelectorResponse)]},
        'source_sha256': semantic_hash({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in source}),
        'permitted_projection': 'V2 supplier-body/assessment/evaluated-option projections only; '
                                'no labels, scripted drafts, raw buyer context or credentials',
        'remote_negotiations': 0, 'remote_lab_writes': 0,
    }


def write(path, value):
    # Private artifacts can contain admitted supplier text, never rejected raw outputs.
    with path.open('x', encoding='utf-8') as stream:
        os.chmod(path, 0o600)
        stream.write(json.dumps(value, indent=2) + '\n')


class MockResponses:
    """HTTP mock rehearsal only. The hosted path never uses authored draft responses."""

    def __init__(self):
        self.payloads = []
        self.examples = {e['label']['text']: e for e in json.loads(FIXTURE.read_text())['examples']}

    async def __call__(self, wire):
        payload = json.loads(wire.content)
        self.payloads.append(payload)
        projection = json.loads(payload['messages'][1]['content'])
        if projection['kind'] == 'interpret':
            message = m.ConversationMessage.model_validate_json(json.dumps(projection['conversation']['messages'][0]))
            response = scripted_draft(self.examples[message.body], message).model_dump(mode='json')
            return httpx.Response(200, json={'model': SNAPSHOT, 'choices': [{'finish_reason': 'stop',
                'message': {'content': json.dumps(response)}}],
                'usage': {'prompt_tokens': 1000, 'completion_tokens': 400}})
        if len(projection['options']) == 1:
            response = {'selected_id': projection['options'][0]['candidate_id'], 'supporting_quote': ''}
            return httpx.Response(200, json={'model': SNAPSHOT, 'choices': [{'finish_reason': 'stop',
                'message': {'content': json.dumps(response)}}],
                'usage': {'prompt_tokens': 1000, 'completion_tokens': 60}})
        return await LocalResponses(projection['assessment']['observations'][0]['citations'][0]['quote'])(wire)


async def p10_trace(dataset, body, config, transport, clock):
    inputs = recorded_p10(dataset, message=body, now=clock.utcnow())
    assembler, baseline = bounded_services(inputs, clock)
    control = await run_recorded_decision(inputs, assembler=assembler, coordinator=baseline)
    assembler, coordinator = bounded_services(inputs, clock, transport, config, prompt_revision='v2')
    trace = await run_recorded_decision(inputs, assembler=assembler, coordinator=coordinator)
    trace.verify()
    control.verify()
    if trace.validation is None or trace.validation.kind != 'valid':
        raise ValueError('independent final validation failed')
    if trace.evaluations != control.evaluations:
        raise ValueError('same-input baseline economic universe changed')
    return trace, control


async def probe_request(dataset, config):
    mock = MockResponses()
    async with httpx.AsyncClient(transport=httpx.MockTransport(mock), trust_env=False) as client:
        transport = ChatCompletionsTransport(config=config, api_key='local-rehearsal', client=client)
        trace, _ = await p10_trace(dataset, dataset['supplier_messages'][0], config, transport, FixedClock())
    original = trace.model_calls[-1].request
    option = next(o for o in original.input.options if o.candidate_id == trace.decision.candidate_id)
    probe_id = uuid5(NAMESPACE_URL, 'semantic-validation-probe:' + semantic_hash(original.input))
    return original.model_copy(update={
        'call_id': probe_id, 'correlation_id': probe_id,
        'input': original.input.model_copy(update={'options': (option,)}),
    })


async def suite(output, config, guard, clock, *, hosted):
    fixture, dataset = json.loads(FIXTURE.read_text()), json.loads(DATASET.read_text())
    predictions, calls, decisions = [], [], []
    report = {'evidence': 'hosted inference' if hosted else 'local HTTP mock; no hosted inference',
              'status': 'incomplete', 'selection_decisions': decisions,
              'plan': {**plan(), 'authorized': hosted, 'token_accounting_confirmed': hosted}}
    try:
        request = await probe_request(dataset, config)
        mb = m.ModelBudget(deadline_at=clock.utcnow() + timedelta(seconds=4), time_limit_s=Decimal('4'),
                           max_tokens=PER_CALL_TOKENS, max_calls=1, retry_limit=0)
        async with asyncio.timeout(4):
            result = await guard(request, mb)
        valid = False
        if result.kind == 'success':
            try:
                response = m.SelectorResponse.model_validate_json(result.raw_response_json)
                valid = (response.selected_id == request.input.options[0].candidate_id
                         and response.supporting_quote == '')
            except ValueError:
                pass
        write(output / 'connectivity.json', {'transport_status': result.kind, 'consumer_valid': valid})
        if not valid:
            raise ValueError('strict connectivity failed; stop without retry')
        for example in fixture['examples']:
            body = example['label']['text']
            inputs = recorded_p10({**dataset, 'supplier_messages': [body]}, message=body, now=clock.utcnow())
            assembler, _ = bounded_services(inputs, clock)
            snapshot = assembler.assemble(inputs)
            ledger = DecisionModelLedger(budget=inputs.budget, clock=clock, token_limit=32768)
            ic = InterpreterConfig(provider_id=config.provider_id, protocol_id=config.protocol_id,
                model_id=config.model_id, prompt_version='grounded-supplier-v2',
                task_schema_version='assessment-draft-v1', max_tokens=PER_CALL_TOKENS,
                time_limit_s=Decimal('8'),
                approved_message_hashes=(snapshot.conversation.messages[0].content_hash,))
            assessment = await GroundedInterpreter(model=AsyncModelGateway(transport=guard, ledger=ledger),
                clock=clock, config=ic).interpret(snapshot.context, snapshot.conversation, None, snapshot.budget)
            predictions.append({'id': example['label']['id'], 'assessment': assessment.model_dump(mode='json')})
            calls.extend(c.model_dump(mode='json', exclude={'permitted_raw_response'}) for c in ledger.traces)
        for index, body in enumerate(dataset['supplier_messages']):
            trace, control = await p10_trace(dataset, body, config, guard, clock)
            row = decision_metrics(trace)
            row.update(message_index=index, assessment=trace.assessment.model_dump(mode='json'),
                       selected_contents=next(i.candidate.contents.model_dump(mode='json')
                           for i in trace.evaluations.items if i.candidate.candidate_id == trace.decision.candidate_id),
                       supporting_citations=[c.model_dump(mode='json') for c in trace.decision.citations],
                       semantic_review='pending independent adjudication',
                       strategic_justification_review='pending independent adjudication')
            decisions.append(row)
            write(output / f'p10-{index}.json', json.loads(trace.model_dump_json()))
            write(output / f'p10-{index}-baseline.json', json.loads(control.model_dump_json()))
        report['status'] = 'complete'
    except Exception:
        report['status'] = 'stopped; no retry; exception text withheld'
        raise
    finally:
        labels = {**fixture, 'examples': [e['label'] for e in fixture['examples']]}
        report.update(interpretation=evaluate(labels, predictions), interpretation_calls=calls,
                      inference=guard.report(), frozen_held_out_sha256_after=frozen_digest())
        write(output / 'predictions.json', predictions)
        write(output / 'report.json', report)
        write(output / 'review-pending.json', {'review_status': 'not independently human adjudicated',
            'interpretation': [{'id': p['id'], 'semantic_correct': None, 'critical_errors': None,
                                'reviewer': None} for p in predictions],
            'selection': [{'message_index': r['message_index'], 'semantic_defensible': None,
                           'critical_errors': None, 'reviewer': None} for r in decisions]})
    return report


async def run(output, authorization=None):
    expected = plan()
    if authorization is not None:
        approve(json.loads(authorization.read_text()), expected)
        config = replace(configuration(), request_model_id=SNAPSHOT, structured_output=True)
        if config != public_config():
            raise ValueError('hosted configuration differs from frozen prepared configuration')
    # Fresh directories are the single-use marker; never resume an ambiguous inference run.
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    write(output / 'authorization-template.json', expected)
    mock = MockResponses()
    async with httpx.AsyncClient(transport=httpx.MockTransport(mock), trust_env=False) as client:
        transport = ChatCompletionsTransport(config=public_config(), api_key='local-rehearsal', client=client)
        preflight = output / 'local-preflight'
        preflight.mkdir(mode=0o700)
        report = await suite(preflight, public_config(), SpendGuard(transport, max_usd=MAX_USD,
                            max_calls=MAX_CALLS), FixedClock(), hosted=False)
    if report['inference']['attempts'] != MAX_CALLS or report['interpretation']['semantic_correct'] != 14:
        raise ValueError('local preflight count/consumer controls failed')
    # Actual HTTP bodies exclude credentials, labels and scripted outputs. Selection inputs
    # are mock-conditioned; hosted assessments/IDs may differ, but projection rules are identical.
    write(output / 'request-preview.json', mock.payloads)
    write(output / 'request-reservations.json', [
        {'index': index, 'input_byte_bound': input_token_upper_bound(
            payload['messages'], 256, payload['response_format']),
         'output_allowance': payload['max_completion_tokens'],
         'reserved_tokens': PER_CALL_TOKENS}
        for index, payload in enumerate(mock.payloads)])
    if authorization is None:
        return {'status': 'prepared; no hosted inference', 'plan': expected}
    write(output / 'hosted-started.json', {**expected, 'authorized': True, 'token_accounting_confirmed': True})
    async with httpx.AsyncClient(follow_redirects=False, trust_env=False) as client:
        transport = ChatCompletionsTransport(config=public_config(), api_key=os.environ['LLM_API_KEY'], client=client)
        return await suite(output, public_config(), SpendGuard(transport, max_usd=MAX_USD,
                           max_calls=MAX_CALLS), Clock(), hosted=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--authorization', type=Path)
    args = parser.parse_args()
    if args.authorization is not None:
        load_dotenv(ROOT / '.env', override=False)
    result = asyncio.run(run(args.out, args.authorization))
    print(json.dumps({'status': result['status'], 'hosted_calls': 0 if args.authorization is None else
                     result['inference']['attempts']}, indent=2))
