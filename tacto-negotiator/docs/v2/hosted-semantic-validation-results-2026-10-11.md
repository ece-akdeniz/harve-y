# Hosted semantic validation — authorized one-time results

11 October 2026, Europe/Zurich. **Do not proceed to Assignment 4.** The authorized experiment
completed once with all 19 provider responses successful, but only one of 16 interpretations
was admitted, and that output contained no commercial understanding. The two P10 selections
were admitted and reproduced the previous choices while interpretation fell back. The semantic
acceptance gate is **not satisfied**; independent human evaluation remains pending.

The user explicitly approved direct OpenAI `gpt-4.1-mini-2025-04-14`, the reviewed configuration,
at most 19 calls, USD 1.00 and 311,296 reserved tokens under the UTF-8 byte/schema/framing
convention. The prepared plan was checked for exact equality before authorization was recorded.
The existing executable runner was invoked once, with no retry, automatic rerun, Arena
negotiation or remote Lab write. No validator, prompt, schema, frozen label or experiment
configuration changed during execution or analysis. Assignment 4 was not implemented.

## 1. Allowance, transport and artifact integrity

| Measure | Actual |
|---|---:|
| Calls attempted | **19/19** maximum |
| Provider transport successes | **19/19** |
| Interpretation calls | 16: fourteen development texts plus two P10 |
| Selection calls | 3: one probe plus two substantive P10 decisions |
| Conservative reserved tokens | **311,296** |
| Full pre-attempt dollar reservations | **USD 0.4980736** |
| Reported input tokens | 52,925 |
| Reported output tokens | 4,866 |
| Total reported usage | 57,791 tokens |
| Uncached usage-derived cost estimate | **USD 0.0289556** |
| Calls with missing usage | 0 |
| Summed call latency | 53.705 seconds |
| Retries / new negotiations / remote Lab writes | 0 / 0 / 0 |

Cost is an estimate from the approved rates and reported usage, not a provider invoice.
Reservations are not refunded when a response is rejected by a consumer. Both amounts remain
below the USD 1.00 ceiling. All provider envelopes had the expected snapshot, completed text
responses and bounded usage. There were no transport errors, refusals, timeouts, truncations or
capacity failures. Strict connectivity passed with the sole permitted minimum ID and empty quote.
Provider transport success must not be reported as consumer admission or semantic correctness.

Original outputs are in `/tmp/v2-semantic-validation-hosted-2026-10-11/`:

- `hosted-started.json`: exact approved plan, with authorization/accounting flags true.
- `authorization-template.json`, request preview/reservations and `local-preflight/`: separately
  labeled preparation/mock controls; not counted as hosted model results.
- `report.json`, `predictions.json`, `connectivity.json`, `review-pending.json`.
- `p10-0.json`, `p10-1.json` and each same-input `*-baseline.json`.

The separate authorization is `/tmp/v2-semantic-validation-approved-2026-10-11.json`.
The execution log is `/tmp/v2-semantic-validation-hosted-execution-2026-10-11.txt`.
All four retained P10/model/baseline trace digests and final payload certificates verify;
both P10 model economic batches equal their respective deterministic baseline batches.
Rejected raw interpretation outputs remain withheld. Originals were not edited or re-exported.

The current executable plan still matches the approved source/prompt/schema/data identities:
source fingerprint `61465b339746c0509360af61d63f481903f7cae71af51f4d9f5a0362c3a1095e`.
The frozen held-out digest remains
`ef9c9d1de0bec90c07ef7185aa12209bd917f4d8bd5325351df6af33316311fc`.
No held-out calls or label changes occurred. Source/schema/labels were verified again after
execution. The new analysis tool and reports do not alter the approved execution source set.

## 2. Interpretation admission, semantics and fallback

| Denominator | Admitted | Rejected / fallback |
|---|---:|---:|
| Fourteen development interpretations | **1/14 (7.14%)** | **13/14** |
| Two P10 interpretations | **0/2** | **2/2** |
| All interpretation calls | **1/16 (6.25%)** | **15/16** |

All fifteen rejections are at the **schema validation stage**, with coarse cause `model_invalid`
and the same safe diagnostic:

```json
{
  "stage": "schema",
  "category": "schema_mismatch",
  "field": "observations.0.citations.0.*.session_id",
  "error_type": "validation"
}
```

The greeting “Hello, thank you.” is the sole admitted development example. Its assessment has
empty observations, constraints, hypotheses, uncertainties, questions and unknowns. That is
reasonable for a greeting, but demonstrates no substantive supplier understanding.

