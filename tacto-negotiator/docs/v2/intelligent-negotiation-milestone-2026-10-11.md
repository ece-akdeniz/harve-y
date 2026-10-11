# Intelligent negotiation milestone — 11 October 2026

The follow-up [hosted sandbox readiness report](hosted-sandbox-readiness-2026-10-11.md)
extends D01/D02 support and supersedes this report's next execution gate. The new order is
offline hosted-model validation, D01 sandbox, D02 sandbox, then P10 practice, with fresh
approval and original transcript review between stages. The controls below remain historical evidence.

Bounded proposal generation and online safety integration are implemented. Genuine hosted
negotiation and the real online experiment remain behind the user's separate inference and
online authorization gates. No hosted calls or online sessions were made in this milestone.

## Implemented capabilities

The adaptive arm interprets messages through validated citation IDs, then requests new legal
price/term bindings using complete public history, grounded assessment, and buyer must-haves.
Independent official economics, policy checks, candidate certification, and dispatch validation
remain authoritative. Invalid proposals fall back to the existing fixed baseline. Private buyer
economic parameters are excluded from the proposal projection. The local scripted control uses
public offers and history; it does not use hidden simulator floors.

Existing Lab interfaces now support initial authoritative acknowledgement, refreshed observations,
attachment hydration, independent closing, terminal retrieval, and admitted-stage telemetry.
The online adapter validates the P10 catalog identity, actual rounds and conservative clock,
standing offers, exact payloads, and independently recomputed closing decisions. Journaled
submission persists exact bytes and pre-submission history before POST. An uncertain operation
blocks further writes; read-only reconciliation requires an exact owned-message/history proof.
There are no automatic submission retries or guessed session reopenings.

## Official simulator control and baseline

Artifacts: `/tmp/v2-intelligent-negotiation-2026-10-11/` contains `complete-transcript.json`,
`milestone-report.json`, original decision traces, original snapshots, and `remote-lab-proof.json`.
Every original decision trace verifies its digest. The transcript contains authoritative threads,
admitted interpretation/proposal outputs, economic evaluations, validation events, and terminal state.

| Arm | Actual run ID | Outcome |
| --- | --- | --- |
| Fixed minimum | faa135d5-c8e0-4374-a886-5f63246ddbfd | Six rounds, no agreement, score 0 |
| Adaptive scripted control | d482589d-cd1a-443e-9d5e-4bb9973869df | Two proposal rounds followed by independently validated acceptance, score 0.8094806135901004 |

The adaptive deal was supplier `sup:70410`, offer `offer:70410-2`, unit price 31.89,
annual volume 23,400, duration 24 months, and lead time 42 days. Official total deal cost:
EUR 1,502,401.68. Its proposed cost changed from EUR 1,486,854.72 to EUR 1,502,401.68.
This is execution evidence from a scripted model, not hosted-model quality or superiority evidence.
Earlier unsuccessful debugging runs remain in separate `/tmp/v2-adaptive-milestone-*` directories.

Both actual simulator runs were successfully uploaded to the team Lab after the user's explicit
retry instruction. Normal `/api/runs`, individual retrieval, and `/api/compare` calls verified their
visibility; responses are retained in `remote-lab-proof.json`. The remote Lab rejects enrichment
of already finished attempts with HTTP 409, `finished attempts are immutable`. Published original
records are preserved. Additional full admitted-stage evidence remains local; it is not claimed
to be remotely published. Future runs collect that evidence before finishing. Comparison exposes
the case-level scores but withholds an overall delta because separate simulator instance URLs
differ. Both runs used dirty source, and source patches are retained.

## Validation and limits

Full V2 suite: 1,257 passed and 298 expected xfailed. After the latest Lab evidence changes,
the adaptive and Lab integration tests passed again: 14 passed. Scoped Ruff checks passed.
The full repository suite has an unrelated existing failure in `tests/test_context.py`:
`test_agent_obtains_context_and_preserves_offer_and_close` raises `KeyError: sup:F` in unchanged
legacy `agent.py`. The full repository is not claimed to pass.

Online compatibility has been tested with stubs and read-only real metadata, not a live session.
P10 matches the local dataset. General RFQ/multipart support and automatic process restart/resume
are not implemented; ambiguous writes stop for reconciliation. Official quote-default disagreement
fails closed. Metadata/quota observations must be refreshed before the authorized online run.
Semantic expectations are provisional development labels; independent human review remains pending.

## Next authorization gate

`/tmp/v2-adaptive-inference-preparation-2026-10-11/authorization-template.json` binds the current
implementation source and defines one offline hosted evaluation with
`gpt-4.1-mini-2025-04-14`: 14 development interpretations, one fixed baseline and one adaptive
official simulator negotiation. Limits: 32 calls, 3,145,728 reserved total tokens, 2,048 output
tokens per call, USD 2 maximum, zero retries, zero automatic reruns, zero online sessions and
zero remote writes. Execution requires exact authorization plus confirmation of the conservative
UTF-8-byte token-accounting convention. The authorization is single-use. No held-out calls.

After genuine hosted offline validation and safety review, request a separate exact one-session
online approval. The draft P10 practice gate allows 18 calls, 1,769,472 reserved tokens, USD 1,
and zero retries. It does not authorize execution now. Do not substitute this scripted control
for genuine hosted offline verification or an actual online outcome.
