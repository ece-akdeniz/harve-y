# Short instructions for V2 coding agents

Work from the development baseline in [A §7](A-current-architecture.md), without merging it into main. Read [C §8](C-interfaces.md), your exact assignment in [task-specs](task-specs.md), and its executable tests. Do one assignment. Do not repair V1, install packages, read dotenv, call services or activate a new default as incidental work.

1. Inspect git status and preserve unrelated changes. Create only the named files. Shared core batches merge serially; feature owners may parallelize only after contracts and codec are frozen. Record the task owner and in_progress state in D/tracker.
2. Read the actual assertions and frozen fixtures. Run the targeted tests first. Missing modules are explicitly UNIMPLEMENTED, not accepted functionality. Use --v2-require for the components you own. Do not add broad xfail/skip decorators, catch assertion errors, change goldens or add a production fake returning the expected outcome.
3. Implement the specified schema/port/algorithm. stdlib and existing Pydantic suffice. Call collaborators through injected ports. Only adapters import legacy modules/kit/provider/storage. Production cannot import tests or fixture answers. The codec decodes input; it never decides precedence, costs, strategy, validation or terminal truth.
4. Test positive and negative cases, numerical/behavioral/recovery invariants relevant to the assignment, then its integration gate. Keep actual unknown/pending/failed outcomes. A partial implementation with absent methods is an ordinary failing test; report it rather than adding another expected-failure rule.
5. Run Ruff and the current bounded legacy comparison. Record inherited failures separately. Update task/tracker evidence and regenerate the test manifest after adding reviewed tests. Report what passed, what remains unimplemented, and exact limits. Do not mark a task completed because files exist.

From tacto-negotiator with the existing locked environment:

```bash
.venv/bin/python -m pytest -q tests/v2/contracts
.venv/bin/python -m pytest -q tests/v2/integration
.venv/bin/python -m pytest -q tests/v2/acceptance
.venv/bin/ruff check tests/v2 src/negotiator/v2
.venv/bin/python tests/v2/catalog.py
.venv/bin/python tests/v2/replay_v1_baseline.py
```

Before src/negotiator/v2 exists, lint only tests/v2. These examples use an already installed environment; normal repo locked uv commands are equivalent when uv is available. Never silently upgrade arena-kit or the lock. This preparation used the existing environment, not a new installation.

A required **task** example (T1.1a, without pretending later classes exist):

```bash
.venv/bin/python -m pytest -q tests/v2/contracts/test_foundation.py --v2-require core.models --v2-require core.serialization -k 'price or basis or term_bindings or canonical'
```

T1.1b requires the ports prefix for its signature gate. T1.1c requires config/models for record and config tests. Task prefixes can be repeated. A later **fully implemented** milestone/release gate is:

```bash
.venv/bin/python -m pytest -q tests/v2 --v2-require all
```

Until deferred features such as the optional model selector exist, use explicit required-prefix/file/function selectors for the milestone cutline and list remaining tests. “All” means all collected contracts, including optional/deferred ones; do not weaken them to announce the first slice complete. M1's required tests are the core/record/config and typed pipeline tests specified in D, not full live-runtime acceptance.

Legacy comparison on the current development branch:

```bash
ARENA_DATA=/home/ugur/harve-y/negotiation-arena-kit/data timeout 30s .venv/bin/python -m pytest -q tests/test_evaluator.py tests/test_context.py tests/test_package_advisor.py tests/test_cost_neutral_delivery.py tests/test_guidance.py tests/test_dossiers.py
```

Use the absolute pinned kit path appropriate to the checkout. Current known result is 56 pass/4 fail; classification is in A. Whole-repository Ruff currently has four inherited tracked-source errors; new V2 test files lint cleanly. The historical exported source passes these same60 tests. The replay script checks historical first-message behavior independently. No full current-suite pass is inferred. Before a later push, repo AGENTS requires locked full pytest/Ruff checks; record inherited failures/hangs honestly and do not claim that this bounded check replaces that rule.

Minimal completion note:

```text
Task / owner / revision:
Owned files and schema:
Required-prefix targeted result (pass/fail/xfail):
Integration / acceptance results and artifact links:
Baseline replay and inherited legacy differences:
Remaining missing/incomplete/deferred capabilities:
No hosted/model calls, V1 changes or dependency changes:
Tracker status and acceptance criterion met/unmet:
```

Unavoidable protocol uncertainty uses the defaults in C: retain owned unknown requests, stop bounded with recovery_required, use authoritative terminal proof, and never invent deadline/round/price-basis evidence. Future budget/provider choices remain separate operational decisions; they are not needed for these offline assignments.
