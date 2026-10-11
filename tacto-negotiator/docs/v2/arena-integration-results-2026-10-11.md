# V2 Arena integration and bounded execution — 11 October 2026

**One official offline negotiation completed; the online negotiation was blocked before session creation.**
No online substitute, second simulator session, live inference, retry, publication or promotion
was performed. The two-run request explicitly permits stopping before online execution if required
safety components or authorization are missing. This result does not achieve the primary objective
of demonstrating live model reasoning and safe completion in both environments.

## Implementation and contract verification

Reviewed the V2 architecture/interfaces, stabilization and latest hosted semantic experiment,
Lab failure analysis, root/package guidance, LAB_PLAYBOOK.md and official kit instructions.
The latest hosted experiment admitted 1/16 interpretations; fifteen failed before grounding.
The union diagnostic incorrectly emphasized SourceRef extra fields instead of MessageSpan errors.
No new inference allowance was inferred from that exhausted authorization.

- Added versioned `grounded-supplier-v3` / `assessment-citation-ids-v1` wire schema. The model
  selects stable, scope/content-derived citation IDs. Code resolves IDs to trusted whole-message
  spans, then applies the original AssessmentDraft schema, supplier grounding and independent
  consumer checks. Unknown IDs, forged spans and buyer citations fail closed. Conditional
  antecedents remain in whole-message spans. Provider schema identity includes the wire schema.
  No admitted live model output demonstrates that the prior hosted failures are solved.
- Retained bounded union diagnostics from both branches; prioritize the actual MessageSpan
  branch, including Pydantic's wrapped validator label. Schema-owned paths are retained and
  unknown keys are replaced by `*`; supplied values and exception prose are never persisted.
- Added a shared public Arena observation normalizer. It retains offer IDs, raw and officially
  completed bindings, standing status, complete ordered buyer/supplier history, claim results,
  attachment text, original-byte hashes and text hashes. Official `closing_terms` and the
  latest quote defaults determine completed terms. Completion does not grant acceptance authority.
- Preserved `final_offer` as actionable but distinct from `open`. Terminal notifications retain
  official result proof and the final normalized conversation; terminal state triggers no new decision.
- Interpretation and selection can see the complete scoped conversation, including changing
  offers and acknowledged buyer actions. V1/V2 body-only interpreter configurations retain their
  previous rejection behavior. New full observation projection is bounded and disclosure checked.
  The existing selector rechecks grounding; supplier text remains untrusted evidence.
- Added optional Lab attachment, acknowledgement and terminal observation hooks. Existing agents
  without hooks retain their behavior. After successful V2 submissions, authoritative thread reads
  supply buyer history. A 409 or uncertain submission never invokes the acknowledgement hook;
  locally appended buyer requests cannot establish execution. This prevents the official kit play
  loop's local request history from being mistaken for acknowledged history after timeout errors.
- Kept the existing Lab runner, recorded-decision coordinator, finite supplied packages, official
  arithmetic, fixed renderer and independent final action validator. No new orchestrator or
  deterministic strategy library, no V1 strategy changes, no closing-authority bypass.

The current recommendation was read from the shared Lab:
`e1d931e4fcce49fb8fd341c40052953a`; three prior findings were reviewed. The initial sandboxed
metadata reads failed to connect; permitted network reads subsequently succeeded. Lab is available.
The exploratory offline run uses the existing dirty-workspace provenance and local persistence;
it is not an immutable comparison campaign or a published candidate.

## Official offline and online compatibility

