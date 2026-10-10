import asyncio
import copy

import pytest

from tests.v2.builders import normalize_fixture
from tests.v2.fakes import FakeClock, ReplayArenaGateway, ReplayModelGateway
from tests.v2.support import inputs, require


async def create_runtime(request, fixture, path):
    factory = require(request, "factory")
    data = inputs(request, fixture)
    arena = ReplayArenaGateway(data.gateway_observations, data.gateway_results)
    runtime = factory.build_offline_runtime(
        fixture=normalize_fixture(fixture), model=ReplayModelGateway(data.model_result), arena=arena,
        clock=FakeClock(), database_path=path,
    )
    return runtime, arena


@pytest.mark.asyncio
async def test_uncertain_send_stays_owned_and_restart_does_not_change_id_or_bytes(request, p10, tmp_path):
    p10["gateway_scenario"] = "uncertain_send"
    runtime, arena = await create_runtime(request, p10, tmp_path / "state.sqlite")
    try:
        first = await runtime.run_once(runtime.inputs.snapshot)
        pending = await runtime.store.pending_operations(p10["run_id"])
        assert first.execution.kind == "uncertain"
        assert len(pending) == 1 and pending[0].status == "uncertain"
        assert first.state.runtime_status == "recovery_required"
        assert first.state.server.status == "open"
        original = pending[0]
        assert {op.operation_id for op in arena.submissions} == {original.operation_id}
        assert {op.payload_hash for op in arena.submissions} == {original.payload_hash}
        original_bytes = await runtime.store.get_artifact(original.payload_bytes_ref)
    finally:
        await runtime.aclose()
    restarted, replay_arena = await create_runtime(request, p10, tmp_path / "state.sqlite")
    try:
        await restarted.resume()
        current = await restarted.store.pending_operations(p10["run_id"])
        assert len(current) == 1 and current[0].operation_id == original.operation_id
        assert await restarted.store.get_artifact(current[0].payload_bytes_ref) == original_bytes
        assert all(op.operation_id == original.operation_id for op in replay_arena.submissions)
        assert all(op.payload_hash == original.payload_hash for op in replay_arena.submissions)
    finally:
        await restarted.aclose()


@pytest.mark.asyncio
async def test_rejected_closes_do_not_end_server_open_case(request, p10, tmp_path):
    p10["gateway_scenario"] = "close_rejected"
    runtime, _ = await create_runtime(request, p10, tmp_path / "state.sqlite")
    try:
        result = await runtime.close(reason_code="deadline")
        assert result.state.server.status == "open"
        assert result.state.runtime_status == "recovery_required"
        assert result.terminal is None
        assert result.state.server.terminal is None
    finally:
        await runtime.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["agreed", "final_offer", "deadline", "exhausted", "restart"])
async def test_all_close_triggers_recheck_same_economic_decision(request, p10, tmp_path, reason):
    p10["gateway_scenario"] = "terminal_confirmed"
    runtime, arena = await create_runtime(request, p10, tmp_path / "state.sqlite")
    try:
        result = await runtime.close(reason_code=reason)
        assert result.close_decision.action.kind == "accept"
        assert result.close_decision.action.offer_id == "offer:valid-standing"
        assert result.close_decision.action.supplier_id == p10["supplier_id"]
        assert result.terminal is not None
        assert result.state.server.status == "ended"
        assert result.state.runtime_status == "ended"
        assert len(arena.submissions) == 1
    finally:
        await runtime.aclose()


@pytest.mark.asyncio
async def test_stale_pending_accept_cannot_replay_against_replaced_offer(request, p10, tmp_path):
    p10["gateway_scenario"] = "standing_offer_changed"
    runtime, arena = await create_runtime(request, p10, tmp_path / "state.sqlite")
    try:
        result = await runtime.resume()
        assert result.state.runtime_status == "recovery_required"
        assert arena.submissions == []
        assert result.terminal is None
    finally:
        await runtime.aclose()


@pytest.mark.asyncio
async def test_unknown_open_cannot_start_second_session(request, p10, tmp_path):
    p10["gateway_scenario"] = "unknown_open"
    runtime, arena = await create_runtime(request, p10, tmp_path / "state.sqlite")
    try:
        result = await runtime.resume()
        pending = await runtime.store.pending_operations(p10["run_id"])
        assert len(pending) == 1 and pending[0].kind == "open"
        assert pending[0].session_id is None
        assert result.state.runtime_status == "recovery_required"
        assert len({op.operation_id for op in arena.submissions}) <= 1
    finally:
        await runtime.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["proposal_exception", "parser_exception", "evaluator_exception"])
async def test_pipeline_faults_are_supervised_and_bounded(request, p10, tmp_path, fault):
    p10["runtime_fault"] = fault
    runtime, arena = await create_runtime(request, p10, tmp_path / "state.sqlite")
    try:
        result = await asyncio.wait_for(runtime.run_once(runtime.inputs.snapshot), timeout=0.5)
        assert result.state.runtime_status == "recovery_required"
        assert result.terminal is None
        assert arena.submissions == []
        assert any(stage.status == "failed" for stage in result.record.stages)
        assert result.record.issues
    finally:
        await runtime.aclose()


@pytest.mark.asyncio
async def test_refusal_history_survives_restart_without_optional_policy_switch(request, p10, tmp_path):
    p10["history_variant"] = "refusal"
    runtime, _ = await create_runtime(request, p10, tmp_path / "state.sqlite")
    initial = copy.deepcopy(runtime.inputs.state.strategic.refusals)
    assert initial
    await runtime.aclose()
    restarted, _ = await create_runtime(request, p10, tmp_path / "state.sqlite")
    try:
        state = await restarted.store.load_state(p10["run_id"], p10["case"]["case_id"])
        assert state.strategic.refusals == initial
    finally:
        await restarted.aclose()
