# V2 negotiation repair: deadline-focused plan

Date: 11 October 2026 (Europe/Zurich). Status: implementation plan, not implemented.

**Objective:** complete a coherent D01 negotiation that responds to the supplier, survives model rejection without destructive repetition, and sends a professional message explaining its validated offer. Preserve independent economics, closing authority, deadlines and exact submission ownership.

Budget the first implementation and local verification pass at **3–4 engineering hours**, then reassess. These are timeboxes, not delivery guarantees. If less time remains, use the reduced scope below. Do not start another architecture rewrite or broad experiment campaign.

This document prioritizes the next work over the broader post-D01 research backlog. It does not replace the runtime safety requirements. The request that produced it is for a plan; it launches no experiments or implementation. For later hosted work, reuse applicable explicit session authority and prepare the required fresh source-bound allowance; consumed authorization files cannot be reused. Repository release-freeze restrictions still apply to push/deployment.

## Evidence that determines the priorities

The latest reviewed completed D01 is run `c4577ad0-5ddd-4667-98e7-d543a46162e4`, session `63485a27db038691`. Its original artifacts are under `/tmp/v2-d01-full-test-2026-10-11-03/execution/`; preserve them. This is newer than the original no-submission D01 report.

| Observed behavior | Engineering consequence |
| --- | --- |
| First buyer proposal: EUR 50.90, 30-day payment, 24 months. Supplier countered at EUR 51.60 with the same payment/duration. | There was a real opportunity for continued bargaining; not every turn was broken. |
| Next three model proposals failed commercial grounding with `unsupported_claim`. | Make rejection reasons actionable and reduce redundant model-generated labels. Rejected output is absent from these traces, so the exact historical label errors are unknown. |
| Fallback sent EUR 48.60, 60-day payment, 24 months four times, including after explicit objection. | A legal minimum-cost package is not an adequate negotiation fallback. |
| Interpreter latency grew 2.7 → 4.2 → 5.9 → 7.3 seconds, then timed out at approximately eight seconds. Output grew from 301 to 1,156 tokens before timeout. | Stop paying for repeated verbatim history generation. History growth is a plausible contributor, not an isolated causal measurement. |
| Supplier issued a final offer, then withdrew after another identical buyer proposal. No closing event was recorded. | Route final offers through explicit closing evaluation before considering another counter. |
| Every offer used the same one-line body. | The renderer and validator deliberately enforce exact fixed text; a prompt-only writing change cannot work. |

The review verified all five decision trace digests. An offline replay with a scripted invalid proposal reproduced identical fallback terms on two different recorded histories, including one containing the supplier's objection. Replay evidence: `/tmp/v2-pipeline-review-2026-10-11-replay.json`. Relevant existing tests: 80 passed across adaptive proposal, commercial effects, grounded model and hosted sandbox suites. Passing those tests establishes neither adaptation nor negotiation quality.

PD1 lifecycle and terminal/publication repairs already have separate implementation reports. Preserve them; do not redo those projects because an older document still lists them as deferred.

## Delivery order and timeboxes

Work in one narrow candidate with a captured starting diff/source manifest, preserving the existing dirty workspace. Execute these steps sequentially; no multi-agent coordination project is required.

| Order | Timebox | Deliverable | Exit condition |
| --- | --- | --- | --- |
| 1 | 45–60 min | History-aware fallback and final-offer routing | Replayed refusal/final-offer histories cannot produce the old repeated fallback loop. |
| 2 | 45–60 min | One-call fast path and precise commercial diagnostics | No hosted interpreter call merely to copy text; valid proposals survive code-derived labels; invalid terms remain rejected. |
| 3 | 25–40 min | Professional deterministic email renderer | Message acknowledges the situation and reproduces the exact approved package, with no additional model call. |
| 4 | 45–60 min | Focused replay, integration checks and review bundle | Evidence below passes; source/config and remaining limitations are recorded. |

If a step exceeds its timebox, cut optional behavior rather than weaken checks. Do not spend the remaining window polishing dashboards, prompts or long explanations.

## 1. Stop the fallback loop first

Primary files: `strategy/proposal.py`, `strategy/testing.py`, `adapters/lab.py`, `adapters/online.py`, and the existing shared closing seam.

