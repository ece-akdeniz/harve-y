# Assignment 3 — bounded strategic selection and offline comparison

11 October 2026, Europe/Zurich. Existing working tree preserved. No hosted inference,
Arena quota, credentials, live execution, persistence, commit, push, V1 changes or
Assignment 4 implementation. T4.4 and its consumed contract now have a working offline
slice; proposal intelligence, full factory/config activation, full recorded codec and
negotiation performance remain unfinished.

## Implemented pipeline

`SelectorResponse` implements exactly `selected_id`, `supporting_quote`, and the inherited
`negotiator-v2/1` schema version. Extras, term edits, missing quotations and empty IDs fail.
`BoundedModelSelector` implements the unchanged `ActionSelectionPolicy.select_action`
signature. It first obtains the existing certified minimum-cost decision, then requests
one `select` result from the existing injected asynchronous gateway. No new gateway purpose
or proposal generation is introduced. `DeterministicSelector` exposes the existing minimum
control through the specified selection module.

Selection verifies original candidate, evaluation and batch hashes, approval disposition,
assessment content identity, snapshot/state/recipient binding and approved source hashes.
The selected candidate ID must belong to that exact approved batch. It maps back to the
original evaluation and contents; models cannot supply altered economics or term sheets.
The actual offline coordinator runs supplied generation, official evaluation, selection,
fixed rendering and independent final validation, preserving exact encoded payload bytes.
Questions are separate actions with an empty economic result, never zero-cost offers.

The prompt is `src/negotiator/v2/intelligence/prompts/grounded-selection-v1.txt`.
Explicit `SelectorConfig` fixes provider/protocol/model/prompt/schema IDs, token/time/input/
output bounds and approved supplier-message hashes. A future provider transport must honor
that prompt and the total input-plus-output token reservation. No hosted transport is supplied.
The selection cap is four seconds; the experiment uses one second of total model time.

## Authorized input projection

`SelectInput` retains the exact batch/snapshot and original approved assessment identity.
Each option contains code-authored package fingerprints, exact negotiable bindings and the
**delta** in official buyer cost from the cheapest approved package, with currency. There
are no absolute buyer cost totals, reservation values, ceilings, internal targets, estimates,
score labels, fixture admissible sets or response schedules in production requests.
Supplier statements cannot alter official costs. Their commercial relevance and willingness
implications remain uncertain hypotheses.

Only explicitly hash-approved supplier source bodies can support the assessment or a selection.
Exact session/thread/message offsets and quotes are checked, with full conditional antecedents.
Documents, observed sheets, claims, mixed/foreign messages, unapproved bodies, private prose,
numeric hypothesis effects and unsupported evidence references are rejected. Assessment
text is recursively checked, including nested summaries, unknowns, citations and IDs. Inputs
are rejected rather than silently redacted or truncated under an original identity. The
shared pure source-grounding helper moved to `core/supplier_grounding.py` so both consumers
retain the existing import boundaries and the interpreter's existing checks.

Approved hashes are caller authorization, not a confidentiality classifier. The lexical
private-data guard is defense in depth; arbitrary approved prose can still contain secrets
that the guard does not recognize. Independent purpose approval of source content remains
required. All candidate economics are trusted code outputs of the real evaluator/validator,
not authenticated remote facts merely because hashes agree.

A small bounded history projection includes acknowledged attempts only when a corresponding
acknowledged send operation has matching recipient/session/case and an applicable state
version. Draft and foreign attempts are excluded. Current-assessment refusals retain their
scope, dimension and validated original citations. Internal memory, raw buyer history,
private rationale and unverified response artifacts are excluded. Twelve history entries,
twenty options and 16,000 serialized input characters are the default bounds; oversized
input falls back without truncation. Earlier assessments/refusals, question answers and
role changes need a separately authorized richer history projection.

## Supporting reasons, questions and fallback

