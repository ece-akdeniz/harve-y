"""Last line of defence before anything is sent (docs/03-playbook.md, universal rules)."""

import re

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
    """Block or repair: must-haves and alternative on accept; complete sheets; monotone
    concessions; unknown IDs removed; ≤ 3 checked claims; no duplicate IDs; no leaks; length."""
    raise NotImplementedError