Every other development example falls back: single/multiple preferences, refusal, conditional
refusal, combined/nested conditions, contradiction, approval, ambiguity, cost assertion,
injection, volume question and conditional commitment. Both P10 interpretations likewise fall
back. The fallback preserves the scoped original supplier text as an explicitly uninterpreted
ambiguity with `supplier interpretation unavailable` and `model_invalid`. It is not a successful
interpretation and does not inherit the meaning of the rejected model response.

### Automated semantic score is not independent human evaluation

The unchanged automatic evaluator reports **1/14 provisional semantic matches**, with all fourteen
critical-error reviews missing. It scores the admitted greeting and gives no understanding credit
to the thirteen fallbacks. Its observation-kind recall is zero and precision undefined because
no commercial observations were admitted.

This measures the availability of usable exported assessments under provisional development
labels. It does **not** prove thirteen reasoning errors inside the model: those responses were
rejected before meaning could be inspected, and their raw content is not retained. A structural
bottleneck may be obscuring correct or incorrect reasoning. Exact representation labels also
have known limitations, especially for greetings, injection and unknown wording.

The evaluator's `critical_errors=0` is **not an evaluated zero-error result**: there are no
independent critical-error annotations. The separate analysis reports critical errors as null
and preserves all human-review fields as null. Fourteen development assessments and two P10
selection decisions remain independently unadjudicated; the two P10 assessments also lack an
independent semantic judgment. No acceptance-gate success is claimed from automatic scores,
agent inspection or absence of counted critical errors.

### Grounding remains substantially untested by admitted model outputs

There are **zero rejections recorded at the grounding stage**, but fifteen interpretation
responses failed schema validation before reaching it. The one output reaching grounding is
empty. Therefore zero grounding-stage failures cannot establish quote/span correctness,
conditional understanding, or reliability on unsupported economic assertions. It also must not
be read as evidence that the fifteen rejected citations were sound.

The two substantive selections pass bounded membership, approved-citation/economic support and
final action validation. Their grounding evidence is narrower and discussed below.

## 3. Repeated citation failure: evidence and diagnostic limit

The safe field path locates the first observation's first citation, but does **not** establish
that `session_id` was copied incorrectly. `Citation` is `SourceRef | MessageSpan`, and the
sanitizer retains only the first Pydantic error. A failing MessageSpan can first produce
`SourceRef.session_id` extra-field errors, because a session-based span is not a SourceRef.
The union branch name becomes `*`; the meaningful MessageSpan error can be later in the list.

A separate, explicitly **local synthetic control** uses correct source IDs and one deliberately
incorrect offset: `end = len(quote) + 1`. It yields the exact same persisted diagnostic. The
full safe error-type/path list shows first `extra_forbidden` at `SourceRef.session_id`, then
other SourceRef branch errors and finally `value_error` at MessageSpan's `ordered_offsets`
validator. Correcting that synthetic offset restores DTO admission. This control is not a
reconstructed hosted response, a repaired prediction, or an additional inference call.

The provider schema bounds start/end to nonnegative integers but does not encode the cross-field
requirement `end - start == len(quote)`. Runtime validation enforces that relationship. The prompt
asks the model to count characters and copy identities; request inputs do not supply a ready-made
full-span citation. **Hypothesis:** guessed offsets/quote lengths, another MessageSpan rule, or
incorrect citation branch shape may explain repeated schema rejection. The current diagnostic
cannot distinguish those causes, and discarded raw responses prevent retrospective adjudication.
Do not assert that all fifteen failures were wrong offsets or wrong IDs.

The previous stabilization's first-error diagnostic is consequently more informative about stage
and location than historical generic failures, but not sufficiently informative about nested
union rejection. No validator or diagnostic implementation was changed in this assignment.

## 4. P10 selection and official economics

| Supplier message | Selected validated package | Forecast official cost | Delta from minimum | Interpretation / selection |
|---|---|---:|---:|---|
| Which volume can you commit to? | EUR 27.60; 23,400/year; 36 months; 56 days | EUR 1,333,891.20 | EUR 0 | Fallback / admitted |
| We prefer delivery in 42 days. | EUR 28.34; 23,400/year; 24 months; 42 days | EUR 1,335,154.08 | +EUR 1,262.88 | Fallback / admitted |

Both final rendered actions are independently valid. The opening selection is the certified
minimum and has no supporting citation. The preference selection cites the complete exact
span “We prefer delivery in 42 days.” and chooses the 42-day package. The evaluated universe
is unchanged: EUR 1,335,154.08, EUR 1,368,754.08 and EUR 1,333,891.20 for the original three offers.

Nonblind **agent inspection**, separately identified in the analysis artifact, finds the opening
package a defensible response within the allowed volume terms and the preference departure a
plausible accommodation. Neither is independent human evaluation or proof of supplier utility.
A preference does not require paying the delta; minimum selection can remain economically
reasonable. No negotiation occurred, so these are proposed costs, not realized agreement costs.

