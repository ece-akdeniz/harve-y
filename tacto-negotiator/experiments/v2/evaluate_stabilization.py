"""Run fixed scripted drafts through the real interpreter and the separate semantic evaluator.

No provider calls, held-out tuning or human-reviewed accuracy claim.
"""

import argparse
import asyncio
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from experiments.v2.evaluate_interpretation import evaluate
from negotiator.v2.adapters.model import AsyncModelGateway
from negotiator.v2.adapters.p10 import recorded_p10
from negotiator.v2.core import models as m
from negotiator.v2.factory import bounded_services
from negotiator.v2.intelligence.interpreter import GroundedInterpreter, InterpreterConfig
from negotiator.v2.orchestration.budgets import DecisionModelLedger

PROJECT = Path(__file__).resolve().parents[2]
FIXTURE = PROJECT / 'tests/fixtures/v2/interpretation-stabilization.json'


class FixedClock:
    def utcnow(self):
        return datetime(2026, 10, 11, tzinfo=UTC)

    def monotonic(self):
        return 0.0


def scripted_draft(example, message):
    raw = json.loads(json.dumps(example['scripted_draft']))
    span = dict(session_id=message.session_id, thread_id=message.thread_id, message_id=message.message_id,
                start=0, end=len(message.body), quote=message.body)
    for name in ('observations', 'reported_constraints', 'uncertainties'):
        for item in raw[name]:
            item['citations'] = [span]
            if name != 'reported_constraints':
                item['summary'] = message.body
    for item in raw['hypotheses']:
        item.update(summary=message.body, supporting_refs=[span], contradicting_refs=[])
    return m.AssessmentDraft.model_validate_json(json.dumps(raw))


async def run_controls():
    fixture = json.loads(FIXTURE.read_text())
    dataset = json.loads((PROJECT / 'experiments/v2/p10-offline-input.json').read_text())
    predictions, calls = [], []
    clock = FixedClock()
    for example in fixture['examples']:
        dataset = {**dataset, 'supplier_messages': [example['label']['text']]}
        inputs = recorded_p10(dataset, message=example['label']['text'], now=clock.utcnow())
        assembler, _ = bounded_services(inputs, clock)
        snapshot = assembler.assemble(inputs)
        draft = scripted_draft(example, snapshot.conversation.messages[0])
        response_json = draft.model_dump_json()
        async def transport(request, budget, response=response_json):
            return m.ModelSuccess(kind='success', call_id=request.call_id, model_id=request.model_id,
                                  elapsed_s=Decimal('0'), issues=(), raw_response_json=response,
                                  response_hash=hashlib.sha256(response.encode()).hexdigest(), usage=m.ModelUsage())
        ledger = DecisionModelLedger(budget=inputs.budget, clock=clock, token_limit=32768)
        config = InterpreterConfig(provider_id='local-fixture', protocol_id='injected-v1', model_id='scripted-control',
                                   prompt_version='grounded-supplier-v2', task_schema_version='assessment-draft-v1',
                                   max_tokens=16384, time_limit_s=Decimal('8'),
                                   approved_message_hashes=(snapshot.conversation.messages[0].content_hash,))
        result = await GroundedInterpreter(model=AsyncModelGateway(transport=transport, ledger=ledger),
                                           clock=clock, config=config).interpret(
            snapshot.context, snapshot.conversation, None, snapshot.budget)
        predictions.append({'id': example['label']['id'], 'assessment': result.model_dump(mode='json')})
        calls.extend(c.model_dump(mode='json', exclude={'request', 'permitted_raw_response'}) for c in ledger.traces)
    labels = {**fixture, 'examples': [e['label'] for e in fixture['examples']]}
    report = evaluate(labels, predictions)
    report.update(evidence=fixture['evidence'], hosted_calls=0, calls=calls)
    return report, predictions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report, predictions = asyncio.run(run_controls())
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    (args.out / 'predictions.json').write_text(json.dumps(predictions, indent=2) + '\n')
    fixture = json.loads(FIXTURE.read_text())
    review = [{"id": e['label']['id'], "supplier_text": e['label']['text'],
               "provisional_expectations": e['label'], "prediction_id": e['label']['id'],
               "human_semantic_correct": None, "critical_errors": None,
               "strategic_relevance": None, "reviewer": None} for e in fixture['examples']]
    (args.out / 'human-review.json').write_text(json.dumps(review, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('evidence', 'denominator', 'structural_admission_rate',
                                          'semantic_correct', 'accuracy', 'fallbacks', 'critical_review_missing')},
                     indent=2))


if __name__ == '__main__':
    main()
