"""Bounded, extractive reply interpretation. Never produces prices, actions or facts.

Signals are supplier statements, not verified economics. Deterministic extraction is the
latency-bounded fallback and current implementation; no provider call or hidden model spend.
"""

import re
from dataclasses import asdict, dataclass

MAX_MESSAGES = 64
MAX_CHARS = 64000
RULES = {
    "index_objection": r"\b(?:hedged|hedging|bought forward|fixed energy contract)\b|"
                       r"\b(?:index|indices|market data)\b[^.!?\n]{0,100}"
                       r"(?:not relevant|irrelevant|do not reflect|does not reflect|not our costs)",
    "payment_trade": r"\b(?:faster payment|shorter payment|earlier payment|cash discount)\b",
    "quality_objection": r"\b(?:quality|defect|ppm|chargeback)\b",
    "clause_required": r"\b(?:require|need|only with)\b[^.!?\n]{0,80}\b(?:index clause|indexation)\b",
    "authority_constraint": r"\b(?:approval|authori[sz]ation)\b[^.!?\n]{0,80}|"
                            r"\b(?:committee|director|management)\b[^.!?\n]{0,80}\bapprove\b",
}


@dataclass(frozen=True)
class Signal:
    kind: str
    message_index: int
    quote: str
    confidence: str = "explicit text; economic relevance unverified"


def interpret(events):
    signals, rejected, consumed = [], set(), 0
    start = max(0, len(events) - MAX_MESSAGES)
    truncated = start > 0
    for index in range(start, len(events)):
        event = events[index]
        if event.get("from") == "buyer":
            continue
        body = str(event.get("body") or "")
        text = body[:max(0, MAX_CHARS - consumed)]
        consumed += len(text)
        truncated |= len(text) != len(body)
        for kind, pattern in RULES.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            prefix = text[max(0, match.start() - 12):match.start()].lower()
            if kind == "index_objection" and re.search(r"(?:not|never|no longer)\s+$", prefix):
                continue
            signals.append(Signal(kind, index, text[match.start():match.end()]))
        for result in event.get("claim_results") or []:
            if isinstance(result, dict) and result.get("result") == "contradicted":
                refs = result.get("refs") or result.get("ids") or []
                if isinstance(refs, list):
                    rejected.update(r for r in refs if isinstance(r, str))
                # Without a specific ID, avoid adding more factual assertions this turn.
                if not refs:
                    rejected.add("*")
    return {"signals": [asdict(s) for s in signals], "rejected_refs": sorted(rejected),
            "truncated": truncated}


def evidence_constraints(events):
    result = interpret(events)
    kinds = {s["kind"] for s in result["signals"]}
    return result, ({"index_change"} if "index_objection" in kinds or result["truncated"] else set())
