"""v0 buyer: complete-cost packages, a price concession schedule and one checked close.

Plugs into `arena_kit.play.play` (one decision per call; the call is the case coordinator).
Every accept goes through `_acceptable`: must-haves, standard terms resolved, C below the
alternative. No claims and no model yet.
"""

from arena_kit.cost import must_haves_ok, total_cost
from arena_kit.docs import standard_terms
from arena_kit.play import latest, live_threads, moves_left

from .guards import leaks
from .optimizer import alternative_cost, best_terms


def standing(case, events):
    """(term_sheet_id, terms) of the cheapest-for-us sheet in the supplier's latest message, or
    (None, {}). Hosted suppliers often send alternatives; the first sheet is not the best."""
    sheets = latest(events).get("term_sheets") or []
    std = standard_terms(events)
    priced = [s for s in sheets if s.get("terms", {}).get("unit_price") is not None]
    if not priced:
        return (sheets[0]["term_sheet_id"], sheets[0]["terms"]) if sheets else (None, {})
    best = min(priced, key=lambda s: total_cost(case, s["terms"], std))
    return best["term_sheet_id"], best["terms"]


class PackageAgent:
    def __init__(self, anchor=0.12, rounds=5, close_gap=0.005, tracer=None):
        self.anchor, self.rounds, self.close_gap, self.tracer = anchor, rounds, close_gap, tracer
        self.locked = {}  # supplier -> non-price terms of our first offer; kept stable after that

    def _package(self, case, sid, price, std):
        if sid not in self.locked:
            terms = best_terms(case, price, std)
            self.locked[sid] = {k: v for k, v in terms.items() if k != "unit_price"}
        return {**self.locked[sid], "unit_price": round(price, 2)}

    # -- helpers ------------------------------------------------------------------------------
    @staticmethod
    def _ours(events):
        return [m["term_sheets"][0]["terms"] for m in events if m.get("from") == "buyer" and m.get("term_sheets")]

    @staticmethod
    def _opening_price(events):
        for m in events:
            if m.get("from") != "buyer" and m.get("term_sheets"):
                return m["term_sheets"][0]["terms"].get("unit_price")
        return None

    def _acceptable(self, case, threads, c_alt):
        """(C, supplier, sheet_id) of every standing sheet we may accept, cheapest first."""
        out = []
        for sid in live_threads(threads):
            sheet_id, terms = standing(case, threads[sid])
            std = standard_terms(threads[sid])
            if not sheet_id or terms.get("unit_price") is None or not must_haves_ok(case, terms, std):
                continue
            c = total_cost(case, terms, std)
            if c < c_alt:
                out.append((c, sid, sheet_id))
        return sorted(out)

    def _log(self, case, kind, sid, **fields):
        if self.tracer:
            self.tracer.log("decision", case=case["case_id"], kind=kind, supplier=sid, **fields)

    def _close(self, case, threads, c_alt, reason):
        cands = self._acceptable(case, threads, c_alt)
        if cands:
            c, sid, sheet_id = cands[0]
            self._log(case, "accept", sid, c=c, c_alt=c_alt, sheet=sheet_id, reason=reason)
            return {"supplier_id": sid, "message": {"action": {"type": "accept", "term_sheet_id": sheet_id}}}
        sid = live_threads(threads)[0]
        self._log(case, "walk_away", sid, c_alt=c_alt, reason=reason)
        return {"supplier_id": sid, "message": {"action": {"type": "walk_away"}}}

    def _offer(self, case, sid, terms, std, c_alt, reason):
        body = (
            f"Thank you for your offer. To go ahead we propose the attached terms: "
            f"unit price EUR {terms['unit_price']:.2f}"
            + "".join(f", {k.replace('_', ' ')} {v}" for k, v in terms.items() if k != "unit_price")
            + ". We look forward to your confirmation."
        )
        assert not leaks(body), "body would leak internal information"
        c = total_cost(case, terms, std)
        self._log(case, "offer", sid, terms=terms, c=c, c_alt=c_alt, reason=reason)
        return {
            "supplier_id": sid,
            "message": {"subject": case["title"], "body": body, "term_sheets": [{"terms": terms}]},
        }

    # -- policy -------------------------------------------------------------------------------
    def decide(self, case, threads):
        c_alt = alternative_cost(case)
        live = live_threads(threads)
        status = {sid: latest(threads[sid]).get("status") for sid in live}

        if any(s == "agreed" for s in status.values()):
            return self._close(case, threads, c_alt, "supplier agreed")

        workable = [
            sid for sid in live if status[sid] in ("open", "final_offer") and moves_left(case, threads[sid]) > 1
        ]
        if not workable:
            return self._close(case, threads, c_alt, "no moves left")

        # RFQ: keep every thread moving; least-worked thread first, then cheapest standing sheet.
        def key(sid):
            _, terms = standing(case, threads[sid])
            c = total_cost(case, terms, standard_terms(threads[sid])) if terms.get("unit_price") else float("inf")
            return (len(self._ours(threads[sid])), c)

        sid = min(workable, key=key)
        events = threads[sid]
        std = standard_terms(events)
        _, theirs = standing(case, events)
        p = theirs.get("unit_price")
        if p is None:
            return self._close(case, threads, c_alt, "no price quoted")
        ours = self._ours(events)
        match = self._package(case, sid, p, std)
        c_theirs = total_cost(case, theirs, std)
        c_match = total_cost(case, match, std)

        if status[sid] == "final_offer":
            if c_match < c_theirs - 1e-6 and not (ours and ours[-1] == match):
                return self._offer(case, sid, match, std, c_alt, "final offer: same price, our terms")
            if all(status[s] == "final_offer" for s in workable):
                return self._close(case, threads, c_alt, "all final offers")
            others = [s for s in workable if status[s] != "final_offer"]
            sid = min(others, key=key)
            return self.decide_thread(case, threads, sid, c_alt)

        return self.decide_thread(case, threads, sid, c_alt)

    def decide_thread(self, case, threads, sid, c_alt):
        events = threads[sid]
        std = standard_terms(events)
        _, theirs = standing(case, events)
        p = theirs["unit_price"]
        p_open = self._opening_price(events) or p
        ours = self._ours(events)
        k = len(ours)
        last = ours[-1]["unit_price"] if ours else None

        if last is not None and p - last <= p * self.close_gap:
            match = self._package(case, sid, p, std)
            if total_cost(case, match, std) < total_cost(case, theirs, std) - 1e-6:
                return self._offer(case, sid, match, std, c_alt, "gap closed: their price, our terms")
            return self._close(case, threads, c_alt, "gap closed")

        floor = p_open * (1 - self.anchor)
        price = floor + (p - floor) * min(1.0, k / self.rounds)
        if last is not None:
            price = max(price, last)  # no backtracking on our own concessions
        price = round(min(price, p), 2)
        return self._offer(case, sid, self._package(case, sid, price, std), std, c_alt, f"round {k + 1} schedule")
