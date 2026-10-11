"""Standalone probe recovery, using only scripted local transport."""

import asyncio
import hashlib
import json
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from experiments.v2 import run_d01_inference_probe as probe
from negotiator.v2.adapters.p10 import recorded_p10
from negotiator.v2.core import models as m
from negotiator.v2.orchestration.budgets import failure


@pytest.fixture
def inputs():
    root = Path(__file__).resolve().parents[3]
    data = json.loads((root / 'experiments/v2/p10-offline-input.json').read_text())
    return recorded_p10(data, message=data['supplier_messages'][0],
                        now=datetime.now(UTC) - timedelta(hours=1))


class ScriptedAllowance:
    def __init__(self, output, *, success=False):
        self.inner = self
        self.calls = []
        self.reserved = Decimal(0)
        self.raw_path = output / 'raw-model-outputs.jsonl'
        self.success = success
        self.stopped = False

    def stop_model_calls(self, reason):
        self.stopped = True

    async def __call__(self, request, budget):
        assert not self.stopped
        self.calls.append({'reserved_tokens': budget.max_tokens, 'latency_s': 0})
        self.raw_path.write_text(json.dumps({
            'usage_unknown': not self.success, 'estimated_cost_from_reported_tokens': None,
            'provider_reported_cost': None,
        }) + '\n')
        if not self.success:
            return failure(request, 'transport_failure', 'scripted failure')
        return m.ModelSuccess(kind='success', call_id=request.call_id, model_id=request.model_id,
                              elapsed_s=Decimal(0), issues=(), raw_response_json='{}',
                              response_hash=hashlib.sha256(b'{}').hexdigest(),
                              usage=m.ModelUsage(input_tokens=1, output_tokens=1))


def _stalled_cleanup_worker(raw_inputs, output):
    async def run():
        # Deliberately leave executor teardown pending, including in unrestricted environments.
        asyncio.get_running_loop().run_in_executor(None, time.sleep, 60)
        inputs = probe.OfflineRecordedInputs.model_validate_json(raw_inputs)
        await probe._persist_probe(inputs, output, ScriptedAllowance(output))
    asyncio.run(run())


def _stalled_decision_worker(raw_inputs, output):
    time.sleep(60)


def test_trace_survives_stalled_teardown(inputs, tmp_path):
    report = probe._supervise_probe(inputs, tmp_path, worker=_stalled_cleanup_worker,
                                   compute_seconds=5, cleanup_seconds=0.1)
    assert report['cleanup_status'] == 'terminated'
    assert report['status'] == 'partial_model_execution'
    assert report['validation_kind'] == 'valid'
    assert report['reserved_transport_invocations'] == 1
    assert (tmp_path / 'decision-trace.json').exists()
    assert report['runner_wall_s'] < 5


def test_whole_decision_timeout_is_reported(inputs, tmp_path):
    # A killed writer may leave its old fixed-name temporary artifact behind.
    (tmp_path / "result.json.tmp").write_text("partial")
    report = probe._supervise_probe(inputs, tmp_path, worker=_stalled_decision_worker,
                                   compute_seconds=0.1, cleanup_seconds=0.1)
    assert report['status'] == 'runner_timeout'
    assert report['cleanup_status'] == 'terminated'
    assert report['arena_message_posts'] == 0


@pytest.mark.asyncio
async def test_known_usage_report_and_original_clocks(inputs, tmp_path):
    original = inputs.model_dump_json()
    report = await probe._persist_probe(inputs, tmp_path, ScriptedAllowance(tmp_path, success=True))
    assert report['reported_usage_unknown'] is False
    assert report['validation_kind'] == 'valid'
    assert inputs.model_dump_json() == original
    trace = json.loads((tmp_path / 'decision-trace.json').read_text())
    recorded = probe.OfflineRecordedInputs.model_validate_json(trace['recorded_input_bytes'])
    assert recorded.server == inputs.server
    assert recorded.state.server == inputs.server
    assert 'offline replay only' in report['validation_clock']


def test_probe_stop_reaches_durable_allowance(tmp_path):
    allowance = probe.ProbeAllowance(tmp_path)
    allowance.stop_model_calls('model_timeout')
    ledger = json.loads((tmp_path / 'inference-ledger.json').read_text())
    assert allowance.stopped is True
    assert ledger['stopped'] is True
    assert ledger['calls'] == []


@pytest.mark.asyncio
async def test_report_before_cancelled_transport_finishes(inputs, tmp_path):
    allowance = ScriptedAllowance(tmp_path)
    original = allowance.__class__.__call__

    class PendingCleanupAllowance(ScriptedAllowance):
        async def __call__(self, request, budget):
            result = await original(self, request, budget)
            # The ledger may return before a cancelled transport's finally block runs.
            self.calls[-1].pop('latency_s')
            self.calls[-1]['call_id'] = str(request.call_id)
            return result

    report = await probe._persist_probe(inputs, tmp_path, PendingCleanupAllowance(tmp_path))
    assert report['transport_cleanup_pending'] is True
    assert report['validation_kind'] == 'valid'
    assert float(report['total_inference_latency_s']) >= 0
    assert report['estimated_cost_from_reported_tokens_usd'] is None



def test_worker_uses_persisted_plan_budgets(inputs, tmp_path, monkeypatch):
    for name in ('STAGE_LIMITS', 'TOTAL_MODEL_SECONDS', 'COMPUTE_SECONDS'):
        monkeypatch.setattr(probe, name, getattr(probe, name))
    monkeypatch.setattr(probe, 'ProbeAllowance', lambda output: ScriptedAllowance(output, success=True))
    probe._atomic_private_json(tmp_path / 'approved-plan.json', {
        'stage_time_limits_s': {'interpret': 30.0, 'propose': 15.0},
        'total_model_time_limit_s': '46', 'compute_limit_s': '60',
    })
    probe._probe_worker(inputs.model_dump_json(), tmp_path)
    trace = json.loads((tmp_path / 'decision-trace.json').read_text())
    snapshot = json.loads(trace['snapshot_bytes'])
    assert Decimal(snapshot['budget']['compute_limit_s']) == Decimal(60)
    assert Decimal(snapshot['budget']['model_time_limit_s']) == Decimal(46)
    assert probe.STAGE_LIMITS['interpret'] == 30
    assert json.loads((tmp_path / 'result.json').read_text())['validation_kind'] == 'valid'
