"""Bounded, source-linked LLM review before accepting a single supplier's final offer.

The model chooses only among complete code-generated counter packages. Its citation is
checked against the current supplier message. Risk, legality and dispatch stay in code.
"""

import copy
import hashlib
import json
import math
import time
from pathlib import Path

from arena_kit.cost import complete_offer, must_haves_ok, total_cost
from arena_kit.docs import standard_terms
from arena_kit.play import latest

from .advice import AdviceCompletion, digest, scoped_notes
from .assessment import CONDITION, REFUSAL, AssessmentStore, admit, refused_candidate, stated_terms_support
from .evaluator import eligible_sheets
from .final_review import no_deal_fallback_cost, review
from .message_prose import checked_body
from .optimizer import alternative_cost
from .package_advisor import ModelResponseError, _legal, bounded_call, complete, failure_reason
from .skill_docs import load_skill, skill_prompt
from .validation_repair import repair

CONTRACT = "final-offer-advice-v1"


def system_prompt(expected_hash):
    return skill_prompt("final", "final-offer-review", expected_hash)


class FinalAdviceRejected(ValueError):
    """Bounded local rejection code suitable for metrics and traces."""


def response_schema(context):
    properties = {
        "selected_id": {"type": "string", "enum": ["keep", *context["approved_packages"]]},
        "message_index": {"type": "integer"},
        "quote": {"type": "string"}}
    if context.get("write_response") is True:
        properties["body"] = {"type": "string"}
    return {"type": "object", "additionalProperties": False,
            "properties": properties, "required": list(properties)}


def dossier_facts(dossier, case):
    """Small, supplier-scoped factual view of the ingested public package."""
    if dossier is None:
        return {}
    parts = set(case.get("parts") or [])
    history = [item for item in dossier.history if not parts or item.get("part_id") in parts]
    return {
        "master": {k: dossier.master[k] for k in ("payment_days", "incoterm", "standard_lead_time_days")
                   if k in dossier.master},
        "scorecard": {k: dossier.scorecard[k] for k in ("quarter", "otd_pct", "ppm")
                      if k in dossier.scorecard},
        "news": [{k: item[k] for k in ("id", "date", "topic", "headline") if k in item}
                 for item in dossier.news[-2:]],
        "negotiation_history": [{k: item[k] for k in ("date", "part_id", "type", "asked_pct", "settled_pct")
                                 if k in item} for item in history[-3:]],
    }


def counter_menu(case, events, supplier=None):
    """Legal cheaper alternatives, including a longer legal lead from a supplier variant.

    A supplier's invalid 54-day variant can support offering a listed 56-day term at
    its stated price. It is never treated as an accepted quote or supplier guarantee.
    """
    standing = eligible_sheets(case, events, supplier)
    if not standing:
        return {}, None
    standing_cost, _, standing_terms = standing[0]
    std = standard_terms(events)
    sent = [complete_offer(case, s.get("terms") or {}) for e in events if e.get("from") == "buyer"
            for s in e.get("term_sheets") or []]
    menu = {}
    for sheet in (latest(events).get("term_sheets") or [])[1:4]:
        raw = sheet.get("terms") or {}
        if type(raw.get("unit_price")) not in (int, float):
            continue
        choices = [raw]
        lead = raw.get("lead_time_days")
        options = (case.get("term_options") or {}).get("lead_time_days") or []
        if (type(lead) in (int, float) and lead not in options and options
                and "lead_time_days" in case.get("negotiable", ())):
            choices = [{**raw, "lead_time_days": v} for v in sorted(options) if v >= lead][:1]
        for candidate in choices:
            if not _legal(case, candidate, std):
                continue
            terms = complete_offer(case, candidate)
            if terms in sent or refused_candidate(events, standing_terms, terms):
                continue
            cost = total_cost(case, terms, std, supplier)
            if not math.isfinite(cost) or cost >= standing_cost - 1e-6:
                continue
            ident = "counter_" + hashlib.sha256(json.dumps(terms, sort_keys=True).encode()).hexdigest()[:12]
            menu[ident] = {"terms": terms, "cost": cost}
    return menu, standing_cost


