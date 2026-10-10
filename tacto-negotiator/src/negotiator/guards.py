"""Last line of defence before anything is sent (docs/03-playbook.md, universal rules)."""

import re
import math

from arena_kit.cost import closing_terms, must_haves_ok, total_cost
from arena_kit.docs import standard_terms

LEAK_PATTERNS = [
    re.compile(p, re.I)
    for p in (
        r"\bbudget\b",
        r"\btarget price\b",
        r"\burgent(ly)?\b",
        r"\bno (other )?alternative\b",
        r"\bwe (have|need) to (close|sign) (today|quickly|now)\b",
        r"\bour (maximum|limit) is\b",
    )
]


def leaks(body: str) -> list[str]:
    """Phrases that would reveal urgency, budget or a missing alternative."""
    return [p.pattern for p in LEAK_PATTERNS if p.search(body)]


def check(case: dict, move, email: dict, thread_state, facts: dict):
    """Validate one final outgoing action. Raise ValueError instead of repairing its economics."""
    if not isinstance(email, dict):
        raise ValueError("outgoing message must be an object")
    action = email.get("action")
    if action:
        if not isinstance(action, dict) or action.get("type") not in {"accept", "walk_away"}:
            raise ValueError("invalid close action")
        if action["type"] == "accept":
            offer_id = action.get("term_sheet_id")
            found_cost = None
            for sid, events in (thread_state or {}).items():
                from .evaluator import eligible_sheets, supplier_for

                std = standard_terms(events)
                supplier = supplier_for(facts.get("estimates"), sid, std) if isinstance(facts, dict) else None
                match = next((cost for cost, sheet_id, _ in eligible_sheets(case, events, supplier)
                              if sheet_id == offer_id), None)
                if match is not None:
                    found_cost = match
                    break
            from .optimizer import alternative_cost

            if found_cost is None or found_cost >= alternative_cost(case):
                raise ValueError("acceptance must reference a current eligible offer below the alternative")
        return email

    subject, body = email.get("subject", ""), email.get("body", "")
    if not isinstance(subject, str) or not isinstance(body, str):
        raise ValueError("subject and body must be text")
    if len(subject) > 200 or len(body.split()) > 150:
        raise ValueError("outgoing message exceeds subject or body limit")
    if leaks(body):
        raise ValueError("outgoing message reveals private urgency or budget information")
    sheets = email.get("term_sheets") or []
    if not isinstance(sheets, list) or len(sheets) > 3:
        raise ValueError("outgoing message must contain at most three term sheets")
    options = case.get("term_options") or {}
    supplier_id = move if isinstance(move, str) else None
    for sheet in sheets:
        terms = sheet.get("terms") if isinstance(sheet, dict) else None
        if not isinstance(terms, dict):
            raise ValueError("term sheet must contain terms")
        price = terms.get("unit_price")
        if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
            raise ValueError("unit price must be finite and positive")
        if any(key not in case.get("negotiable", []) for key in terms):
            raise ValueError("term sheet contains a field outside the case negotiation schema")
        for field, choices in options.items():
            if field in terms and choices and terms[field] not in choices:
                raise ValueError(f"term sheet has an unsupported {field}")
        events = thread_state.get(move, []) if isinstance(thread_state, dict) else thread_state or []
        std = standard_terms(events)
        from .evaluator import supplier_for

        supplier = supplier_for((facts or {}).get("estimates"), supplier_id, std)
        complete = closing_terms(case, terms, std)
        if not must_haves_ok(case, terms, std):
            raise ValueError("term sheet violates a case must-have")
        cost = total_cost(case, terms, std, supplier)
        if not math.isfinite(cost) or complete.get("unit_price") is None:
            raise ValueError("term sheet does not resolve to complete finite terms")
    return email