Every departure from the certified minimum and every clarification needs an exact approved
supporting quote. Offer departures must cite a commercial cue relevant to a changed issue.
Narrow explicit delivery/contract/payment/price phrase checks reject correct-quote/wrong-option
cases, including choosing the explicitly refused option or a value contrary to the quoted
condition. These are grounding checks, not deterministic supplier utility or negotiation
heuristics. Arbitrary entailment, complex negation, bundled trade value and likely acceptance
are not certified. Those require independent semantic review and real-model measurement.
The minimum permits an empty quote; a nonempty quote must still be valid.

The shared fixed catalog registers `clarify:terms`, `clarify:approval` and
`clarify:conditions`. The latter two ask who must approve/pending status and which permitted
terms belong together. Each has a fixed reviewed-in-code template; generation and evaluation
reject unknown IDs. Rendering checks registered membership. Independent final validation
accepts only catalog text and rejects appended assertions or arbitrary wording. Outgoing
text never includes model rationale, supplier quotes or generated commitments.

One coordinator ledger now binds either model consumer, including the direct-selector arm
with a deterministic echo interpreter. All gateways inside that scope share the two-call,
token, elapsed compute/model/deadline and fallback/submission reserves. Unknown usage retains
its full reservation. Invalid/refused/malformed/late/unaffordable/ungrounded results return
the original certified minimum decision with fallback reason and call attribution. External
cancellation propagates. A model failure never changes the evaluated batch. If no approved
fallback exists, the coordinator retains cannot-decide behavior.

The trace retains filtered requests, model configuration/schema hashes, raw-output hashes,
permitted accepted responses, elapsed time, nullable usage, charged reservations and selector
rejection cause. Unsafe raw output is withheld. Fallback reason/attribution also appear on the
decision. Official snapshots/fingerprints/costs and validated exact action bytes survive trace
JSON reload. These diagnostic artifacts confer no durable ownership or sending authority.

## Paired benchmark and measured local results

`tests/fixtures/v2/selection-pilot.json` contains 12 pairs / 24 scenarios. Delivery,
commitment, refusal scope, conditions, approval, greetings, irrelevant wording, unsupported
claims, contradictions, injection, forged IDs/quotes and a cost-only intervention are included.
Each selection arm receives identical registered candidates and official economic results.
The cost-only pair holds supplier language/packages fixed while an economic source changes.
The fixtures extend a clearly synthetic relationship case with legal delivery/commitment
options; they do not modify frozen P10 or V1 goldens.

Four paired groups / eight examples are frozen as held-out before any pilot-driven prompt
tuning; no tuning was performed. Their SHA-256 is
`ef9c9d1de0bec90c07ef7185aa12209bd917f4d8bd5325351df6af33316311fc`.
The runner verifies the freeze hash and equal economic batch hashes across arms. Admissible
**sets** are separate author annotations; independent human review is pending. Reviewers
should assess quotes/conditions/refusal scope, approval uncertainty and the commercial
trade-off against the fixed packages, then approve or revise the sets before real scoring.
There is no claim that these are independently reviewed labels or an unseen-model holdout.

The separate `selection-pilot-fake-responses.json` is an explicit recorded response schedule.
It never enters production prompts. The three arms are minimum-cost, direct LLM selection
from approved raw spans retained as uninterpreted observations, and grounded interpretation
followed by selection. All share a two-call ceiling, 2,048 total reserved tokens, one second
total model time, and the same compute/deadline/fallback/submission reserves. The direct arm
uses one call; the grounded arm uses up to two. Equal ceilings do not imply equal actual usage.

| Fake-response arm | Valid actions | Provisional set matches | Held-out matches | Grounded departures | Selector fallbacks | Calls | Charged tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| Minimum | 24/24 | 14/24 | 2/8 | 0 | 0 | 0 | 0 |
| Direct | 24/24 | 24/24 | 8/8 | 10 | 4 | 23 | 11,776 |
| Interpreter + selector | 24/24 | 24/24 | 8/8 | 10 | 4 | 46 | 23,552 |

