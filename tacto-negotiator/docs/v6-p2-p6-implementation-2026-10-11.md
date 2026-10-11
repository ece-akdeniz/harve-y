# V6 supplier intelligence: P2–P6 implementation and gate record

Date: 11 October 2026. Base source: `279f7a8348f4f94f0de650cb5f990aeaff794ab4`.
All changes are in the opt-in worktree. `configs/score-push-v6.json` remains the default.
This record describes local evidence, not a commercial score improvement or rollout.
The candidate at that stage had byte identity
`bcea19954ff7fb95e94de195670df614218fd9f410b570242bef33be6ab56e3d`.
The manifest file now identifies the later final-offer-review candidate; this earlier
identity remains in the provider-probe report. Re-run
`python scripts/fingerprint_v6_candidate.py` before any hosted comparison;
any changed identity needs a new freeze and evaluation record.

## P2: source-linked assessment

`assessment.py` admits observations independently from the model's selection. Every
admitted observation records the session/case/supplier, source ID and role, exact
source span, fields, condition, interpretation type, prompt version, history digest,
uncertainty and lifecycle. Conditional sentences retain antecedent and consequence;
ambiguous splits remain unresolved and cannot support a changed package. Field cues,
refusal cues and question cues are checked against the cited quote. Newer explicit
refusals supersede older same-field observations, retaining the old record. A current
explicit resolution blocks a historical note from justifying a new trade.

The append-only `assessment.jsonl` sits beside the owned session journal. On restart,
source-valid facts are reconstructed from current owned history; changed or foreign
sources are discarded. Provider reservations are appended before calls, so an unknown
attempt is charged after restart and the same update cannot be queried twice. The
`shadow-v1` mode collects evidence while sending the prepared V6 move unchanged.
Public dossiers remain scoped to the selected supplier. Fixed-volume commitments now
require the source price unit and unit of measure to match the briefing; bad or
missing units abstain.

## P3: bounded package selection

`select-v1` supports serial single-supplier capacity and renewal. One response
contains observations and the selected complete package ID. Packages come from
current supplier sheets, approved case options and bounded one/two-field exchanges.
Selection is checked against independent source admission, active conditions, current
refusals, legal options, must-haves, full buyer cost and the executable alternative.
The initial envelope allows no cost increase above the scheduled V6 move. A price
increase requires a current explicit matching conditional supplier sheet. Rendering
uses code-owned terms and fixed wording. No model rationale enters the outbound text.
Paired synthetic capacity constraints change the selected field; a renewal fixture
verifies that the same contract transfers to a second family. These are local
behavior checks, not supplier acceptance evidence.

## P4: questions

`questions-v1` adds at most one registered question per supplier session to the
same response schema. Every question carries one legal complete package and two
feasible branches: keep the prepared move or pursue the attached package. The model
can select only an ID; code appends the fixed question to the selected package.
Questions are absent below a 45-second remaining window, when a question is still
unanswered, or after the session's one-question limit. Values already supplied by
the supplier are excluded. No message-only action is enabled. Local tests verify
package attachment, no repeat, an unsupported question's fallback and time reserve.
Actual answer usefulness remains an experiment metric, not a local gate result.

## P5: separate final review and routing

`bounded_review` is a separate opt-in `final_offer_risk` policy. It evaluates one
legal same-price counter against the current valid standing offer and a concrete
must-have-compliant quote or current-contract alternative. It records gain, possible
loss, `p* = gain/(gain+loss)`, sensitivity, unpriced continuation and a 20-second
minimum deadline. The binary accept/walk screen admits the counter only when the
configured maximum walk probability is below `p*`. An absent executable
alternative leaves the standing offer with the coordinator. No hidden post-run
utility or model confidence enters the review. Tests cover the threshold, absent
alternative, one-counter limit and deadline. This mode is not included in V6.

The async runner still disables package advice and logs its capability skip.
Cost-target paths still precede the adviser. Multi-supplier and async selection
are intentionally gated on separate ablations; no result for those paths is
claimed. Their V6 execution and closing paths remain available.