Replace the hosted adaptive arm's unconditional fixed-minimum fallback with a small explicit decision policy:

1. On authoritative `final_offer`, invoke the existing shared closing evaluator before model work. Under this deadline-focused policy, choose its independently validated accept/walk result. Do not equate finality with acceptance or bypass the alternative comparison. Record this as a deliberate conservative policy; richer last-round counters can wait.
2. After ordinary model failure, inspect acknowledged buyer packages and subsequent supplier responses. Do not reset to the seed candidate universe as though this were an opening turn.
3. Permit a last validated buyer package to be held at most once only when it remains legal/current and no subsequent supplier response has rejected it. Freshly validate it; an old certificate is not reusable authority. Since compact interpretation is deferred, treat a substantive supplier counter after that package conservatively as grounds not to auto-repeat it.
4. Otherwise, use one registered clarification if no equivalent question has already been sent since the latest substantive supplier update and enough time/rounds remain. If clarification is exhausted or closing is due, use shared closing evaluation.
5. For an opening failure with no buyer history, prefer the same bounded clarification/closing policy rather than inventing an aggressive anchor from a test fixture.

Use canonical term bindings/package fingerprints for repetition detection, not message IDs or changing snapshot hashes. Obtain prior actions from acknowledged history. A changed supplier message ID alone does not reset the repetition guard. Hold/clarify counts can initially be derived from this history; a new durable strategy-state subsystem is unnecessary.

Keep refusal-aware strategy separate from universal action legality: a deliberate repeated offer may be a future strategy, but the automatic failure path must not silently repeat it. Record `action_origin`, rejection reason, repetition disposition and closing reason without changing original run artifacts.

## 2. Remove avoidable inference work and rejection fragility

Primary files: `factory.py`, `intelligence/interpreter.py`, `strategy/proposal.py`, `economics/effects.py`, relevant DTOs/prompts and `core/diagnostics.py`.

**Fast path:** construct attributed supplier observations directly from trusted message spans and call the proposer once. The current interpreter is largely being asked to reproduce exact text; code can preserve that evidence without inference. Pass the proposer the existing scoped conversation, current standing reference and acknowledged buyer packages so it can reason about the actual response. Mark the assessment as deterministic evidence preservation, not successful model interpretation. Keep the current path selectable for comparison; name/version the new mode explicitly.

Do not silently satisfy a predecessor gate requiring genuine interpretation with this new mode. D01 evaluation must state what was exercised; D02 stays outside this batch. Compact semantic extraction, delta memory and a combined rich interpretation/proposal schema are later work if this one-call path proves insufficient.

Keep existing input bounds and original decision deadline. Do not fix latency by increasing every timeout or adding a repair/critic call. If context exceeds the bound, fall back explicitly; do not silently drop a refusal or current term sheet. Begin with the existing bounded conversation rather than a new summarization system.

**Commercial labels:** term direction is already computable from the reference and proposed bindings. In a versioned fast-path response contract, ask the model for bindings, supplier citations and a concise internal rationale; compute request/offer/unknown labels in code. Do not require the model to reproduce arithmetic direction labels merely to admit an otherwise valid package. Preserve complete-field, option, must-have, precision, source-scope and independent economic checks. Record that code-derived labels do not certify free-text reasoning or supplier willingness.

Do not silently overwrite contradictory labels in the existing contract. Preserve its validation for historical compatibility. The new contract should omit those redundant output fields and explicitly record the derivation/version.

Add bounded diagnostics such as `request_direction_mismatch`, `offer_direction_mismatch`, `missing_value_uncertainty`, `missing_binding` and `foreign_citation`, including affected field names and expected/actual structured labels where safe. Do not persist credentials, entire private prompts or unrestricted rejected prose to debug one label. Log timeout separately from a proposer call that was never admitted to transport.

## 3. Send a professional email without another LLM call

Primary files: `execution/render.py`, `execution/validation.py`, and focused renderer tests.

Ship deterministic, parameterized email templates first: opening proposal, revised proposal, holding response and clarification. Keep the existing closing message path. Select the template from the decision/history; fill commercial values exclusively from the approved package.

