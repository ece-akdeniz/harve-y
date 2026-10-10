"""Run summaries for experiments (metrics in docs/04-experiments.md)."""


def summarise(run_dir) -> dict:
    """mean/min score, deals, must-have breaks, timeouts, claim results, C lost by component,
    LLM latency p50/p95, fallbacks."""
    raise NotImplementedError
