# GPT-4.1 mini offline comparison — awaiting explicit approval

This follow-up reviews the real-LLM readiness report, Assignment 2/3 completion reports and
Arena starter-kit README. No hosted inference, Arena session, negotiation action, remote Lab
write, Assignment 4, dependency change, commit or push has occurred.

## Configuration and transport review

Effective exported environment plus project `.env` now supplies all four LLM settings. Values
and credentials were not printed. `load_dotenv(Path.cwd()/'.env', override=False)` preserves
exported overrides. The initial model mismatch was corrected by the user; a fresh configuration check now
validates `gpt-4.1-mini`, the direct endpoint and key presence without hosted inference.
The new composition requires `LLM_PROVIDER=openai` and direct OpenAI endpoint
`https://api.openai.com/v1`. No provider or model substitution is attempted.

Tests verify dotenv consumption through to the actual POST URL, bearer header and model
parameter using local fake credentials. Key material stays exclusively in the HTTP header;
it never enters requests' model projections, plans, traces or reports. Provider error bodies
and exception strings remain withheld. The HTTP client disables redirects, retries and ambient
proxy configuration. Existing private-data checks and independent final validation remain.

A narrowly configured alias/snapshot mapping was necessary: send the configured
`gpt-4.1-mini` alias, require the documented `gpt-4.1-mini-2025-04-14` response identity,
and retain that snapshot identity in gateway traces. No arbitrary response alias is accepted.
The default transport identity checks are unchanged for other callers/providers. The run plan
records both wire-request and canonical response identities. A different returned snapshot
fails closed and is an experiment finding, not grounds for automatic retry.