The selector received the fallback's original quote and could respond directly to it. There is
**no demonstrated contribution from the improved interpreter**. Both substantive selections
are admitted (2/2), with zero selector fallbacks; including the probe gives 3/3 selections.
The probe is a connectivity/control result, not a third meaningful strategic decision.

## 5. Comparison with the previous hosted experiment

| Measure | Previous hosted experiment | This hosted experiment |
|---|---|---|
| Provider responses | 74/74 successful | 19/19 successful |
| Interpretation admission overall | 1/25 | 1/16 |
| Selection admission overall | 26/49 | 3/3, including trivial probe |
| Same two P10 interpretations | 0/2, fallback | 0/2, fallback |
| Same two P10 selections | 2/2 admitted | 2/2 admitted |
| P10 selected package contents/costs | Minimum; 42-day preference package | Exactly the same contents and costs |
| Exact interpretation rejection cause | Generic historic metadata; raw withheld | Repeated schema/citation path, union branch unresolved |
| Hosted selection benchmark | 24 examples, three arms | Not repeated; no held-out calls |
| Usage-derived uncached cost estimate | USD 0.0859440 | USD 0.0289556 |

The two P10 selected-content hashes match the previous run, even though snapshots and candidate
IDs differ. Direct comparison shows **no improvement in P10 interpreter admission or final
choices**. The development corpus differs from the original benchmark; percentages over 25
versus 16 interpretations cannot support a general improvement claim. The previous 26/49
selection rate also cannot be compared directly to a one-option probe plus two P10 selections.
This is not a randomized prompt/schema ablation or a repeated held-out benchmark.

The earlier mock success and this run's mock preflight success were reproducible authored
controls. Their contrast with live admission demonstrates why mock scores do not validate
supplier understanding or robust source copying.

## 6. Readiness decision and smallest next step

**Assignment 4 is not ready to proceed.** The preregistered criterion requires at least 12/14
usable, semantically acceptable development interpretations. Only 1/14 was admitted, so its
operational usability condition is unmet even before independent adjudication. Independent
human review is also pending. Good provider connectivity and two valid P10 selections do not
satisfy the supplier-understanding prerequisite.

The next implementation assignment should be a narrow **citation-interface and diagnostic
compatibility correction**, with no bargaining strategy or validator relaxation:

1. Make failures distinguish SourceRef branch noise from the relevant MessageSpan rule using
   bounded, schema-owned error types/paths. Continue withholding inputs, exception prose and
   rejected raw responses.
2. Supply deterministically computed, copyable source-span metadata or a scoped citation catalog
   in the approved interpretation projection, so the model need not invent IDs or count quote
   characters. Preserve exact source membership, text identity, offsets, negation and full
   conditional scope at independent validation. Scope any DTO/projection amendment explicitly.
3. Test realistic wrong offsets, padded/foreign identities, wrong union shapes, missing sources
   and correct spans through the same consumers. Freeze that correction and expectations before
   another separately authorized hosted run; the present one-time allowance is consumed.
4. Obtain independent human adjudication of the retained greeting, unavailable-understanding
   cases and both P10 decisions. Lost conditional scope/authority and cost attribution still
   need substantive evaluation once responses can be admitted.

This recommendation is a proposal, not implemented work. Do not reconstruct discarded model
outputs, relabel held-out examples, remove the quote-length rule, coerce malformed citations,
start a second hosted run, or implement Assignment 4 from these results.

The earlier [Lab failure analysis](hosted-semantic-validation-and-lab-failure-analysis-2026-10-11.md)
also remains applicable: fixed below-floor packages explained those no-deal simulator controls,
while current offer sheets, terminal status, acknowledged buyer history and production closing
are missing from the local bridge. No new Lab outcome evidence was generated by this offline run.
After supplier understanding meets its gate, those inputs are necessary for meaningful
multi-round proposal-strategy research through the existing interfaces.

## 7. Reproducible local analysis

The analysis is stored separately in `/tmp/v2-semantic-validation-hosted-analysis-2026-10-11.json`.
Reproduce it with a fresh output filename; this command has no inference or negotiation capability:

```bash
.venv/bin/python -m experiments.v2.analyze_semantic_validation \
  --run /tmp/v2-semantic-validation-hosted-2026-10-11 \
  --previous /tmp/v2-hosted-comparison-first-run \
  --out /tmp/v2-semantic-validation-hosted-analysis-new.json
```

The tool verifies budget/digest/certificate/economic invariants, separates all-call/development/
P10 denominators, compares original P10 package contents and marks human review pending. The
synthetic union diagnostic is clearly labeled. Scoped Ruff and whitespace checks pass. No new
production behavior or contract was introduced, so no repository-wide passing gate is claimed
from this analysis task.
