"""LLM e-mail writing and reply reading, with a template fallback.

The writer receives a fully decided Move (sheets, claim sentences, question) and only words it.
It must not add figures or IDs. Hard timeout from Settings; on timeout use `template()`.
"""


def compose(move, case: dict, dossier, history: list[dict], timeout_s: float) -> dict:
    """Return {"subject", "body"}; body ≤ 150 words, claim sentences verbatim."""
    raise NotImplementedError


def template(move, case: dict, dossier) -> dict:
    """Deterministic fallback e-mail for any Move kind."""
    raise NotImplementedError


def read(reply: dict) -> dict:
    """Structured signals from the supplier's prose: concerns raised, levers mentioned,
    variants offered, tone. Optional; code-level fields are read without the LLM."""
    raise NotImplementedError
