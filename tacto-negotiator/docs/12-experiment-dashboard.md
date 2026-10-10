# Shared experiment lab

Four teammates run agents on their own laptops. One laptop hosts the dashboard and receives
results through a VS Code forwarded port. The dashboard records experiments; it does not execute
code sent by teammates or replace the agent's existing negotiation runtime.

## Host setup

Use Python 3.12 and run these commands from the `tacto-negotiator` directory:

```bash
uv sync --locked
uv run --locked negotiator lab init
uv run --locked negotiator lab serve --secure-cookies
```

`init` creates `.lab-secrets.env` with an independently generated `LAB_PASSWORD` and
`LAB_UPLOAD_TOKEN`. It prints the file path, never the credentials, and will not overwrite an
existing file. The file is ignored by Git and owner-readable. Open it locally to get the values.
The password signs people into the dashboard; the token lets local runners publish results.
Share these two values only with your teammates, outside Git. They are not your arena key.

In VS Code, open **Ports**, choose **Forward a Port**, and enter **8000**. Set its visibility
to **Public**, then copy the forwarded HTTPS address. The application still requires its own
password/token. A private VS Code forwarded port is restricted to the account that created it;
it is not a shared team login. See [VS Code's port forwarding documentation](https://code.visualstudio.com/docs/debugtest/port-forwarding).

Open the forwarded HTTPS address and sign in using `LAB_PASSWORD`. Only forward this application
port. The server binds to `127.0.0.1` by default, with data at `experiments/dashboard.sqlite3`.
For local-only development, run `lab serve` without `--secure-cookies` and visit
`http://127.0.0.1:8000`. Use the HTTPS forwarded address when secure cookies are enabled.

Keep the laptop awake, on power and connected; keep VS Code, forwarding and the server running.
Restarting the server preserves SQLite records but expires browser logins. Stop the server before
copying the database for a backup. Preserve the secret file so runners can reconnect after restart.
If the forwarding address changes, teammates update `LAB_URL` and run `lab sync`.

## Every teammate's laptop

Check out the dashboard code and install the locked dependencies. Create `.env` from `.env.example`
only if one does not already exist. Configure these fields locally:

```dotenv
ARENA_URL=https://arena.tacto.ai
ARENA_API_KEY=your_existing_team_arena_key
ARENA_DATA=data/package
LAB_URL=https://your-vscode-forwarded-address
LAB_UPLOAD_TOKEN=the_upload_token_from_the_host
LAB_AUTHOR=your_name
```

The browser needs the dashboard password; the CLI needs the upload token. Keep model credentials
in environment variables, never in agent configuration JSON. The host does not need your model key.
To record locally without publishing, leave both `LAB_URL` and `LAB_UPLOAD_TOKEN` unset or empty.

## First experiment

Commit the version of the agent you intend to measure. This makes the run reproducible from Git.
The lab rejects a dirty checkout by default. `--allow-dirty` explicitly permits development runs,
saves a local `source.patch`, and labels the run as containing uncommitted changes. Only the patch
fingerprint is uploaded. A redacted patch or changes to excluded private files cannot reproduce
an experiment exactly; use a clean commit for baseline/decision runs.

This example opens two free sandbox sessions when you choose to run it:

```bash
uv run --locked negotiator lab run \
  --name "Package baseline" \
  --hypothesis "Establish the reference for complete-package negotiation" \
  --agent package \
  --environment sandbox \
  --cases case:D01 case:D02 \
  --repetitions 1 \
  --max-sessions 2
```

The command prints the saved run path. Its directory name is the run ID used for comparisons.
Use an identical case plan when trying a candidate:

```bash
uv run --locked negotiator lab run \
  --name "Smaller opening concession" \
  --hypothesis "A 10 percent anchor improves score on the same cases" \
  --agent package --config '{"anchor":0.10,"rounds":5}' \
  --baseline BASELINE_RUN_ID \
  --environment sandbox --cases case:D01 case:D02 \
  --repetitions 1 --max-sessions 2
```

These are example experiments, not recommended strategy changes or evidence of improved scores.
For practice, explicitly select `--environment practice`, your hosted case IDs, and a session ceiling.
The lab has no final mode. Existing `negotiator play` / `negotiator run` commands retain their behavior
and are not automatically instrumented; use `lab run` for tracked development experiments.

## Plug in an agent

`--agent package` uses the current PackageAgent; `--agent naive` uses the official starter.
For team work, provide an importable local factory or class:

```python
# src/negotiator/candidates/my_agent.py
from negotiator.agent import PackageAgent

def make_agent(anchor=0.12):
    return PackageAgent(anchor=anchor)
```

Select it with `--agent negotiator.candidates.my_agent:make_agent --config '{"anchor":0.10}'`.
The factory receives configuration as keyword arguments and must return an object implementing
the official `decide(case, threads)` interface. A fresh instance is used for every attempt.
Factory code runs only on the laptop that launches it, never on the dashboard host.

## Import previous attempts

On the dashboard host, set `ARENA_URL` and `ARENA_API_KEY` locally, then run:

```bash
uv run --locked negotiator lab import --environment sandbox
uv run --locked negotiator lab import --environment practice
```

When the default dashboard database exists, imports are written directly to it. `--db` selects a
different existing dashboard database. Imports also leave local snapshots; runners configured with
`LAB_URL` and `LAB_UPLOAD_TOKEN` can publish them to the shared host.

Import uses owned session-history, session and thread GET requests only. It does not open sessions,
consume practice starts or read spectator endpoints. Open sessions are skipped until they finish.
The imported record includes available results, costs, messages and a replay link, but code,
configuration and original author remain unknown. The command's author identifies the importer.
Repeated imports deduplicate by arena URL and session ID. Tracked provenance takes precedence
when a delayed local run corresponds to a previously imported session.
Finished outcomes are retained even if an older laptop snapshot arrives afterward. Reimport retries
incomplete records. For a tracked attempt that failed or lost its response, recovered arena evidence
appears separately in the details; the original failure and comparison score remain unchanged.
Local recovery uses a `reconciliation.json` sidecar so it cannot overwrite an active runner's snapshot.

## Reading the dashboard

- **Experiments:** search/filter by author, environment and status. Progress is polled every five
  seconds while the page is visible. The remaining quota is a dated server snapshot, not a reservation.
- **Experiment report:** score/completion/timeout/duration summary, followed by expandable case
  results. Each case shows final terms with units, cost components, and buyer/supplier conversations
  with expandable offers. Supplier threads retain their own recorded order. Experiment settings
  are readable fields; fingerprints and raw JSON live under collapsed technical details.
  Open sections and scroll position survive live updates. Missing or truncated evidence is labeled,
  and recovered arena outcomes stay separate from the original execution status and score.
- **Comparisons:** choose a baseline and candidate. Cases are aligned by ID; scored/planned repeat
  counts and failed attempts remain visible. A partial mean is explicitly labeled.
- **Aggregate change:** equal weight per common, fully scored case. Cases with missing or failed
  outcomes do not produce a delta; warnings identify incomplete coverage. Do not interpret a positive
  subset delta as an improvement over the full planned suite. Different environments/arena sources
  cannot produce an aggregate comparison. Data-version and repeat-count differences are flagged.

The dashboard supplies descriptive evidence. Interleave baseline/candidate runs on a fixed case set,
repeat comparisons, and inspect regressions before promoting a change. Simulator scores do not
demonstrate hosted persuasion quality. Keep holdout cases separate as described in
[the experiment protocol](04-experiments.md).

## Outages, failures and team limits

Snapshots are persisted under `experiments/runs/<run_id>/run.json` before asynchronous upload.
The latest revision wins, so duplicate/reordered uploads cannot replace a newer result.
Dashboard network failures do not block agent decisions. Retry any saved results with:

```bash
uv run --locked negotiator lab sync
```

Graceful interruption records incomplete attempts. A hard process/laptop crash can leave a run
marked running; syncing republishes what was saved, it does not resume negotiations or infer an
outcome. Inspect its arena session before opening another attempt. Import finished arena history
to inspect results when the local run was lost. Do not rerun a session automatically after an
uncertain POST; the underlying negotiation recovery limitations still apply.

All four laptops share one arena key, practice allowance and open-session/rate limits. The wrapper
runs serially per laptop and uses a conservative request rate, but does not enforce a global quota.
Assign session budgets, preserve the team's regression/preflight reserve, and coordinate other
scripts that use the same key. A per-run `--max-sessions` ceiling is not a team-wide reservation.
The shared dashboard is development tooling for a trusted four-person team, not a hardened
multi-tenant hosting service.

## Verification without arena spend

```bash
uv run --locked pytest -q
uv run --locked ruff check .
node tests/test_lab_ui.cjs
```

Lab tests use temporary SQLite files, local HTTP and fake arena responses. They do not use hosted
practice or model tokens. Browser validation uses a separate temporary database with explicitly
synthetic data; those fixtures are not loaded into the real dashboard.

For manual simulator runs, explicitly set `ARENA_URL` to your loopback simulator address
(for example `http://127.0.0.1:8092`) and use its separate local credentials. Select
`--environment simulator` and the simulator's case IDs. Simulator mode rejects hosted endpoints
before making requests, so it cannot silently fall back to hosted practice.

## Coding-agent campaigns

See [Agent experiment loop](13-agent-experiment-loop.md) for immutable checkpoints, explicit
recommendations and bounded paired campaigns. These records appear below historical experiments;
the read-only dashboard copies restore/evidence commands for execution on a teammate laptop.