The official [starter-kit instructions](https://github.com/tacto-ai/negotiation-arena-kit/blob/main/starter-kit/README.md)
identify `arena-sim` as the contract simulator and describe the same API and agent thread contract
for simulator and hosted Arena. The [API contract](https://github.com/tacto-ai/negotiation-arena-kit/blob/main/brief/api.md)
is also present in the pinned local kit.

Installed `arena-kit` is **0.1.0**, pinned revision
`1b5516bb95ef28e37f69aa446dc62168864bca53`. Installed `arena_kit.sim` matches the pinned kit
source byte for byte; SHA-256 `df9a22cd277113ac22be16ecbcf9a9de3258b27aebb80b0a8a3c015979c9404f`.
`arena-sim serve` wraps this `Sim` engine. Run A uses it in process, with the clock enabled,
through the existing Lab client seam. It does not test HTTP routing, header idempotency or
network recovery. The supplied case is public **case:P10**, not bundled simulator case:S01-S03.

| Interface | Official offline | Official online |
|---|---|---|
| Case/session/thread/message shapes | Verified against pinned engine | Official shared contract; read-only case permissions verified |
| Attachments and full thread reader | Normalized in actual run | Same normalizer available; live hosted thread ingestion untested |
| Action validation and economics | Existing V2 pipeline exercised | Shared arithmetic exists; live execution not enabled |
| Closing and durable execution | Sends only certified offers/questions; supplier ends negotiation | Missing V2 authority and durable execution/reconciliation integration |
| Outcome retrieval | Actual owned terminal result retrieved by Lab | Not exercised; no hosted session opened |
| Server/software version | Kit 0.1.0 and pinned source revision | Hosted service build/version not exposed by these reads |

Thus the offline engine and public observation contract are compatible. **Online V2 production
compatibility is not confirmed.** The local-only factory remains deliberately blocked remotely.
Generic/multipart case loading and remote safety integration were not fabricated to satisfy a run.

## Run A — actual official simulator outcome

Lab run: `939a46c9-8689-4aae-8493-a14761fd0d5f`, session `sim1`, case:P10.
One grounded arm, one repetition, `max-sessions=1`; no other negotiation arm ran.
The actual V2 interpreter → proposal → finite generation → official economics → selector →
renderer → independent validation pipeline executed six times. The model transport is explicitly
scripted ambiguity/minimum selection, with no provider access or model expenditure.

| Round | Supplier state before action | Supplier price EUR | Buyer price EUR | Official buyer proposal cost EUR | Action valid |
|---:|---|---:|---:|---:|---|
| 1 | open | 32.88 | 27.60 | 1,333,891.20 | yes |
| 2 | open | 32.22 | 27.60 | 1,333,891.20 | yes |
| 3 | open | 31.56 | 27.60 | 1,333,891.20 | yes |
| 4 | open | 30.90 | 27.60 | 1,333,891.20 | yes |
| 5 | open | 30.24 | 27.60 | 1,333,891.20 | yes |
| 6 | final_offer | 29.59 | 27.60 | 1,333,891.20 | yes |

Each buyer sheet proposes 23,400/year, 36 months and 56-day delivery alongside EUR 27.60;
all exact fixed and negotiable terms are retained in the complete transcript. Supplier's final
response is walked_away. **Actual no deal, official score 0.0, `c_deal=null`, zero timeouts.**
The original result omits `end_reason`; the terminal thread establishes supplier walk-away.
Proposal cost is not realized agreement cost or a no-deal cost.

Read-only official supplier-sheet evaluations, using the actual quote defaults and disabled
supplier estimates, are EUR 1,962,792.50; 1,951,910.29; 1,941,028.08; 1,930,145.87;
1,919,263.67; and 1,908,546.34. All six supplier sheets fail P10's volume must-have.
These post-run evaluations are labeled separately from decision-time candidate evaluations.
They do not authorize accepting a standing supplier offer.

V2 received all six current prices and states, historical offers, attachments and buyer messages.
The terminal observation contains all thirteen messages and walked_away status. Six decision
trace digests and certified payloads verify. Observations and decisions are private local artifacts.

- Interpretation admission: **6/6**, fallback **0/6**. Selection admission: **6/6**, fallback **0/6**.
  These are scripted controls, not hosted reliability or supplier-understanding evidence.
- Proposal changes: **zero**. The existing fixed universe repeatedly selects the official cost
  minimum. No adaptation or strategic superiority is claimed; no model-driven proposal policy
  was added. All supplied prices are below the simulator's attainable agreement threshold.
- Model seam calls: **12 scripted calls**, **0 hosted calls**; measured summed latency
  **0.009638008 seconds**. Complete negotiation elapsed **0.687742498 seconds**.
- Inference expenditure: **USD 0**. Scripted token usage is unknown; the ledger conservatively
  charges **196,608 reserved tokens**, which are not provider tokens or expenditure.
- Official score is on the kit's 0–1 scale. No online buyer score exists for this assignment.

The successful run preceded the final authoritative-acknowledgement hook tightening and immutable
catalog representation fix. The run's saved provenance and traces remain unchanged and verify under
the compatible wire serializer. The final hooks have read-only unit verification; **the negotiation
was not rerun**. Its original history is corroborated by the final official thread retrieval.

## Run B — stopped before execution

Read-only credential/quota/case verification against **https://arena.tacto.ai** succeeded,
with transport retries disabled. No session POST, manual move, hosted inference or spectator
endpoint was used. Both D01/D02 sandbox cases and P10 practice are accessible. Authoritative
quota snapshot: **303 used / 297 left / 600 limit**. This current server allowance supersedes
historical documentation's 200-session limit; it is a snapshot, not a future guarantee.

Concrete blockers:

1. No fresh hosted-inference configuration/spending authorization; the previous 19-call
   authorization is exhausted and incompatible with the changed source/prompt/schema.
2. V2 has no issued production closing authority for accept/walk-away and complete closing checks.
3. V2 lacks the remote durable execution/feedback/reconciliation integration required to preserve
   move identity, exact certified payloads and safe recovery after uncertain results.
4. The registered V2 factory remains local-only and supports the reviewed single-part P10 input;
   it cannot safely substitute arbitrary hosted cases or multipart/RFQ sessions.

The user authorizes one online negotiation session, conditional on these checks; this is not an
inference-dollar allowance or permission to bypass authority. No online outcome, rounds, offers,
admission rate, latency, action validity, model expenditure or buyer score is reported.

## Evidence and verification

Original Lab record and the complete exported transcript:

- `/tmp/v2-arena-integration-offline-2026-10-11/runs/939a46c9-8689-4aae-8493-a14761fd0d5f/run.json`
- `/tmp/v2-arena-integration-offline-2026-10-11/complete-transcript.json`: every original event,
  terminal normalized history, all six decisions, economic batches, validations and supplier evaluations.
- `/tmp/v2-arena-integration-offline-2026-10-11/integration-report.json`: metrics and online preflight.
- `/tmp/v2-arena-integration-offline-2026-10-11/traces/939a46c9-8689-4aae-8493-a14761fd0d5f/sim1/`:
  six observation/decision pairs and terminal observation, including attachment text/provenance.
- `/tmp/v2-arena-online-preflight-2026-10-11.json`: credential presence/verification, case access,
  quota and blockers. No credentials are exported.

`experiments/v2/export_arena_integration.py` is a read-only exporter; it verifies original decision
traces and never opens a session. Simulator-creating integration tests were deliberately not run
because this assignment allows only one offline negotiation. The new tests use fabricated public
observations and nonnetworked client stubs to test state, grounding, schema and acknowledgements.
Final focused validation counts are recorded in the experiment log. No full repository acceptance,
live model quality gate or remote deployment readiness is claimed.

## Comparison and next steps

Only offline contract behavior was measured. Online metadata access succeeded, but there is no
hosted negotiation outcome to compare. A plain scripted supplier does not predict online supplier
reasoning. Even the fixed local strategy did not adapt to offers; richer observations alone do
not create strategy intelligence. No superiority claim is supported.

Next implement the missing remote safety components behind existing V2 ports and Lab runner,
including issued closing authority and complete checks, durable execution/reconciliation and
verified hosted-case ingestion. Separately prepare a bounded fresh inference allowance and
independent semantic review of the new citation format. Only then conduct the single online
negotiation with no automatic retry or extra session under a fresh approved execution plan.
Model-driven proposal work remains separate from this interface correction; do not add a second
orchestrator or replace official economics to obtain an agreement.
