"""Bounded, schema-driven trades. History is authoritative across restarts."""

import math
import time

from arena_kit.cost import complete_offer, must_haves_ok, total_cost
from arena_kit.play import moves_left

from .dossiers import build_one, for_case, load_package
from .evaluator import eligible_sheets, nonprice, price_for_cost
from .optimizer import best_terms, option_combinations
from .replies import interpret


def packages(case, price, standard, supplier=None):
    fields = [f for f in case["negotiable"] if f != "unit_price" and case.get("term_options", {}).get(f)]
    base = complete_offer(case, {"unit_price": price})
    out = []
    for values in option_combinations(case.get("term_options") or {}, fields):
        t = {**base, **dict(zip(fields, values, strict=True))}
        if must_haves_ok(case, t, standard):
            out.append((total_cost(case, t, standard, supplier), t))
    return sorted(out, key=lambda x: x[0])


def history(case, events):
    ours = [m["term_sheets"][0]["terms"] for m in events if m.get("from") == "buyer" and m.get("term_sheets")]
    keys = [nonprice(case, t) for t in ours]
    switches = sum(a != b for a, b in zip(keys, keys[1:], strict=False))
    return ours, keys, switches


class TradePolicy:
    def __init__(self, config, log):
        self.config, self.log = config, log
        self.traits = {}
        self.deadlines = {}

    def prepare(self, case):
        """Precompute dossiers before opening a session where the runner has case metadata."""
        for sid in case.get("suppliers", []):
            if sid in self.traits:
                continue
            try:
                d = for_case({sid: build_one(load_package(), sid)}, case)[sid]
                self.traits[sid] = set(d.traits) if d else set()
            except (OSError, ValueError, KeyError, TypeError):
                self.traits[sid] = set()

    def initial(self, case, sid, price, anchor, standard, supplier, reference=None):
        self.prepare(case)
        preference = self.config.preferences.get(case["type"], self.config.preference)
        candidates = packages(case, price * (1 - anchor), standard, supplier)
        # Record both price surfaces; do not confuse buyer value with supplier willingness.
        self.log(
            case, "package_candidates", sid, at_quote=packages(case, price, standard, supplier), at_proposed=candidates
        )
        t = dict(candidates[0][1]) if candidates else best_terms(case, price, standard, supplier)
        options = case.get("term_options", {})
        if "multi_year_only" in self.traits[sid] and "contract_months" in t:
            tenors = [m for m in options.get("contract_months", []) if m >= 12 * case["buyer"]["horizon_years"]]
            if tenors:
                t["contract_months"] = max(tenors) if preference == "longer_tenor" else min(tenors)
            if "volume_per_year" in t and (reference or {}).get("volume_per_year") is not None:
                t["volume_per_year"] = reference["volume_per_year"]
        if "ppm_commitment" in t:
            # Relax only if the buyer's formula values the package equally and the must-have holds.
            for ppm in sorted(options.get("ppm_commitment", []), reverse=True):
                trial = {**t, "ppm_commitment": ppm}
                if must_haves_ok(case, trial, standard) and total_cost(case, trial, standard, supplier) <= total_cost(
                    case, t, standard, supplier
                ):
                    t = trial
                    break
        if preference == "standard_payment" and "payment_days" in t:
            if standard.get("payment_days") in options.get("payment_days", []):
                t["payment_days"] = standard["payment_days"]
        if preference == "lower_chargeback" and "chargeback_eur_per_complaint" in t:
            lower = [
                x for x in options.get("chargeback_eur_per_complaint", []) if x < t["chargeback_eur_per_complaint"]
            ]
            if lower:
                t["chargeback_eur_per_complaint"] = sorted(lower, reverse=True)[
                    min(self.config.chargeback_steps, len(lower)) - 1
                ]
                t["ppm_commitment"] = min(options["ppm_commitment"])
        return nonprice(case, t)

    def switch(self, case, sid, events, terms, standard, supplier):
        ours, tried, switches = history(case, events)
        if switches >= 2 or moves_left(case, events) < 3 or self.deadlines.get(sid, 0) - time.time() < 20:
            return terms, None
        replies = []
        for i, m in enumerate(events):
            if m.get("from") != "buyer" and m.get("term_sheets"):
                sheets = eligible_sheets(case, events[: i + 1], supplier, alternatives=True)
                if sheets:
                    replies.append(sheets[0][0])
        if len(replies) < 3 or replies[-1] < replies[-2] - 0.01 or replies[-2] < replies[-3] - 0.01:
            return terms, None
        options = case.get("term_options", {})
        # Only explore dimensions with a concrete case/supplier signal.
        fields = []
        signals = {s["kind"] for s in interpret(events)["signals"]}
        if "payment_days" in terms and (
            "wants_fast_payment" in self.traits.get(sid, set()) or "payment_trade" in signals
        ):
            fields.append("payment_days")
        if "contract_months" in terms:
            fields.append("contract_months")
        if "ppm_commitment" in terms:
            fields += ["chargeback_eur_per_complaint", "ppm_commitment"]
        if "index_clause" in terms:
            fields.append("index_clause")
        target = total_cost(case, terms, standard, supplier)
        for field in fields:
            values = list(options.get(field, []))
            if field == "payment_days":
                values = sorted((x for x in values if x < terms[field]), reverse=True)
            if field in ("contract_months", "ppm_commitment"):
                values = sorted(x for x in values if x > terms[field])
            if field == "chargeback_eur_per_complaint":
                values = sorted((x for x in values if x < terms[field]), reverse=True)
            for v in values:
                trial = {**terms, field: v}
                if v == terms.get(field) or nonprice(case, trial) in tried or not must_haves_ok(case, trial, standard):
                    continue
                if supplier:
                    continue  # inverse-price search is not monotonic with relationship estimates
                trial["unit_price"] = math.floor(price_for_cost(case, trial, target, standard) * 100) / 100
                if trial["unit_price"] <= 0 or total_cost(case, trial, standard) > target + 0.01:
                    continue
                self.log(
                    case,
                    "package_trade",
                    sid,
                    previous=terms,
                    selected=trial,
                    target_c=target,
                    selected_c=total_cost(case, trial, standard),
                    switches=switches + 1,
                )
                return complete_offer(case, trial), f"conditional trade: {field}"
        return terms, None
