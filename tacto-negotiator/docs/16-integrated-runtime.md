# Integrated harve/y runtime and lab

Implementation on `codex/harvey-integrated-runtime`, based on main `dc3a109` and lab `08274aa`.
The original development checkout and its local credentials remain separate.

## Implemented

- Unconfirmed closes raise an incomplete-session error without writing a finished journal result.
  Resume keeps the existing session. Exhausted uncertain sends retain their persisted move ID.
  Cached replies keep server-derived remaining time; worker failures reach the caller.
- Main's package policies and shared closing evaluator are retained. `economics.evaluate` rejects
  invalid prices/options/fixed-term changes/must-haves and returns full components plus demand coverage.
  Price-budget search handles non-monotonic relationship costs with bounded sampling and validates
  rounded prices. Sampling is conservative; it does not claim a global optimum.
- Versioned public ingestion records file hashes, case context and explicit source conflicts.
  Conflicting release IDs are excluded from claims. Missing optional tables produce diagnostics;
  explicit missing data paths do not silently load a different package. Contact notes and
  previously unknown suppliers are retained. Prep output includes the data manifest.
- Bounded extractive reply interpretation identifies supplier statements about hedging, payment,
  quality, clauses and authority. Verified alternative arguments replace vetoed index arguments.
  Final offers receive no new evidence decoration. This implementation uses deterministic rules,
  not an LLM or personality inference; it makes zero provider calls.
- The lab accepts embedded validated policy configurations in immutable checkpoints, so its worker
  can execute the same package policy as the normal CLI. Workers retain decision traces.
- `FeedbackAgent` audits original outcomes and conversations and emits referenced keep/change/test
  findings. Recovered scores remain separate, unknown timeouts stay unknown, and uncovered demand
  triggers a contract comparison recommendation. Matching versioned public data enables qualified
  offer checks; unknown historical versions are skipped rather than checked against today's data.
  Cross-run observations are retained as observations, never auto-approved runtime policy.
- Feedback is available from the authenticated `/api/feedback/<run_id>` read endpoint and in each
  dashboard experiment's Decision feedback disclosure. CLI audits are stored separately from
  immutable attempt records and can be regenerated.

## Use the integrated candidate

```sh
uv run --locked negotiator play case:D01 --runner async --policy-config configs/candidate.json
uv run --locked negotiator lab feedback --data "$ARENA_DATA"
```

The first command starts a free hosted sandbox session when configured for the arena. The second
only audits the local lab database. Do not run practice as an incidental verification command.

For a lab checkpoint, pass `configs/harvey-lab-checkpoint.json` as the config and select `--runner async`.
Use the explicit `configs/lab-async-sandbox-suite.json` suite and a matching base data manifest.
That suite has three repeats per case per arm: twelve free sandbox sessions, not two. Publication,
baseline seeding, family budget and campaign execution remain explicit actions using the lab CLI.
The committed base hash matches the audited kit data; a new release requires a new manifest/suite.

Local end-to-end rehearsal:

```sh
uv run --locked python tools/rehearse_loop.py --runner async \
  --policy configs/candidate.json --data "$ARENA_DATA"
```

This creates an isolated temporary lab, local Git remote and kit simulator, then runs twelve local
sessions through restored checkpoints. It does not change the shared lab recommendation or use
hosted quota. Its deliberately weak control tests integration, not production competitiveness.

## Imported evidence

The integration checkout's ignored `experiments/dashboard.sqlite3` contains 100 run records / 113
attempts: the two saved practice sweeps (15 attempts), plus 53 sandbox and 45 additional practice
sessions read from owned history. Fifteen existing practice sessions were deduplicated. No import
failures. Original source/config is unknown for server-only history, and the importer is not the
original author. P10's operator-assisted recovery preserves its original failed execution.

This is a local database. It has not replaced Barış's running shared database or deployed the UI.
Use the existing lab sync workflow with the team's configured destination when publishing records.
Keep credentials and the local derived feedback JSON out of Git.

## Hosted recovery verification

The planned free sandbox crash/restart at source `fedd609` completed D01 and D02 on their original
sessions after killing the first process immediately after its first journalled send. D01 scored
91.92% (session `99e5175b6c5630be`); D02 scored 46.09% (`2da225d3421b1101`). Both deals satisfied
must-haves and recorded zero timeouts. No replacement sessions were opened. Practice quota stayed
at 60 used / 140 left. Evidence is in the local ignored
`experiments/runs/integrated-free-recovery-fedd609/` directory. These are recovery observations,
not a paired comparison or proof of final-wave readiness.

Final local guards additionally cap contract option enumeration and charge document-fetch time
against recovered deadlines. They are covered by regression tests; the hosted run above precedes
those guards. The shared graph contract and module ownership are in
[the handoff](17-shared-memory-handoff.md).

## Limits

The model-backed interpreter/critic, automatic policy mutation and approved runtime lesson retrieval
are not enabled. Feedback proposes experiments; the lab's paired gates and explicit promotion still
decide policy adoption. New-release and final wave/host rehearsal remain release gates. The bounded
relationship search may reject an unsampled narrow feasible interval; it never fabricates a price.
General web news is not attached to fictional arena suppliers.

## Opt-in model interpretation candidate

`--model-assist` enables a short model read of each new supplier email. Set `LLM_PROVIDER`
(`anthropic` or `openai`), `LLM_MODEL`, and that provider's API key. The lab checkpoint stores
the provider and model name in its resolved configuration. A provider error, malformed JSON or
uncited extraction falls back to the existing deterministic parser. The async runner does the
bounded call outside its case decision lock; calls are cached per supplier message.

The model may extract objections, constraints, questions and proposed terms only when it cites
verbatim text from the current supplier email. Extracted terms carry `sheet_matched` or
`prose_only_unverified`; only the actual structured term sheet can be accepted. A cited index
objection can suppress that argument and select another verified claim. Template wording can
acknowledge selected concerns, but offers, prices, refs and closing decisions remain in code.

Optional live memory is read from `NEGOTIATOR_APPROVED_MEMORY` with
`NEGOTIATOR_DATA_SHA256` set to the lab data fingerprint. The snapshot must contain version 1
`lessons` with an exact supplier, case type, environment and data hash, valid-from/expiry,
approver, campaign, confidence and cited run/attempt evidence. Only explicitly approved lessons
are sent to the model; raw graph history and scores are never sent to the live agent. Barış's
graph service can replace this file adapter while retaining those filters. The model can cite
an approved lesson and summarize it as an observation; only its approved `avoid_claim_kind` may
change claim selection. No automatic lesson approval is implemented.

This candidate has local tests, including a full async simulator case. It has not passed a
hosted baseline/candidate campaign. Model quality, latency and token cost need measurement on
the actual provider before selection for a final run.
