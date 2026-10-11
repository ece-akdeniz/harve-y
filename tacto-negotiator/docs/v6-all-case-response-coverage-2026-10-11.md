# V6 response coverage across practice case types

Date: 11 October 2026. Status: **local opt-in implementation; no Arena session or
provider call for this change**.

Arena lists 19 practice cases, of which ten are hosted today. Those ten cover all
seven case types. The existing deterministic agent already routes every type. The
new `configs/score-push-v6-all-cases.json` enables a separate buyer response writer
for an already approved, single-sheet email on every type. The only config change
from `score-push-v6-skilled.json` is `llm_response_mode: all-v1`.

| Case type | Hosted practice cases | Decision path with `all-v1` | Writing handoff |
| --- | --- | --- | --- |
| Price increase | P01, P02 | Existing expected-cost target and closing | Serial, after decision |
| Renewal | P03, P04 | Existing guarded strategy and final review | Serial, after decision |
| RFQ | P05 | Existing multi-supplier coordinator | Async preview outside lock; exact move match before journaling |
| Bundling | P07 | Existing package and volume rules | Serial, after decision |
| Raw material | P08, P18 | Existing fixed-volume/index rules | Serial, after decision |
| Capacity | P10 | Existing guarded strategy and final review | Serial, after decision |
| Quality | P11 | Existing quality package/chargeback rules | Serial, after decision |

`src/negotiator/skills/response/SKILL.md` tells the writer to use the current
supplier reply, source-scoped brief, case requirements and approved quantitative
terms. It adds no decision authority. Code still owns package selection, legal and
economic checks, accept, walk-away, verified claims and final dispatch. In
`all-v1`, the strategy and final advisers choose from their existing menus without
generating email text; the writer then authors the email for the selected move.
This avoids requiring the decision model to complete a longer combined response.

The writer is bounded to two calls per supplier and at most six seconds per call,
with at least twenty seconds left for execution. It runs only for one-sheet emails
without existing references or attachments, so a rewrite cannot drop verified
claims, a forecast attachment or simultaneous offers. It may write a later email
after an evidence-bearing opening. Model prose passes the same numeric, source,
commitment and private-information checks as the earlier V6 writer. A skipped,
invalid or failed call leaves the prepared email intact. The async runner previews
outside its coordinator lock and uses the prose only when the live move exactly
matches the preview; journaling and retries still use one final payload.

Local evidence: all seven fixture types admitted a safe model body; a saved P11
quality and P07 bundling situation each passed the serial handoff with a fake
provider; a serial quality runner dispatched model prose; the local two-supplier
RFQ simulator sent model prose with zero timeouts under the full candidate config
and a real clock. The CLI launch and zipped
package resource were checked. These checks
establish routing and safety behavior. They do not establish that the model will
write valid prose in every hosted case, improve scores, or meet live latency.
An exploratory compressed-clock RFQ diagnostic of an earlier draft produced
timeouts, including in its baseline control. The current candidate's hosted RFQ
latency remains unmeasured.

Source manifest: `experiments/v6-all-cases-source-manifest.json`, candidate identity
`3257be9d2c67d644ae6e021573917f8b567e156ebe1002250c6f1ad4612e106e`.
Config SHA-256: `3e526e4ad6c691c37ef49a1d9032dcb29096a1631cc66f95fb0f3752b51e6779`.
