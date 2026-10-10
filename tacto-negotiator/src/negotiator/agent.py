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
from .optimizer import alternative_cost, best_terms

log = logging.getLogger("negotiator")


def standing(case, events, supplier=None):
    """(term_sheet_id, terms) of the cheapest eligible sheet in the supplier's latest message, else
    of its cheapest priced sheet, else (None, {})."""
    cands = eligible_sheets(case, events, supplier) or _priced(case, events, supplier)
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
        self, anchor=0.12, rounds=5, close_gap=0.005, tracer=None, estimates=None, final_hold_s=40.0, meso=None,
        p_walk=0.25,
    ):
        self.anchor, self.rounds, self.close_gap, self.tracer = anchor, rounds, close_gap, tracer
        self.meso = os.environ.get("NEGOTIATOR_MESO") == "1" if meso is None else meso
        self.final_hold_s = final_hold_s
        self.p_walk = p_walk  # chance a supplier walks when its final offer is countered (D02: 2 of 9)
        self.prev = {}  # supplier -> non-price terms of our last offer
        self.final_counters = {}  # supplier -> counters sent to its final offers (at most one)
        self.beat_asked = {}  # rival supplier -> final-offer sheet id we asked it to beat
        self.final_seen = {}  # final-offer sheet id -> monotonic time first seen
        self._estimates, self._est_case, self._est_cache = estimates, None, {}

    # -- estimates ----------------------------------------------------------------------------
    def estimates_for(self, case):
        """{supplier_id: estimate}: the injected estimates, else `dossiers.supplier_estimate`."""
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
        if prev is None:
            n = nonprice(case, best_terms(case, ref_terms["unit_price"], std, sup))
        elif not eligible:
            return prev
        else:
            n = prev
            on_prev = [c for c, _, t in cands if same_package(case, {**prev, "unit_price": 0}, t, std)]
            if on_prev and min(on_prev) > ref_c + 1e-6:
                n = nonprice(case, complete_offer(case, closing_terms(case, ref_terms, std)))
                self._log(case, "package_switch", sid, prev=prev, new=n, c_prev=min(on_prev), c_new=ref_c)
        return self._free_concessions(case, n, ref_terms, std, sup) if eligible else n

    def _free_concessions(self, case, n, theirs, std, sup):
        price = theirs["unit_price"]
        for f, v in theirs.items():
            if f == "unit_price" or f not in n or v is None or n[f] == v:
                continue
            trial = {**n, f: v}
            if not must_haves_ok(case, {**trial, "unit_price": price}, std):
                continue
            if total_cost(case, {**trial, "unit_price": price}, std, sup) <= total_cost(
                case, {**n, "unit_price": price}, std, sup
            ) + 1e-6:
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

    # -- policy -------------------------------------------------------------------------------
    def _workable(self, case, threads):
        live = live_threads(threads)
        status = {sid: latest(threads[sid]).get("status") for sid in live}
        workable = [s for s in live if status[s] in ("open", "final_offer") and moves_left(case, threads[s]) > 1]
        return status, workable

    def decide(self, case, threads):
        """Serial wrapper: final-offer threads first, then the least-worked open thread; the first
        proposal that is not a hold is sent, and a close request is resolved by the evaluator."""
        status, workable = self._workable(case, threads)
        order = sorted(workable, key=lambda s: (status[s] != "final_offer", self._key(case, threads, s)))
        reason = "no moves left"
        for sid in order or live_threads(threads)[:1]:
            move = self.propose(case, threads, sid)
            if move.get("close"):
                return self._close(case, threads, move.get("reason", ""))
            if not move.get("hold"):
                return move
            reason = move.get("reason", reason)
        return self._close(case, threads, reason)

    def propose(self, case, threads, supplier_id):
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
            return None
        c_f, _, terms_f = cands[0]
        n = self.prev.get(sid) or nonprice(case, best_terms(case, terms_f["unit_price"], std, sup))
        best = best_close(case, threads, self.estimates_for(case))
        if best is None:
            if not math.isfinite(c_alt):
                return None
            price = price_for_cost(case, {**n, "unit_price": terms_f["unit_price"]}, c_alt * 0.998, std, sup)
            price = math.floor(price * 100) / 100
            terms, reason = {**n, "unit_price": price}, "final offer above alternative: one counter"
        elif best[1] == sid:
            terms, reason = {**n, "unit_price": terms_f["unit_price"]}, "final offer: same price, our terms"
            gain = c_f - total_cost(case, terms, std, sup)
            rivals = [
                c for s in live_threads(threads) if s != sid
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
        cands = eligible_sheets(case, events, sup)
        eligible = bool(cands)
        cands = cands or _priced(case, events, sup)
        if not cands:
            return {"close": True, "reason": "no price quoted"}
        if deltas := revealed_deltas(case, latest(events).get("term_sheets") or [], std):
            self._log(case, "revealed", sid, deltas=deltas)

        ref_c = cands[0][0]
        n = self._nonprice(case, sid, events, std, sup, cands, eligible)
        p = self._ask_on(case, n, cands, std, sup)
        first = next((i for i, m in enumerate(events) if m.get("from") != "buyer" and m.get("term_sheets")), None)
        p_open = p
        if first is not None:
            first_events = events[: first + 1]
            open_cands = eligible_sheets(case, first_events, sup) or _priced(case, first_events, sup)
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
        variants = self._payment_variants(case, terms, cands[0][2], std, sup) if self.meso else []
        return self._offer(case, sid, terms, std, sup, c_alt, why or f"round {k + 1} schedule", variants)