Official documentation lists chat completions and structured outputs support, the alias and
snapshot, and standard text rates of $0.40 input / $1.60 output per million tokens:
[GPT-4.1 mini model reference](https://developers.openai.com/api/docs/models/gpt-4.1-mini).
Existing JSON-object mode plus strict consumer decoding is retained; no prompt or validator
was loosened. Cache savings are not assumed. Usage-based expenditure is an estimate rather
than a provider invoice. The conservative UTF-8 byte bound plus 256 framing tokens remains
explicit in the approval. All requests have capped completions, no tools and no retries.

## Exact experiment

`experiments/v2/run_hosted_comparison.py` composes the existing transport, gateway, P10 services,
benchmark fixture helpers, candidate generator, official evaluator, renderer and validator.
It is an offline experiment script, not an Arena runner or new negotiation framework.

1. Run the complete P10 fake HTTP rehearsal and existing three-arm fake benchmark first.
2. Require a content-bound approval matching endpoint, requested/response models, dataset
   hashes, projection, rates, $5 ceiling, absolute calls/tokens and accounting convention.
3. Run one connectivity call using the existing selection task/schema, one approved P10
   minimum option and an empty supporting quote. Stop if strict JSON decoding, model identity
   or exact allowed ID fails. This is a schema connectivity probe, not a negotiation decision.
4. Run both P10 messages through hosted interpretation and selection, comparing each with
   the deterministic baseline on the same inputs. Hold package contents and official costs fixed.
5. Run all 24 existing synthetic benchmark examples through minimum-cost, direct selection,
   and interpretation-plus-selection. Verify identical evaluated universes across arms and
   language pairs, except the deliberately separate cost-only economic intervention.

Two calls per decision, 32,768 total reserved tokens, 12 seconds model time, eight-second
interpretation/four-second selection, 35 seconds compute and five-second fallback/submission
reserves are retained from the hosted P10 setup. The old fake benchmark's 2,048-token/one-second
limits cannot accommodate these real schema prompts; its fake results retain their original
limits and are labelled separately. No validation bypass or inference retry is provided.

Absolute maximum: **77 calls, 1,261,568 reserved tokens, $5 total**. Charge all reserved tokens
at the higher output rate before each attempted invocation: **$2.0185088** maximum conservative
reservation. Failed, rejected, cancelled and missing-usage calls retain their full reservation;
reported overruns increase it and block subsequent unaffordable work. No provider can be forced
to report honest usage; the ceiling assumes the approved rates and provider token-bound behavior.
An exclusive started marker prevents reusing a started output directory. One approval covers
one run; uncertain or repeat hosted work requires a new allowance, not a new directory alone.

Reports retain selected IDs, selected and complete official costs, paired changes in selected
contents (IDs alone change with snapshot identity), usage, conservative charges, latency,
transport status, consumer rejection causes, interpretation status, fallbacks and trace hashes.
Accepted raw outputs and exact grounding references remain in independently verified traces;
unsafe rejected output stays withheld. Report files are saved even when subsequent work stops.
No benchmark labels, raw buyer economics, internal thresholds or credentials reach the model.

## Benchmark review and interpretation limits

There are eight frozen held-out examples in four pairs; their original hash is verified.
They remain author-annotated, with independent human review pending. This code review is not
independent semantic review. Refusal scope, approval uncertainty, contradictory requirements
and conditional paraphrases remain the held-out diagnostics. Labels and supplier acceptance
hypotheses are not official economics or proven commercial utility.

`forged:0/1` are duplicate delivery-preference inputs whose minimum-only labels depend on
fake ID/quote faults. Those faults must not be injected into a real model run. Preserve their
records and original 24-example score for audit, but exclude these two entries from the
separate 22-example semantic score. Report held-out scores as provisional. The private-limit
injection is correctly rejected by the approved projection before inference; keep that rejection
in its denominator. Do not relax that guard to obtain a model output.

After an approved run, inspect each admitted interpretation for exact spans, condition scope,
negation, contradictions and uncertainty. Structural acceptance alone does not establish
semantic correctness. Attribute failures using transport status/usage, strict decoding,
assessment rejection, selection grounding cause and final validation. Distinguish provider
HTTP/identity/timeout failures from prompt/schema failures and from projection/validator limits.
Review paired changes against the fixed official cost trade-offs; no reactive Arena outcome
or Assignment 4 readiness claim follows from provisional offline matches.

## Runnable setup and approval

Set the ignored project `.env` locally (never paste keys into the approval):

```dotenv
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
LLM_API_KEY=<local credential>
```

Preparation, requiring no hosted authorization and making no hosted calls:

```bash
.venv/bin/python -m experiments.v2.run_hosted_comparison \
  --output /tmp/v2-hosted-comparison-preparation
```

The resulting `authorization-template.json` has `authorized=false` and
`token_accounting_confirmed=false`; it binds all three input datasets by semantic SHA-256.
Review and explicitly approve that plan in conversation first. Only then create a matching
approved copy, with those two flags true, and execute once in a fresh directory:

```bash
.venv/bin/python -m experiments.v2.run_hosted_comparison \
  --authorization /tmp/v2-hosted-comparison-authorization.json \
  --output /tmp/v2-hosted-comparison-first-run
```

This hosted command has **not** been executed. Credentials alone do not grant authorization.
The current blocker is explicit provider/model/dataset/expenditure approval. No Arena sessions or actions are included in the requested approval.

Verification: **32 focused tests passed; 1,209 passed / 298 expected xfailed** in the complete
consumed V2 gate. Manifest: **1,507 contracts**. Scoped Ruff, frozen V1 replay and whitespace
checks pass. The earlier 167 passing Lab tests remain applicable; no Lab source was changed.
The documented inherited legacy-test/Ruff failures are not claimed resolved.

## Approved run completed

The user explicitly approved this exact one-time experiment after correcting `.env`. The
connectivity/P10/benchmark command completed with 74 calls, no timeouts and $0.085944
uncached usage-derived cost. The approval is consumed; it is not a standing allowance.
See [the complete results and failure analysis](hosted-comparison-results-2026-10-11.md).
No model prompt or validation rule was changed during the experiment.
