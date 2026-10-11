"""Canonical candidate certificates and admission predicates; no arithmetic."""

from . import models as m
from .errors import ContractViolation
from .serialization import semantic_hash

QUESTION_ID = "clarify:terms"


def candidate_id(candidate):
    return "sha256:" + semantic_hash(
        {
            k: getattr(candidate, k)
            for k in (
                "schema_version",
                "snapshot",
                "intent_id",
                "supplier_id",
                "contents",
            )
        }
    )


def evaluation_id(item):
    return "sha256:" + semantic_hash(item.model_dump(mode="json", exclude={"evaluation_id"}))


def batch_hash(batch):
    return semantic_hash(
        {
            "schema_version": batch.schema_version,
            "snapshot": batch.snapshot,
            "items": sorted(batch.items, key=lambda i: i.candidate.candidate_id),
            "issues": batch.issues,
        }
    )


def verify_batch(batch):
    if batch_hash(batch) != batch.batch_hash or any(
        candidate_id(i.candidate) != i.candidate.candidate_id or evaluation_id(i) != i.evaluation_id
        for i in batch.items
    ):
        raise ContractViolation("invalid_schema: candidate/evaluation/batch identity mismatch")


def issue(code, detail, refs=()):
    return m.Issue(code=code, severity="error", component="economics.candidates", refs=refs, detail=detail)


def policy_issues(results, context):
    problems = [i for r in results for i in r.issues if i.severity == "error"]
    for r in results:
        if not (r.numerically_valid and r.basis_verified and r.must_haves_ok and r.nominal_cost):
            problems.append(issue("infeasible", "package lacks admissible complete costs"))
            continue
        costs = (
            (r.nominal_cost,)
            if context.cost_policy.comparison == "nominal"
            else tuple(s.cost for s in r.scenario_costs)
        )
        if not costs:
            problems.append(issue("missing_source", "robust comparison requires scenario costs"))
        if context.cost_policy.ceiling and any(c.amount > context.cost_policy.ceiling.amount for c in costs):
            problems.append(issue("infeasible", "complete cost exceeds explicit policy ceiling"))
    return tuple(problems)


def economic_fingerprint(context: m.EconomicContext) -> str:
    """The C-defined economic projection, excluding incidental evidence prose."""
    projection = context.model_dump(mode="json", exclude={"fingerprint", "issues"})
    case = projection["case"]
    projection["case"] = {k: case[k] for k in (
        "case_id", "case_type", "supplier_ids", "parts", "negotiable_fields", "options",
        "fixed_terms", "buyer", "round_limit",
    )}
    case = projection["case"]
    case["supplier_ids"] = sorted(case["supplier_ids"])
    case["parts"] = sorted(case["parts"], key=lambda x: x["part_id"])
    for key in ("fixed_terms", "options"):
        case[key] = sorted(case[key], key=lambda x: x["field"])
    projection["standards_by_supplier"] = sorted(projection["standards_by_supplier"], key=lambda x: x["supplier_id"])
    projection["estimates"] = sorted(projection["estimates"], key=lambda x: x["estimate_id"])
    for entry in projection["standards_by_supplier"]:
        for key in ("bindings", "field_origins"):
            entry["standards"][key] = sorted(entry["standards"][key], key=lambda x: x["field"])
    for entry in projection["estimates"]:
        for key in ("bindings", "field_origins"):
            entry["standard"][key] = sorted(entry["standard"][key], key=lambda x: x["field"])
    projection["scenario_policy"]["scenarios"] = sorted(
        projection["scenario_policy"]["scenarios"], key=lambda x: x["scenario_id"],
    )
    projection["scenario_policy"]["required_supplier_ids"] = sorted(
        projection["scenario_policy"]["required_supplier_ids"],
    )
    for scenario in projection["scenario_policy"]["scenarios"]:
        scenario["estimate_ids"] = sorted(scenario["estimate_ids"])
    return semantic_hash(projection)



def case_contract_hash(case: m.CaseContract) -> str:
    projection = case.model_dump(mode="json", exclude={"contract_hash", "title", "refs"})
    for key in ("fixed_terms", "options"):
        projection[key] = sorted(projection[key], key=lambda item: item["field"])
    projection["parts"] = sorted(projection["parts"], key=lambda item: item["part_id"])
    projection["supplier_ids"] = sorted(projection["supplier_ids"])
    return semantic_hash(projection)
