# GPT-4.1 mini hosted comparison — results before Assignment 4

The explicitly approved one-time experiment completed through direct OpenAI with
`gpt-4.1-mini`, returning `gpt-4.1-mini-2025-04-14`. **Transport connectivity works; grounded
interpretation is not ready. Neither benchmark model arm improved on the minimum-cost
baseline. Do not advance to Assignment 4 on this evidence.**

The user approved the provider, alias/snapshot, reviewed P10 and synthetic benchmark
projections, conservative accounting, $5 ceiling and maximum 77 calls. Credentials were
consumed locally from `.env`, never printed or retained in model projections/artifacts.
No Arena session/action or remote Lab write occurred. No provider retry, prompt tuning,
validation relaxation or Assignment 4 was performed during or after the experiment.

## Components and verification

Assignments 1–3 already provided context assembly, grounded interpretation, supplied packages,
official economics, ID selection, rendering, independent validation and reproducible traces.
The earlier readiness task added P10 loading and chat-completions HTTP transport. This follow-up
added a strict documented request-alias/response-snapshot mapping, the combined offline
comparison composition, pre-call dollar reservations and an exact combined approval gate.
The interpreter and selector prompts, input projections and validators were unchanged.

Required local P10 HTTP mock and original three-arm fake benchmark ran before hosted inference.
The complete combined composition also passed its local HTTP mock test. Final gates:
**32 focused checks; 1,209 passed / 298 expected xfailed** in the complete consumed V2 gate;
**1,507** catalogued contracts. Scoped Ruff, frozen V1 replay and whitespace checks pass.
The prior **167 passing Lab tests** remain applicable; no Lab source changed. Earlier inherited
legacy failures and repository-wide Ruff violations were not claimed resolved.

The first hosted call was a strict structured-response connectivity probe: one existing
selection-task option, exact permitted ID, empty quote, no action execution. It passed in
1.637 seconds, using 1,207 input / 60 output tokens. All 74 HTTP model responses subsequently
had the required model identity and usable provider envelopes. No capacity errors, HTTP errors,
usage gaps, truncations or timeouts occurred.

## P10 paired real-model decisions

The fixed official package universe was identical to the local fake rehearsal and the
same-input deterministic baselines. Its complete costs were EUR 1,335,154.08 (42-day delivery,
24-month contract), EUR 1,368,754.08 (56-day delivery, 24 months), and EUR 1,333,891.20
(56-day delivery, 36 months). Buyer inputs and alternatives did not change with language.

| Supplier message | Real selected package/cost | Relative to minimum | Interpretation | Selection/final validation |
|---|---|---:|---|---|
| Which volume can you commit to? | EUR 27.60, 23,400/year, 36 months, 56 days; **EUR 1,333,891.20** | EUR 0 | Rejected; existing fallback | Accepted / valid |
| We prefer delivery in 42 days. | EUR 28.34, 23,400/year, 24 months, 42 days; **EUR 1,335,154.08** | **+EUR 1,262.88** | Rejected; existing fallback | Accepted / valid |

Selected IDs, bound to their distinct snapshots:

- Opening: `sha256:ddd8bbe7e5c5565310b7acb3167be8298d37537f96d5fe7253026e011e38b509`.
- Delivery preference: `sha256:5a2d4e76eaff710db680acdb657c2eb132a9cb22e71f7b39e785de1ed49a75b9`.
- Preference-message deterministic baseline:
  `sha256:4788498ee2dc828c224ad3b36f2d5ac0309297dbb8dfddc8784c96efcfde523f`.

The accepted departure cites the exact approved span “We prefer delivery in 42 days.”
This reproduces the fake P10 selection change and proves one hosted selection passes the
bounded grounding checks. Both interpreter responses fell back with `model_invalid`; the
selector operated on the existing fallback's uninterpreted supplier quote. Thus this does
**not** demonstrate successful grounded interpretation or value added by that interpreter.
P10 consumed four calls, 10,541 tokens and approximately 6.68 seconds of summed model-call
latency. The two final actions and both deterministic baseline traces independently validate.

## Three-arm benchmark comparison

