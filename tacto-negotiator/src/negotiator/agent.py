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

from . import value_swap
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
        multi_supplier_anchor=None,
        llm=None,
    ):
        self.anchor, self.rounds, self.close_gap, self.tracer = anchor, rounds, close_gap, tracer
        if multi_supplier_anchor is not None and (
            type(multi_supplier_anchor) not in (int, float)
            or not math.isfinite(multi_supplier_anchor)
            or not 0 <= multi_supplier_anchor < 1
        ):
            raise ValueError("multi_supplier_anchor must be a finite fraction below one")
        self.multi_supplier_anchor = multi_supplier_anchor
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
        # Opt-in model layer: one bounded client; every feature falls back deterministically.
        self.llm, self.trait_reader, self._budget, self._traits_prefetched = None, None, None, set()
        if policy and (policy.model_traits or policy.model_choice or policy.model_answers):
            from .llm import LlmClient, configured

            if llm is not None or configured():
                self.llm = llm if isinstance(llm, LlmClient) else LlmClient(llm)
            else:
                log.warning("model_* policy fields set but LLM_BASE_URL/LLM_API_KEY/LLM_MODEL missing: rules only")
            if self.llm and policy.model_traits:
                from .llm_traits import TraitReader

                self.trait_reader = TraitReader(self.llm)
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
            self.claims = bool(policy.evidence_types or policy.recent_index_window_types)
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

            self.evidence = EvidencePolicy(
                tracer=tracer, case_types=policy.evidence_types if policy else None,
                interpretation=self.model_context,
                recent_window_types=policy.recent_index_window_types if policy else (),
                rival_quote_types=policy.rival_quote_types if policy else (),
                index_window_types=policy.index_window_types if policy else ())
        self.prev = {}  # supplier -> non-price terms of our last offer
        self.final_counters = {}  # supplier -> counters sent to its final offers (at most one)
        self.beat_asked = {}  # rival supplier -> final-offer sheet id we asked it to beat
        self.reanchored = set()  # rfq suppliers re-anchored after undercutting our own ask
        self.value_swapped = set()  # suppliers offered the value-equivalent chargeback swap (once)
        self.final_seen = {}  # final-offer sheet id -> monotonic time first seen
        if estimates is None and os.environ.get("NEGOTIATOR_ESTIMATES") != "1":
            estimates = {}  # dossier estimates are opt-in until calibrated (docs: experiments/LOG.md)
        self._estimates, self._est_case, self._est_cache = estimates, None, {}
        self._target_cache = {}
        self._traits_cache = {}

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
                "llm": self.llm.metrics() if self.llm is not None else None,
                "memory_snapshot_id": self.memory["snapshot_id"] if self.memory else None}

    # -- model layer (opt-in; src/negotiator/llm_*.py) -----------------------------------------
    def _turn_budget(self, fresh=False):
        """One `TurnBudget` per buyer decision: `decide` opens it; `propose` opens one only when it
        is called directly (async workers)."""
        from .llm import TurnBudget

        if fresh or self._budget is None:
            self._budget = TurnBudget()
        return self._budget

    def _window_s(self, sid):
        """Seconds left in this thread's reply window (and the wave cap, when a runner set one)."""
        now = time.time()
        windows = []
        if self.trades and sid in self.trades.deadlines:
            windows.append(self.trades.deadlines[sid] - now)
        cap = getattr(self, "wave_deadline", None)
        cap = cap() if callable(cap) else cap
        if cap:
            windows.append(cap - now)
        return min(windows) if windows else None

    def _model_traits(self, case, sid):
        """Model traits for `sid` (cached). The first call per case extracts every supplier of the
        case in parallel, waiting at most the decision's remaining model budget; later calls only
        read the cache, so a slow model never delays a later message."""
        if not (self.trait_reader and self.policy and case["type"] in self.policy.model_traits):
            return set()
        if case["case_id"] not in self._traits_prefetched:
            self._traits_prefetched.add(case["case_id"])
            budget = self._turn_budget()
            if budget.allow("traits", window_s=self._window_s(sid), need_s=2.0):
                dossiers = {s: self._public_traits(s)[1] for s in case.get("suppliers", [])}
                self.trait_reader.log = lambda s, entry: self._log(
                    case, "model_traits", s, traits=sorted(entry["traits"]), items=entry["items"],
                    elapsed_s=entry["elapsed_s"])
                future = self.trait_reader.prefetch_async(dossiers)
                try:
                    budget.timed(future.result, timeout=budget.timeout_for())
                except Exception:
                    self._log(case, "model_fallback", sid, kind="traits", reason="prefetch still running")
            else:
                self._log(case, "model_fallback", sid, kind="traits", skipped=budget.skipped[-1:])
        return self.trait_reader.traits(sid)

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

    def _anchor_for(self, case):
        """Freeze the scope to the case roster; changing live thread status cannot change the schedule."""
        if self.policy and case["type"] in self.policy.anchor_by_type:
            return self.policy.anchor_by_type[case["type"]]
        if self.multi_supplier_anchor is not None and len(set(case.get("suppliers") or ())) > 1:
            return self.multi_supplier_anchor
        return self.anchor

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
            return self.trades.initial(case, sid, ref_terms["unit_price"], self._anchor_for(case), std, sup,
                                       reference=ref_terms)
        if prev is None:
            n = nonprice(case, best_terms(
                case, ref_terms["unit_price"], std, sup,
                prefer_longer_lead=bool(self.policy and self.policy.cost_neutral_lead_time),
                prefer_longer_tenor=self._longer_tenor(case),
            ))
            pay_options = (case.get("term_options") or {}).get("payment_days") or []
            if (self._standard_payment(case) and "payment_days" in n and std.get("payment_days") in pay_options
                    and must_haves_ok(case, {**ref_terms, **n, "payment_days": std["payment_days"]}, std)):
                n["payment_days"] = std["payment_days"]
            fast = self._fast_payment(case, sid, {**ref_terms, **n}, std)
            if fast is not None:
                n["payment_days"] = fast
            if self.policy and self.policy.rfq_supplier_lead_time and case["type"] == "rfq":
                n = self._supplier_lead_time(case, sid, events, n, std)
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
                if "payment_days" in new and prev.get("payment_days") == self._fast_payment(
                        case, sid, {**ref_terms, **new}, std):
                    new["payment_days"] = prev["payment_days"]
                n = new
                self._log(case, "package_switch", sid, prev=prev, new=n, c_prev=min(on_prev), c_new=ref_c)
        if self.policy and self.policy.rfq_supplier_payment and case["type"] == "rfq":
            n = self._supplier_payment(case, sid, events, n, std)
        n = self._free_concessions(case, n, ref_terms, std, sup, sid) if eligible else n
        identity = (case['case_id'], sid)
        if prev is None and not self._ours(events) and identity not in self._memory_seen:
            self._memory_seen.add(identity)
            n, trace = prefer_package(case, n, ref_terms['unit_price'], std, sup, memory=self.memory)
            if trace:
                self._log(case, 'memory_package', sid, **trace)
        return n

    def _standard_payment(self, case):
        return bool(self.policy and case["type"] in self.policy.standard_payment_types)

    def _public_traits(self, sid, case=None):
        """(traits, dossier) from public data: regex traits, plus model traits when `case` is given
        and `model_traits` covers its type (the dossier copy then carries the union too)."""
        if sid not in self._traits_cache:
            from .context import DATA_ERRORS
            from .dossiers import build_one, load_package

            try:
                dossier = build_one(load_package(), sid)
            except DATA_ERRORS:
                dossier = None
            self._traits_cache[sid] = (set(dossier.traits), dossier) if dossier else (set(), None)
        traits, dossier = self._traits_cache[sid]
        extra = self._model_traits(case, sid) - traits if case is not None else set()
        if not extra:
            return traits, dossier
        from .llm_traits import with_traits

        return traits | extra, with_traits(dossier, extra)

    def _fast_payment(self, case, sid, terms, std):
        """Shortest legal payment option for a supplier whose public notes ask for faster payment
        (opt-in `fast_payment_types`); None when off, not applicable or not legal."""
        if not (self.policy and case["type"] in self.policy.fast_payment_types and "payment_days" in terms):
            return None
        if "wants_fast_payment" not in self._public_traits(sid, case)[0]:
            return None
        for days in sorted((case.get("term_options") or {}).get("payment_days") or []):
            if must_haves_ok(case, complete_offer(case, {**terms, "payment_days": days}), std):
                return days
        return None

    def _fast_payment_note(self, case, threads, sid, move):
        """First offer only: answer the supplier's public fast-payment note with the offered term."""
        msg = move.get("message")
        if not (self.policy and case["type"] in self.policy.fast_payment_types):
            return move
        events = threads.get(sid, [])
        if not msg or msg.get("action") or not msg.get("term_sheets") or self._ours(events):
            return move
        terms = msg["term_sheets"][0].get("terms") or {}
        days = terms.get("payment_days")
        if days is None or days != self._fast_payment(case, sid, terms, standard_terms(events)):
            return move
        from . import traits as T

        traits, dossier = self._public_traits(sid, case)
        ids = T.evidence(dossier, "wants_fast_payment") if dossier else []
        if not ids and self.trait_reader:
            ids = [i for i in self.trait_reader.evidence(sid, "wants_fast_payment") if i.startswith("doc:")]
        source = f"Your note {ids[0]}" if ids else "Your note"
        text = (f"{source} asked whether we could pay your invoices faster in return for a cash discount."
                f" We offer payment within {days} days; the attached unit price reflects that discount.")
        body = msg["body"] + "\n\n" + text
        assert not leaks(body), "body would leak internal information"
        self._log(case, "fast_payment", sid, payment_days=days, refs=ids[:1])
        return {**move, "message": {**msg, "body": body}}

    def _supplier_payment(self, case, sid, events, n, std):
        """Concede payment to the supplier's own stated term (never below 30 days) so that every
        later round negotiates price only, instead of re-asking a payment term it keeps refusing."""
        if "payment_days" not in n:
            return n
        stated = [s["terms"]["payment_days"] for m in events if m.get("from") != "buyer"
                  for s in (m.get("term_sheets") or [])[:1] if (s.get("terms") or {}).get("payment_days") is not None]
        if not stated:
            return n
        pay = stated[-1]
        options = (case.get("term_options") or {}).get("payment_days", [])
        if pay < 30 or pay >= n["payment_days"] or pay not in options:
            return n
        out = {**n, "payment_days": pay}
        if not must_haves_ok(case, complete_offer(case, {**out, "unit_price": 1.0}), std):
            return n
        self._log(case, "supplier_payment", sid, prev=n["payment_days"], new=pay)
        return out

    def _supplier_lead_time(self, case, sid, events, n, std):
        """A supplier quoting a longer lead time than ours gets the longest legal option up to its
        quote: its capacity premium for short lead times can exceed our late-delivery cost."""
        if "lead_time_days" not in n:
            return n
        quoted = [s["terms"]["lead_time_days"] for m in events if m.get("from") != "buyer"
                  for s in m.get("term_sheets") or [] if (s.get("terms") or {}).get("lead_time_days") is not None]
        if not quoted or max(quoted) <= n["lead_time_days"]:
            return n
        legal = [v for v in (case.get("term_options") or {}).get("lead_time_days", [])
                 if n["lead_time_days"] < v <= max(quoted)
                 and must_haves_ok(case, complete_offer(case, {**n, "lead_time_days": v, "unit_price": 1.0}), std)]
        if not legal:
            return n
        out = {**n, "lead_time_days": max(legal)}
        self._log(case, "supplier_lead_time", sid, quoted=max(quoted), prev=n["lead_time_days"],
                  new=out["lead_time_days"])
        return out

    def _anchor(self, case):
        return self._anchor_for(case)

    def _rounds(self, case):
        if self.policy and case["type"] in self.policy.rounds_by_type:
            return self.policy.rounds_by_type[case["type"]]
        return self.rounds

    def _longer_tenor(self, case):
        return bool(self.policy and case["type"] in self.policy.longer_tenor_types)

    def _free_concessions(self, case, n, theirs, std, sup, sid=None):
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
            if f == "contract_months" and self._longer_tenor(case) and v < n[f] and trial_c >= previous_c - 1e-6:
                continue
            if f == "payment_days" and self._standard_payment(case) and n[f] == std.get("payment_days"):
                continue
            if f == "payment_days" and self._fast_payment(case, sid, {**n, "unit_price": price}, std) == n[f]:
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

        s_max = getattr(self.policy, "cost_target_posterior", 0.0)
        if s_max > 0:
            return self._posterior_move(case, sid, events, msg, status, std, sup, tterms, sheets, c_alt, ours, left,
                                        accept, close, s_max)
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

    def _posterior_move(self, case, sid, events, msg, status, std, sup, tterms, sheets, c_alt, ours, left,
                        accept, close, s_max):
        """In-session supplier-cost posterior on the target package. Every offer of ours that drew
        any reply other than an agreement is a refusal. We offer the self-consistent price p with
        p = argmin E[C | refusals so far, p accepted]: the price we would still be happy with if the
        supplier took it at once. Refusals raise the posterior, so offers rise only as the supplier
        reveals that its cost is higher; we never offer above its own sheet on that package."""
        from . import cost_target as ct

        package = {**tterms, "unit_price": 0}
        refusals = [(t, False) for t in ours if same_package(case, t, package, std)]
        grid = ct.posterior(case, std, sup, refusals, s_max)

        def ec(t, g=grid):
            return ct.expected_cost(case, t, std, sup, g)

        p = tterms["unit_price"]
        for _ in range(8):  # fixed point of p -> argmin E[C | refusals, p accepted]
            g = ct.posterior(case, std, sup, [*refusals, ({**tterms, "unit_price": p}, True)], s_max)
            q = ct.min_price(case, tterms, std, sup, g)
            if abs(q - p) < 0.01:
                break
            p = q
        if ours and same_package(case, ours[-1], package, std):
            p = max(p, ours[-1]["unit_price"])  # never retreat below our own last offer
        # A counter is partly bargaining, not only cost: refusals may lift us back to the prior
        # optimum, never above it (the prior-target behaviour is the ceiling of this probe).
        p = min(p, tterms["unit_price"])
        opt = min(ct.min_price(case, tterms, std, sup, grid), tterms["unit_price"])
        asks = [t["unit_price"] for _, _, t in sheets if same_package(case, t, package, std)]
        ask = min(asks) if asks else None
        standing_c, standing_id, _ = sheets[0]
        mark_c = ec({**tterms, "unit_price": max(p, opt)})
        self._log(case, "cost_posterior", sid, offer=round(p, 2), opt=opt, ask=ask, refusals=len(refusals),
                  e_fc=round(sum(s["_w"] * s["full_cost"] for s in grid) / sum(s["_w"] for s in grid), 2)
                  if all("_w" in s for s in grid) else None, standing_c=standing_c, mark_c=mark_c)
        if same_package(case, sheets[0][2], package, std) and sheets[0][2]["unit_price"] <= max(p, opt) + 0.005:
            return close("posterior: standing sheet meets the posterior target")
        if status == "final_offer" or left <= 1:
            countered = sum(1 for i, e in enumerate(events) if e.get("from") == "buyer" and e.get("term_sheets")
                            and any(x.get("status") == "final_offer" for x in events[:i] if x.get("from") != "buyer"))
            if status == "final_offer" and left > 1 and countered < 1 and (ask is None or p < ask):
                return self._target_offer(case, sid, {**tterms, "unit_price": round(p, 2)}, std, sup, c_alt,
                                          ec({**tterms, "unit_price": p}), "posterior: one counter to final offer")
            return close("posterior: final offer or last move")
        terms = {**tterms, "unit_price": round(min(p, ask) if ask is not None else p, 2)}
        return self._target_offer(case, sid, terms, std, sup, c_alt, ec(terms), "posterior: self-consistent price")

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
        self._turn_budget(fresh=True)
        try:
            return self._decide(case, threads)
        finally:
            self._budget = None

    def _decide(self, case, threads):
        if self.policy and case["type"] in self.policy.cost_target_types:
            move = self._cost_target_move(case, threads)
            if move is not None:
                return move
        status, workable = self._workable(case, threads)
        order = sorted(workable, key=lambda s: (status[s] != "final_offer", self._key(case, threads, s)))
        reason = "no moves left"
        for sid in order or live_threads(threads)[:1]:
            advising = bool(self.package_advisor and case["type"] in self.policy.package_advice_types)
            move = self.propose(case, threads, sid, defer_evidence=advising)
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
                return self._enrich_evidence(case, threads, sid, move) if advising else move
            reason = move.get("reason", reason)
        return self._close(case, threads, reason)

    def propose(self, case, threads, supplier_id, *, defer_evidence=False):
        if supplier_id not in self.model_seen:
            self.prepare_email(case, threads, supplier_id)
        if self._budget is None:  # called directly by an async worker: one budget per proposal
            self._turn_budget(fresh=True)
            try:
                return self._propose_budgeted(case, threads, supplier_id, defer_evidence=defer_evidence)
            finally:
                self._budget = None
        return self._propose_budgeted(case, threads, supplier_id, defer_evidence=defer_evidence)

    def _propose_budgeted(self, case, threads, supplier_id, *, defer_evidence=False):
        if self.trait_reader and self.policy and case["type"] in self.policy.model_traits and self.trades:
            self.trades.prepare(case)
            self.trades.traits[supplier_id] |= self._model_traits(case, supplier_id)
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
        move = self._bundle_volume(case, threads, supplier_id, move)
        move = self._fast_payment_note(case, threads, supplier_id, move)
        if self.policy and self.policy.rfq_rival_offer and case["type"] == "rfq":
            before = move
            move = self._rival_offer_claim(case, threads, supplier_id, move)
            stack = self.policy.rfq_data_claims_stack
            if (self.policy.rfq_data_claims or stack) and self.evidence and (move is before or stack):
                # No rival undercuts this supplier: back the counter with one fresh verified fact.
                from .context import DATA_ERRORS

                try:
                    context = self.evidence.context_for(case)
                except DATA_ERRORS as exc:
                    self.evidence.fallback(case, exc)
                    return move
                return self.evidence.enrich(case, threads, supplier_id, move, context=context, rfq_claims=1)
        return move if defer_evidence else self._enrich_evidence(case, threads, supplier_id, move)

    def _enrich_evidence(self, case, threads, supplier_id, move):
        if self.evidence and self.evidence.eligible(case, move):
            from .context import DATA_ERRORS

            try:
                context = self.evidence.context_for(case)
            except DATA_ERRORS as exc:
                self.evidence.fallback(case, exc)
                return move
            return self.evidence.enrich(case, threads, supplier_id, move, context=context)
        return move

    def _rival_offer_claim(self, case, threads, sid, move):
        """Cite the lowest-priced must-have-valid standing rival offer from this session when it
        undercuts this supplier's standing price. Figure and ID come from the live sheet; each
        offer ID is cited at most once per receiving supplier (citing reveals it)."""
        from .claims import offer_claim

        message = move.get("message") or {}
        if not message.get("term_sheets") or message.get("action") or len(case.get("parts") or []) != 1:
            return move
        own = [t["unit_price"] for _, _, t in eligible_sheets(case, threads[sid], None, alternatives=True)]
        if not own:
            return move
        cited = {r for e in threads[sid] if e.get("from") == "buyer" for r in e.get("refs") or []}
        best = None
        for s in live_threads(threads):
            if s == sid:
                continue
            if self.policy.rfq_rival_offer_history:
                sheets = [(sh.get("term_sheet_id"), sh.get("terms") or {}) for m in threads[s]
                          if m.get("from") != "buyer" for sh in m.get("term_sheets") or []]
            else:
                sheets = [(i, t) for _, i, t in eligible_sheets(case, threads[s], None, alternatives=True)]
            for offer_id, terms in sheets:
                p = terms.get("unit_price")
                if not offer_id:
                    continue
                if offer_id in cited or p is None or p >= min(own) - 1e-6:
                    continue
                if best is None or (p, offer_id) < (best[0], best[1]):
                    best = (p, offer_id, s)
        if best is None:
            return move
        claim = offer_claim(best[1], best[0], best[2], sid, case["parts"][0])
        refs = list(dict.fromkeys([*(message.get("refs") or []), best[1]]))
        self._log(case, "rival_offer_claim", sid, offer_id=best[1], figure=best[0], rival=best[2])
        return {**move, "message": {**message, "body": message.get("body", "") + "\n\n" + claim.sentence,
                                     "refs": refs}}

    def _bundle_volume(self, case, threads, sid, move):
        """Opt-in: add the kit's volume facts (cited once, in the first offer; a reminder later)."""
        if not (self.policy and case["type"] in self.policy.bundle_volume_types):
            return move
        msg = move.get("message")
        if not msg or msg.get("action") or not msg.get("term_sheets"):
            return move
        from . import bundle_volume
        from .context import DATA_ERRORS
        from .dossiers import load_package

        try:
            package = load_package()
            dossier = self._public_traits(sid, case)[1]
            p = bundle_volume.plan(case, package, sid, dossier)
        except DATA_ERRORS:
            p = dossier = None
        if not p:
            return move
        if self._ours(threads[sid]):
            if case["type"] in self.policy.bundle_commitment_types:
                sheet = (msg.get("term_sheets") or [{}])[0]
                text = bundle_volume.commitment(p, case, sheet.get("terms") or sheet,
                                                bundle_volume.committee_threshold(dossier))
            else:
                text = bundle_volume.reminder(p)
            ids = []
        else:
            text, ids = bundle_volume.first_paragraph(p)
        body = msg["body"] + "\n\n" + text
        assert not leaks(body), "body would leak internal information"
        refs = list(dict.fromkeys([*(msg.get("refs") or []), *ids]))
        self._log(case, "bundle_volume", sid, new=p["new"], total=p["total"], refs=ids)
        return {**move, "message": {**msg, "body": body, **({"refs": refs} if refs else {})}}

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
        if (
            self.policy
            and case["type"] in self.policy.value_swap_types
            and cap_c is None
            and sid not in self.value_swapped
            and eligible
            and latest(events).get("status") == "open"
            and moves_left(case, events) > 1
            and value_swap.holds(case, events, sup) >= self.policy.value_swap_holds
        ):
            self.value_swapped.add(sid)
            standing_terms = eligible_sheets(case, events, sup)[0][2]
            ours_ = self._ours(events)
            swapped, trace = value_swap.swap(
                case, events, standing_terms, std, sup,
                last_price=ours_[-1].get("unit_price") if ours_ else None, split=self.policy.value_swap_split,
            )
            self._log(case, "value_swap", sid, **trace)
            if swapped:
                return self._offer(case, sid, complete_offer(case, swapped), std, sup, c_alt,
                                   "value-equivalent chargeback swap")
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
            if (
                self.policy
                and self.policy.rfq_undercut_reanchor
                and case["type"] == "rfq"
                and sid not in self.reanchored
                and latest(events).get("status") == "open"
                and moves_left(case, events) > 2
                and p < last_p * (1 - self.anchor / 2)
            ):
                # The supplier jumped well below our own ask: its floor is lower than our schedule
                # assumed, so counter once more below its new price instead of matching it.
                self.reanchored.add(sid)
                price = math.floor(p * (1 - self.anchor / 2) * 100) / 100
                self._log(case, "undercut_reanchor", sid, their=p, ours_last=last_p, counter=price)
                terms = complete_offer(case, {**n, "unit_price": price})
                return self._offer(case, sid, terms, std, sup, c_alt, "undercut our ask: re-anchor")
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

        floor = p_open * (1 - self._anchor_for(case))
        price = floor + (p - floor) * min(1.0, k / self._rounds(case))
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