Every actual fake model call reports unknown token usage; token figures are conservative
charges, not measured consumption. Machine-dependent fake transport latency is reported
separately in `/tmp/v2-selection-pilot/report.json`. Grounding/admissibility/set matching,
fallbacks, inference and latency have separate counters and complete denominators; missing
records score as missing. Exact spans and accepted departures are structural grounding
measurements, not independently measured semantic support. There are no model precision/
recall, semantic competence, negotiation outcomes, real-model latency or hosted-spend results.
Perfect scripted matches reflect the supplied schedule, not evidence of an effective strategy.

Focused integration demonstrates three distinct affordable offers under identical economics:
minimum commitment-36/delivery-21, a supplier-requested commitment-12 option, and a higher-cost
supplier-requested delivery-49 option. Fixed clarification is selected for approval/conditional
uncertainty. Greetings preserve the minimum. Forged source/batch IDs, unrelated or unsupported
quotes, explicit wrong options, private nested content, arbitrary question IDs, edited outputs,
model failures, exhausted tokens, late/hung results and cancellation are exercised. Approved
questions also pass independent validation; edited question text fails. These are fake-response
routing and boundary demonstrations only.

Reproduce without hosted calls:

```bash
.venv/bin/python -m pytest -q tests/v2/integration/test_grounded_selection.py
.venv/bin/python -m experiments.v2.run_selection_pilot --output /tmp/v2-selection-pilot
.venv/bin/ruff check src/negotiator/v2 tests/v2 experiments/v2
.venv/bin/python tests/v2/replay_v1_baseline.py
.venv/bin/python tests/v2/catalog.py
git diff --check
```

The full scoped gate retains the complete L/M and Assignment-2 module/symbol requirements,
adding `--v2-require strategy.selection` and `--v2-dto-require SelectorResponse`. Existing
scaffold selection tests still xfail on the absent full `adapters.recorded` binding; no test
assertion or absence policy was weakened. Introduced tests are catalogued explicitly and
parent tasks remain partial. Final verification counts are recorded in the test catalog.

Repository-wide Ruff still has four inherited violations in unchanged V1 evaluator/guards/
runner files; V2/tests/experiment Ruff passes. Frozen V1 first-message replay matches 3653046.
No unrelated V1 cleanup was made.

## Assignment 4 contract handoff — design only

The minimal next revision is an explicit versioned `propose` gateway task, typed permitted
input and strict output added to the existing complete task/input union. Do not disguise it
as selection or simulation. Its input needs authorized evidence/assessment/history plus
code-authored legal domains, exact fixed/negotiable fields and bounded price-grid instructions,
without private ceilings/targets or evaluation labels.

Extend the consumed proposal/intent contract with joint issue directives, explicit conditional
trade linkage, bounded legal price exploration (range/grid origin/tick/maximum evaluated
points) and validated strategic priority. Keep optional legacy single-issue intents compatible
or explicitly version the consumers; reject unsupported combinations. Models request bounded
search and trade conditions, while code constructs full packages, enforces cent/tick/bounds/
options/must-haves, evaluates every generated candidate and certifies final membership. Supplier
conditions remain reported hypotheses, never economic or acceptance authority.

Within two calls, compare `interpret + propose` followed by mechanical priority/cost selection
against the existing `interpret + select` arm. A fused assessment/proposal task would require
an explicit separate contract revision. Keep a baseline and registered clarification in each
admitted universe and preserve independent final validation, shared reserves and exact trace
identities. New packages require a common-universe comparison to separate generation coverage
from selection quality. No Assignment 4 contracts or generation behavior were implemented here.

Final scoped verification: **1,177 passed, 298 expected xfailed**; **36** focused
Assignment-3 tests pass; regenerated manifest contains **1,475** expanded test contracts.
V2/tests/experiment Ruff, frozen V1 replay and `git diff --check` pass. Expected failures
still identify absent unrelated capabilities; SelectorResponse accounts for four former
absent-export xfails now passing.
