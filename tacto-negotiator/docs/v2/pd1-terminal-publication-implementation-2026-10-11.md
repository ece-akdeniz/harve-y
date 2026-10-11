# PD1.3 terminal evidence and publication recovery

Date: 11 October 2026 (Europe/Zurich). Scope: PD1.3, plus focused PD1.1/PD1.2 verification and the missing final post-journal dispatch guard. Local implementation only. No hosted inference, Arena session, Lab publication, authorization edit, push, or promotion occurred.

## Implementation

- Verified online attempts now defer final run completion until bounded terminal collection finishes. The Lab runner skips its older unbounded complete-history reads for this opt-in agent and does not refresh quota after negotiation. Successful attempts remain `running` until terminal evidence is attached; failed execution remains failed.
- Terminal collection reads only the owned session, its listed threads, and referenced attachments. Each read has a caller-side request timeout inside an overall monotonic deadline. Transient read errors retry reads only. Atomic local evidence is written as each part arrives; restart resumes the same session and re-reads authoritative state. Missing or interrupted evidence blocks publication.
- Publication state is durable per run under `publication-state/<run_id>.json`. It records evidence status, destination, run ID, frozen payload/hash, write state, retrieval state, and transitions. A per-run exclusive write-attempt marker is fsynced before HTTP; only one process can claim it. After that marker, execution has no PUT retry path.
- Acknowledged writes require exact individual retrieval and normal listing proof. Timeout, connection loss, ambiguous status, or malformed acknowledgement enters `outcome_unknown`; recovery uses GET only. A missing record, mismatch, or read failure remains unverified and cannot trigger another write. Definite rejection is recorded separately.
- Added a final local dispatch permit check after operation intent fsync and immediately before HTTP. Expiry closes the journal intent as `proven_not_dispatched`; no Arena request is issued. Experimental decision evidence now labels fallback actions and records the fallback call reasons.

## PD1.1/PD1.2 focused verification

1. The background worker executes only the decision coroutine. Agent trace, supplier-memory, observation, and pending-message changes occur on the owning caller after the bounded wait returns. Timeout revokes execution and model admission before raising; a late worker result is discarded. The cancellation-resistant cleanup regression verifies bounded caller return.
2. The model-call gate and decision ledger reject later inference after revocation. The worker cannot call the Arena dispatch adapter; dispatch happens only after `decide` returns. The timeout fallback regression verifies one certified fallback reaches the local simulator and its evidence says `action_origin: fallback`.
3. Full owned-state validation occurs before intent persistence. The newly added post-intent check is local-only and checks the current certificate/observed server clock after fsync. A fake clock-expiry test observes one intent, a proven-not-dispatched outcome, and zero POSTs.
4. Exact encoded payload, hash, and move ID remain journaled. Tests verify the HTTP body and move header match those persisted values.

## Publication state and ownership

```text
not_started → in_progress → complete
                         ↘ missing (local evidence retained; read-only recovery)
complete + frozen run → prepared → write_attempted
                                      ├─ acknowledged → verified (GET item + listing)
                                      ├─ rejected
                                      └─ outcome_unknown → GET-only reconciliation
```

The Arena owns terminal outcome. The experiment runner owns execution status and preserves an agent failure even after a later terminal result is collected. The local terminal artifact owns partial collection progress. The publication journal owns the single-write claim and frozen payload. Experiment Lab owns acceptance and retrieval; only a matching record plus listing can become verified.

## Regression evidence

All checks used local fixtures, the in-process official simulator, or `httpx.MockTransport`:

```text
.venv/bin/python -m pytest -q tests/v2
1285 passed, 298 xfailed

.venv/bin/python -m pytest -q tests/test_lab_runner.py  [localhost socket permission]
32 passed

scoped Ruff check
All checks passed

git diff --check
clean
```

The V2 suite includes terminal completion/publication, failed execution followed by terminal evidence, collection timeout, transient GET recovery, interrupted collection and same-session resume, pre-write recovery, uncertain and rejected writes, GET-only reconciliation, multiple publication owners, payload tampering, zero writes without complete evidence, fallback evidence, dispatch expiry after journal fsync, and the legacy trace digest test. The two model-budget xfails still require the absent `negotiator.v2.adapters.recorded` module. The full V2 suite has additional pre-existing expected failures; this batch did not alter or reinterpret them.

The first sandboxed Lab runner invocation failed because local socket binding is denied. The same test file passed with local socket permission. No remote test target was used.

## Limits and disposition

Timed-out read workers may finish later in daemon threads, but they perform only read-only calls and cannot update the collection state. Recovery always re-reads the owned session and threads. The local collector is intended for the one-session hosted bridge, with a 300-second overall bound, ten-second per-read bound, and at most 100 listed threads. The terminal evidence artifact is local; the immutable Lab payload uses the existing bounded `Run` schema and includes complete run/thread/agent evidence.

The workspace had extensive pre-existing tracked and untracked V2 changes at HEAD `a88bf86820214be9fdf4e0d4e679675d946e0607`; this report does not claim HEAD alone reproduces the current implementation. Authorization files and original D01 artifacts were left untouched.

**PD2.1 recommendation:** begin the planned local commercial-effects contract and payment-direction regression after review of this lifecycle diff. Keep it local and deterministic first. Do not include real-model probes, another Arena session, Lab write, or PD2.2 in that batch.
