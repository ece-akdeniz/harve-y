# V2 architecture compliance checklist

Apply to each task and milestone. Check only with linked evidence; missing code, passing fakes and a model explanation cannot satisfy a production criterion. “Not in this task” lists the owning later task; it does not excuse a violated boundary in code already changed. [Contracts](C-interfaces.md) and [tests](test-catalog.md) define the objective gates.

| Check | Objective evidence | Gate |
|---|---|---|
| Scope preserved | git diff touches assigned V2/tests/docs paths; V1 production/defaults/deps untouched unless separately assigned | Every task |
| Strict contracts | Required-prefix schema/signature tests pass; immutable tuple fields, literal version and finite Decimal values; extra/invalid types rejected | Core/component |
| Generic foundation | No capacity-policy/provider fields in CaseContract/Package/core commercial schemas; feature-specific policy remains in strategy | Core/strategy |
| Dependency direction | test_boundaries actual graph plus negative scanner controls pass; no production test import or dynamic plugin loader | Every source task |
| Source consistency | Layer winner/provenance/collision/scope/units/temporal tests; claim and estimator share immutable revision | Evidence/economics |
| Assessment authority | Four separate collections; grounded spans/refs; conditional/approval uncertainty preserved; historical revisions appended | Interpreter/state |
| Strategy separation | Proposal has no price/action authority; generator owns legal numbers; evaluator independently certifies; selector ID/evaluation/batch match | Strategy/pipeline |
| Economic correctness | Frozen kit totals/components, relationship nonmonotonic points, feasible-positive candidates, exact standards references and tagged alternative | Economics |
| Final validation | Positive/negative wire tests; invalid option/price/claim/private/action/state/limit rejected, no snapping; final payload hash used by dispatch | Validator/runtime |
| Complete M1 integration | All ten typed stages, fake provider/server identified, persisted DecisionRecord, frozen config/input hashes and replay result | M1 |
| Record integrity | Artifact closure verified; immutable revision chain; model output fingerprints; no orphan selection or misleading completed stage | Records/runtime |
| Honest terminal state | All close reasons invoke same fresh evaluator; rejected-close/open remains resumable; proof-backed ended only | M5 |
| Uncertain operation ownership | Restart preserves ID/bytes/claim scope; no new conflicting operation/open; stale accept held, retries not evidence of cancellation | M5 |
| State/restart | CAS/atomic outbox and crash tests; deduped accepted-source/rounds; refusal/question/assessment history independent of feature flags | M5 |
| Deadline/model failure | Hung/late/malformed/refused/hallucinated/injected outputs fallback within real total budget; queued time charged; no late write | Model/runtime |
| Metamorphic behavior | Preference flip changes supported direction and affordable package; greeting leaves choice/cost; refusal/approval/ceiling override unsupported exchange | M4/M5 |
| Reproducibility | Same frozen input/config yields same semantic decision/payload; changed model output recorded; no ambient flag switch | M1 onward |
| Baseline accounting | Historical replay exact; four inherited current failures classified; v1-adapted and V2 have distinct identities | Comparisons |
| Extension remains narrow | New dummy bundle uses same read-only intents/candidates/evaluations; no foundational edits or simulated ServerState | Optional extension |
| Completion is evidenced | Targeted required-prefix result, remaining xfails/failures and task owner/date/revision in tracker | Every task |
| Promotion remains scoped | All implemented cutline gates, complete frozen original-session report and separately authorized usage | Later funded promotion |

Reviewer rejects a task if it changes assertions to fit an implementation, imports expected fixture answers, implements a fake error switch in a live module, treats unsupported data as zero, creates authority from model text, abandons an uncertain POST, marks an open session ended, or presents partial/fixture performance as a hosted win. Request a concrete contract amendment when required, rather than letting separate owners invent different interfaces.
