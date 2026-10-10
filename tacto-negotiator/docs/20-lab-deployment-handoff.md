# Learning-loop deployment handoff for Barış

The implementation is on `codex/combined-latest-updates`; compare its final commit with
`origin/main` before integrating. The new lab paths are `lab/learning.py` plus changes in
`lab/server.py`, `lab/knowledge.py`, `lab/feedback.py`, `lab/loop_store.py`, `lab/loop_cli.py`,
`lab/cli.py`, `lab/static/loop.js`, and the runtime metric plumbing. The existing `runs`,
`sessions`, `loop_records`, and recommendation rows must survive deployment unchanged.

## Migration and verification

1. Record the deployed commit from the `Deploy y/agent lab` GitHub Actions run and back up the
   existing SQLite database using SQLite's online backup API. Check the backup with
   `PRAGMA integrity_check`; record run and recommendation counts. Do not copy credentials into
   the backup report.
2. Deploy a reviewed commit containing this branch's changes through the existing `main` workflow.
   Constructing `LearningStore` creates `learning_data`, `learning_status`, and
   `learning_proposals` with `CREATE TABLE IF NOT EXISTS`. `LoopStore` keeps its existing tables;
   there is no destructive migration. Keep the original database file and WAL together during
   any host-level move or restore.
3. With the existing upload token, read `GET /api/learning/status/<known-run-id>`,
   `GET /api/learning/proposals`, and `GET /api/learning/graph`. A successful response from all
   three confirms the new route set is deployed; 404 means the old code is still serving.
   Confirm the deployed commit separately from the Actions run and host release record.
4. For one already saved terminal run, use `POST /api/learning/retry/<run-id>` with `{}` and
   then read `GET /api/feedback/<run-id>`. Compare the run snapshot before and after: feedback
   may change, original result and recommendation must not. A retry failure remains visible via
   the status endpoint. Do not open an Arena session for this check.
5. On the host, ingest the exact supplied base/release package using
   `negotiator lab learn ingest --db "$LAB_DB" --data BASE [--release RELEASE]`. Confirm the
   resulting lab fingerprint matches a tracked run before expecting public-data context in its
   feedback. The host has no Arena or model credentials; this step reads only supplied files.

Review `docs/19-supplier-learning-loop.md` for proposal and teammate-review commands. A deployment
does not approve a candidate or enable model assistance or memory-based decisions. A budgeted held-out
async campaign remains a separate team decision.
