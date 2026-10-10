import pytest

from tests.v2.support import inputs, require


async def seeded_store(request, p10, tmp_path):
    module = require(request, "adapters.sqlite")
    data = inputs(request, p10)
    store = module.SQLiteStateStore(tmp_path / "store.sqlite")
    await store.initialize(data.state)
    for reference, payload in data.artifacts:
        await store.put_artifact(reference, payload)
    return store, data


@pytest.mark.asyncio
async def test_compare_and_swap_commit_is_atomic_and_prepares_exact_outbox(request, p10, tmp_path):
    store, data = await seeded_store(request, p10, tmp_path)
    try:
        result = await store.persist_state(data.state.version, data.commit)
        assert result.kind == "committed"
        assert result.new_state.version > data.state.version
        assert result.operation.operation_id == data.commit.operation_id
        pending = await store.pending_operations(p10["run_id"])
        assert pending == (result.operation,)
        assert result.permit.payload_hash == result.operation.payload_hash
        stale = await store.persist_state(data.state.version, data.commit)
        assert stale.kind == "conflict"
        assert await store.pending_operations(p10["run_id"]) == pending
    finally:
        await store.aclose()


@pytest.mark.asyncio
async def test_decision_records_append_immutable_revisions(request, p10, tmp_path):
    store, data = await seeded_store(request, p10, tmp_path)
    try:
        await store.save_decision_record(data.record)
        await store.save_decision_record(data.record)  # Exact duplicate is idempotent.
        records = await store.decision_records(p10["run_id"], p10["case"]["case_id"])
        assert records == (data.record,)
        with pytest.raises(ValueError, match="record"):
            await store.save_decision_record(data.conflicting_record)
        assert await store.decision_records(p10["run_id"], p10["case"]["case_id"]) == records
    finally:
        await store.aclose()


@pytest.mark.asyncio
async def test_duplicate_source_keys_do_not_consume_another_round(request, p10, tmp_path):
    store, data = await seeded_store(request, p10, tmp_path)
    try:
        first = await store.append_observations(data.state.version, (data.message_event,))
        second = await store.append_observations(first.new_state.version, (data.message_event,))
        assert second.new_state.version == first.new_state.version
        assert second.new_state.server == first.new_state.server
    finally:
        await store.aclose()


def test_projector_rejects_terminal_event_without_authoritative_proof(request, p10):
    projector = require(request, "orchestration.state").EventStateProjector()
    data = inputs(request, p10)
    with pytest.raises(ValueError, match="terminal"):
        projector.apply_event(data.state, data.unproven_terminal_event)


def test_historical_assessment_is_preserved_on_new_revision(request, p10):
    projector = require(request, "orchestration.state").EventStateProjector()
    data = inputs(request, p10)
    one = projector.apply_event(data.state, data.assessment_event)
    two = projector.apply_event(one, data.next_assessment_event)
    assert len(two.strategic.assessments) == len(one.strategic.assessments) + 1
    assert two.strategic.assessments[-2] == one.strategic.assessments[-1]
    assert two.strategic.assessments[-1].parent_assessment_id == two.strategic.assessments[-2].assessment_id
