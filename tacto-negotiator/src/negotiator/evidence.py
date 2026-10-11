"""Opt-in, deterministic claim decoration; does not change the package policy.

Only single-supplier price-increase cases are enabled for the first experiment.
Reconstruct used IDs from buyer messages after resume. Reserve proposed IDs too:
skipping an unsent claim is preferable to consuming the same fact twice.
"""

from dataclasses import asdict

from arena_kit.cost import total_cost

from .claims import (
    DEFAULT_DISCLOSURE,
    MAX_CHECKED,
    case_facts,
    claim_keys,
    history_claims,
    index_relevance,
    pick,
    public_rival_quotes,
    recent_index_claims,
    verify,
)
from .context import DATA_ERRORS, build_context, content_hash
from .cost_breakdown import arithmetic_sentence
from .cost_breakdown import find as find_breakdown
from .dossiers import load_package
from .replies import evidence_constraints


class EvidencePolicy:
    def __init__(self, package=None, tracer=None, case_types=None, interpretation=None, recent_window_types=(),
                 rival_quote_types=(), index_window_types=(), claim_pacing=False, cost_breakdown=False):
        self.recent_window_types = set(recent_window_types)
        self.default_types = set(case_types if case_types is not None else ["price_increase"])
        self.case_types = self.default_types | self.recent_window_types
        # Opt-in: disclose a documented, still-valid public rival quote for the case part when its
        # complete cost (case cost model) beats the supplier's standing sheet.
        self.rival_quote_types = set(rival_quote_types or ())
        # Opt-in: allow the verified buyer-favourable index window (<= 12 months, ending in the last 12)
        # for listed cost drivers whose latest 12-month change supports the supplier.
        self.index_window_types = set(index_window_types or ())
        # Opt-in: release at most one new verified claim PER KIND per message (two index decreases in
        # one message buy one concession, P18: each acknowledgement names exactly one claim); a second
        # claim of a kind the message already carries waits for the next message. Claims of different
        # kinds still travel together, so every bundle v3 sends in one message is unchanged. Once pacing
        # has deferred a claim in a thread and the preferred queue is exhausted, fall back to the deeper
        # bank - one claim per message: latest index windows, scorecards, the supplier's own quote and our
        # order history with it (`claims.history_claims`). Never cherry-picked windows, never should-cost.
        # Threads where nothing was ever deferred behave exactly as without the option.
        self.claim_pacing = bool(claim_pacing)
        # Opt-in (`cost_breakdown_request`): the supplier's own cost breakdown XLSX, once received, ranks the
        # index claims and may add one ID-free arithmetic sentence after the verified index claim.
        self.cost_breakdown = bool(cost_breakdown)
        self.package = package
        self.tracer = tracer
        self.banks = {}
        self.contexts = {}
        self.context_keys = {}
        self.reserved = {}
        self.interpretation = interpretation

    def eligible(self, case, move):
        message = move.get("message") or {}
        return (
            case.get("type") in self.case_types
            and len(case.get("suppliers", [])) == 1
            and bool(message.get("term_sheets"))
            and not message.get("action")
        )

    def context_for(self, case):
        """Prepare/cache a snapshot; no selection, reservations or sends."""
        if self.package is None:
            self.package = load_package()
        cid = case["case_id"]
        key = content_hash({"case": case, "facts": self.package.facts})
        if self.context_keys.get(cid) != key:
            context = build_context(case, self.package)
            self.contexts[cid] = context
            self.context_keys[cid] = key
            self.banks[cid] = context.candidates
            if self.tracer:
                self.tracer.log("evidence_context", case=cid, context_version=context.version,
                                context=context.to_dict())
        return self.contexts[cid]

    def cheaper_rivals(self, case, events, sid):
        """Public rival quotes whose complete buyer cost beats the supplier's standing sheet."""
        if case.get("type") not in self.rival_quote_types:
            return []
        standing = next((e for e in reversed(events) if e.get("from") != "buyer" and e.get("term_sheets")), None)
        if standing is None:
            return []
        c_standing = min(total_cost(case, s.get("terms") or {}) for s in standing["term_sheets"])
        cited = {r for e in events if e.get("from") == "buyer" for r in e.get("refs") or []}
        out = []
        for claim, terms in public_rival_quotes(case, self.package):
            if claim.supplier_id != sid or set(claim.ids) & cited:
                continue
            c_rival = total_cost(case, terms)
            if c_rival < c_standing:
                out.append(claim)
            if self.tracer:
                self.tracer.log("rival_quote_check", case=case["case_id"], supplier=sid, ids=list(claim.ids),
                                c_rival=c_rival, c_standing=c_standing, cites=c_rival < c_standing)
        return out

    def fallback(self, case, exc):
        if self.tracer:
            self.tracer.log("evidence_fallback", case=case["case_id"], error_type=type(exc).__name__)

    @staticmethod
    def pace(chosen):
        """`claim_pacing` trim of one message's selection: the first claim of each kind stays, every
        further claim of an already carried kind is deferred. Returns (kept, deferred)."""
        kept, deferred, kinds = [], [], set()
        for c in chosen:
            (deferred if c.kind in kinds else kept).append(c)
            kinds.add(c.kind)
        return kept, deferred

    @staticmethod
    def paced_before(bank, events):
        """True once this thread carries two or more of our sent claims of one kind - i.e. pacing has
        already spread a bundle over messages. Rebuilt from the thread's buyer refs (restart-safe)."""
        sent = {r for e in events if e.get("from") == "buyer" for r in e.get("refs") or []}
        kinds = {}
        for c in bank:
            if c.ids and set(c.ids) <= sent:
                kinds[c.kind] = kinds.get(c.kind, 0) + 1
        return any(n >= 2 for n in kinds.values())

    def deep_bank(self, case, events, sid, usable, context):
        """Pacing fallback queue: the context bank without cherry-picked windows, plus the supplier's
        own quote and our order history with it - the latter only below its standing ask (a figure at
        or above what it asks is no argument)."""
        bank = [c for c in usable(context.candidates) if not c.cherry_picked]
        standing = next((e for e in reversed(events) if e.get("from") != "buyer" and e.get("term_sheets")), None)
        ask = None
        if standing is not None:
            prices = [(s.get("terms") or {}).get("unit_price") for s in standing["term_sheets"]]
            prices = [p for p in prices if isinstance(p, (int, float))]
            ask = min(prices) if prices else None
        for claim in usable(history_claims(case, self.package)):
            if ask is not None and claim.figure is not None and claim.figure >= ask - 0.005:
                if self.tracer:
                    self.tracer.log("history_claim_skipped", case=case["case_id"], supplier=sid,
                                    kind=claim.kind, figure=claim.figure, ask=ask)
                continue
            bank.append(claim)
        return bank

    def enrich(self, case, threads, sid, move, context=None, rfq_claims=0):
        """`rfq_claims` > 0 enables RFQ (multi-supplier) decoration with at most that many claims,
        excluding our internal should-cost; the single-supplier gate stays for every other path."""
        message = move.get("message")
        rfq = rfq_claims > 0 and case.get("type") == "rfq"
        if rfq:
            if not message or not message.get("term_sheets") or message.get("action"):
                return move
        elif not self.eligible(case, move):
            return move
        cid = case["case_id"]
        events = threads.get(sid, [])
        latest_supplier = next((m for m in reversed(events) if m.get("from") != "buyer"), {})
        if latest_supplier.get("status") in {"final_offer", "agreed", "walked_away", "no_bid"}:
            return move
        try:
            context = context if context is not None else self.context_for(case)
            if (
                context.case_id != cid
                or context.supplier_ids != tuple(case.get("suppliers") or [])
                or context.part_ids != tuple(case.get("parts") or [])
            ):
                raise ValueError("context scope mismatch")
            facts = case_facts(case, self.package)
            breakdown = find_breakdown(events) if self.cost_breakdown else None
            used = set(self.reserved.get(cid, set()))
            for events in threads.values():
                for event in events:
                    if event.get("from") == "buyer":
                        used.update(event.get("refs") or [])
            existing = set(message.get("refs") or [])
            used.update(existing)
            interpretation, skip_kinds = evidence_constraints(
                events, self.interpretation.get(sid) if self.interpretation else None
            )
            skip_kinds.update(lesson["avoid_claim_kind"] for lesson in interpretation.get("lessons", [])
                              if lesson.get("avoid_claim_kind"))
            rejected = set(interpretation["rejected_refs"])
            if self.tracer:
                self.tracer.log("reply_interpretation", case=cid, supplier=sid, **interpretation)
            if "*" in rejected:
                return move

            def usable(claims):
                return [c for c in claims if verify(c, facts, self.package, case)
                        and not rejected.intersection(c.ids) and c.kind not in skip_kinds]

            bank = usable(context.candidates)
            recent = False
            if case["type"] in self.recent_window_types:
                # Public facts decide: material drivers falling at the latest month and not documented as
                # hedged by the supplier. Otherwise behave exactly as without the option.
                fresh = usable(recent_index_claims(case, self.package, facts))
                if fresh:
                    bank, recent = fresh, True
                elif case["type"] not in self.default_types:
                    bank = []
            disclosures = DEFAULT_DISCLOSURE
            if case["type"] in self.index_window_types:  # only the most recent fall, never a stale window
                bank = [c for c in bank if not c.cherry_picked or c.note.startswith("recent buyer window")]
            rivals = self.cheaper_rivals(case, threads.get(sid, []), sid)
            if rivals:
                bank = [c for c in bank if c.kind != "rival_quote"] + rivals
                disclosures = DEFAULT_DISCLOSURE | {"reveals_rival"}
            priorities, reasons = index_relevance(bank, case, self.package, threads.get(sid, []), breakdown=breakdown)
            # Each pre-existing ref conservatively consumes one checked-claim slot.
            budget = max(0, MAX_CHECKED - len(existing))
            if rfq:
                budget = min(budget, rfq_claims)
            case_type = "renewal_trade" if case["type"] == "renewal" else case["type"]
            chosen = pick(
                bank, used, max_claims=budget, supplier_id=sid,
                case_type=case_type,
                index_priorities=priorities, disclosures=disclosures,
                allow_cherry_pick=recent or case["type"] in self.index_window_types,
                skip_kinds=frozenset({"should_cost"}) if rfq else frozenset(),
            )
            queue, deferred = "preferred", []
            if self.claim_pacing:
                chosen, deferred = self.pace(chosen)
                if deferred and self.tracer:
                    self.tracer.log("claim_deferred", case=cid, supplier=sid,
                                    deferred=[{"kind": c.kind, "ids": list(c.ids)} for c in deferred])
            if (not chosen and self.claim_pacing and budget > 0
                    and self.paced_before(bank, threads.get(sid, []))):
                deep = self.deep_bank(case, threads.get(sid, []), sid, usable, context)
                priorities, reasons = index_relevance(deep, case, self.package, threads.get(sid, []),
                                                      breakdown=breakdown)
                chosen = pick(
                    deep, used, max_claims=1, supplier_id=sid, case_type=case_type,
                    index_priorities=priorities, disclosures=DEFAULT_DISCLOSURE,
                    skip_kinds=frozenset({"should_cost"}),
                )
                queue = "deep"
        except DATA_ERRORS as exc:
            self.fallback(case, exc)
            return move
        if self.tracer:
            self.tracer.log("evidence_selection", case=cid, supplier=sid, context_version=context.version,
                            index_relevance=reasons, available_slots=budget, queue=queue,
                            selected=[{"kind": c.kind, "ids": list(c.ids)} for c in chosen])
        if not chosen:
            return move
        refs = list(dict.fromkeys([*(message.get("refs") or []), *(i for c in chosen for i in c.ids)]))
        self.reserved.setdefault(cid, set()).update(k for c in chosen for k in claim_keys(c))
        lines = [c.sentence for c in chosen]
        if breakdown:
            parts = case.get("parts") or []
            for i, c in enumerate(chosen):
                extra = arithmetic_sentence(breakdown, c, parts[0] if parts else None, self.package, facts)
                if extra:
                    lines.insert(i + 1, extra)
                    if self.tracer:
                        self.tracer.log("cost_breakdown_arithmetic", case=cid, supplier=sid, series=c.subject,
                                        sentence=extra)
                    break
        body = message.get("body", "") + "\n\n" + "\n".join(lines)
        if self.tracer:
            self.tracer.log("evidence", case=cid, supplier=sid, context_version=context.version,
                            claims=[asdict(c) for c in chosen])
        return {**move, "message": {**message, "body": body, "refs": refs}}
