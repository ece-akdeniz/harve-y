"""Small source-linked strategy check around a prepared deterministic buyer move."""

import copy
import json
import math
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from arena_kit.cost import total_cost
from arena_kit.docs import standard_terms
from arena_kit.play import latest

from .advice import (
    RESERVE_S,
    AdviceCompletion,
    AdviceExecutionBlocked,
    CapacityAdvisor,
    candidates,
    commercial_changes,
    digest,
    render,
    scoped_notes,
)
from .assessment import AssessmentStore, admit, refused_candidate, stated_terms_support
from .evaluator import alternative_cost
from .message_prose import checked_body
from .package_advisor import ModelResponseError, _legal, bounded_call, complete, failure_reason
from .questions import catalog
from .skill_docs import load_skill, skill_prompt
from .validation_repair import repair

CONTRACT = "negotiation-strategy-v1"
MAX_CONTEXT_BYTES = 14000
MAX_QUOTE_CHARS = 600
ACTION_CUE = re.compile(
    r"\b(need|require|cannot|can't|unable|constrain|prefer|would help|necessitat|"
    r"in exchange|if|only if|only with|subject to|ben[oö]tig|brauchen|nur wenn)\w*\b",
    re.I,
)


@dataclass(frozen=True)
class NegotiationSkill:
    text: str
    sha256: str

    @classmethod
    def load(cls):
        skill = load_skill("negotiation", "negotiation-decision")
        return cls(skill.text, skill.sha256)


def system_prompt(expected_hash):
    return skill_prompt("negotiation", "negotiation-decision", expected_hash)


def response_schema(context):
    writing = context.get("write_response") is True
    properties = {
        "selected_id": {"type": "string", "enum": ["keep", *context["approved_packages"],
                                                  *context["registered_questions"]]},
        "message_index": {"type": "integer"},
        "quote": {"type": "string"},
        "kind": {"type": "string", "enum": ["none", "objection", "conditional_trade", "question",
                                           "stated_terms"]}}
    if writing:
        properties["body"] = {"type": "string"}
    return {"type": "object", "additionalProperties": False,
            "properties": properties, "required": list(properties)}


class StrategyRejected(ValueError):
    """A bounded validation reason that can appear in the experiment trace."""


