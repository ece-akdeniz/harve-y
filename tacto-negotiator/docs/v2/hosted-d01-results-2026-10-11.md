# Hosted D01 execution — 11 October 2026

Exactly one authorized real Arena D01 sandbox session was created using the actual
adaptive V2 strategy and GPT-4.1-mini-2025-04-14. It failed before submitting a buyer
move. The server subsequently ended it after three automatic timeout moves: no deal,
score 0. This demonstrates actual hosted execution and real inference, but does not
demonstrate successful LLM interpretation or supplier-facing adaptive negotiation.
The cancelled 32-call offline experiment was not run. No D02 or P10 session was created.

## Identity and evidence

- Arena session: `de6f67ea54658727`, case `case:D01`, supplier `sup:DEMO-F1`.
- Experiment Lab run: `04a6789d-593b-4722-a7f4-5f289da374f1`.
- Lab destination: `https://66-201-6-11.sslip.io/`; one publication, individual retrieval
  and ordinary listing verified. The Lab attempt accurately retains status `failed`.
- Artifacts: `/tmp/v2-d01-hosted-execution-2026-10-11/`, including
  `complete-transcript.json`, `execution-report.json`, original decision traces,
  inference ledger, exact Arena write journal, initial and final owned observations,
  and `lab-proof-04a6789d-593b-4722-a7f4-5f289da374f1.json`.
- Approved authorization:
  `/tmp/v2-d01-direct-preparation-2026-10-11/approved-authorization.json`.
  Its single-use consumed marker remains. Original source SHA-256:
  `9d47aec6e5538f5e601f96aa9edb6f76b3ca0ddab6166fd17774a30aa20b25cd`.
  Original dirty source patch and manifest are retained; later fixes do not rewrite them.

**Publication limitation:** the one authorized publication happened when the agent failed,
before the server expired the session. That immutable record contains initial observations,
decisions, fallback, inference accounting and failure, but its terminal evidence is null.
The later authoritative timeout outcome and supplier withdrawal are complete locally in
`final-owned-observation.json` and the exported transcript. They were not remotely
published. No second write or enrichment was attempted. Therefore the remote record
does not satisfy the requested complete terminal-evidence publication requirement.

## What happened

The opening offer was EUR 52.90 per unit, payment in 30 days, a 12-month contract,
effective 1 December 2026. The owner emphasized the existing relationship and cited
a 3.1% wage-index increase with wages representing 28% of cost. These are observed
supplier claims, not independently established full supplier economics.

The interpreter call hit its eight-second deadline. Usage and any output from that
cancelled request are unknown. V2 recorded the ambiguity/uninterpreted-text fallback.
A cancellation race allowed the proposer to start before asynchronous interpreter
cleanup marked the transport stopped. The genuine model proposal completed in about
3.974 seconds and was admitted. Independent economics and action validation accepted
its legal terms. Dispatch then observed the stopped transport and refused submission.

The proposed, **unsent** terms were EUR 50.50, payment in 45 days, a 24-month contract,
effective 1 January 2027. There is no supplier response to this proposal. Subsequent
supplier messages were responses to server-generated timeout moves, followed by
withdrawal. The journal records one session creation and zero buyer action/message
submissions, with no uncertain write pending and no automatic submission retry.

## Behavior and economics

The proposal rationale recognized the potential relationship benefit of longer
commitment. However, it characterized 45-day payment as balancing supplier cash flow;
relative to the opening 30 days this delays the supplier's receipts. Lower price,
later effective date and slower payment all favor the buyer. The trace does not show
that the longer contract compensates the supplier for these changes. Because interpretation
fell back and nothing was sent, genuine supplier understanding, adaptation over rounds,
and negotiated reciprocity remain untested.

Independent nominal proposal cost was EUR 414,299.04: price EUR 403,354.5205479452,
payment EUR 1,344.5150684931507, freight EUR 9,600, with other components zero.
The same-observation fixed candidate cost was EUR 398,400.00; this proposal was
EUR 15,899.04 more expensive. This is a local candidate comparison, not a separate
hosted baseline or a realized deal. Sustainable supplier relationship cost remained
unestimated because a grounded supplier full-cost estimate was unavailable.

The authoritative terminal result reports opening cost EUR 448,810.67, best cost
EUR 408,623.99, no deal cost and score 0. These server results are retained as reported;
the best-cost field is not evidence of an attainable offer received by this agent.

Two calls reserved 196,608 tokens and USD 0.0835584, within the approved ceilings
of 18 calls, 1,769,472 reserved tokens and USD 1. The successful proposal used 3,163
input and 261 output tokens, estimated USD 0.0016828. Total actual spend is unknown
because interpreter usage was not returned; its reservation remains charged against
the allowance. There were no additional inference calls or session reruns.

## Concrete fixes and D02 recommendations

Post-execution fixes synchronously stop model calls when a call times out and collect
owned terminal evidence before a future failed run's sole final Lab publication.
If terminal retrieval remains unavailable after the bounded wait, publication stops
with evidence preserved locally. These changes were checked with two focused regression
tests (2 passed) and scoped Ruff checks (passed), without hosted calls or remote writes.

Before D02, revise the eight-second per-call cap and 12-second combined model allowance
to accommodate observed hosted latency while retaining the official clock, submission
reserve, zero retries and exact inference ceiling. This concrete timing defect must be
addressed; a broad offline evaluation is not required.

Review the proposal instructions for correct payment-direction reasoning and explicit
reciprocal trades grounded in supplier evidence. Preserve the independent arithmetic,
legal bindings and closing authority; do not aim merely to secure an agreement or
tune to hidden simulator behavior. In D02 inspect understanding and allocation across
suppliers, RFQ coverage, package changes and whether the model distinguishes buyer
benefits from supplier benefits. Record relationship-cost uncertainty explicitly.

The existing D02 predecessor gate requires a completed predecessor and admitted
interpretation. This failed D01 does not meet that gate. Prepare a transparent review
of this actual failed run and its resolved blocking defects before adapting the gate;
do not fabricate a successful predecessor or silently bypass it. D02 needs a fresh
exact session, inference and Lab authorization. P10 remains a later separate gate.