## P6: evaluation audit and rollout decision

The exposure manifest labels all checked-in practice cases and known suppliers as
development evidence. P10 and the known practice cohort cannot be a clean hosted
holdout. Local tests cover the engineering scenario matrix where fixtures exist:
paired constraints, conditional exchanges, explicit refusal, historical/current
conflict, renamed identities, per-unit facts, final offers, provider faults,
restart and deadline behavior. They are designed examples, not an independent
supplier-disjoint holdout. The separately authorized 30-call provider-only probe
was run sequentially against `gpt-6-sol`, with a fresh HTTP client per call and
no Arena session. Its measurements are in
`experiments/v6-provider-probe-2026-10-11.json` (SHA-256
`850d7743434d946baf7b192a94dff85f4dd7881c4366a45602356544be1ad5b5`;
probe script SHA-256 `1ec059c75964b0cf4071d75d6a8b6eebb236f1713b526a0e4329debf6f5e3bbd`).
The original complete P10 request was unavailable; all three variants were
reconstructions. The probe records provider HTTP and response parsing together.

| Contract/payload | Valid / calls | Observed wall time | Failure |
|---|---:|---:|---|
| Legacy, all three variants | 15 / 15 | 1.60–3.02 s | None |
| Combined, saved P10 opening | 0 / 5 | 7.67–8.16 s | 3 invalid JSON, 2 read timeouts |
| Combined, capacity delivery | 5 / 5 | 2.62–3.51 s | None |
| Combined, conditional commitment | 5 / 5 | 2.67–6.00 s | None |

Combined validity was 10/15 (67%); nearest-rank p95 wall time was 8.16 s.
Across all 30, validity was 25/30, with 30,440 input and 5,054 output tokens
reported for the 25 valid calls and unknown usage for five failures. This
exploratory batch does not estimate a reliable tail under concurrency; it is
already enough to reject the proposed 95%-valid and six-second p95 gate for
this frozen candidate. The failed P10 outputs' finish reasons were not saved,
so timeout versus completion-token exhaustion cannot be assigned precisely.
No Arena screening follows a failed inference gate. The 12 + 18 Arena sessions
remain unspent; question and final-review arms need separate budgets and gates.

| Gate | Local status |
|---|---|
| Engineering | 112 relevant tests passed (111 in sandbox, one local dashboard socket test outside it); full Ruff passed. Full suite cannot complete here because `uv` and `data/package` are absent and an async simulator test stalls. |
| Inference p95/schema validity | Exploratory sequential probe failed (10/15 combined valid; p95 8.16 s); representative concurrency remains unmeasured. |
| Behavior on frozen independent cases | Unmeasured; development examples pass locally. |
| Commercial matched arms | Unmeasured; one prior P10 run is exposed and did not change its package. |
| Promotion | Withheld. V6 stays default and the new modes remain opt-in. |

The arm configs and byte hashes are:

| Arm | Config | SHA-256 |
|---|---|---|
| B shadow | `configs/score-push-v6-shadow.json` | `acd83bb5b09ffcb7361bab96bc6efac75ec6f1782bfaf19ec0b72ac57ea8afd5` |
| C selection | `configs/score-push-v6-select.json` | `ae6bc0079f460567f5103d5e1f7ad7ec221d7d3b0bbcc1b948f479694b196310` |
| D questions | `configs/score-push-v6-questions.json` | `c1f3f15ab2a4131c4dd509f35780e4278378d4123014e9a92dea1fd566555488` |
| E final review | `configs/score-push-v6-final-review.json` | `f351a3f03454fe3e330bdee39383062e30710191f488781fec2b6d35f92223f3` |

The A control is `configs/score-push-v6.json` (hash in the P0/P1 record).
No provider model, settings, live data release or fresh holdout has been frozen.
The separate evaluation must pin those before the first hosted arm and report
all sessions, including fallbacks, no-deals and incomplete outcomes. Any tuned
cohort becomes development evidence and cannot be reused as a clean holdout.