The email should have a greeting, a grounded acknowledgement where supported, a readable proposal sentence/list, a clear question and a sign-off. Describe concessions relative to an explicit reference. Do not claim compensation, guaranteed volume, savings, supplier margin or an agreement merely because a package was validated. Use a neutral greeting if no reliable contact name is available.

Illustrative revised-proposal wording, **only if those exact terms are selected**:

> Guten Tag,
>
> Thank you for your revised offer. We propose EUR 51.20 per unit, with payment in 30 days, a 24-month contract and an effective date of 1 December 2026.
>
> Could you accept this package as set out in the attached term sheet?
>
> Kind regards,
> Procurement team

This example is not a price recommendation or an approved action. A later template can acknowledge a verified concession, but never invent a buyer concession when the package actually worsens the supplier's terms.

Update validation alongside rendering: validate the allowed template ID/slots and reconstruct the expected text from approved inputs. Require exact package/text agreement, permitted acknowledgements and no private facts. Preserve exact encoded payload hashes through validation, journaling and submission. Do not replace today's exact-body guard with acceptance of arbitrary model prose.

A free-form LLM email writer is deferred. The deterministic version meets the immediate communication need with zero added inference latency and a much smaller validation surface.

## 4. Verification and the next trial

Use saved D01 observations before spending another hosted session. Run targeted regressions for these behaviors:

| Scenario | Required result |
| --- | --- |
| Supplier counters the initial EUR 50.90 package at EUR 51.60 | Next action reflects the counter or follows the documented fallback; no automatic reset to EUR 48.60/60 days. |
| Invalid model proposal after an explicit objection | Exact refusal-triggering package is not automatically resent. |
| Repeated model failure or repeated clarification | Bounded transition to shared closing; no endless hold/question loop. |
| Authoritative final offer | Shared closing evaluation happens before inference; any close is independently validated. |
| New one-call path | No hosted copy-only interpreter request; provenance and truthful stage metrics retained. |
| Illegal or incomplete model bindings, foreign citation | Rejected despite code-derived commercial labels. |
| Email number or acknowledgement tampering | Final validation rejects it; no journaled POST. |
| Advisory timeout, stale state, uncertain POST | Existing admission, reserve and execution protections still hold. |

Run the affected adaptive-proposal, commercial-effects, grounded-model, hosted-sandbox and Lab integration tests; add renderer/closing tests for the new behavior. Include Lab runner tests if its interfaces change. Run scoped Ruff and `git diff --check`. Broad suite reruns are warranted only by shared-contract changes or unexplained failures, not as a substitute for the behavioral checks above.

Freeze source/config/prompt identities and retain baseline versus candidate replay evidence. If applicable hosted authority and time remain, run **one D01 capability trial** through the tracked runner with a fresh exact allowance. Keep model identity fixed to isolate pipeline changes; maintain the existing bounded session/inference/publication ceilings. Inspect every turn before considering another run. No automatic retry campaign.

Pass requires acknowledged buyer actions, no unintentional repeated rejected package, professional text matching the term sheet, appropriate final-offer handling, intact safety checks and complete terminal evidence. Report model/fallback origins and elapsed time per turn. A no-deal can pass execution checks but requires a separate commercial explanation. One agreement does not prove strategy superiority. Compare actual offers and realized outcome; the cheapest generated candidate is not evidence of an attainable deal.

## Cuts and stop conditions

**If only 60–90 minutes remain:** ship step 1 plus its refusal/final-offer regressions first. Add the deterministic email only if it fits with validation. Retain existing model timing and mark rejection/latency repair incomplete. Do not open a hosted session merely because a prettier message is ready.

Defer D02/P10 expansion, multi-supplier allocation, free-form email generation, learned opponent models, lookahead, new frameworks, general durable strategy memory, broad benchmarks and dashboard changes. Reuse existing publication recovery and arithmetic rather than rebuilding them.

Stop a trial sequence after a safety violation, unresolved write, missing terminal evidence or renewed repetition. Preserve evidence and fix the specific cause locally. If the implementation window expires, deliver the verified subset and remaining gaps; do not advertise unfinished behavior as ready.

**Review deliverable:** a small diff, saved replay comparison, focused test results, source/config fingerprint, one optional D01 result, and a candid disposition: execution capability, negotiation behavior, economic outcome, remaining limitations.