class FinalOfferAdvisor:
    """One final-review call, charged before execution and never retried after uncertainty."""

    def __init__(self, complete_fn=complete, *, mode="shadow-v1", write_response=False,
                 repair_fn=None, clock=time.monotonic):
        if mode not in ("shadow-v1", "select-v1", "explore-v1"):
            raise ValueError("invalid final advice mode")
        self.complete_fn, self.mode, self.clock = complete_fn, mode, clock
        self.skill = load_skill("final", "final-offer-review")
        self.write_response = write_response
        self.repair_fn = repair_fn if repair_fn is not None else (complete if complete_fn is complete else None)
        self.session_id, self.store = None, None
        self.seen, self.calls, self.reserved_s, self.disabled = set(), 0, 0.0, False
        self.input_tokens = self.output_tokens = self.usage_reported_calls = 0
        self.outcomes = []

    def attach(self, session_id, journal_path=None):
        if self.session_id == session_id:
            return
        if self.session_id is not None and self.calls:
            raise ValueError("cannot rebind active final adviser")
        self.session_id = session_id
        self.store = AssessmentStore(Path(journal_path).with_name("assessment.jsonl")) if journal_path else None
        for row in self.store.reservations(session_id) if self.store else ():
            if row.get("contract") == CONTRACT:
                self.seen.add(row["update_hash"])
                self.calls += 1
                self.reserved_s += row["seconds"]

    def metrics(self):
        return {"contract": CONTRACT, "mode": self.mode, "skill_sha256": self.skill.sha256,
                "write_response": self.write_response,
                "calls": self.calls,
                "reserved_s": self.reserved_s, "reported_input_tokens": self.input_tokens,
                "reported_output_tokens": self.output_tokens,
                "unknown_usage_calls": self.calls - self.usage_reported_calls,
                "outcomes": list(self.outcomes)}

    def select(self, case, threads, sid, *, supplier=None, dossier=None, notes=(), prior=(), brief=None, remaining_s=0,
               other_reserved_s=0, other_calls=0, walk_bound=0, max_loss_fraction=0.0):
        started = self.clock()
        trace = {"status": "skipped", "reason": None, "selected_id": None,
                 "changed": False, "skill_sha256": self.skill.sha256}
        events = threads[sid]
        menu, standing_cost = counter_menu(case, events, supplier)
        if not menu:
            return None, {**trace, "reason": "no_legal_cheaper_counter"}
        if (self.disabled or self.calls >= 1 or other_calls + self.calls >= 8
                or remaining_s <= 28):
            return None, {**trace, "reason": "admission_closed"}
        current = [(i, e) for i, e in enumerate(events) if e.get("from") != "buyer"]
        index, message = current[-1]
        if message.get("status") != "final_offer" or len(message.get("body") or "") > 3000:
            return None, {**trace, "reason": "source_unavailable"}
        part = (case.get("parts") or [None])[0] if len(case.get("parts") or []) == 1 else None
        scoped = [n for n in notes if isinstance(n, dict) and n.get("part", part) in (None, part)]
        public = [n for n in scoped_notes(sid, scoped) if len(n.get("text", "")) <= 1500][:2 if brief else 3]
        context = {"response_contract": CONTRACT, "skill_sha256": self.skill.sha256,
                   "write_response": self.write_response,
                   "supplier_id": sid,
                   "latest_supplier_message": {"message_index": index, "body": message["body"]},
                   "current_supplier_term_sheets": [s.get("terms") or {}
                                                     for s in (message.get("term_sheets") or [])[:4]],
                   "earlier_supplier_messages": [{"message_index": i, "body": e.get("body") or ""}
                                                 for i, e in current[-3:-1] if len(e.get("body") or "") <= 1500],
                   "public_dossier_notes": public,
                   "supplier_brief": brief if isinstance(brief, dict) and brief.get("supplier_id") == sid else None,
                   "public_dossier_facts": dossier_facts(dossier, case),
                   "case_requirements": {"allowed_options": case.get("term_options", {}),
                                         "must_haves": case.get("buyer", {}).get("must_haves", [])},
                   "prior_assessment": [{"kind": e["kind"], "quote": e["span"]["quote"],
                                          "fields": e["fields"], "lifecycle": e["lifecycle"]}
                                         for e in list(prior)[-6:]],
                   "standing_terms": eligible_sheets(case, events, supplier)[0][2],
                   "approved_packages": {k: v["terms"] for k, v in menu.items()}}
        if len(json.dumps(context, ensure_ascii=False)) > 12000:
            return None, {**trace, "reason": "context_bound"}
        update = digest([case.get("case_id"), sid, index, message.get("body"), message.get("term_sheets")])
        if update in self.seen:
            return None, {**trace, "reason": "already_reviewed"}
        allowance = min(8.0, 24.0 - other_reserved_s - self.reserved_s,
                        remaining_s - 20.0 - (self.clock() - started))
        if allowance <= 0:
            return None, {**trace, "reason": "budget_closed"}
        if budget := getattr(self, "model_budget", None):
            allowed, reason, _ = budget.reserve(CONTRACT, sid, update, digest(context),
                                                allowance, remaining_s=remaining_s)
            if not allowed:
                return None, {**trace, "reason": reason}
        self.seen.add(update)
        self.calls += 1
        self.reserved_s += allowance
        if self.store:
            self.store.append([{"record": "reservation", "session_id": self.session_id,
                                "supplier_id": sid, "update_hash": update,
                                "history_hash": digest(events), "seconds": allowance,
                                "contract": CONTRACT}])
        trace.update(status="fallback", request_digest=digest(context),
                     context_bytes=len(json.dumps(context, ensure_ascii=False).encode()),
                     brief_status=context["supplier_brief"].get("status") if context["supplier_brief"] else None,
                     brief_data_sha256=(context["supplier_brief"].get("data_sha256")
                                        if context["supplier_brief"] else None),
                     brief_source_digest=(context["supplier_brief"].get("source_digest")
                                          if context["supplier_brief"] else None),
                     candidate_count=len(menu), context_s=self.clock() - started)
        try:
            def validate_answer(answer):
                expected_fields = {"selected_id", "message_index", "quote"}
                if self.write_response:
                    expected_fields.add("body")
                if not isinstance(answer, dict) or set(answer) != expected_fields:
                    raise FinalAdviceRejected("response_fields")
                chosen = answer["selected_id"]
                if chosen == "keep":
                    if answer["message_index"] != -1 or answer["quote"] != "":
                        raise FinalAdviceRejected("invalid_keep")
                    trace.update(status="ok", reason="model_keep", selected_id="keep")
                    return None, trace
                if chosen not in menu or answer["message_index"] != index:
                    raise FinalAdviceRejected("invalid_selection")
                terms = menu[chosen]["terms"]
                changed = [f for f in case["negotiable"] if f != "unit_price"
                           and terms.get(f) != context["standing_terms"].get(f)]
                exact_supplier_variant = any(
                    terms == complete_offer(case, sheet)
                    for sheet in context["current_supplier_term_sheets"][1:]
                )
                fields = changed or (["unit_price"] if exact_supplier_variant else [])
                if REFUSAL.search(answer["quote"]) and not CONDITION.search(answer["quote"]):
                    raise FinalAdviceRejected("refusal_not_counter_support")
                quote_kind = ("conditional_trade" if CONDITION.search(answer["quote"])
                              else "stated_terms" if stated_terms_support(answer["quote"], fields, terms)
                              else "objection")
                observation = {"kind": quote_kind, "message_index": index,
                               "public_note_id": None, "quote": answer["quote"],
                               "addressed_fields": fields}
                admitted, rejected = admit([observation], case, events, sid, public,
                                           session_id=self.session_id, prompt_version=CONTRACT)
                trace["assessment_rejected"] = rejected
                if rejected or not admitted or not fields:
                    raise FinalAdviceRejected("unsupported_citation")
                from .assessment import condition_supported

                if not condition_supported(admitted[0], terms):
                    raise FinalAdviceRejected("unresolved_condition")
                if self.clock() - started >= remaining_s - 20:
                    raise TimeoutError("closing_reserve_expired")
                if refused_candidate(events, context["standing_terms"], terms):
                    raise FinalAdviceRejected("explicit_refusal")
                outside = case.get("buyer", {}).get("alternative") or {}
                outside_terms = outside.get("terms") or {}
                executable = (outside.get("kind") in ("quote", "current_contract")
                              and type(outside_terms.get("unit_price")) in (int, float)
                              and must_haves_ok(case, complete_offer(case, outside_terms)))
                no_deal_cost = (no_deal_fallback_cost(case) if outside.get("kind") == "none" else None)
                outcome = review(standing_cost, menu[chosen]["cost"],
                                 alternative_cost(case) if executable else math.inf,
                                 walk_bound=walk_bound, remaining_s=remaining_s - (self.clock() - started),
                                 no_deal_cost=no_deal_cost, exploratory=self.mode == "explore-v1",
                                 max_loss_fraction=max_loss_fraction)
                trace.update(status="ok", selected_id=chosen, quote=answer["quote"],
                             evidence_id=admitted[0]["event_id"], risk=outcome,
                             reason=outcome["reason"])
                if self.write_response and outcome["admitted"] and self.mode != "shadow-v1":
                    check = {}
                    body = checked_body(answer["body"], terms,
                                        prepared_body="These terms are offered together as one conditional package.",
                                        reason_out=check)
                    trace["body_source"] = "model" if body else "deterministic_fallback"
                    trace["prose_check"] = check.get("check")
                    if body:
                        trace["body"] = body
                if self.store:
                    self.store.append(admitted)
                if self.mode == "shadow-v1" or not outcome["admitted"]:
                    return None, trace
                trace["changed"] = True
                return terms, trace

            call_started = self.clock()
            try:
                answer = bounded_call(self.complete_fn, copy.deepcopy(context), allowance)
                if budget:
                    budget.artifact(CONTRACT, digest(context), context,
                                    response=answer.response if isinstance(answer, AdviceCompletion) else answer)
            finally:
                trace["provider_s"] = self.clock() - call_started
            if self.clock() - call_started >= allowance:
                raise TimeoutError("late final advice")
            if isinstance(answer, AdviceCompletion):
                usage = answer.usage
                if all(type(usage.get(k)) is int and usage[k] >= 0
                       for k in ("prompt_tokens", "completion_tokens")):
                    self.input_tokens += usage["prompt_tokens"]
                    self.output_tokens += usage["completion_tokens"]
                    self.usage_reported_calls += 1
                answer = answer.response

            try:
                return validate_answer(answer)
            except FinalAdviceRejected as first:
                trace["initial_rejection"] = str(first)
                repaired, repair_trace = repair(
                    self.repair_fn, context, answer, str(first), supplier_id=sid,
                    update_hash=digest([update, "validation-repair"]),
                    remaining_s=remaining_s - (self.clock() - started), budget=budget, clock=self.clock)
                trace["repair"] = repair_trace
                if repaired is None:
                    raise
                trace["status"] = "fallback"
                trace["reason"] = None
                try:
                    result = validate_answer(repaired)
                except FinalAdviceRejected as second:
                    repair_trace.update(status="rejected", reason=str(second))
                    raise
                trace["repaired"] = True
                return result
        except Exception as exc:
            if budget:
                budget.artifact(CONTRACT, digest(context), context, error=exc)
            if isinstance(exc, TimeoutError):
                self.disabled = True
            provider_failure = (isinstance(exc, (TimeoutError, ModelResponseError))
                                or type(exc).__module__.startswith("httpx")
                                or isinstance(exc, ValueError)
                                and str(exc).startswith("LLM endpoint, key and model"))
            if provider_failure and "repair" not in trace:
                trace["initial_rejection"] = failure_reason(exc)
                repaired, repair_trace = repair(
                    self.repair_fn, context, None, trace["initial_rejection"], supplier_id=sid,
                    update_hash=digest([update, "validation-repair"]),
                    remaining_s=remaining_s - (self.clock() - started), budget=budget, clock=self.clock)
                trace["repair"] = repair_trace
                if repaired is not None:
                    try:
                        result = validate_answer(repaired)
                    except Exception as second:
                        repair_trace.update(status="rejected", reason=(str(second)
                                            if isinstance(second, FinalAdviceRejected) else failure_reason(second)))
                    else:
                        trace["repaired"] = True
                        return result
            trace["reason"] = str(exc) if isinstance(exc, FinalAdviceRejected) else failure_reason(exc)
            return None, trace
        finally:
            trace["elapsed_s"] = self.clock() - started
            self.outcomes.append({k: trace.get(k) for k in ("status", "reason", "selected_id", "changed",
                                                         "elapsed_s", "request_digest", "candidate_count",
                                                         "context_bytes", "context_s", "provider_s",
                                                         "risk", "evidence_id", "brief_status",
                                                         "brief_data_sha256", "brief_source_digest",
                                                         "body_source", "prose_check", "assessment_rejected",
                                                         "initial_rejection", "repair", "repaired",
                                                         "skill_sha256")})