All 24 existing examples ran through all three arms, with identical evaluated candidate
universes across arms and language pairs. The cost-only pair deliberately changed a cost
source while preserving language/packages. Standard examples' official candidate costs were
EUR 431,800 / 432,080 / 401,600; the altered-source case costs were EUR 449,504.08 /
449,784.08 / 437,008.16. Each benchmark arm ultimately selected its minimum-cost package.
There were **no paired language-driven action changes** in the benchmark.

| Arm | Final valid actions | Provisional matches, all 24 | Semantic subset, 22 | Frozen held-out matches | Selection fallbacks | Calls | Model-call latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Minimum cost | 24/24 | 14/24 | 12/22 | 2/8 | 0/24 | 0 | 0 s |
| Direct selection | 24/24 | 14/24 | 12/22 | 2/8 | 10/24 | 23 | 29.24 s |
| Interpretation + selection | 24/24 | 14/24 | 12/22 | 2/8 | 15/24 | 46 | 80.30 s |

Eight held-out examples remain frozen and author-annotated; independent human review is
pending. These are **provisional set matches**, not validated semantic accuracy or proof of
supplier utility. The 22-example score excludes only `forged:0/1`: those minimum-only labels
were tied to fake injected output faults that were not injected into the real model.
The original 24-example score remains available for audit. No label was changed or provided
to the model. Exact IDs, every official cost and grounding references are in the trace files.

The original fake benchmark achieved 24/24 and 8/8 provisional matches in both model arms,
with four selection fallbacks each. Those results reflect scripted responses, not hosted
competence. Its original one-second/2,048-token limits are preserved in its report; this real
run used the prepared P10 hosted limits equally across arms (two calls, 32,768 reserved tokens,
12 seconds model time, eight-second interpretation/four-second selection). This is an
explicit inference-configuration difference, not a prompt/validator change.

## Held-out semantic review of final decisions

A fresh text-to-action review in this task found the frozen sets reasonable as provisional
requirements/clarification diagnostics. No annotations were changed. This review is not an
independent human adjudication and does not establish supplier acceptance or optimal utility.
Both model arms ended at the same minimum action as the control in every row:

| Held-out message | Reviewed semantic issue | Minimum final decision |
|---|---|---|
| Cannot accept delivery in 49 days | Preserve refusal; 21-day minimum is outside refused value | Consistent |
| If contract is 12 months, cannot accept delivery in 21 days | Preserve joint scope; clarify or select 49-day option | Does not resolve stated condition |
| This needs manager approval | Retain unknown authority; ask registered approval question | Does not address approval uncertainty |
| Please consider the price | No supported issue preference/condition; minimum is reasonable | Consistent |
| Require delivery in 21 days and 49 days | Recognize contradictory active requirements; clarify | Contradiction unresolved |
| If delivery is 21 days and 49 days, can consider price | Preserve inconsistent antecedent; clarify conditions | Condition unresolved |
| If delivery is 49 days, can consider price | Preserve antecedent; delivery option or clarification | Does not meet/clarify condition |
| Provided delivery is 49 days, can consider price | Same condition under paraphrase | Does not meet/clarify condition |

These findings concern final decision relevance, not the exact unseen rejected model draft.
Minimum remains economically certified; reported supplier conditions never become canonical
hard constraints merely because a provisional benchmark annotates them.

## Accepted outputs, rejections and semantic assessment

Of **25 actual interpretation calls**, only **one** draft was admitted; 24 were rejected:
21 generic `model_invalid` and three `ungrounded_output`. Across the 24 grounded benchmark
examples, 23 assessments fell back (including one pre-network projection block). The only
admitted interpretation was the exact “Our capacity costs increased.” span, classified as
`stated_driver`, with no invented numeric effect. It retained no explicit `support` uncertainty,
although the prompt requests unknown support for unverified cost claims: structural admission
therefore does not certify complete semantic correctness even for this one output.

There were **49 actual selection calls**, including connectivity and P10: 26 admitted outputs
and 23 grounding rejections. The benchmark alone had 23 admitted selections and 23 rejected
selections. Private-disclosure projection rejection blocked three additional potential calls
(one direct selector; grounded interpreter and selector). It was preserved, not bypassed.
Including either interpretation or selection fallback, **all 24 grounded benchmark decisions**
and **both P10 decisions** relied on a model fallback somewhere. Direct selection had 10/24
fallback decisions. Minimum controls intentionally use the echo interpreter; its fallback
status is not counted as a hosted model failure.

