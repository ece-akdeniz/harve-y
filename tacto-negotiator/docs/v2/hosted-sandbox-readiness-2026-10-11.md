# Hosted sandbox validation before practice — 11 October 2026

## Actual execution update

The user approved direct D01 and exactly one hosted session was executed. It failed
before any buyer submission and ended with no deal, score 0 after server timeouts.
The failed Lab publication was verified; subsequent terminal evidence is local only.
See [actual D01 results and D02 recommendations](hosted-d01-results-2026-10-11.md).
The preparation statements below describe the earlier pre-execution state.

## Priority change: direct hosted D01

The user's latest instruction supersedes the offline-first sequence below. Do not execute the
32-call offline plan. Proceed directly to one genuine hosted D01 sandbox negotiation after
explicit approval. The D01 runner no longer requires an offline review or falsely records
offline verification: its allowance declares `direct_sandbox_validation: true` and
`offline_verification: false`. D02 and P10 still require review of the preceding actual hosted
transcript and fresh authorization. The direct first-stage exception is limited to D01.

Exact current approval artifact:
`/tmp/v2-d01-direct-preparation-2026-10-11/authorization-template.json`.
Scope: one `case:D01` session at `https://arena.tacto.ai`, real
`gpt-4.1-mini-2025-04-14` interpretation and adaptive proposals, at most 18 model calls,
1,769,472 reserved total tokens, 2,048 output tokens per call and USD 1 maximum; one final
Lab publication at `https://66-201-6-11.sslip.io/`. No retries, automatic reruns, additional
sessions, or offline evaluation. The existing conservative accounting convention requires
confirmation as part of approval. Uncertain operations remain journaled and block further writes.

Read-only Arena/model/Lab access checks were refreshed for this request. Four existing focused
adapter/session/gate checks passed, plus the existing uncertain-submission restart/reconciliation
test. No broad test suite was run for this priority change. No hosted inference, session, or Lab
write was performed. After approval, retrieve and analyze the actual D01 understanding,
adaptation, fallbacks, independent nominal economics, Arena outcome and failures, then prepare D02.
The unestimated supplier relationship component remains an explicit limitation, not a fabricated
cost or margin claim. Agreement is an observed outcome, not the execution objective.

The remainder records the prior preparation and is retained for history.

The execution order is now offline GPT-4.1-mini validation, D01 sandbox, D02 sandbox,
then P10 practice. Each hosted stage requires fresh explicit approval of inference,
one Arena session and one final Lab publication. No previous approval is reused.
No hosted inference calls, hosted sessions or remote Lab writes were made during this update.

## Implemented and tested

The existing V2 Lab adapter supports the reviewed D01 price-increase and D02 two-supplier
RFQ contracts as well as P10. It maintains separate assessments and acknowledged histories
per supplier and schedules live bidders serially. The adaptive model receives the target's
complete history and observed rival packages for internal comparison. Deterministic scheduling
does not substitute for the model's interpretation or proposal generation. Rendering continues
to send independently validated own packages; rival-price disclosure is not enabled by these notes.

Economics retains the one-part/one-supplier oracle: D02 proposal evaluation uses a faithful
target-specific economic slice. The D02 executable alternative quote is preserved in each slice.
The shared case coordinator independently compares every live standing offer and the alternative
when closing. Quote standards are parsed with the official reader and retained as explicitly
scoped current quote evidence with attachment provenance. The resolver opt-in admits only
declared session quote records with the official quote parser; default unsupported-layer behavior
and all grounding/economic/action validators remain intact.

The Lab runner refreshes all bidder histories and documents before observing clocks. Global RFQ
round counts must exactly match all acknowledged buyer messages before a new proposal is admitted;
unassignable timeouts stop execution. Closing checks current offer ownership and every live bidder.
Model interruption stops further decisions and submissions. Exact payloads and move IDs remain
durable before POST. One-session transport prevents reopening even after a definite rejection and
restricts messages to the owned session's supplier endpoints. Uncertain opens or messages stop;
read-only exact-history reconciliation is available, without automatic retries or session guessing.

Completed Lab attempts are now finalized only after terminal observations, complete thread retrieval,
decision/economic records and inference evidence are captured. V2 fails the completion gate if
required evidence is truncated. The authorized stage runner uploads the final record once, then
checks exact retrieval and normal listing. It publishes the original failed record too; upload
failure never permits a replacement negotiation. The offline interpretation gate is persisted in
the normal Lab snapshots even if it fails before either simulator session starts.

The stage runner is `experiments/v2/run_hosted_sandbox.py`, composed around the existing
`plan_run`/`run_experiment`, V2 factory, journal and Lab publication APIs. Its default operation
only writes local review templates. The paid offline runner is
`experiments/v2/run_adaptive_milestone.py`; it now includes explicit final publication allowances,
normal Lab evidence for the development interpretation evaluation and failed-gate persistence.

