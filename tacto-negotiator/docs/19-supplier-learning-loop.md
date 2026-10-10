# Supplier learning loop (local implementation)

The shared lab stores original runs separately from derived data, graph, feedback and policy
proposals. This branch implements the loop locally; the hosted dashboard still requires deployment
and revision checks. No command below opens an Arena session unless it explicitly runs a campaign.

1. On the lab host, register a supplied base/release package with
   `negotiator lab learn ingest --db PATH --data BASE [--release RELEASE]`. This uses the
   `dossiers.load_package` adapter contract, records both the ingestion and lab fingerprints,
   source layers, conflicts and optional-input diagnostics, then refreshes matching terminal-run
   feedback. Later releases add new facts without changing saved messages or outcomes. It does not
   fetch internet news.
2. A terminal tracked-run upload saves its original outcome first. The lab then projects the
   version-matched public graph, prior attempt history and Barış's cited episodic observations into
   descriptive feedback. `/api/learning/status/<run-id>` reports `ready` or a persistent failure;
   bearer-authenticated `POST /api/learning/retry/<run-id>` with `{}` retries it. The original run
   stays intact. Authenticated `/api/feedback/<run-id>`, `/api/learning/graph` and
   `/api/learning/proposals` expose the saved projections. `/api/learning/context` requires an
   exact supplier, case, arena, environment, data hash and as-of time; it returns bounded source
   references. Live-purpose queries never return raw episodic observations or scores.
3. Two evidence thresholds can generate machine-actionable configuration drafts: recorded thread
   timeouts can propose `final_hold_s=20`; at least two distinct completed, valid, low-scoring,
   price-dominated cases with no timeouts can propose testing `anchor=0.16`. The latter is a
   hypothesis about opening price, not an explanation of the observed scores. Other findings
   remain engineering hypotheses. Each draft has source-linked
   evidence and does not alter a checkpoint. Use `lab learning proposals` and
   `lab learning prepare --proposal ID --suite SUITE --repo RESTORED_RECOMMENDED_REPO` to capture
   an immutable config-only child checkpoint from the exact recommended source tree. Publish it,
   then `lab learning register --body '{"proposal_id":"...","checkpoint_id":"..."}'`.
4. Run a separately budgeted, paired lab campaign on the registered checkpoint. A passing
   campaign becomes `awaiting_review` rather than changing the recommendation. The reviewer
   inspects every gate and original evidence, then writes
   `lab learning review --body '{"proposal_id":"...","campaign_id":"...", "author":"...", "approve":true}'`.
   The reviewer must differ from the campaign author. A stale source run, stale baseline or
   failed gate cannot be approved. Rejection uses `approve:false`.

The live worker already loads one immutable checkpoint per attempt. Its public dossiers come
from the matching package; optional validated memory preferences come from the checkpoint's
registered immutable snapshot. Neither graph history nor feedback scores enter outbound
arguments. The model-assisted interpreter remains opt-in and unpromoted. Current case-local facts
are merged at runtime by `dossiers.for_case`; they are not yet persisted as globally reusable
public graph facts. Uğur's final adapter must preserve the existing package interface and the
separate lab fingerprint, or migrate stored manifests explicitly.

The graph has source-backed supplier/part, quote, purchase-order, contract, performance,
quality, news, correspondence and explicit-contact relationships. Matching names do not establish
identity or authority. No unsupported alternative, personality or leverage edges are inferred.
Historical data with unknown versions remains isolated.
