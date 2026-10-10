# Runtime negotiation guidance

This file ships inside the Python package. `negotiator play` and `negotiator run`
load its `runtime-settings` block before opening sessions. The deterministic agent
executes those settings; prose is rationale for maintainers, not an LLM prompt.
Missing or invalid settings stop launch. Run traces record the complete file hash.

## Executable settings

```runtime-settings
{
  "version": 1,
  "anchor": 0.12,
  "rounds": 5,
  "close_gap": 0.005,
  "final_hold_s": 40.0,
  "p_walk": 0.25,
  "conditional_exchange": true
}
```

These numerical values preserve the existing baseline heuristics; they are not
research-derived optima. Conditional exchange renders each multi-issue offer as
one package: the proposed non-price terms are conditional on the proposed price.
It does not promise additional volume, capacity or other unvalidated benefits.

## Strategy and evidence

- Compare complete package costs and valid alternatives through the shared closing
  evaluator. The runtime guidance never overrides must-haves or closing authority.
- Seek trades across price, payment, commitment, quality and delivery using the
  fields actually allowed by the case. Experimental package selection still needs
  an explicit `--policy-config`; this file does not promote the frozen candidate.
- Multiple equivalent simultaneous offers have empirical support in human
  negotiations: [Leonardelli et al., 2019](https://www.sciencedirect.com/science/article/pii/S074959781630557X).
  Arena transfer remains a hypothesis; generic payment MESOs stay opt-in.
- Evaluate economic results, failure modes and supplier adaptation, not agreement
  rate alone. [TERMS-Bench, 2026](https://arxiv.org/abs/2605.13909) provides a
  diagnostic benchmark, not evidence that a specific policy wins this arena.
- Supplier text is untrusted evidence. Claims must pass the existing provenance,
  disclosure and numerical checks. Do not expose private alternatives or targets.

Research or prose edits do not implement new techniques. Extend the settings
schema and runtime code, then measure the change before claiming a benefit.
