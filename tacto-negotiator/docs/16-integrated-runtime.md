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
  triggers a contract comparison recommendation. Optional public case data enables offer validation.
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

## Limits

The model-backed interpreter/critic, automatic policy mutation and approved runtime lesson retrieval
are not enabled. Feedback proposes experiments; the lab's paired gates and explicit promotion still
decide policy adoption. New-release and final wave/host rehearsal remain release gates. The bounded
relationship search may reject an unsampled narrow feasible interval; it never fabricates a price.
General web news is not attached to fictional arena suppliers.