class StrategyAdvisor(CapacityAdvisor):
    """One skill-guided choice among code-generated complete moves on an open thread.

    Inherits bounded session accounting and the serial guarded-decision integration.
    The smaller response contract intentionally avoids the older multi-observation
    provider request that timed out on P10.
    """

    def __init__(self, complete_fn=complete, *, case_types=("capacity", "renewal"),
                 max_calls=3, total_s=16.0, timeout_s=8.0, shadow=False,
                 write_response=False, repair_fn=None, clock=time.monotonic):
        super().__init__(complete_fn, concession=0.0, max_calls=max_calls, total_s=total_s,
                         timeout_s=timeout_s, clock=clock, case_types=case_types,
                         shadow=shadow, questions=True)
        self.skill = NegotiationSkill.load()
        self.write_response = write_response
        self.repair_fn = repair_fn if repair_fn is not None else (complete if complete_fn is complete else None)

    def attach(self, session_id, journal_path=None):
        if self.session_id == session_id:
            return
        if self.session_id is not None and self.calls:
            raise ValueError("cannot rebind active strategy adviser")
        self.session_id = session_id
        self.store = AssessmentStore(Path(journal_path).with_name("assessment.jsonl")) if journal_path else None
        for row in self.store.reservations(session_id) if self.store else ():
            if row.get("contract") == CONTRACT:
                self.seen.add(row["update_hash"])
                self.calls += 1
                self.reserved_s += row["seconds"]

    def metrics(self):
        return {**super().metrics(), "contract": CONTRACT, "skill_sha256": self.skill.sha256,
                "write_response": self.write_response}

    def select(self, case, threads, move, *, supplier=None, public_notes=(), brief=None, remaining_s=None):
        started = self.clock()
        sid, message = move["supplier_id"], move.get("message") or {}
        trace = {"contract": CONTRACT, "status": "skipped", "reason": None,
                 "admitted": False, "changed": False, "skill_sha256": self.skill.sha256}
        if (case.get("type") not in self.case_types or len(threads) != 1 or message.get("action")
                or len(message.get("term_sheets") or []) != 1 or message.get("refs")
                or message.get("attachments") or remaining_s is None or remaining_s <= RESERVE_S):
            return move, {**trace, "reason": "ineligible_or_reserve"}
        events = threads[sid]
        if latest(events).get("status") != "open":
            return move, {**trace, "reason": "not_open"}
        snapshot = digest([case, threads, move, supplier])
        terms = message["term_sheets"][0]["terms"]
        notes = scoped_notes(sid, public_notes)[:2 if brief else 4]
        packages, ceiling = candidates(case, events, terms, supplier, 0.0, notes)
        if not packages:
            return move, {**trace, "reason": "no_candidates"}
        questions = catalog(events, terms, packages) if remaining_s > 45 else {}
        source = [{"message_index": i, "body": e.get("body") or ""}
                  for i, e in enumerate(events) if e.get("from") != "buyer"]
        if not source or len(source[-1]["body"]) > 3000:
            return move, {**trace, "reason": "source_unavailable"}
        context = {
            "response_contract": CONTRACT, "skill_sha256": self.skill.sha256,
            "write_response": self.write_response,
            "supplier_id": sid, "supplier_messages": source,
            "deterministic_move": {"subject": message.get("subject"), "body": message.get("body"),
                                   "terms": terms},
            "case_requirements": {"type": case.get("type"),
                                  "category_goal": case.get("buyer", {}).get("category_goal"),
                                  "allowed_options": case.get("term_options", {}),
                                  "must_haves": case.get("buyer", {}).get("must_haves", []),
                                  "preferred_lead_time_days": case.get("buyer", {}).get("need_lead_time_days")},
            "public_dossier_notes": notes,
            "supplier_brief": brief if isinstance(brief, dict) and brief.get("supplier_id") == sid else None,
            "acknowledged_buyer_packages": [s.get("terms") for e in events if e.get("from") == "buyer"
                                            for s in e.get("term_sheets") or []],
            "current_supplier_packages": [s.get("terms") or {} for s in
                                          latest(events).get("term_sheets") or []],
            "approved_packages": packages,
            "registered_questions": questions,
            "commercial_changes": {key: commercial_changes(terms, value)
                                   for key, value in packages.items()},
        }
        encoded = json.dumps(context, ensure_ascii=False)
        if len(encoded.encode()) > MAX_CONTEXT_BYTES:
            return move, {**trace, "reason": "context_bound"}
        update = digest([case.get("case_id"), sid, source[-1]])
        if self.disabled or update in self.seen or self.calls >= self.max_calls:
            return move, {**trace, "reason": "admission_closed"}
        allowance = min(self.timeout_s, self.total_s - self.reserved_s,
                        remaining_s - RESERVE_S - (self.clock() - started))
        if allowance <= 0:
            return move, {**trace, "reason": "budget_closed"}
        if budget := getattr(self, "model_budget", None):
            allowed, reason, _ = budget.reserve(CONTRACT, sid, update, digest(context),
                                                allowance, remaining_s=remaining_s)
            if not allowed:
                return move, {**trace, "reason": reason}
        self.seen.add(update)
        self.calls += 1
        self.reserved_s += allowance
        if self.store:
            self.store.append([{"record": "reservation", "session_id": self.session_id,
                                "supplier_id": sid, "update_hash": update,
                                "history_hash": digest(events), "seconds": allowance,
                                "contract": CONTRACT}])
        trace.update(status="fallback", request_digest=digest(context), context_bytes=len(encoded.encode()),
                     candidate_count=len(packages), question_count=len(questions),
                     brief_status=context["supplier_brief"].get("status") if context["supplier_brief"] else None,
                     brief_data_sha256=(context["supplier_brief"].get("data_sha256")
                                        if context["supplier_brief"] else None),
                     brief_source_digest=(context["supplier_brief"].get("source_digest")
                                          if context["supplier_brief"] else None),
                     context_s=self.clock() - started, model=os.environ.get("LLM_MODEL"))
        try:
            def validate_answer(answer):
                expected_fields = {"selected_id", "message_index", "quote", "kind"}
                if self.write_response:
                    expected_fields.add("body")
                if not isinstance(answer, dict) or set(answer) != expected_fields:
                    raise StrategyRejected("response_fields")
                selected, index, quote, kind = (answer[k] for k in
                                                ("selected_id", "message_index", "quote", "kind"))
                if selected == "keep":
                    if index != -1 or quote != "" or kind != "none":
                        raise StrategyRejected("invalid_keep")
                    trace.update(status="ok", admitted=True, reason="model_keep", selected_id="keep")
                    if self.write_response and not self.shadow:
                        check = {}
                        body = checked_body(answer["body"], terms, prepared_body=message["body"],
                                            reason_out=check)
                        trace["body_source"] = "model" if body else "deterministic_fallback"
                        trace["prose_check"] = check.get("check")
                        if body:
                            result = copy.deepcopy(move)
                            result["message"]["body"] = body
                            return result, trace
                    return move, trace
                if selected not in packages and selected not in questions:
                    raise StrategyRejected("unknown_choice")
                if (type(index) is not int or index != source[-1]["message_index"]
                        or not isinstance(quote, str) or not 8 <= len(quote) <= MAX_QUOTE_CHARS
                        or quote not in source[-1]["body"]
                        or kind not in ("objection", "conditional_trade", "question", "stated_terms")):
                    raise StrategyRejected("unsupported_current_quote")
                if kind != "question" and not ACTION_CUE.search(quote):
                    if stated_terms_support(quote, [f for f in case["negotiable"] if f != "unit_price"
                                                    and packages.get(selected, {}).get(f) != terms.get(f)],
                                            packages.get(selected, {})):
                        kind = "stated_terms"
                    else:
                        raise StrategyRejected("quotation_without_constraint")
                package_id = questions[selected]["package_id"] if selected in questions else selected
                candidate = packages[package_id]
                changed = [field for field in case["negotiable"] if field != "unit_price"
                           and candidate.get(field) != terms.get(field)]
                if not changed or (selected in questions and questions[selected]["field"] not in changed):
                    raise StrategyRejected("unsupported_trade_fields")
                if kind == "stated_terms" and not stated_terms_support(quote, changed, candidate):
                    raise StrategyRejected("unsupported_stated_terms")
                observation = {"kind": kind, "message_index": index, "public_note_id": None,
                               "quote": quote, "addressed_fields": changed}
                admitted, rejected = admit([observation], case, events, sid, notes,
                                           session_id=self.session_id, prompt_version=CONTRACT)
                trace["assessment_rejected"] = rejected
                from .assessment import condition_supported

                if rejected or not admitted or not condition_supported(admitted[0], candidate):
                    raise StrategyRejected("unsupported_interpretation")
                if refused_candidate(events, terms, candidate):
                    raise StrategyRejected("explicit_refusal")
                if selected in questions and kind not in ("question", "objection", "conditional_trade"):
                    raise StrategyRejected("question_without_constraint")
                if candidate["unit_price"] > terms["unit_price"] and (
                        kind != "conditional_trade" or candidate not in context["current_supplier_packages"]):
                    raise StrategyRejected("unsupported_price_increase")
                cost = total_cost(case, candidate, standard_terms(events), supplier)
                if (not _legal(case, candidate, standard_terms(events)) or not math.isfinite(cost)
                        or cost > ceiling + 1e-7 or cost >= alternative_cost(case)):
                    raise StrategyRejected("cost_envelope")
                if self.clock() - started >= remaining_s - RESERVE_S:
                    raise AdviceExecutionBlocked("strategy consumed execution reserve")
                result = copy.deepcopy(move)
                result["message"]["term_sheets"][0]["terms"] = dict(candidate)
                question_text = questions[selected]["text"] if selected in questions else ""
                result["message"]["body"] = render(candidate)
                if question_text:
                    result["message"]["body"] += " " + question_text
                    trace["question_id"] = selected
                if self.write_response and not self.shadow:
                    check = {}
                    body = checked_body(answer["body"], candidate, required_question=question_text,
                                        prepared_body=result["message"]["body"], reason_out=check)
                    trace["body_source"] = "model" if body else "deterministic_fallback"
                    trace["prose_check"] = check.get("check")
                    if body:
                        result["message"]["body"] = body
                if self.store:
                    self.store.append(admitted)
                trace.update(status="ok", admitted=True, selected_id=selected,
                             evidence_id=admitted[0]["event_id"], quote=quote,
                             selected_cost=cost, cost_ceiling=ceiling,
                             changed=not self.shadow)
                if self.shadow:
                    trace["shadow_selected_id"] = selected
                    return move, trace
                return result, trace

            call_started = self.clock()
            try:
                answer = bounded_call(self.complete_fn, copy.deepcopy(context), allowance)
                if budget:
                    budget.artifact(CONTRACT, digest(context), context,
                                    response=answer.response if isinstance(answer, AdviceCompletion) else answer)
            finally:
                trace["provider_s"] = self.clock() - call_started
            if self.clock() - call_started >= allowance:
                raise TimeoutError("late strategy response")
            if self.clock() - started >= remaining_s - RESERVE_S:
                raise AdviceExecutionBlocked("strategy consumed execution reserve")
            if digest([case, threads, move, supplier]) != snapshot:
                raise AdviceExecutionBlocked("state changed during strategy review")
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
            except StrategyRejected as first:
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
                except StrategyRejected as second:
                    repair_trace.update(status="rejected", reason=str(second))
                    raise
                trace["repaired"] = True
                return result
        except AdviceExecutionBlocked:
            self.disabled = True
            raise
        except Exception as exc:
            if budget:
                budget.artifact(CONTRACT, digest(context), context, error=exc)
            if isinstance(exc, TimeoutError):
                self.disabled = True
            if digest([case, threads, move, supplier]) != snapshot:
                raise AdviceExecutionBlocked("state changed during failed strategy review") from exc
            if self.clock() - started >= remaining_s - RESERVE_S:
                raise AdviceExecutionBlocked("strategy reserve expired") from exc
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
                    except AdviceExecutionBlocked:
                        raise
                    except Exception as second:
                        repair_trace.update(status="rejected", reason=(str(second)
                                            if isinstance(second, StrategyRejected) else failure_reason(second)))
                    else:
                        trace["repaired"] = True
                        return result
            trace["reason"] = str(exc) if isinstance(exc, StrategyRejected) else failure_reason(exc)
            return move, trace
        finally:
            trace["elapsed_s"] = self.clock() - started
            if self.store:
                self.store.append([{"record": "decision", "session_id": self.session_id,
                                    "supplier_id": sid, "history_hash": digest(events),
                                    "update_hash": update, "status": trace["status"],
                                    "reason": trace.get("reason"), "selected_id": trace.get("selected_id"),
                                    "changed": trace["changed"], "contract": CONTRACT}])
            self.latencies.append(trace["elapsed_s"])
            self.admitted += int(trace["admitted"])
            self.changed += int(trace["changed"])
            self.fallbacks += int(trace["status"] == "fallback")
            self.outcomes.append({key: trace.get(key) for key in
                                  ("status", "reason", "selected_id", "admitted", "changed", "elapsed_s",
                                   "request_digest", "context_bytes", "candidate_count", "question_count",
                                   "provider_s", "model", "skill_sha256", "evidence_id", "brief_status",
                                   "brief_data_sha256", "brief_source_digest", "body_source",
                                   "prose_check", "assessment_rejected", "initial_rejection",
                                   "repair", "repaired")})
