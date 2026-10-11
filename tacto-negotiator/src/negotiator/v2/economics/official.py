"""Complete package evaluation through an injected authoritative oracle."""

import operator
from decimal import Decimal

from ..core.certificates import economic_fingerprint
from ..core.errors import ContractViolation
from ..core.models import (
    CandidateAction,
    EconomicContext,
    EvaluationBatch,
    FieldOrigin,
    Issue,
    NegotiationContext,
    Package,
    PackageEvaluation,
    ResolvedTerms,
    ScenarioCost,
    SourceRef,
    TermBinding,
)
from ..core.ports import OfficialCostOracle
from ..core.serialization import semantic_hash


def _version(value, origin_key):
    projection = value.model_dump(mode="json", exclude={"version_hash"})
    for key in ("bindings", origin_key):
        projection[key] = sorted(projection[key], key=lambda x: x["field"])
    return semantic_hash(projection)




class OfficialEconomicEvaluator:
    def __init__(self, *, oracle: OfficialCostOracle):
        self.oracle = oracle

    def evaluate_candidates(
        self, candidates: tuple[CandidateAction, ...], context: NegotiationContext,
    ) -> EvaluationBatch:
        from .finite import evaluate_candidates

        return evaluate_candidates(self, candidates, context)

    def evaluate_package(self, package: Package, supplier_id: str, context: EconomicContext) -> PackageEvaluation:
        if not isinstance(package, Package) or not isinstance(context, EconomicContext):
            raise TypeError("evaluation requires validated Package and EconomicContext")
        case = context.case
        if supplier_id not in case.supplier_ids:
            raise ContractViolation("scope_mismatch: supplier is not in case")
        if economic_fingerprint(context) != context.fingerprint:
            raise ContractViolation("invalid_schema: economic fingerprint mismatch")
        if any(i.severity == "error" for i in context.issues):
            raise ContractViolation("missing_source: economic context contains unresolved errors")
        basis = case.buyer.fallback_price.basis
        def basis_key(b):
            return b.currency, b.price_unit, b.part_ids, b.quantity_basis
        if basis_key(package.price_basis) != basis_key(basis):
            raise ContractViolation("unknown_basis: package basis does not match buyer basis")
        standards = next((s.standards for s in context.standards_by_supplier if s.supplier_id == supplier_id), None)
        if standards is None:
            raise ContractViolation("missing_source: supplier standards unavailable")
        if _version(standards, "field_origins") != standards.version_hash:
            raise ContractViolation("invalid_schema: supplier standards hash mismatch")
        ref = SourceRef(record_id=f"case:{case.contract_hash}")
        buyer = case.buyer
        # Explicit pinned-kit buyer-plan defaults, with a separate origin for every value.
        defaults = {"payment_days": buyer.reference_payment_days, "lead_time_days": buyer.need_lead_time_days,
                    "contract_months": round(12 * buyer.horizon_years),
                    "incoterm": max(buyer.freight, key=lambda r: r.eur_per_unit).incoterm}
        if buyer.need_per_year == buyer.need_per_year.to_integral_value():
            defaults["volume_per_year"] = int(buyer.need_per_year)
        values = {k: TermBinding(field=k, value=v) for k, v in defaults.items()}
        origins = {k: FieldOrigin(field=k, source_kind="buyer_default", source_refs=(ref,)) for k in defaults}
        values.update({t.field: t for t in standards.bindings})
        origins.update({o.field: o for o in standards.field_origins})
        for term in case.fixed_terms:
            values[term.field] = term
            origins[term.field] = FieldOrigin(field=term.field, source_kind="fixed", source_refs=(ref,))
        declared = {t.field: t for t in package.bindings}
        if not set(declared).issubset(case.negotiable_fields):
            raise ContractViolation("infeasible: package contains fixed or nonnegotiable fields")
        if "unit_price" not in declared:
            raise ContractViolation("missing_source: package must declare its own price")
        options = {o.field: o for o in case.options}
        for term in package.bindings:
            option = options.get(term.field)
            if option and term.value not in option.values:
                standard = next((t for t in standards.bindings if t.field == term.field), None)
                origin = origins.get(term.field)
                if not (option.allow_verified_standard and standard == term and origin and
                        origin.source_kind == "quote"):
                    raise ContractViolation("infeasible: outside-option package term")
            if term.field != "unit_price" and option is None:
                raise ContractViolation("unsupported_capability: negotiable field has no declared option domain")
            values[term.field] = term
            origins[term.field] = FieldOrigin(field=term.field, source_kind="sheet", source_refs=(
                SourceRef(record_id=f"sha256:{package.fingerprint}"),
            ))
        required = {"unit_price", "volume_per_year", "contract_months", "payment_days", "lead_time_days", "incoterm"}
        if not required.issubset(values):
            raise ContractViolation("missing_source: incomplete resolved economic terms")
        for field, option in options.items():
            if field in values and values[field].value not in option.values:
                standard = next((t for t in standards.bindings if t.field == field), None)
                source = next((o for o in standards.field_origins if o.field == field), None)
                if not (option.allow_verified_standard and standard == values[field] and source and
                        source.source_kind == "quote"):
                    raise ContractViolation("infeasible: resolved term is outside declared options")
        price = values["unit_price"].value
        bounds = context.cost_policy.price_bounds
        if basis_key(bounds.minimum.basis) != basis_key(basis):
            raise ContractViolation("unknown_basis: policy bounds do not match case")
        if context.cost_policy.tick != Decimal("0.01"):
            raise ContractViolation("unsupported_capability: contract v1 requires a cent price tick")
        if (
            not bounds.minimum.amount <= price <= bounds.maximum.amount
            or price % Decimal("0.01")
            or price % context.cost_policy.tick
        ):
            raise ContractViolation("uncertified_price: price outside policy bounds or ticks")
        resolved = ResolvedTerms(bindings=tuple(values[k] for k in sorted(values)),
                                 origins=tuple(origins[k] for k in sorted(origins)), version_hash="0" * 64)
        resolved = resolved.model_copy(update={"version_hash": _version(resolved, "origins")})
        ops = {"==": operator.eq, "!=": operator.ne, ">=": operator.ge, "<=": operator.le,
               ">": operator.gt, "<": operator.lt}
        must_ok = all(m.field in values and ops[m.op](values[m.field].value, m.value)
                      for m in case.buyer.must_haves)
        issues = list(context.issues)
        if not must_ok:
            issues.append(Issue(code="infeasible", severity="error", component="economics.official",
                                refs=(package.fingerprint,), detail="resolved terms violate buyer must-haves"))
        policy = context.scenario_policy
        if policy.mode != "disabled_explicit" and supplier_id not in policy.required_supplier_ids:
            raise ContractViolation("missing_source: evaluated supplier has no required scenario estimate")
        if len(policy.scenarios) > 1:
            raise ContractViolation("unsupported_capability: multiple scenarios do not declare a nominal estimate")
        estimates = {e.estimate_id: e for e in context.estimates}
        selected = []
        for scenario in policy.scenarios:
            e = next(estimates[i] for i in scenario.estimate_ids if estimates[i].supplier_id == supplier_id)
            if _version(e.standard, "field_origins") != e.standard.version_hash or e.standard != standards:
                raise ContractViolation("source_conflict: estimate standards differ from applicable standards")
            selected.append((scenario, e))
        assumptions = tuple(dict.fromkeys(r for _, e in selected for r in e.assumption_refs))
        fingerprint = semantic_hash({"schema_version": context.schema_version, "context": context.fingerprint,
                                     "supplier_id": supplier_id, "resolved_terms": resolved,
                                     "package_basis": package.price_basis})
        try:
            nominal = self.oracle.evaluate(case, resolved, selected[0][1] if selected else None)
            scenarios = tuple(ScenarioCost(scenario_id=s.scenario_id, estimate_id=e.estimate_id,
                                           cost=nominal.total, components=nominal.components)
                              for s, e in selected)
        except (ArithmeticError, ContractViolation) as error:
            if isinstance(error, ContractViolation) and not str(error).startswith((
                "nonfinite_cost", "official_calculation_failed",
                "unsupported_numeric_domain", "component_rounding_mismatch",
            )):
                raise
            issues.append(Issue(code="nonfinite_cost", severity="error", component="economics.official",
                                refs=(package.fingerprint,), detail=str(error)))
            return PackageEvaluation(package_fingerprint=package.fingerprint, resolved_terms=resolved,
                                     components=(), scenario_costs=(), must_haves_ok=must_ok, numerically_valid=False,
                                     basis_verified=True, assumption_refs=assumptions,
                                     economic_fingerprint=fingerprint, issues=tuple(issues))
        return PackageEvaluation(package_fingerprint=package.fingerprint, resolved_terms=resolved,
                                 nominal_cost=nominal.total, components=nominal.components, scenario_costs=scenarios,
                                 must_haves_ok=must_ok, numerically_valid=True, basis_verified=True,
                                 assumption_refs=assumptions, economic_fingerprint=fingerprint, issues=tuple(issues))
