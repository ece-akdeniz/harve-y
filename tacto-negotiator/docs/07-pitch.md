# Pitch: demonstrate procurement judgment

Target: strong track performance plus an understandable, evidence-backed case for the overall
jury. Neither a polished interface nor one high-scoring run proves the agent is a winner.
Confirm track weighting and overall-title criteria with organizers; they remain unresolved.

## Core claim

Our agent finds better procurement agreements and shows the evidence and trade-offs behind
its decisions. Support this with measured runs. Do not present simulated savings as proven
real-world impact or imply supplier economics are known exactly.

## Five-minute track pitch (plus two-minute Q&A)

1. **30 seconds — decision:** a supplier asks for an increase; show why headline price alone
   hides financing, coverage, freight or continuity costs.
2. **45 seconds — approach:** code computes packages; the model interprets and explains;
   a coordinator checks every close. Show the distinctive decision capability, not a module list.
3. **Two minutes — actual replay:** source evidence -> supplier hypothesis -> two feasible
   packages and their C -> observed response -> final decision. Include relationship assumptions
   and uncertainty. Explain why the rejected package was worse.
4. **One minute — measured results:** baseline versus candidate on named sets and repeats;
   normalized score, failures, latency and limitations. Separate development from holdout.
5. **45 seconds — transfer:** what could help a real buyer, what would require human approval
   and further validation, and one concrete next integration. Do not claim production readiness.

## Minimal viewer

Use the existing trace as the single source: thread timeline, source IDs, complete packages,
cost components, supplier assumptions, guard outcomes and concise decision reasons. A small
static HTML or React replay is enough. It must work without live model or arena requests.
Evaluation owns it; Samet supplies decision records. Start with a practice replay before freeze.

## Evidence requirements

- One measured success involving a meaningful non-price trade-off; a justified walk-away is
  also useful. Do not fabricate an ideal trace if the desired case does not occur.
- A counterexample or failure and the change it motivated.
- Repeated baseline/candidate results, with run count and configuration; no best-run-only claim.
- Clear distinction between observed facts, estimated supplier costs and policy hypotheses.

Slides freeze Sunday 12:00. Prepare the practice replay and fixed narrative beforehand. Ask
whether final results can be displayed live after the final without modifying frozen slides.
Do not promise zero timeouts or real-world savings before evidence exists.

## Questions to prepare

Why this package? Show the arithmetic and evidence. Why trust the claim? Show provenance.
What if the model fails? Show a tested fallback trace. Does it generalize? Show the holdout and
its limits. Does it protect supplier viability? Show sensitivity, not a claimed private floor.