## Read-only readiness evidence

`/tmp/v2-sandbox-readiness-2026-10-11.json` records official case catalogs and team status.
The key is active, D01/D02 are available through the sandbox catalog, and P10 is hosted for
practice. The observed practice quota was 286 remaining of 600. These are observations, not
reservations; all permissions, catalogs and quotas must be refreshed immediately before execution.

`/tmp/v2-hosted-access-readiness-2026-10-11.json` records successful HTTP 200 checks for the
configured Lab listing and the exact model metadata. Current configured Lab destination:
`https://66-201-6-11.sslip.io/`. No credential values are saved. Model metadata access does not
prove completion latency or account billing headroom; the explicit call/token/dollar guard controls
the experiment and stops on failures.

The Lab recommendation remains `e1d931e4fcce49fb8fd341c40052953a`, generation 1, for
`d01-d02-sandbox-serial-v1`. Existing findings reject global stronger anchoring and the measured
payment-response candidate. This standalone intelligence validation does not change that recommendation.

## Authorization sequence

Local preparation artifacts live under `/tmp/v2-hosted-sandbox-preparation-2026-10-11/`.
Every authorization is source-bound, exact-match and single-use. All four templates are initially
unauthorized. Hosted draft templates have no predecessor review hash and cannot execute as prepared.

| Stage | Maximum inference calls | Reserved total tokens | USD ceiling | Arena sessions | Final Lab writes |
| --- | ---: | ---: | ---: | --- | ---: |
| Offline | 32 | 3,145,728 | 2.00 | 0 hosted; 2 in-process Sim | 2 |
| D01 | 18 | 1,769,472 | 1.00 | 1 sandbox | 1 |
| D02 | 36 | 3,538,944 | 2.00 | 1 sandbox | 1 |
| P10 | 18 | 1,769,472 | 1.00 | 1 practice | 1 |

All stages use `gpt-4.1-mini-2025-04-14`, structured outputs, 2,048 output tokens per call,
zero retries and zero automatic reruns. Reservation uses a conservative UTF-8-byte upper bound
plus schema and framing allowance. That accounting convention requires explicit confirmation.
Pricing assumptions were verified against [official OpenAI model documentation](https://developers.openai.com/api/docs/models/gpt-4.1-mini):
USD 0.40/M input and USD 1.60/M output. The offline conservative reservation is USD 1.3369344;
USD 2 is the approved maximum, not a claim of actual expenditure.

First request approval only for `offline/authorization-template.json`: 14 development
interpretations, the existing fixed baseline and one genuine adaptive official-Sim negotiation,
with two final Lab records published to the exact configured destination. Its decision traces,
development predictions, interpretation evaluation, economics and inference ledger are retained.
The provisional development gate requires at least 12 semantically correct examples of 14;
independent transcript review is still required before hosted execution.

Before D01, review the actual offline transcript and Lab proof. Before D02, review the original
D01 transcript, fallbacks, economics, deadline behavior and outcome, then resolve blockers.
Before P10, do the same for D02. A prior-review artifact must bind original files by hashes and
include the exact adaptive predecessor's Lab retrieval proof, admitted interpretation/proposal
evidence and correct environment/case/terminal state. Rebuild the next stage's allowance around
that review hash and request a fresh explicit authorization. There is no automatic stage chain.

## Validation and remaining limitations

Full V2 suite after adapter changes: **1,263 passed, 298 expected xfailed**. The new D01/D02
conformance tests exercise the official in-process Sim with mock inference, both bidder histories,
executable alternative preservation, validated proposals, terminal evidence and Lab Store retrieval.
After runner/script updates: **17 focused adaptive/hosted tests passed**. Lab runner regression
suite: **32 passed**, using a local loopback test server. Scoped Ruff and `git diff --check` pass.
These checks are not hosted negotiation or persuasion evidence. The previously documented unrelated
legacy context failure remains outside this change; no full-repository pass is claimed.

D01 full-cost supplier estimates are unavailable in the loaded public package. The official
relationship formula is retained, but its nominal component is explicitly unestimated when the
oracle receives no supplier estimate. Do not infer hidden costs or claim sustainable margins or
complete realized-cost accuracy from that nominal projection; review the actual Arena breakdown.
The model is told the category goal and that hidden supplier full costs are unknown.

RFQ scheduling is serial. Real supplier reply latency may exhaust another bidder's independent
clock; conservative checks stop or close on current validated evidence. Concurrent supplier
orchestration is not claimed. Multipart cases, automatic process restart/resume, foreign/unowned
session recovery, general claim-based persuasion and automatic Lab-upload retry are not implemented.
Generalization and behavior comparisons across environments await the actual authorized sequence.

Arena contracts were reviewed in the [official API documentation](https://raw.githubusercontent.com/tacto-ai/negotiation-arena-kit/main/brief/api.md).
No final cases or spectator endpoints are used.
