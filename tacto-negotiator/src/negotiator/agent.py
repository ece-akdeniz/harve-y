"""v0.2 buyer: complete-cost packages, a price concession schedule and one checked close.

Every accept and walk-away goes through `evaluator.close_decision` (eligible sheets first, then
C with supplier estimates, against the alternative). Our non-price terms stay as offered unless a
supplier package evaluated by C is cheaper than its price for ours. No claims and no model yet.
"""

import logging
import math
import os
import time

from arena_kit.cost import closing_terms, complete_offer, must_haves_ok, total_cost
from arena_kit.docs import standard_terms
from arena_kit.play import latest, live_threads, moves_left

from .evaluator import (
    best_close,
    close_decision,
    eligible_sheets,
    nonprice,
    price_for_cost,
    revealed_deltas,
    same_package,
    supplier_for,
)
from .guards import leaks
from .memory import validate_memory
from .memory_policy import prefer_package
from .optimizer import alternative_cost, best_terms

log = logging.getLogger("negotiator")


def standing(case, events, supplier=None):
    """(term_sheet_id, terms) of the cheapest eligible sheet in the supplier's latest message, else
    of its cheapest priced sheet, else (None, {})."""
    cands = eligible_sheets(case, events, supplier, alternatives=True) or _priced(case, events, supplier)
    if cands:
        return cands[0][1], cands[0][2]
    sheets = latest(events).get("term_sheets") or [] if events else []
    return (sheets[0]["term_sheet_id"], sheets[0]["terms"]) if sheets else (None, {})


def _priced(case, events, supplier=None):
    """[(C, sheet_id, terms)] of every priced sheet in the latest message, must-haves ignored."""
    std = standard_terms(events)
    out = []
    for s in latest(events).get("term_sheets") or []:
        c = total_cost(case, s.get("terms") or {}, std, supplier)
        if s.get("term_sheet_id") and math.isfinite(c):
            out.append((c, s["term_sheet_id"], s["terms"]))
    return sorted(out, key=lambda x: (x[0], x[1]))


def load_estimates(case):
    """{supplier_id: estimate} from `dossiers.supplier_estimate` once it exists, else {}."""
    try:
        from .dossiers import supplier_estimate
    except ImportError:
        return {}
    out = {}
    for sid in case.get("suppliers", []):
        try:
            est = supplier_estimate(case, sid)
        except NotImplementedError:
            return {}
        except Exception:
            log.exception("supplier estimate for %s failed; using none", sid)
            continue
        if est:
            out[sid] = est
    return out


def _ceil2(x):
    return math.ceil(round(x * 100, 6)) / 100


