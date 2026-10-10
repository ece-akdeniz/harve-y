import copy
from decimal import Decimal
from types import SimpleNamespace

import pytest

from tests.v2.builders import normalize_fixture
from tests.v2.fakes import FakeClock, ReplayArenaGateway, ReplayModelGateway, ScriptedPipeline
from tests.v2.support import inputs, require, terms_of


async def reference_wiring(ports, data):
    """Test-only call sequence, not a production negotiation engine or arithmetic oracle."""
    evidence = ports.build_context(*data["context_args"])
    context = data["context_from_evidence"](evidence)
    assessment = await ports.interpret(context, data["conversation"], None, data["budget"])
    intents = await ports.propose_strategies(context, assessment, data["state"], data["budget"], data["research"])
    generated = ports.generate_candidates(intents.intents[0], context, data["state"], data["budget"])
    evaluations = ports.evaluate_candidates(generated.candidates, context)
    decision = await ports.select_action(evaluations, assessment, data["state"], data["budget"], data["research"])
    rendered = ports.render(decision, evaluations.items[0], (), context)
    validated = ports.validate_action(rendered, context, data["state"], data["budget"])
    execution = await ports.execute_action(
        validated.action, data["permit"], data["operation"], data["transport_budget"],
    )
    feedback = ports.process_feedback(data["state"], data["operation"], data["response"])
    return execution, feedback


@pytest.mark.asyncio
async def test_reference_fake_pipeline_calls_every_stage_without_network():
    # Distinct sentinels verify argument routing before domain types exist. The typed production
    # loop below is a separate gate; this test makes no production correctness claim.
    names = ["context", "assessment", "intents", "generation", "evaluations", "decision",
             "rendered", "validation", "execution", "feedback"]
    artifacts = {name: object() for name in names}
    artifacts["intents"] = SimpleNamespace(intents=(object(),))
    artifacts["generation"] = SimpleNamespace(candidates=(object(),))
    artifacts["evaluations"] = SimpleNamespace(items=(object(),))
    artifacts["validation"] = SimpleNamespace(kind="valid", action=object())
    ports = ScriptedPipeline(artifacts)
    data = {name: object() for name in ["conversation", "budget", "state", "research", "permit",
                                      "operation", "transport_budget", "response"]}
    data["context_args"] = (object(), object(), object(), (), object())
    data["context_from_evidence"] = lambda evidence: evidence
    assert await reference_wiring(ports, data) == (artifacts["execution"], artifacts["feedback"])
    assert [stage for stage, _ in ports.calls] == names
    by_name = dict(ports.calls)
    assert by_name["intents"][1] is artifacts["assessment"]
    assert by_name["decision"][0] is artifacts["evaluations"]
    assert by_name["rendered"][0] is artifacts["decision"]
    assert by_name["validation"][0] is artifacts["rendered"]
    assert by_name["execution"][0] is artifacts["validation"].action


async def runtime(request, p10, tmp_path):
    factory = require(request, "factory")
    data = inputs(request, p10)
    model = ReplayModelGateway(data.model_result)
    arena = ReplayArenaGateway(observations=data.gateway_observations, results=data.gateway_results)
    built = factory.build_offline_runtime(
        fixture=normalize_fixture(p10), model=model, arena=arena, clock=FakeClock(),
        database_path=tmp_path / "state.sqlite",
    )
    return built, model, arena


@pytest.mark.asyncio
async def test_typed_complete_offline_loop_and_trace(request, p10, tmp_path):
    built, model, arena = await runtime(request, p10, tmp_path)
    try:
        result = await built.run_once(built.inputs.snapshot)
        assert result.outcome.kind == "selected"
        assert result.record.schema_version == "negotiator-v2/1"
        assert result.record.snapshot == built.inputs.snapshot.context.snapshot
        assert [stage.name for stage in result.record.stages] == [
            "evidence", "assessment", "proposal", "generation", "evaluation", "selection",
            "rendering", "validation", "execution", "feedback",
        ]
        assert all(stage.status == "completed" and stage.artifact_refs for stage in result.record.stages)
        assert terms_of(result.selected.candidate.contents.packages[0]) == {
            "unit_price": 28.34, "volume_per_year": 23400, "contract_months": 24, "lead_time_days": 42,
        }
        assert result.selected.economic[0].nominal_cost.amount == Decimal("1335154.08")
        assert result.execution.kind == "acknowledged"
        assert len(arena.submissions) == 1
        assert arena.submissions[0].payload_hash == result.validated.payload_hash
        assert len(model.calls) <= 1
    finally:
        await built.aclose()


@pytest.mark.asyncio
async def test_frozen_replay_has_identical_semantic_decision_and_record(request, p10, tmp_path):
    one, _, _ = await runtime(request, copy.deepcopy(p10), tmp_path / "one")
    two, _, _ = await runtime(request, copy.deepcopy(p10), tmp_path / "two")
    try:
        first = await one.run_once(one.inputs.snapshot)
        second = await two.run_once(two.inputs.snapshot)
        assert first.record.semantic_hash == second.record.semantic_hash
        assert first.validated.payload_hash == second.validated.payload_hash
        assert first.selected.candidate.contents == second.selected.candidate.contents
        assert first.record.config_artifact_ref == second.record.config_artifact_ref
    finally:
        await one.aclose()
        await two.aclose()


@pytest.mark.asyncio
async def test_model_variability_is_recorded_without_faking_determinism(request, p10, tmp_path):
    first_fixture = copy.deepcopy(p10)
    second_fixture = copy.deepcopy(p10)
    first_fixture["model_fixture_id"] = "longer"
    second_fixture["model_fixture_id"] = "uncertain"
    one, _, _ = await runtime(request, first_fixture, tmp_path / "one")
    two, _, _ = await runtime(request, second_fixture, tmp_path / "two")
    try:
        a = await one.run_once(one.inputs.snapshot)
        b = await two.run_once(two.inputs.snapshot)
        assert a.record.model_call_refs and b.record.model_call_refs
        assert a.record.model_output_hashes != b.record.model_output_hashes
        assert a.record.fixture_input_hash != b.record.fixture_input_hash
    finally:
        await one.aclose()
        await two.aclose()


@pytest.mark.asyncio
async def test_final_record_can_be_loaded_after_restart(request, p10, tmp_path):
    built, _, _ = await runtime(request, p10, tmp_path)
    result = await built.run_once(built.inputs.snapshot)
    record_hash = result.record.record_hash
    await built.aclose()
    reopened, _, arena = await runtime(request, p10, tmp_path)
    try:
        records = await reopened.store.decision_records(p10["run_id"], p10["case"]["case_id"])
        assert records[-1].record_hash == record_hash
        assert arena.submissions == []
    finally:
        await reopened.aclose()
