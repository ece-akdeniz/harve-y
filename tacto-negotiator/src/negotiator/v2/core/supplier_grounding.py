"""Pure source/assessment admission shared by the interpreter and selector."""

import re

from . import models as m
from .errors import ContractViolation

_PRIVATE = re.compile(
    r"reservation|fallback[_ ]?(?:cost|price|unit)|target[_ ]?price|ceiling|api[_ ]?key|secret|"
    r"buyer.{0,20}(?:budget|limit)|terminal[_ ]?score|expected[_ ]?(?:action|label)|private", re.I,
)
_CONDITIONAL = re.compile(r"\b(if|unless|provided|subject to|conditional)\b", re.I)
_CUES = {
    "request": r"(?:\b(please|request|need|want|could you|can you)\b|\b(which|what|when|who|how)\b[^?]*\?)",
    "refusal": r"\b(no|not|cannot|can't|won't|refuse|unable)\b",
    "conditional_offer": r"\b(if|unless|provided|subject to|conditional)\b",
    "constraint": r"\b(must|cannot|can't|minimum|maximum|at least|no more|require|only)\b",
    "approval_requirement": r"\b(approv|authori|manager|sign.off)",
    "stated_driver": r"\b(cost|energy|material|inflation|increase|capacity)\b",
    "ambiguity": r".+",
}
_UNKNOWN = {"approval", "discount", "conditions", "contradiction", "scope", "support", "supplier preference"}
_QUESTION_INFORMATION = "Clarify the reported uncertainty."


def ground(draft, projection):
    messages = {msg.message_id: msg for msg in projection.conversation.messages}
    observations = {o.observation_id: o for o in draft.observations}
    if len(observations) != len(draft.observations):
        raise ContractViolation("ungrounded_output: duplicate observation identity")

    def citation(c):
        if not isinstance(c, m.MessageSpan):
            raise ContractViolation("missing_source: evidence excluded from this projection")
        msg = messages.get(c.message_id)
        if (msg is None or msg.speaker != "supplier" or c.session_id != msg.session_id or c.thread_id != msg.thread_id
                or c.end > len(msg.body) or msg.body[c.start:c.end] != c.quote):
            raise ContractViolation("ungrounded_output: invalid message span")
        if _CONDITIONAL.search(msg.body) and (c.start != 0 or c.end != len(msg.body)):
            raise ContractViolation("ungrounded_output: conditional antecedent must be retained")
        return c.quote

    for obs in draft.observations:
        quotes = tuple(citation(c) for c in obs.citations)
        if obs.summary not in quotes or not any(re.search(_CUES[obs.kind], q, re.I) for q in quotes):
            raise ContractViolation("ungrounded_output: quotation does not support bounded observation kind")
        if obs.kind != "conditional_offer" and any(_CONDITIONAL.search(q) for q in quotes):
            if obs.kind not in ("refusal", "approval_requirement", "ambiguity"):
                raise ContractViolation("ungrounded_output: conditional statement mislabeled unconditional")
        if obs.package_fingerprint is not None:
            raise ContractViolation("ungrounded_output: no package reference admitted in this input slice")
    for constraint in draft.reported_constraints:
        quotes = tuple(citation(c) for c in constraint.citations)
        value = str(constraint.value)
        if (not quotes or not any(re.search(r"(?<![\w.])" + re.escape(value) + r"(?![\w.])", q) for q in quotes)
                or not any(re.search(_CUES["constraint"], q, re.I) for q in quotes)
                or any(re.search(r"\b(prefer|would like)\b", q, re.I) for q in quotes)
                or not set(constraint.condition_observation_refs) <= observations.keys()):
            raise ContractViolation("ungrounded_output: unsupported explicit constraint")
        cues = {"==": r"\b(only|exactly|must be|require)\b", "!=": r"\b(not|cannot|can't)\b",
                ">=": r"\b(at least|minimum)\b", "<=": r"\b(at most|maximum|no more)\b"}
        dimensions = {"payment_days": r"\bpayment\b", "lead_time_days": r"\b(delivery|lead)\b",
                      "unit_price": r"\b(price|EUR|€)\b", "volume_per_year": r"\b(volume|units)\b",
                      "contract_months": r"\b(contract|months)\b"}
        if (constraint.dimension not in dimensions
                or not any(re.search(dimensions[constraint.dimension], q, re.I)
                           and re.search(cues[constraint.op], q, re.I) for q in quotes)):
            raise ContractViolation("ungrounded_output: unsupported dimension/operator")
        conditional = any(_CONDITIONAL.search(q) for q in quotes)
        linked = [observations[r] for r in constraint.condition_observation_refs]
        if conditional and not any(o.kind == "conditional_offer" and set(o.citations) & set(constraint.citations)
                                   for o in linked):
            raise ContractViolation("ungrounded_output: conditional constraint lost its antecedent")
    for hypothesis in draft.hypotheses:
        quotes = tuple(citation(c) for c in (*hypothesis.supporting_refs, *hypothesis.contradicting_refs))
        if (not quotes or hypothesis.summary not in quotes or hypothesis.numeric_effect is not None
                or hypothesis.confidence not in ("low", "unknown")):
            raise ContractViolation("ungrounded_output: uncalibrated or unsupported hypothesis")
        if hypothesis.relation == "prefers" and not any(re.search(r"\b(prefer|rather|would like)\b", q, re.I)
                                                        for q in quotes):
            raise ContractViolation("ungrounded_output: preference lacks an explicit cue")
    for uncertainty in draft.uncertainties:
        quotes = tuple(citation(c) for c in uncertainty.citations)
        if (not quotes or uncertainty.summary not in quotes
                or not set(uncertainty.related_observation_refs) <= observations.keys()):
            raise ContractViolation("ungrounded_output: unsupported uncertainty")
    # Internal clarification suggestions do not register outbound actions.
    for question in draft.questions:
        for c in question.citations:
            citation(c)
        if (not question.citations or question.template_id != "clarify:terms"
                or question.unknown_id not in draft.unknowns
                or question.expected_information != _QUESTION_INFORMATION):
            raise ContractViolation("unsupported_capability: unregistered clarification suggestion")
    if not set(draft.unknowns) <= _UNKNOWN:
        raise ContractViolation("unsupported_capability: unregistered question/unknown label")
    for obs in draft.observations:
        if obs.kind == "approval_requirement" and "approval" not in draft.unknowns:
            raise ContractViolation("ungrounded_output: approval authority must remain unknown")
    for a in draft.reported_constraints:
        for b in draft.reported_constraints:
            if (a.constraint_id != b.constraint_id and a.dimension == b.dimension and a.op == b.op == "=="
                    and a.value != b.value and a.status == b.status == "active"
                    and not any(u.kind == "contradiction" and u.blocking for u in draft.uncertainties)):
                raise ContractViolation("ungrounded_output: contradictory constraints need blocking uncertainty")
    return draft



def safe_projection(value):
    """Recursive fail-closed guard; never redact prose while retaining its original identity."""
    if isinstance(value, dict):
        for key, item in value.items():
            if _PRIVATE.search(key):
                raise ContractViolation("private_disclosure: unauthorized projection field")
            safe_projection(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            safe_projection(item)
    elif isinstance(value, str) and _PRIVATE.search(value):
        raise ContractViolation("private_disclosure: unauthorized projection text")

