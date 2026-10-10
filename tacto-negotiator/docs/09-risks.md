# Risks and validation

These are engineering priorities, not measured probabilities. Owners refer to the four roles
in 05-team-and-timeline.md. A mitigation is complete only when its validation has evidence.

| Risk | Required mitigation and evidence | Owner |
|---|---|---|
| RFQ starvation or server queuing | D02 timestamps; bounded workers; no long-held state lock; clock contract confirmed | Runtime |
| Two workers close the same case | One coordinator owns accept and walk-away; simultaneous-proposal test | Runtime |
| Agreed/stale/infeasible offer accepted | Same complete-cost/must-have/current-offer checks on every close | Decision |
| Relationship penalty omitted | Supplier-specific estimates and sensitivity; reconcile realized hosted components | Decision |
| Coverage/freight/unit mismatch | Complete terms; price_unit checks; case normalization clarified | Decision + Evidence |
| Unsupported claim survives ID filtering | Typed assertions and exact rendering; reject/replace unsupported content | Evidence |
| Claim IDs duplicated across workers | Atomic scope ledger and per-recipient rival-quote exception | Evidence + Runtime |
| LLM or document latency exceeds budget | End-to-end deadline, bounded retries, tested deterministic fallback | Runtime + Evaluation |
| Wave cap beats queued acceptance | Measured close latency, pending-request policy and watchdog | Runtime |
| Lost response leads to duplicate move | Persist move ID and exact payload; reconcile after restart | Runtime |
| Sunday overlay absent from SQLite | Load overlay facts, CSVs and letters; verify new IDs/documents | Evidence |
| Supplier/claim template overfit | Frozen holdout, unknown-supplier and paraphrase tests; explicit uncertainty | Evaluation |
| Quota exhausted before final preflight | One shared rolling ledger; protected reserve; no assumed overnight reset | Evaluation |
| Spectator input reaches final agent | Endpoint guard and isolation of human viewing; negative tests | Runtime |
| Credentials leak | No values in logs; redacting secret scan; excluded env files | All |
| Scaffold mistaken for final runner | CLI dispatch and full rehearsal gates; verify process actually waits/plays | Runtime |
| Laptop/network failure | Power/sleep setup; tested recovery under organizer policy | Runtime |
| Frozen submission changed | Recorded revision/config; feature freeze; no pushes after official freeze | All |
| Demo overstates results | Actual traces, repeat counts, holdout limits and simulated-impact labels | Evaluation/pitch |

If behind schedule, remove optional tactics and UI polish before weakening closing checks,
request reconciliation, deadline handling or evidence provenance.
