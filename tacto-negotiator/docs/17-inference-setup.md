# Independent inference setup — prepared, not run

The project now includes an opt-in inference connection probe that can use the existing shared
Experiment Lab. No inference requests, negotiations, tests, lab uploads or server launches were
performed for this setup. The new code is unvalidated until the local checks below are authorized.

## Credentials and missing connection details

Open the ignored `tacto-negotiator/.env` locally. Put the Tacto **inference** key into
`LLM_API_KEY=`. This is separate from `ARENA_API_KEY` (negotiation API access) and
`LAB_UPLOAD_TOKEN` (result publication). Never put credentials in agent config JSON or Git.
The file was created with blank credentials; existing files must never be overwritten by copying
the example. Real exported environment variables take precedence over `.env`.

The repository does not supply the Tacto inference endpoint or model ID. Obtain these from the
organizer before connecting:

- The inference base URL, including any version prefix, for `LLM_BASE_URL`.
- The exact model identifier for `LLM_MODEL`.
- Confirmation that it supports OpenAI-compatible `POST <base>/chat/completions`, Bearer
  authentication, `messages`, `max_tokens`, and a `choices[0].message.content` string.

`LLM_PROVIDER=openai` selects that wire protocol; it does not imply an OpenAI-hosted model.
There is no fallback to a public provider. If Tacto uses a different protocol, adapt the connector
before using it. The key alone cannot identify an endpoint, model or account limits.

## Shared Lab connection

The Lab URL is taken from `LAB_PLAYBOOK.md`:
`https://1r9qgc6b-8000.euw.devtunnels.ms/`. It is prefilled in `.env`, along with `LAB_AUTHOR=ugur`.
Its availability was not checked. Obtain `LAB_UPLOAD_TOKEN` from the Lab host and paste it locally.
The browser uses a separate dashboard password. No local dashboard server or `lab init` is needed.

Use `negotiator lab run` for the probe. Its existing publisher sends versioned snapshots to the
shared dashboard; failed uploads leave local records under `experiments/runs` for later `lab sync`.
Normal play/run commands do not automatically appear in the Lab. Bare inference/unit tests do not
produce negotiation scores or Lab experiment records; do not invent arena results for them.

The probe is available as `negotiator.inference:InferenceProbeAgent`. It inherits PackageAgent's
economics, evidence selection and closing authority. At most once per case, it sends a fixed,
non-sensitive prompt and accepts only one of two fixed closing-style IDs. No model-generated
figures, claims, term sheets or closing actions are accepted. Errors keep the original move.
This tests connectivity, response shape and runtime integration; it is not a general model writer.

The standalone Lab runner records `agent_metrics.inference_probe` in each attempt's result,
alongside the standard scores, terms and supplier threads. These metrics contain call/fallback
counts and per-call elapsed times, never raw prompts/responses or provider exception text.
They are available in the saved/uploaded result JSON; no separate latency chart is added.
The checkpoint campaign worker still constructs PackageAgent directly: use standalone serial
`lab run` for this exploratory probe, not campaigns. Do not promote it as a verified candidate.

`LLM_TIMEOUT_S=2` sets HTTP phase timeouts, with no automatic retry or redirects. It is not a hard
total wall-clock deadline. Measure end-to-end latency before any broader model use on the move clock.
The inference service can incur spend even when the arena environment is a free sandbox or local simulator.

## Later validation and execution

The following commands are instructions for a later, explicitly authorized step. None were run.
Run them from `tacto-negotiator`. First validate locally with fake inference transport:

```bash
uv run --locked pytest -q
uv run --locked ruff check .
```

Before a real experiment, read the Lab recommendation/findings as directed in `LAB_PLAYBOOK.md`,
coordinate shared Arena starts with teammates and confirm the inference allowance and session
budget. The probe uses the existing standalone runner; it does not acquire campaign leases.
After the user authorizes one D01 sandbox session, the tracked command would be:

```bash
uv run --locked negotiator lab run \
  --name "ugur-inference-connectivity" \
  --hypothesis "Tacto inference returns an allowed closing style without changing approved terms" \
  --agent negotiator.inference:InferenceProbeAgent \
  --config '{"claims":true}' \
  --environment sandbox --cases case:D01 \
  --repetitions 1 --max-sessions 1 \
  --data ../negotiation-arena-kit/data
```

Use a clean committed revision for reproducibility. For an authorized exploratory dirty-checkout
run, explicitly add `--allow-dirty`; the Lab records the patch hash and labels the source dirty.
The example uses the available local data explicitly; substitute your verified package path if different.
To recover failed result uploads later, use `uv run --locked negotiator lab sync`.

No sessions, inference budget or shared publication have been authorized by this setup document.
