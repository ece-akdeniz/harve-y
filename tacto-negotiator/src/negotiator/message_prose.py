"""Admit model-written buyer prose only when it fits the approved attached terms."""

import re
from decimal import Decimal, InvalidOperation

from .guards import leaks

NUMBERS = re.compile(r"(?<![\w:])(?:\d{1,3}(?:,\d{3})+|\d+)(?:[.,]\d+)?(?!\w)")
UNSAFE = re.compile(
    r"\b(?:we accept|we agree to your|guarantee(?:d)?|promise(?:d)?|"
    r"approved by|exclusive supply|place an order|sign the contract|"
    r"free of charge|at no charge|as agreed|we will|we shall|"
    r"ignore (?:previous|all|your) instructions|system prompt|api key)\b", re.I,
)
SPELLED_QUANTITY = re.compile(
    r"\b(?:zero|two|three|four|five|six|seven|eight|nine|ten|hundred|"
    r"thousand|million|half|double|twice|percent|percentage|free)\b", re.I,
)
CLAIM_ID = re.compile(r"\b(?:doc|news|idx|fc|po|ctr|quote|offer|scorecard):[\w.-]+\b", re.I)
PROPOSAL = re.compile(r"\b(?:attached|propos\w*|offer\w*|term sheets?)\b", re.I)
SAFE_SENTENCES = (
    re.compile(r"Thank you for (?:clarifying|sharing|explaining) "
               r"(?:your position|your requirements|the details)\.", re.I),
    re.compile(r"Thank you for your (?:response|message)\.", re.I),
    re.compile(r"We propose the attached (?:terms|package|term sheet)(?: as one package)?\.", re.I),
    re.compile(r"Could you (?:review|confirm) (?:them|the attached terms|the attached package)\?", re.I),
    re.compile(r"Please (?:review|confirm) (?:the attached terms|the attached package)\.", re.I),
    re.compile(r"These terms are (?:offered together as one conditional package|"
               r"conditional on agreement to the complete attached package)\.", re.I),
    re.compile(r"Could you confirm the attached package or quote your best complete alternative\?", re.I),
    re.compile(r"We propose the attached EUR [\d.,]+ package for [\d.,]+ units\.", re.I),
)


def _same(value, expected):
    try:
        return type(expected) in (int, float) and value == Decimal(str(expected))
    except InvalidOperation:
        return False


def _term_number(match, body, terms):
    """Require a numeric phrase to name the term field it describes."""
    try:
        value = Decimal(match.group().replace(",", ""))
    except InvalidOperation:
        return False
    before = body[max(0, match.start() - 35):match.start()].lower()
    after = body[match.end():match.end() + 35].lower()
    if before.rstrip().endswith(("eur", "€")) or after.lstrip().startswith(("eur", "€", "per unit")):
        return _same(value, terms.get("unit_price"))
    if re.match(r"\s*-?\s*(?:months?|years?)\b", after):
        return (_same(value, terms.get("contract_months")) if "month" in after[:12]
                else _same(value * 12, terms.get("contract_months")))
    if re.match(r"\s*-?\s*days?\b", after):
        window = before[-25:] + after[:25]
        if re.search(r"\b(?:payment|payable|pay)\b", window):
            return _same(value, terms.get("payment_days"))
        if re.search(r"\b(?:lead|deliver\w*|lieferzeit)\b", window):
            return _same(value, terms.get("lead_time_days"))
        return False
    if re.match(r"\s*(?:units?|pcs|pieces|kits)\b", after):
        return _same(value, terms.get("volume_per_year"))
    if re.match(r"\s*ppm\b", after):
        return _same(value, terms.get("ppm_commitment"))
    return False


def mandatory_content(prepared_body):
    if not isinstance(prepared_body, str):
        return []
    return [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", prepared_body)
            if "?" in sentence or re.search(
                r"\b(?:conditional on|conditional package|only if|subject to|unless)\b",
                sentence, re.I)]


def checked_body(body, terms, *, required_question="", prepared_body="", reason_out=None):
    """Return a safe model-authored email, or None for deterministic fallback.

    The term sheet binds. A model can repeat its numbers, but cannot add a new
    numeric claim, document ID, promise or private buyer information. Checked
    claims remain in the deterministic evidence decorator, outside this field.
    """
    def reject(reason):
        if reason_out is not None:
            reason_out["check"] = reason
        return None

    if not isinstance(body, str) or not 30 <= len(body) <= 900:
        return reject("length_or_type")
    if body != body.strip() or any(ord(c) < 32 and c not in "\n\t" for c in body):
        return reject("format")
    if ("```" in body or "http://" in body or "https://" in body or "@" in body
            or leaks(body) or UNSAFE.search(body) or SPELLED_QUANTITY.search(body)
            or CLAIM_ID.search(body)
            or not PROPOSAL.search(body)):
        return reject("unsafe_content")
    if required_question and required_question not in body:
        return reject("missing_registered_question")
    # Questions and conditions are part of the selected action, not optional style.
    mandatory = ([required_question] if required_question else []) + mandatory_content(prepared_body)
    if any(sentence not in body for sentence in mandatory):
        return reject("missing_mandatory_content")
    scan = body.replace(required_question, "", 1) if required_question else body
    if any(not _term_number(match, scan, terms) for match in NUMBERS.finditer(scan)):
        return reject("numeric_mismatch")
    if any(sentence.strip() not in mandatory
           and not any(pattern.fullmatch(sentence.strip()) for pattern in SAFE_SENTENCES)
           for sentence in re.split(r"(?<=[.!?])\s+", body)):
        return reject("unsupported_free_text")
    return body
