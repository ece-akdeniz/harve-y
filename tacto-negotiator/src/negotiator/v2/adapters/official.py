"""Typed adapter to the locked arena kit; no alternative economic formulas."""

import math
from datetime import date
from decimal import Decimal

from arena_kit.cost import cost_breakdown, total_cost
from pydantic import ValidationError

from ..core.certificates import case_contract_hash
from ..core.errors import ContractViolation
from ..core.models import (
    CaseContract,
    CostComponent,
    IndexClause,
    Money,
    OfficialCostResult,
    ResolvedTerms,
    SupplierEstimate,
)


def _number(value: Decimal) -> float:
    result = float(value)
    if not math.isfinite(result) or value != 0 and result == 0:
        raise ContractViolation("unsupported_numeric_domain: decimal is outside the kit float domain")
    return result


def _term_value(value):
    if isinstance(value, Decimal):
        return _number(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, IndexClause):
        return {key: _term_value(item) for key, item in value.model_dump().items() if key != "schema_version"}
    return value


def _terms(bindings):
    return {term.field: _term_value(term.value) for term in bindings}


def _basis_key(basis):
    return basis.currency, basis.price_unit, basis.part_ids, basis.quantity_basis


class OfficialArithmetic:
    def evaluate(
        self, case: CaseContract, terms: ResolvedTerms, supplier: SupplierEstimate | None,
    ) -> OfficialCostResult:
        if not isinstance(case, CaseContract) or not isinstance(terms, ResolvedTerms):
            raise TypeError("official arithmetic requires validated case and resolved terms")
        if supplier is not None and not isinstance(supplier, SupplierEstimate):
            raise TypeError("supplier must be an explicit validated estimate or None")
        # The oracle has no package/supplier target parameter to establish a basket join.
        if len(case.parts) != 1 or len(case.supplier_ids) != 1:
            raise ContractViolation("unsupported_capability: first oracle supports one part and one supplier")
        basis = case.buyer.fallback_price.basis
        if _basis_key(case.parts[0].price_basis) != _basis_key(basis):
            raise ContractViolation("unknown_basis: case and buyer price bases disagree")
        if supplier is not None and (
            supplier.supplier_id not in case.supplier_ids or _basis_key(supplier.basis) != _basis_key(basis)
        ):
            raise ContractViolation("unknown_basis: supplier estimate must match case supplier and price basis")
        if case_contract_hash(case) != case.contract_hash:
            raise ContractViolation("invalid_schema: case contract hash does not match its inputs")
        b = case.buyer
        buyer = {name: _number(getattr(b, name)) for name in (
            "need_per_year", "horizon_years", "interest_rate", "fallback_risk_pct", "index_risk_pct",
        )}
        buyer.update(category_goal=b.category_goal, fallback_unit_price=_number(b.fallback_price.amount),
                     reference_payment_days=b.reference_payment_days, need_lead_time_days=b.need_lead_time_days,
                     late_cost_per_day=_number(b.late_cost_per_day.amount),
                     cost_per_defect=_number(b.cost_per_defect.amount),
                     freight_eur_per_unit={r.incoterm: _number(r.eur_per_unit) for r in b.freight},
                     index_paths={p.series: _number(p.delta_fraction) for p in b.index_paths})
        if b.current_price is not None:
            buyer["current_unit_price"] = _number(b.current_price.amount)
        if b.sustainable_margin_pct is not None:
            buyer["sustainable_margin_pct"] = _number(b.sustainable_margin_pct)
        if b.relationship_eur_per_point is not None:
            buyer["relationship_eur_per_point"] = _number(b.relationship_eur_per_point.amount)
        official_case = {"buyer": buyer, "fixed_terms": _terms(case.fixed_terms),
                         "term_options": {o.field: [_term_value(v) for v in o.values] for o in case.options}}
        complete = _terms(terms.bindings)
        required = {"unit_price", "volume_per_year", "contract_months", "payment_days", "lead_time_days", "incoterm"}
        if not required.issubset(complete):
            raise ContractViolation("invalid_schema: resolved economic terms must be complete")
        if any(complete.get(t.field) != _term_value(t.value) for t in case.fixed_terms):
            raise ContractViolation("invalid_schema: resolved terms disagree with fixed case terms")
        clause = complete.get("index_clause")
        if clause is not None and clause["series"] not in buyer["index_paths"]:
            raise ContractViolation("missing_source: indexed package has no declared index path")
        estimate = None
        if supplier is not None:
            estimate = {"standard": _terms(supplier.standard.bindings), "full_cost": _number(supplier.full_cost.amount),
                        "interest_rate": _number(supplier.interest_rate), "usual_rate": _number(supplier.usual_rate)}
            if not {"payment_days", "incoterm"}.issubset(estimate["standard"]):
                raise ContractViolation("invalid_schema: supplier cash-value calculation requires complete standards")
            if supplier.ppm is not None:
                estimate["ppm"] = supplier.ppm
            if supplier.extra_per_unit is not None:
                estimate["extra"] = _number(supplier.extra_per_unit)
        try:
            components = cost_breakdown(official_case, complete, supplier=estimate)
            total = total_cost(official_case, complete, supplier=estimate)
            if not math.isfinite(total) or any(not math.isfinite(value) for value in components.values()):
                raise ContractViolation("nonfinite_cost: official calculation returned a nonfinite value")
            return OfficialCostResult(
                total=Money(amount=Decimal(str(total))),
                components=tuple(CostComponent(kind=kind, amount=Money(amount=Decimal(str(value))))
                                 for kind, value in components.items()),
            )
        except (ArithmeticError, ValueError) as error:
            if isinstance(error, ContractViolation):
                raise
            reason = ("component_rounding_mismatch" if isinstance(error, ValidationError)
                      else "official_calculation_failed")
            raise ContractViolation(f"{reason}: {error}") from error
