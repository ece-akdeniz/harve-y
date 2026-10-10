import json
from types import SimpleNamespace

import pytest

from tests.v2.builders import normalize_fixture
from tests.v2.support import digest, inputs, read_fixture, require


def fake_request(prefixes=()):
    return SimpleNamespace(config=SimpleNamespace(getoption=lambda name: list(prefixes)))


def fake_package(monkeypatch, tmp_path):
    monkeypatch.setattr("tests.v2.support.importlib.util.find_spec", lambda name: SimpleNamespace(
        submodule_search_locations=[str(tmp_path)],
    ))


def test_only_absent_components_can_be_expected_failures(monkeypatch, tmp_path):
    fake_package(monkeypatch, tmp_path)
    with pytest.raises(pytest.xfail.Exception, match="UNIMPLEMENTED"):
        require(fake_request(), "missing.component")


def test_required_absent_component_is_a_failure(monkeypatch, tmp_path):
    fake_package(monkeypatch, tmp_path)
    with pytest.raises(pytest.fail.Exception, match="Required V2 component absent"):
        require(fake_request(["core"]), "core.models")


@pytest.mark.parametrize("error", [RuntimeError("broken implementation"), ModuleNotFoundError("missing dependency")])
def test_existing_component_import_failures_are_never_hidden(monkeypatch, tmp_path, error):
    fake_package(monkeypatch, tmp_path)
    module = tmp_path / "v2/core/models.py"
    module.parent.mkdir(parents=True)
    module.write_text("# Present implementation\n")

    def broken(name):
        raise error

    monkeypatch.setattr("tests.v2.support.importlib.import_module", broken)
    with pytest.raises(type(error), match=str(error)):
        require(fake_request(), "core.models")


def test_normalizer_removes_answers_and_does_not_mutate_fixture(p10):
    normalized = normalize_fixture(p10)
    assert "official_cost_goldens" not in normalized
    assert "expected_evidence" not in normalized
    assert "variants" not in normalized
    assert "official_cost_goldens" in p10
    assert normalized["case"] == p10["case"]


@pytest.mark.parametrize("fault,key,length", [
    ("subject_301", "subject", 301), ("body_8001", "body", 8001),
    ("four_sheets", "term_sheets", 4), ("refs_21", "refs", 21),
    ("attachments_6", "attachments", 6),
])
def test_negative_fixture_labels_change_real_wire_inputs(p10, fault, key, length):
    p10["validation_fault"] = fault
    assert len(normalize_fixture(p10)["wire_message"][key]) == length


def test_effective_config_rejects_unsupported_and_hidden_values(request, p10):
    config = require(request, "config")
    with pytest.raises(ValueError):
        config.resolve_config({**p10["config"], "made_up_feature": True})
    with pytest.raises(ValueError):
        config.resolve_config({**p10["config"], "strategy_id": "unknown-bundle"})


def test_effective_config_is_ambient_environment_independent(request, p10, monkeypatch):
    config = require(request, "config")
    before = config.resolve_config(p10["config"])
    monkeypatch.setenv("NEGOTIATOR_CLAIMS", "1")
    monkeypatch.setenv("NEGOTIATOR_ESTIMATES", "1")
    monkeypatch.setenv("LLM_MODEL", "not-the-frozen-model")
    after = config.resolve_config(p10["config"])
    assert before == after
    assert before.config_hash == after.config_hash


def test_future_provider_identity_does_not_change_foundational_models(request, p10):
    data = inputs(request, p10)
    fields = set(type(data.context.case).model_fields)
    assert not fields & {"llm_provider", "llm_model", "openai_model", "capacity_strategy"}


def test_decision_record_binds_every_stage_and_rejects_orphan_selection(request, p10):
    models = require(request, "core.models")
    data = inputs(request, p10)
    raw = data.record.model_dump(mode="json")
    assert raw["schema_version"] == "negotiator-v2/1"
    assert raw["revision"] >= 1
    assert raw["snapshot"] == data.context.snapshot.model_dump(mode="json")
    raw["evaluation_artifact_refs"] = []
    with pytest.raises(ValueError):
        models.DecisionRecord.model_validate_json(json.dumps(raw))


def test_decision_record_schema_roundtrip_without_fixture_codec(request):
    models = require(request, "core.models")
    raw = read_fixture("decision-record.json")
    record = models.DecisionRecord.model_validate_json(json.dumps(raw))
    assert record.schema_version == "negotiator-v2/1"
    assert record.revision == 1
    assert record.parent_record_hash is None
    assert record.evaluation_artifact_refs
    assert record.selection_artifact_ref
    assert models.DecisionRecord.model_validate_json(record.model_dump_json()) == record


@pytest.mark.parametrize("fault", ["orphan_selection", "reordered_stages", "failed_without_issue", "unknown_version"])
def test_record_invariants_reject_misleading_trace(request, fault):
    models = require(request, "core.models")
    raw = read_fixture("decision-record.json")
    if fault == "orphan_selection":
        raw["evaluation_artifact_refs"] = []
    elif fault == "reordered_stages":
        raw["stages"].reverse()
    elif fault == "failed_without_issue":
        raw["stages"][0]["status"] = "failed"
    else:
        raw["schema_version"] = "negotiator-v2/999"
    raw["record_hash"] = digest({key: value for key, value in raw.items() if key != "record_hash"})
    expected = {
        "orphan_selection": "orphan_selection", "reordered_stages": "stage_order",
        "failed_without_issue": "stage_issue_required", "unknown_version": "schema_version",
    }[fault]
    with pytest.raises(ValueError, match=expected):
        models.DecisionRecord.model_validate_json(json.dumps(raw))


def test_assessment_draft_distinguishes_all_four_collections(request, p10):
    models = require(request, "core.models")
    variant = next(v for v in p10["variants"] if v["id"] == "delivery")
    draft = models.AssessmentDraft.model_validate_json(json.dumps(variant["model_response"]))
    assert draft.observations[0].kind == "conditional_offer"
    assert draft.reported_constraints[0].authority == "supplier_reported"
    assert draft.hypotheses[0].direction == "increase"
    assert draft.hypotheses[0].numeric_effect is None
    assert isinstance(draft.uncertainties, tuple)


@pytest.mark.parametrize("fault", ["no_citation", "false_authority", "negative_span", "binding_action"])
def test_assessment_draft_rejects_boundary_authority_faults(request, p10, fault):
    models = require(request, "core.models")
    draft = next(v for v in p10["variants"] if v["id"] == "delivery")["model_response"]
    if fault == "no_citation":
        draft["observations"][0]["citations"] = []
    elif fault == "false_authority":
        draft["reported_constraints"][0]["authority"] = "canonical_fact"
    elif fault == "negative_span":
        draft["observations"][0]["citations"][0]["start"] = -1
    else:
        draft["action"] = {"type": "accept"}
    with pytest.raises(ValueError):
        models.AssessmentDraft.model_validate_json(json.dumps(draft))