class PackageAgent:
    version = "PackageAgent-v0.2"

    def __init__(
        self,
        anchor=0.12,
        rounds=5,
        close_gap=0.005,
        tracer=None,
        estimates=None,
        final_hold_s=40.0,
        meso=None,
        p_walk=0.25,
        claims=None,
        policy=None,
        model_assist=False,
        model_provider=None,
        model_name=None,
        memory=None,
    ):
        self.anchor, self.rounds, self.close_gap, self.tracer = anchor, rounds, close_gap, tracer
        if isinstance(policy, dict):
            from .policy import PolicyConfig

            policy = PolicyConfig.from_dict(policy)
        self.policy = policy
        self.package_advisor, self.package_notes = None, {}
        if policy and policy.package_advice_types:
            from .package_advisor import PackageAdvisor

            self.package_advisor = PackageAdvisor()
        self.memory = validate_memory(memory) if memory is not None else None
        self._memory_seen = set()
        self.conditional_exchange = False
        self.trades = None
        if policy:
            from .trades import TradePolicy

            self.trades = TradePolicy(policy, self._log)
        self.meso = os.environ.get("NEGOTIATOR_MESO") == "1" if meso is None else meso
        self.final_hold_s = final_hold_s
        self.p_walk = p_walk  # chance a supplier walks when its final offer is countered (D02: 2 of 9)
        self.claims = os.environ.get("NEGOTIATOR_CLAIMS") == "1" if claims is None else claims
        if policy is not None:
            self.claims = bool(policy.evidence_types)
        self.evidence = None
        self.model_context = {}
        self.model_seen = {}
        self.model_assist = None
        if model_assist:
            from .model_assist import ModelAssist

            self.model_assist = model_assist if isinstance(model_assist, ModelAssist) else ModelAssist(
                memory_path=os.environ.get("NEGOTIATOR_APPROVED_MEMORY"),
                data_sha256=os.environ.get("NEGOTIATOR_DATA_SHA256"),
                provider=model_provider, model=model_name,
            )
        if self.claims:
            from .evidence import EvidencePolicy

            self.evidence = EvidencePolicy(tracer=tracer, case_types=policy.evidence_types if policy else None,
                                           interpretation=self.model_context)
        self.prev = {}  # supplier -> non-price terms of our last offer
        self.final_counters = {}  # supplier -> counters sent to its final offers (at most one)
        self.beat_asked = {}  # rival supplier -> final-offer sheet id we asked it to beat
        self.final_seen = {}  # final-offer sheet id -> monotonic time first seen
        if estimates is None and os.environ.get("NEGOTIATOR_ESTIMATES") != "1":
            estimates = {}  # dossier estimates are opt-in until calibrated (docs: experiments/LOG.md)
        self._estimates, self._est_case, self._est_cache = estimates, None, {}
        self._target_cache = {}

    def prepare_email(self, case, threads, sid):
        """Read each supplier message once; the async runner calls this outside its lock."""
        if self.model_assist is None:
            return
        events = threads.get(sid, [])
        latest_supplier = next(((i, e) for i, e in reversed(list(enumerate(events)))
                                if e.get("from") != "buyer"), None)
        if latest_supplier is None:
            return
        from .ingestion import fingerprint

        token = (latest_supplier[0], fingerprint(latest_supplier[1]))
        if self.model_seen.get(sid) == token:
            return
        try:
            result = self.model_assist.read(case, events, sid)
        except Exception:
            from .replies import interpret

            result = {**interpret(events), "terms": [], "questions": [], "lessons": [], "source": "rules"}
        self.model_context[sid] = result
        self.model_seen[sid] = token
        self._log(case, "model_interpretation", sid, interpretation=result)

    def experiment_metrics(self):
        return {"model": self.model_assist.metrics() if self.model_assist is not None else
                {"calls": 0, "fallbacks": 0, "latency_s": [], "input_tokens": 0, "output_tokens": 0},
                "memory_snapshot_id": self.memory["snapshot_id"] if self.memory else None}

    # -- estimates ----------------------------------------------------------------------------
    def estimates_for(self, case):
        """{supplier_id: estimate}: the injected estimates, else `dossiers.supplier_estimate`
        (with NEGOTIATOR_ESTIMATES=1)."""
        if self._estimates is not None:
            return self._estimates
        if self._est_case != case["case_id"]:
            self._est_case, self._est_cache = case["case_id"], load_estimates(case)
        return self._est_cache

    def _sup(self, case, threads, sid):
        return supplier_for(self.estimates_for(case), sid, standard_terms(threads[sid]))

    # -- helpers ------------------------------------------------------------------------------
    @staticmethod
    def _ours(events):
        return [m["term_sheets"][0]["terms"] for m in events if m.get("from") == "buyer" and m.get("term_sheets")]

    def _log(self, case, kind, sid, **fields):
        if self.tracer:
            self.tracer.log("decision", case=case["case_id"], kind=kind, supplier=sid, **fields)

    def log_close(self, case, threads, decision, reason):
        best = best_close(case, threads, self.estimates_for(case))
        action = decision["message"]["action"]
        fields = {"c_alt": alternative_cost(case), "reason": reason}
        if action["type"] == "accept" and best:
            fields.update(c=best[0], sheet=action["term_sheet_id"])
        self._log(case, action["type"], decision["supplier_id"], **fields)

    def _close(self, case, threads, reason):
        decision = close_decision(case, threads, self.estimates_for(case), reason)
        self.log_close(case, threads, decision, reason)
        return decision

    def _offer(self, case, sid, terms, std, sup, c_alt, reason, variants=()):
        body = (
            f"Thank you for your offer. To go ahead we propose the attached terms: "
            f"unit price EUR {terms['unit_price']:.2f}"
            + "".join(f", {k.replace('_', ' ')} {v}" for k, v in terms.items() if k != "unit_price")
            + ". We look forward to your confirmation."
        )
        if self.trades and case["type"] in self.policy.package_types:
            if "contract_months" in terms:
                body += (
                    f" We offer a {terms['contract_months']}-month commitment"
                    + (
                        f" at annual volume {terms['volume_per_year']};"
                        if "volume_per_year" in terms
                        else " at unchanged annual volume;"
                    )
                    + " please reflect that commitment in your price, with payment priced as part of the package."
                )
            if "ppm_commitment" in terms:
                body += (
                    f" We can accept the proposed future quality commitment of {terms['ppm_commitment']} ppm"
                    " in exchange for the proposed price and chargeback terms."
                )
            body += (
                " This is a conditional exchange: we can commit to this package in return for the proposed unit price."
            )
        elif self.conditional_exchange and any(k != "unit_price" for k in terms):
            body += " The proposed non-price terms are conditional on the proposed unit price as one package."
        context = self.model_context.get(sid, {})
        signals = [x for x in context.get("signals", [])
                   if x.get("message_index") == self.model_seen.get(sid, (-1,))[0]]
        latest_signal = next(
            (x for x in reversed(signals) if x.get("kind") in
             {"payment_trade", "quality_objection", "delivery_constraint", "capacity_constraint"}),
            None,
        )
        if latest_signal:
            body += {
                "payment_trade": " We can consider payment terms as part of the full package.",
                "quality_objection": " We can discuss the quality requirements as part of this package.",
                "delivery_constraint": " Please clarify which delivery requirement is difficult to meet.",
                "capacity_constraint": " Please clarify the capacity you can commit to.",
            }[latest_signal["kind"]]
        if any(v.get("index_clause") != terms.get("index_clause") for v in variants):
            body += " Alternatively, please consider the attached packages; each is a separate proposal."
        assert not leaks(body), "body would leak internal information"
        self.prev[sid] = {k: v for k, v in terms.items() if k != "unit_price"}
        c = total_cost(case, terms, std, sup)
        sheets = [{"terms": t} for t in [terms, *variants][:3]]
        self._log(case, "offer", sid, terms=terms, c=c, c_alt=c_alt, reason=reason, variants=list(variants) or None)
        return {
            "supplier_id": sid,
            "message": {"subject": case["title"], "body": body, "term_sheets": sheets},
        }

    def _payment_variants(self, case, terms, theirs, std, sup):
        """Up to two sheets at our main sheet's C that differ only in payment days (the supplier's
        and the fastest option): the supplier picks the mix it values."""
        options = (case.get("term_options") or {}).get("payment_days") or []
        if "payment_days" not in terms or not options:
            return []
        c_main = total_cost(case, terms, std, sup)
        out = []
        for pay in (theirs.get("payment_days"), min(options)):
            if pay is None or pay == terms["payment_days"] or pay in [v["payment_days"] for v in out]:
                continue
            v = {**terms, "payment_days": pay}
            v["unit_price"] = math.floor(price_for_cost(case, v, c_main, std, sup) * 100) / 100
            if must_haves_ok(case, v, std):
                out.append(complete_offer(case, v))
        return out

    def _clause_on(self, case):
        return bool(self.policy and case["type"] in self.policy.clause_variant_types)

    @staticmethod
    def _clause_probed(events):
        """True once one of our messages carried sheets that differ in index_clause."""
        for m in events:
            if m.get("from") == "buyer" and len(m.get("term_sheets") or []) > 1:
                if len({repr(s["terms"].get("index_clause")) for s in m["term_sheets"]}) > 1:
                    return True
        return False

    def _clause_track(self, case, sid, events, prev, ref_terms):
        """Locked previous terms, except for the index clause when clause variants are enabled:
        a mandatory clause (we offered none; every latest supplier sheet carries one) adopts the
        supplier's clause, and after our deadband probe the cheapest supplier sheet's (by C)
        clause is adopted. Never insists on no clause."""
        if not self._clause_on(case) or "index_clause" not in prev:
            return prev
        sheets = latest(events).get("term_sheets") or []
        clause = ref_terms.get("index_clause")
        if clause is None or clause not in (case.get("term_options") or {}).get("index_clause", []):
            return prev
        mandatory = prev["index_clause"] is None and sheets and all(s["terms"].get("index_clause") for s in sheets)
        if (mandatory or self._clause_probed(events)) and clause != prev["index_clause"]:
            self._log(case, "clause_track", sid, prev=prev["index_clause"], new=clause, mandatory=bool(mandatory))
            return {**prev, "index_clause": clause}
        return prev

    def _clause_variants(self, case, events, terms, std, sup):
        """Once, after the supplier made the clause mandatory: up to two sheets at our main sheet's
        C that differ only in deadband (legal options of the same series), so the supplier reveals
        which deadband it prices cheaper."""
        clause = terms.get("index_clause")
        if not self._clause_on(case) or not clause or self._clause_probed(events):
            return []
        options = [
            o for o in (case.get("term_options") or {}).get("index_clause") or []
            if o and o.get("series") == clause.get("series") and o != clause
        ]
        c_main = total_cost(case, terms, std, sup)
        out = []
        for o in sorted(options, key=lambda o: -o.get("deadband_pct", 0))[:2]:
            v = {**terms, "index_clause": o}
            v["unit_price"] = math.floor(price_for_cost(case, v, c_main, std, sup) * 100) / 100
            if v["unit_price"] > 0 and must_haves_ok(case, v, std):
                out.append(complete_offer(case, v))
        return out

    def _key(self, case, threads, sid):
        sheets = eligible_sheets(case, threads[sid], self._sup(case, threads, sid))
        return (len(self._ours(threads[sid])), sheets[0][0] if sheets else math.inf)

    # -- packages -----------------------------------------------------------------------------
    def _nonprice(self, case, sid, events, std, sup, cands, eligible):
        """Our non-price terms: the previous ones, unless a supplier package (by C) is cheaper
        than the supplier's own price for ours. First offer: cheapest terms at its best price.
        Values the supplier asks for that cost us nothing at the same price are adopted."""
        ref_c, _, ref_terms = cands[0]
        prev = self.prev.get(sid)
        if self.trades and case["type"] in self.policy.package_types:
            if prev is not None:
                return self._clause_track(case, sid, events, prev, ref_terms)
            return self.trades.initial(case, sid, ref_terms["unit_price"], self.anchor, std, sup, reference=ref_terms)
        if prev is None:
            n = nonprice(case, best_terms(
                case, ref_terms["unit_price"], std, sup,
                prefer_longer_lead=bool(self.policy and self.policy.cost_neutral_lead_time),
            ))
            pay_options = (case.get("term_options") or {}).get("payment_days") or []
            if (self._standard_payment(case) and "payment_days" in n and std.get("payment_days") in pay_options
                    and must_haves_ok(case, {**ref_terms, **n, "payment_days": std["payment_days"]}, std)):
                n["payment_days"] = std["payment_days"]
        elif not eligible:
            return prev
        else:
            n = prev
            on_prev = [c for c, _, t in cands if same_package(case, {**prev, "unit_price": 0}, t, std)]
            if on_prev and min(on_prev) > ref_c + 1e-6:
                new = nonprice(case, complete_offer(case, closing_terms(case, ref_terms, std)))
                if (self._standard_payment(case) and "payment_days" in new
                        and prev.get("payment_days") == std.get("payment_days")):
                    new["payment_days"] = prev["payment_days"]
                n = new
                self._log(case, "package_switch", sid, prev=prev, new=n, c_prev=min(on_prev), c_new=ref_c)
        n = self._free_concessions(case, n, ref_terms, std, sup) if eligible else n
        identity = (case['case_id'], sid)
        if prev is None and not self._ours(events) and identity not in self._memory_seen:
            self._memory_seen.add(identity)
            n, trace = prefer_package(case, n, ref_terms['unit_price'], std, sup, memory=self.memory)
            if trace:
                self._log(case, 'memory_package', sid, **trace)
        return n

    def _standard_payment(self, case):
        return bool(self.policy and case["type"] in self.policy.standard_payment_types)

    def _free_concessions(self, case, n, theirs, std, sup):
        price = theirs["unit_price"]
        for f, v in theirs.items():
            if f == "unit_price" or f not in n or v is None or n[f] == v:
                continue
            trial = {**n, f: v}
            if not must_haves_ok(case, {**trial, "unit_price": price}, std):
                continue
            trial_c = total_cost(case, {**trial, "unit_price": price}, std, sup)
            previous_c = total_cost(case, {**n, "unit_price": price}, std, sup)
            if (self.policy and case['type'] in self.policy.package_advice_types and f == "contract_months"
                    and v < n[f] and trial_c == previous_c):
                continue
            if f == "payment_days" and self._standard_payment(case) and n[f] == std.get("payment_days"):
                continue
            if trial_c <= previous_c + 1e-6:
                n = trial
        return n

    def _ask_on(self, case, n, cands, std, sup):
        """The supplier's price for non-price terms `n`: its sheet on `n`, else the nominal price of
        its cheapest package (an unpriced combined difference) - never above the price at which `n`
        costs as much as that package."""
        on_n = [t["unit_price"] for _, _, t in cands if same_package(case, {**n, "unit_price": 0}, t, std)]
        nominal = min(on_n) if on_n else cands[0][2]["unit_price"]
        equal_c = price_for_cost(case, {**n, "unit_price": nominal}, cands[0][0], std, sup)
        return round(min(nominal, equal_c), 2)

    # -- expected-cost target (opt-in: policy.cost_target_types) --------------------------------
    def _target_supplier(self, case, sid, std):
        """Public dossier estimate for the relationship term, standard terms from the quote."""
        key = (case["case_id"], sid)
        if key not in self._target_cache:
            try:
                from .dossiers import supplier_estimate

                est = supplier_estimate(case, sid)
            except Exception:
                log.exception("cost target estimate for %s failed; flag inactive", sid)
                est = None
            self._target_cache[key] = est
        est = self._target_cache[key]
        return {**est, "standard": {**(est.get("standard") or {}), **(std or {})}} if est else None

    def _cost_target_move(self, case, threads):
        """Single-supplier relationship cases only; None falls back to the default policy."""
        from . import cost_target as ct

        live = live_threads(threads)
        if len(case.get("suppliers", [])) != 1 or len(live) != 1:
            return None
        sid = live[0]
        events = threads[sid]
        msg = latest(events)
        status = msg.get("status")
        if status not in ("open", "final_offer"):
            return None
        std = standard_terms(events)
        sup = self._target_supplier(case, sid, std)
        if not ct.active(case, sup):
            return None
        key = ("target", case["case_id"], sid)
        if key not in self._target_cache:
            self._target_cache[key] = ct.target(case, std, sup, index_clause=self.policy.cost_target_index_clause)
        tgt = self._target_cache[key]
        if tgt is None:
            return None
        tc, tterms = tgt
        grid = ct.scenarios(sup)

        def ec(t):
            return ct.expected_cost(case, t, std, sup, grid)

        sheets = [
            (ec(s["terms"]), s["term_sheet_id"], s["terms"])
            for s in msg.get("term_sheets") or []
            if s.get("term_sheet_id") and (s.get("terms") or {}).get("unit_price") is not None
            and must_haves_ok(case, s["terms"], std)
        ]
        if not sheets:
            return None
        c_alt = alternative_cost(case)
        ours = self._ours(events)
        left = moves_left(case, events)
        standing_c, standing_id, standing_terms = sheets[0]
        mark = min(tc, ec(ours[-1])) if ours else tc
        accept = {"supplier_id": sid, "message": {"action": {"type": "accept", "term_sheet_id": standing_id}}}
        walk = {"supplier_id": sid, "message": {"action": {"type": "walk_away"}}}

        def close(reason):
            self._log(case, "cost_target_close", sid, c=standing_c, target_c=tc, c_alt=c_alt, reason=reason)
            return accept if standing_c < c_alt else walk

        on_ours = same_package(case, standing_terms, ours[-1] if ours else tterms, std)
        if on_ours and standing_c <= mark + 1.0:
            return close("standing sheet meets our offer by expected C")
        if status == "final_offer" or left <= 1:
            countered, seen_final = 0, False
            for e in events:
                seen_final = seen_final or (e.get("from") != "buyer" and e.get("status") == "final_offer")
                countered += bool(seen_final and e.get("from") == "buyer" and e.get("term_sheets"))
            if status == "final_offer" and left > 1 and countered < 1:
                return self._target_offer(case, sid, tterms, std, sup, c_alt, tc, "final offer: one counter at target")
            return close("final offer or last move")
        on_target = [t["unit_price"] for _, _, t in sheets if same_package(case, {**tterms, "unit_price": 0}, t, std)]
        ask = min(on_target) if on_target else None
        tp = tterms["unit_price"]
        if ask is None or ask <= tp:
            return self._target_offer(case, sid, tterms, std, sup, c_alt, tc, "expected-C target package")
        price = tp + (ask - tp) * min(1.0, len(ours) / self.rounds)
        if ours and same_package(case, ours[-1], tterms, std):
            price = max(price, ours[-1]["unit_price"])
        cap = ct.ceiling(case, tterms, min(standing_c, c_alt), std, sup)
        if cap is not None:
            price = min(price, cap)
        terms = {**tterms, "unit_price": round(min(price, ask), 2)}
        return self._target_offer(case, sid, terms, std, sup, c_alt, ec(terms), "expected-C concession")

    def _target_offer(self, case, sid, terms, std, sup, c_alt, expected_c, reason):
        self._log(case, "cost_target", sid, terms=terms, expected_c=expected_c, reason=reason)
        move = self._offer(case, sid, complete_offer(case, terms), std, sup, c_alt, reason)
        if terms.get("index_clause"):
            move["message"]["body"] += (
                " We propose this risk-sharing package, including the index clause,"
                " in exchange for the attached unit price."
            )
        return move

    # -- policy -------------------------------------------------------------------------------
    def _workable(self, case, threads):
        live = live_threads(threads)
        status = {sid: latest(threads[sid]).get("status") for sid in live}
        workable = [s for s in live if status[s] in ("open", "final_offer") and moves_left(case, threads[s]) > 1]
        return status, workable

    def decide(self, case, threads):
        """Serial wrapper: final-offer threads first, then the least-worked open thread; the first
        proposal that is not a hold is sent, and a close request is resolved by the evaluator."""
        if self.policy and case["type"] in self.policy.cost_target_types:
            move = self._cost_target_move(case, threads)
            if move is not None:
                return move
        status, workable = self._workable(case, threads)
        order = sorted(workable, key=lambda s: (status[s] != "final_offer", self._key(case, threads, s)))
        reason = "no moves left"
        for sid in order or live_threads(threads)[:1]:
            move = self.propose(case, threads, sid)
            if move.get("close"):
                return self._close(case, threads, move.get("reason", ""))
            if not move.get("hold"):
                if self.package_advisor and case['type'] in self.policy.package_advice_types:
                    from .context import DATA_ERRORS
                    from .dossiers import build_one, load_package

                    if sid not in self.package_notes:
                        try:
                            dossier = build_one(load_package(), sid)
                            self.package_notes[sid] = list(reversed(dossier.notes))[:12] if dossier else []
                        except DATA_ERRORS:
                            self.package_notes[sid] = []
                    remaining = self.trades.deadlines.get(sid, 0) - time.time()
                    original = move['message']['term_sheets'][0]['terms']
                    move, advice = self.package_advisor.select(
                        case, threads, move, supplier=self._sup(case, threads, sid),
                        public_notes=self.package_notes[sid], remaining_s=remaining,
                    )
                    selected = move['message']['term_sheets'][0]['terms']
                    self.prev[sid] = nonprice(case, selected)
                    self._log(case, 'package_advice', sid, **advice, original=original, selected=selected)
                return move
            reason = move.get("reason", reason)
        return self._close(case, threads, reason)

    def propose(self, case, threads, supplier_id):
        if supplier_id not in self.model_seen:
            self.prepare_email(case, threads, supplier_id)
        if self.policy:
            ours = self._ours(threads[supplier_id])
            if ours:
                self.prev[supplier_id] = nonprice(case, ours[-1])
            # Rebuild the final-counter budget from actual buyer history after restart.
            saw_final, count = False, 0
            for event in threads[supplier_id]:
                if event.get("from") != "buyer" and event.get("status") == "final_offer":
                    saw_final = True
                if saw_final and event.get("from") == "buyer" and event.get("term_sheets"):
                    count += 1
            self.final_counters[supplier_id] = count
        move = self._propose(case, threads, supplier_id)
        if self.evidence and self.evidence.eligible(case, move):
            from .context import DATA_ERRORS

            try:
                context = self.evidence.context_for(case)
            except DATA_ERRORS as exc:
                self.evidence.fallback(case, exc)
                return move
            return self.evidence.enrich(case, threads, supplier_id, move, context=context)
        return move

    def _propose(self, case, threads, supplier_id):
        """The proposal for one thread given the whole snapshot: an offer move
        ({"supplier_id", "message"}), {"close": True, "reason"} for the coordinator to resolve with
        `evaluator.close_decision`, or {"hold": True, "reason"} when this thread should wait.
        Records what it proposes (our last terms, counters to final offers) as if it is sent."""
        c_alt = alternative_cost(case)
        status, workable = self._workable(case, threads)
        if any(s == "agreed" for s in status.values()):
            return {"close": True, "reason": "supplier agreed"}
        if not workable:
            return {"close": True, "reason": "no moves left"}
        if supplier_id not in workable:
            return {"hold": True, "reason": "thread not workable"}

        now = time.monotonic()
        finals = [s for s in workable if status[s] == "final_offer"]
        opens = [s for s in workable if status[s] == "open"]
        for sid in finals:
            for sheet in latest(threads[sid]).get("term_sheets") or []:
                self.final_seen.setdefault(sheet.get("term_sheet_id"), now)
        best = best_close(case, threads, self.estimates_for(case)) if finals else None
        leading_final = best is not None and best[1] in finals

        if leading_final and self.policy and self.policy.rfq_final_guard and case["type"] == "rfq":
            # A rival HTTP call can outlast the held offer's 60s response window.
            return {"close": True, "reason": "preserve leading final offer before blocking rival call"}

        if supplier_id in finals:
            counter = self._final_counter(case, threads, supplier_id, c_alt)
            if counter:
                return counter
            if not opens:
                return {"close": True, "reason": "all final offers"}
            if leading_final and now - self.final_seen.get(best[2], now) > self.final_hold_s:
                return {"close": True, "reason": "final offer held too long"}
            return {"hold": True, "reason": "final offer stands; rival still open"}

        if leading_final:
            if now - self.final_seen.get(best[2], now) > self.final_hold_s:
                return {"close": True, "reason": "final offer held too long"}
            if self.beat_asked.get(supplier_id) == best[2]:
                return {"close": True, "reason": "rival did not beat the final offer"}
            self.beat_asked[supplier_id] = best[2]
            return self.decide_thread(case, threads, supplier_id, c_alt, cap_c=best[0], why="beat final offer")
        return self.decide_thread(case, threads, supplier_id, c_alt)

    def _final_counter(self, case, threads, sid, c_alt):
        """At most one counter to a supplier's final offers: its price on our cheaper terms when the
        offer leads, or a package at the alternative's C when the offer does not beat it."""
        if self.final_counters.get(sid, 0) >= 1:
            return None
        events, std, sup = threads[sid], standard_terms(threads[sid]), self._sup(case, threads, sid)
        cands = eligible_sheets(case, events, sup)
        if not cands:
            alts = eligible_sheets(case, events, sup, alternatives=True)
            best = best_close(case, threads, self.estimates_for(case))
            if alts and alts[0][0] < min(c_alt, best[0] if best else math.inf):
                self.final_counters[sid] = self.final_counters.get(sid, 0) + 1
                reason = "final offer breaks a must-have: take its valid alternative"
                return self._offer(case, sid, complete_offer(case, alts[0][2]), std, sup, c_alt, reason)
            return None
        c_f, _, terms_f = cands[0]
        n = self.prev.get(sid) or nonprice(case, best_terms(case, terms_f["unit_price"], std, sup))
        best = best_close(case, threads, self.estimates_for(case))
        alts = [x for x in eligible_sheets(case, events, sup, alternatives=True) if x[1] != cands[0][1]]
        if best is None and alts and alts[0][0] < c_alt:
            terms, reason = complete_offer(case, alts[0][2]), "final offer above alternative: take its alternative"
        elif best is None:
            if not math.isfinite(c_alt):
                return None
            price = price_for_cost(case, {**n, "unit_price": terms_f["unit_price"]}, c_alt * 0.998, std, sup)
            price = math.floor(price * 100) / 100
            terms, reason = {**n, "unit_price": price}, "final offer above alternative: one counter"
        elif (
            best[1] == sid
            and not math.isfinite(c_alt)
            and self.policy
            and self.policy.final_offer_risk == "opening_proxy"
        ):
            if not alts or alts[0][0] >= c_f:
                return None
            opening = []
            for events_ in threads.values():
                for i, event in enumerate(events_):
                    if event.get("from") != "buyer" and event.get("term_sheets"):
                        opening += [x[0] for x in eligible_sheets(case, events_[: i + 1], alternatives=True)]
                        break
            if not opening:
                self._log(case, "final_proxy_unavailable", sid,
                          reason="no must-have-compliant opening; retain standing offer")
                return None
            c_open = min(opening)
            gain = max(0, c_open - alts[0][0]) - max(0, c_open - c_f)
            loss = max(0, c_open - c_f)
            values = {str(p): (1 - p) * gain - p * loss for p in (0.1, self.p_walk, 0.5)}
            self._log(
                case,
                "final_proxy",
                sid,
                gain=gain,
                loss=loss,
                p_walk=self.p_walk,
                sensitivity=values,
                interpretation="opening-relative proxy, not expected normalized score",
            )
            if values[str(self.p_walk)] <= 0:
                return None
            terms, reason = complete_offer(case, alts[0][2]), "final offer: own alternative, positive opening proxy"
        elif best[1] == sid:
            terms, reason = {**n, "unit_price": terms_f["unit_price"]}, "final offer: same price, our terms"
            c_alt_sheet, alt_id, alt_terms = eligible_sheets(case, events, sup, alternatives=True)[0]
            if alt_id != cands[0][1] and c_alt_sheet < total_cost(case, terms, std, sup):
                terms, reason = complete_offer(case, alt_terms), "final offer: its own cheaper alternative"
            gain = c_f - total_cost(case, terms, std, sup)
            rivals = [
                c
                for s in live_threads(threads)
                if s != sid
                for c, _, _ in eligible_sheets(case, threads[s], self._sup(case, threads, s))[:1]
            ]
            loss = min([c_alt, *rivals]) - c_f  # if the supplier walks, we fall back to this
            if gain <= 1e-6 or gain * (1 - self.p_walk) <= loss * self.p_walk:
                self._log(case, "final_accept_safe", sid, gain=gain, loss=loss, p_walk=self.p_walk)
                return None
        else:
            return None
        ours = self._ours(events)
        if ours and ours[-1] == terms:
            return None
        self.final_counters[sid] = self.final_counters.get(sid, 0) + 1
        return self._offer(case, sid, complete_offer(case, terms), std, sup, c_alt, reason)

    def decide_thread(self, case, threads, sid, c_alt, cap_c=None, why=None):
        events = threads[sid]
        std, sup = standard_terms(events), self._sup(case, threads, sid)
        cands = eligible_sheets(case, events, sup, alternatives=True)
        eligible = bool(cands)
        cands = cands or _priced(case, events, sup)
        if not cands:
            return {"close": True, "reason": "no price quoted"}
        standing_id = ((latest(events).get("term_sheets") or [{}])[0]).get("term_sheet_id")
        if deltas := revealed_deltas(case, latest(events).get("term_sheets") or [], std):
            self._log(case, "revealed", sid, deltas=deltas)

        ref_c = cands[0][0]
        n = self._nonprice(case, sid, events, std, sup, cands, eligible)
        p = self._ask_on(case, n, cands, std, sup)
        first = next((i for i, m in enumerate(events) if m.get("from") != "buyer" and m.get("term_sheets")), None)
        p_open = p
        if first is not None:
            first_events = events[: first + 1]
            open_cands = eligible_sheets(case, first_events, sup, alternatives=True) or _priced(case, first_events, sup)
            if open_cands:
                p_open = self._ask_on(case, n, open_cands, std, sup)

        ours = self._ours(events)
        k = len(ours)
        last_c = total_cost(case, ours[-1], std, sup) if ours else None
        last_p = price_for_cost(case, {**n, "unit_price": p}, last_c, std, sup) if last_c is not None else None

        if last_p is not None and p - last_p <= p * self.close_gap and cap_c is None:
            match = {**n, "unit_price": p}
            if total_cost(case, match, std, sup) < ref_c - 1e-6 and ours[-1] != match:
                return self._offer(case, sid, match, std, sup, c_alt, "gap closed: their price, our terms")
            if eligible and cands[0][1] != standing_id and complete_offer(case, cands[0][2]) != ours[-1]:
                # only the standing sheet can be accepted: counter with the cheaper alternative
                alt = complete_offer(case, cands[0][2])
                return self._offer(case, sid, alt, std, sup, c_alt, "gap closed: take alternative")
            if self.policy and self.policy.rfq_nonleading_hold and case["type"] == "rfq":
                best = best_close(case, threads, self.estimates_for(case))
                if (best and best[1] != sid and latest(threads[best[1]]).get("status") == "open"
                        and moves_left(case, threads[best[1]]) > 1):
                    # A losing rival converging must not end the case while the leader is workable;
                    # letting the loser's window lapse is cheaper than closing on its sheet.
                    self._log(case, "nonleading_convergence", sid, leading_supplier=best[1], leading_cost=best[0])
                    return {"hold": True, "reason": "nonleading supplier converged; leader still workable"}
            return {"close": True, "reason": "gap closed"}

        floor = p_open * (1 - self.anchor)
        price = floor + (p - floor) * min(1.0, k / self.rounds)
        if last_p is not None:
            price = max(price, _ceil2(last_p))  # no backtracking on our own concessions (by C)
        price = min(price, p)
        if cap_c is not None:
            cap_p = math.floor(price_for_cost(case, {**n, "unit_price": p}, cap_c, std, sup) * 100) / 100 - 0.01
            if last_p is not None and cap_p < last_p - 1e-6:
                return {"close": True, "reason": "rival cannot beat the final offer without backtracking"}
            price = min(price, cap_p)
        terms = complete_offer(case, {**n, "unit_price": round(price, 2)})
        if self.trades and case["type"] in self.policy.package_types:
            terms, trade_reason = self.trades.switch(case, sid, events, terms, std, sup)
            why = trade_reason or why
        payment_requested = any(
            signal.get("kind") == "payment_trade"
            and signal.get("message_index") == self.model_seen.get(sid, (-1,))[0]
            for signal in self.model_context.get(sid, {}).get("signals", [])
        )
        variants = self._payment_variants(case, terms, cands[0][2], std, sup) if self.meso or payment_requested else []
        if not variants and cap_c is None:
            variants = self._clause_variants(case, events, terms, std, sup)
            if variants:
                why = why or "deadband probe at equal cost"
        return self._offer(case, sid, terms, std, sup, c_alt, why or f"round {k + 1} schedule", variants)


def configured_agent(policy_config, trace_dir=None, **kwargs):
    """Lab factory `negotiator.agent:configured_agent`: JSON policy dict -> validated PackageAgent.

    Keeps the full policy in the lab run manifest (the plain `package` factory cannot take a
    PolicyConfig from JSON). `trace_dir` creates a Tracer there; other kwargs pass through.
    """
    from .policy import PolicyConfig

    if trace_dir is not None:
        from pathlib import Path

        from .trace import Tracer

        kwargs["tracer"] = Tracer(Path(trace_dir))
    return PackageAgent(policy=PolicyConfig.from_dict(policy_config), **kwargs)