All final actions remained valid because existing certified fallbacks, code-authored packages,
official evaluation and final validation remained active. Valid final actions are **not** the
same as accepted model outputs or correct supplier understanding.

Failure attribution established by this run:

- **Transport/provider:** operational for this approved model and request protocol. No observed
  identity, envelope, budget, HTTP, truncation or timeout failure explains the consumer rejections.
- **Input projection:** the private-limit injection was deliberately blocked before inference.
  This is a functioning boundary, not missing hosted compatibility.
- **Interpreter/model/prompt interface:** 24 returned drafts failed consumer admission. Generic
  `model_invalid` is consistent with schema/assessment validation failure; three failures are
  explicitly grounding failures. The current prompt plus JSON mode did not yield reliable usable
  interpretations. Their exact failed fields cannot be established retrospectively.
- **Selector/grounding interface:** 23 real outputs were rejected for grounding. Accepted P10
  departure and fake positive tests show the validator admits supported departures. They do not
  prove each real rejection is semantically correct; false-positive grounding rejection versus
  bad model quotation/ID/meaning cannot be distinguished from the retained coarse codes alone.
- **Diagnostics:** interpreter rejection does not set the model-call trace's rejection cause;
  only the fallback assessment retains its coarse code. Unsafe rejected raw output is correctly
  withheld. Consequently, transport status can be `success` with no call cause while interpretation
  fails. This is an observability limitation of the existing interpreter, not a model-success claim.
- **Economics/final validation:** all universe checks and final certificates passed. No economic
  manipulation or validation bypass was used to improve apparent success.

## Inference allowance and expenditure

| Metric | Actual recorded value |
|---|---:|
| Hosted calls | **74 / maximum 77** |
| Input tokens | **171,436** |
| Output tokens | **10,856** |
| Total known tokens | **182,292** |
| Missing usage / timeouts | **0 / 0** |
| Summed model-call latency | **117.80 s** |
| Median / maximum call latency | **1.36 / 3.45 s** |
| Uncached usage-derived expenditure | **$0.085944** |
| Conservative retained expenditure reservation | **$1.9398656** |
| Approved ceiling | **$5.00** |

Rates: $0.40 input and $1.60 output per million tokens, from the
[official GPT-4.1 mini reference](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
Cache discounts are not credited. This is usage-derived expenditure estimation, not an account
invoice. All usage was known; rejected outputs still incurred and retained charges. Each
attempt reserved $0.0262144 beforehand. The entire 77-call plan reserved at most $2.0185088.
No additional diagnostic call, retry or unused-allowance experiment was performed afterward.

## Artifacts and next decision

Artifacts under `/tmp/v2-hosted-comparison-first-run`:

- `connectivity.json`: exact initial protocol/model/usage result.
- `report.json`: all 72 benchmark records, P10 comparison, costs, scores, paired changes and
  every call's usage/latency/expenditure reservation.
- `review.json`: safe aggregate rejection analysis and approved-authorization hash.
- 76 hash-verified complete decision traces, including P10 controls and all three arms.
- `fake-p10/` and `fake-benchmark/`: separate local comparators; never reported as real outputs.
- `hosted-started.json`: exclusive run marker. Its embedded plan is the unsigned template;
  the separately checked approval is `/tmp/v2-hosted-comparison-authorization.json` and the
  explicit conversation approval. Do not infer lack of authorization from that template flag.

Improve interpretation/schema/prompt compatibility and sanitized rejection diagnostics before
proposal generation. Preserve withheld unsafe output; record only safe error locations/types
and consumer cause codes. Independently review the frozen held-out labels and semantic spans,
then obtain a new explicit allowance for any follow-up hosted experiment. This run provides
no evidence that unrestricted proposals or Assignment 4 would improve performance.

Remote Arena negotiation still requires separate authorization and the missing V2 observation,
freshness, ownership/reconciliation, execution/recovery and multi-turn composition described
in the readiness report. Hosted inference success does not supply those capabilities.
