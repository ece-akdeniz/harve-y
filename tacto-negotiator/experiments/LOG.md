# Experiment log

Format and decision rule: `docs/04-experiments.md`. Newest on top. One entry per change.

## 2026-10-11 — V6 supplier intelligence reliability repair (LOCAL ONLY)

- Hypothesis: field-specific source admission, constrained buyer wording, shared durable model reservations and issue-aware context reduce unsupported advice/writing without changing the selected package economics or the closing policy.
- Source/config: base `279f7a8`; current uncommitted worktree identity in `experiments/v6-reliability-source-manifest.json`. Default V6, briefed, skilled and all-case configurations remain distinct; no config was promoted. The existing zero-concession strategy setting and final risk limits are unchanged. Candidate source, lock, data, skill and nonsecret model identities are in the manifest.
- Cases/quota: synthetic payment/delivery and English/German condition fixtures; saved P10 capacity fixture; seven practice case-type writer fixtures; serial/async simulator paths. Zero new provider calls and zero new Arena sessions. No practice quota was spent.
- Validation: 140 focused tests passed with the two async RFQ writing tests excluded from that sandbox run. Those two tests and one async ModelAssist test passed individually outside the sandbox. After the final semantic parsing fix, the full available local suite passed **985 tests**, with two lab subprocess tests deselected because this environment has no `uv` executable. Ruff and `git diff --check` passed. A repeatable async wave-cap control failure was fixed by waiting for a pending supplier reply through the existing closing window; all seven wave-guard tests then passed. A minimal `asyncio.to_thread` stalls inside the tool sandbox and works outside it, establishing an environment cause for the async RFQ stall reported in review.
- Results/failures: payment-only evidence cannot authorize delivery; an unmet conditional antecedent cannot authorize a trade; unsupported qualitative claims or additional-volume promises fall back to the code-rendered body without losing a legal selected package. Reservations cover strategy, final review, legacy advice, writer and optional ModelAssist across restart. Private bounded model artifacts and stable rejection checks are retained locally. Provider completion after client timeout remains uncertain and charged; no supplier impact was measured.
- Decision: keep this as a local safety candidate. The two `uv`-dependent lab tests and a locked `uv run --locked` invocation remain unverified in this environment. Follow the separate provider-only and controlled Arena proposal in `docs/v6-supplier-intelligence-reliability-implementation-2026-10-11.md` only after a frozen checkpoint and explicit call/session allowance. No commercial or release-readiness claim.

## 2026-10-11 — All seven practice case types can reach opt-in model prose (LOCAL ONLY)

- Hypothesis: moving response writing to a separate bounded step after the code-approved decision lets every case type use qualitative supplier context and approved quantitative terms without weakening each type's existing package and closing logic.
- Source/config: isolated candidate identity `3257be9d2c67d644ae6e021573917f8b567e156ebe1002250c6f1ad4612e106e` in `experiments/v6-all-cases-source-manifest.json`; opt-in `configs/score-push-v6-all-cases.json` SHA-256 `3e526e4ad6c691c37ef49a1d9032dcb29096a1631cc66f95fb0f3752b51e6779`. This config differs from the preceding skilled config only by `llm_response_mode: all-v1`. The previously tested three-session candidate and its source/config hashes remain preserved.
- Coverage: Arena lists 19 practice cases, ten hosted, spanning price increase, renewal, RFQ, bundling, raw material, capacity and quality. The generic writer is eligible for all seven types. Serial cases call it after decision and before dispatch; RFQ previews outside the async coordinator lock and applies model prose only when the live message exactly matches the preview. Strategy/final advisers retain their earlier capacity/renewal choice scope but no longer generate prose in this mode. Code owns terms, verified claims, economics, accept/walk-away and journaling. A message with references, attachments, multiple sheets or insufficient time retains deterministic text; at most two writer calls per supplier are admitted.
- Evidence/budget: fake-provider tests admitted safe prose for all seven fixture types; saved P11 quality and P07 bundling situations were locally replayed through `agent.decide` and `rewrite_response`; a serial quality runner dispatched model prose; a local two-supplier RFQ simulator under the full candidate config sent model prose with zero timeouts using a real clock. Strict provider schema, CLI launch, zipped skill resource, unsafe-prose fallback, guarded-payload rehash and async worker dispatch were checked. A 129-test targeted regression suite and Ruff passed. Zero new provider calls and zero new Arena sessions for this change.
- Timing limitation: an exploratory 250x accelerated-clock RFQ diagnostic of the earlier unoptimized preview incurred two/four thread timeouts, versus one/one in its baseline control; it magnifies subsecond local setup and is not a hosted timing estimate. The candidate now skips brief loading for ineligible messages and passed the real-clock local simulator, but hosted latency is still unmeasured.
- Decision: retain this as an unpromoted opt-in coverage candidate. The previous P10 hosted failure remains evidence against claiming a score gain. Live provider validity, latency and outcomes across all seven types remain unmeasured; any further practice requires a separately bounded run.

## 2026-10-11 — Same three hosted practices with role skills and LLM buyer prose

- Hypothesis: the opt-in role skills and model-written buyer prose improve the P10 exchange without weakening validity or timing; P11 and P07 are comparison smoke cases but outside the live writing scope.
- Budget/provenance: one tracked Lab run `1ab0d8f8-95f9-4c05-9f92-3a84c3f67f17`, exactly three authorized practice sessions, P11/P07/P10 once each, `negotiator.agent:configured_agent`, runner `auto`, `gpt-6-sol`. Config `configs/score-push-v6-skilled.json` SHA-256 `d87eb7bbb5c06447714bf0391fec6830589d4fd207fcb8898feb913f39bd3eb6` differs from the earlier briefed config only by `llm_response_mode: skill-v1`. Candidate identity `b8f4e66e5e92fa72be8c3e04a72af9e6e11268710d7615cd7adc374c92c10369`; captured source patch SHA-256 `0795dd2bc41748be385a33babba6c315500e366de0b587322644fa0cba96b713`; base-plus-Sunday data SHA-256 `eccf11a79ba1d0afcbc4c839eaddf3e1335c3790cc84da8d47ee4272d15988ad`, matching the prior three runs. Final shared quota snapshot 235/750 remaining; this is a shared account, so its change since the previous snapshot is not attributed solely to these sessions.
- Outcomes: P11 session `c70d007b613ef639` scored **0.8771273853**, deal, 6 rounds, 0 timeouts (identical score to earlier P11). P07 session `ea5a7fd81a9073a7` scored **0.7599706752**, deal, 5 rounds, 0 timeouts (identical to earlier P07). P10 session `aba3502b4f89d128` scored **0.5546564482**, deal at EUR33.80/42 days/24 months, 2 rounds, 0 timeouts; earlier P10 scored **0.6472939821** at EUR31.90/56 days/24 months, 3 rounds. Three-case mean fell from **0.7614640142** to **0.7305848363**; this single unpaired repeat is not a causal estimate.
- Agent behavior: P11 and P07 made zero live adviser calls. P10's strategy call took 4.41 s, chose `keep`, and its `body` failed prose admission, so the deterministic opening email was sent. The final-advice call took 6.62 s and fell back with `ValueError` before a selected counter or model-written email was admitted; the coordinator accepted the standing offer. P10 used an extractive supplier brief; the new model brief compiler skill was not exercised. The trace records the exception class, but not the raw provider response, so the exact `ValueError` cause is unknown. There were zero model-authored buyer emails in these sessions.
- Decision: do not promote this candidate from this screen. Preserve the saved outcomes, investigate the prose rejection and final provider failure locally, then require another separately authorized bounded practice comparison before claiming an improvement.

## 2026-10-11 — Packaged role skills and opt-in LLM buyer prose (LOCAL ONLY)

- Hypothesis: role-specific instructions and model-authored buyer prose can use qualitative evidence and code-approved quantitative terms to express a better conditional exchange, while deterministic code retains terms, verified claims and closing authority.
- Source/config: isolated V6 candidate identity `b8f4e66e5e92fa72be8c3e04a72af9e6e11268710d7615cd7adc374c92c10369` in `experiments/v6-skilled-source-manifest.json`; new opt-in `configs/score-push-v6-skilled.json` SHA-256 `d87eb7bbb5c06447714bf0391fec6830589d4fd207fcb8898feb913f39bd3eb6`. The briefed config used in the three prior practices is unchanged and remains separately reproducible.
- Change: packaged skill files now guide the brief compiler, strategy adviser and final reviewer. The strategy skill adds active listening, calibrated questions, objective standards, private alternative discipline, approved anchoring, reciprocal conditional trades and explicit qualitative/quantitative input handling. The two live advisers can return model-authored buyer prose in their existing bounded calls; code validates the prose and falls back to its prepared text if unsupported. No model can alter term sheets, verified claims, accept/walk-away or the coordinator's risk screen through prose.
- Cases/budget: local synthetic capacity, final-offer and brief fixtures, plus an installed-resource zip check. Zero new Arena sessions and zero provider calls. Scope remains serial single-supplier capacity/renewal for model-written responses; other case types keep existing dispatch. The eight previously compiled model briefs still use their older inline compiler instruction until explicitly refreshed.
- Validation: 48 adviser/brief/config tests and 128 broader agent, evidence, claim, policy and context tests passed; Ruff and diff check passed. A supported model-written opening and final counter reach fresh dispatch validation; unsupported numbers, private phrases and promises fall back to the prepared text. No hosted score, production latency or semantic quality gain is claimed.
- Decision: retain as an opt-in candidate. Compare exact saved situations with writing on/off before any promotion; inspect the resulting supplier reply and full commercial outcome in a separately bounded Arena test.

## 2026-10-11 — Three random hosted practice screens of V6 briefed candidate

- Hypothesis: the opt-in briefed policy completes varied hosted cases without timeouts; a capacity case exercises the strategy and final-offer handoff. This is a three-case smoke test, not a paired comparison or promotion gate.
- Draw/budget: randomly drew P11, P16, P07 from Arena's 19 listed practice cases. P16 was `hosted: false`, so it was replaced by a random draw from the hosted roster, P10. The user authorized three practices. Three sessions opened, one each for P11, P07 and P10; quota 243/750 left before the first session and 240/750 left after the third. Preflight runs `23e6f07d-7e1a-4037-8dee-95b58ea2e50c` and `e8138823-e79e-45e1-9c0c-f6aa14a8d8de` failed before sessions (wrong factory arguments, then an unhosted case in the batch). The isolated P16 attempt `e6423cb0-6f5b-402f-8102-f6396b923067` also opened no session.
- Provenance: isolated V6 worktree commit `279f7a8348f4f94f0de650cb5f990aeaff794ab4` plus captured dirty-source patch SHA-256 `474a87255d5005259b4ec3c82daa3cd900ad290b9ad214b29835628debcd42e6`; `configs/score-push-v6-briefed.json` SHA-256 `c1083b1d1ecd671383d856cd7d2f994b74ab587c79fbb9c1474daec1de340c1e`; Lab base+Sunday data SHA-256 `eccf11a79ba1d0afcbc4c839eaddf3e1335c3790cc84da8d47ee4272d15988ad`. Agent `negotiator.agent:configured_agent`, `estimates={}`, `meso=false`, runner `auto`, provider model `gpt-6-sol`.
- Results: P11 run `544223be-a6ab-41d3-9c42-54c1829ab508`, session `f3f940a92916f3e9`: score **0.8771273853**, deal, 6 rounds, 0 timeouts. P07 run `f8212a55-55a7-46ba-9587-8d4e1a7d47fc`, session `cc4d5eac7a5aaed9`: **0.7599706752**, deal, 5 rounds, 0 timeouts. P10 run `bad636e8-21a4-4ce8-bf2f-a254b681baac`, session `2b19a78be2219f61`: **0.6472939821**, deal at EUR31.90/56 days/24 months, 3 rounds, 0 timeouts. All three passed Arena must-haves; mean **0.7614640142** across this sampled trio only.
- Behavior: P11 and P07 made no live adviser calls, as expected for their case types. P10 supplier `sup:70410` used an **extractive**, source-linked brief. The strategy adviser made one admitted call in 5.36 s and kept the prepared move; the final adviser made one admitted call in 4.57 s and chose a legal exploratory counter, which the supplier accepted. The P10 score repeats the earlier exploratory-counter result (0.6473) and is below the previously recorded 0.6551 P10 practice; one sample does not identify a brief effect. No model-compiled brief was exercised in these three sessions.
- Decision: keep the combined policy opt-in and unpromoted. This verifies end-to-end execution and bounded adviser latency on one capacity case, not a score gain, walk-risk calibration, or the latency percentile gate. Saved original results and owned threads are under the three run IDs above.

## 2026-10-11 — General supplier brief compiler and runtime handoff (LOCAL + PROVIDER ONLY)

- Hypothesis: a source-linked brief compiled ahead of negotiation can carry subjective supplier statements, conflicting news and past observations into the existing strategy/final reviewers without adding a live compilation call or granting the brief authority over terms.
- Source/config: local candidate identity `f25874c9414f8f8bb7b18d1af0845f5ba85a6bfc0415810c355dc2f25e6fc4c4` in `experiments/v6-candidate-source-manifest.json`; opt-in combined config `configs/score-push-v6-briefed.json` SHA-256 `c1083b1d1ecd671383d856cd7d2f994b74ab587c79fbb9c1474daec1de340c1e`; permanent package data identity `00317624303f28b4cbae883fd0554d9ce88779fb40b33de7f262e6784e0b5980`. Default V6 behavior remains unchanged.
- Data/calls: `prep --briefs` stored 46 versioned briefs under the permanent `tacto-negotiator/data/briefs/<data-sha256>/`: eight model briefs for suppliers affected by the Sunday release and 38 extractive fallbacks. Ten provider-only calls were made: one empty response, one initially rejected conflict, then eight successfully admitted semantic briefs. No Arena session, practice quota or new score. The earlier DNS-blocked sandbox attempts did not reach the provider.
- Validation: 154 focused tests passed across brief source scope, quote admission, stale/tampered fallback, strict provider schema, CLI prep, strategy and final-review routing, policy, release, dossier, claims, context and agent behavior; 42 additional package-adviser, memory, question and assessment tests passed. Ruff and `git diff --check` passed. The separate runner suite stalled on its first slow-reply simulator test under this sandbox and was interrupted; no runner-suite pass is claimed. A fake-provider local P10 strategy decision and final-offer decision both read the prepared brief and retained current-reply citation and closing checks. The live runtime latency and commercial effect of this combination are not measured.
- Decision: retain the combined config opt-in and unpromoted. The compiled brief's tactics are hypotheses; the latest supplier reply, current case facts, legal package menu and coordinator checks control action. The remaining 38 suppliers have source excerpts but no model interpretation. See `docs/v6-supplier-brief-architecture-2026-10-11.md`.

## 2026-10-11 — Skill-guided strategy review of prepared moves (LOCAL ONLY)

- Hypothesis: a smaller, skill-guided choice contract can select a supported complete package or registered question from the deterministic V6 move when the latest supplier reply supplies a relevant constraint. Provider latency and commercial effect remain unmeasured.
- Source/config: local candidate identity `c855992909105e71907fddb0a3ebe302f451ac2895928bb73b9a72ec25ea077b` in `experiments/v6-candidate-source-manifest.json`; opt-in `configs/score-push-v6-strategy.json` SHA-256 `08f9eb993a9a11d9e626a4d4a5768673f54d3141be42069cdf59c15e5acd6d97`; packaged negotiation skill SHA-256 `e2e7a26387d9f1381da837705aff0c26bc4c96f08468b307674a3c681f2e50c1`. The default V6 config is unchanged.
- Cases/budget: synthetic capacity and renewal fixtures and a fake-provider CLI launch. Zero provider calls, zero hosted Arena sessions and no practice quota used; no new score.
- Validation: 96 focused strategy/advice/final/policy/launch tests passed. Ruff and `git diff --check` passed. Tests cover legal package and question selection, exact source quote, refusal/term/cost checks, timeout and malformed fallback, stale state, restart accounting, scoped public notes, skill resource loading from a zipped package and default isolation. The recorded source manifest includes the new module, skill, config and tests.
- Decision: keep `strategy-v1` opt-in and unpromoted. A live latency and outcome comparison is required before claiming that the shorter contract remedies the P10 opening timeout or improves negotiation results. The separate final-offer reviewer and closing coordinator retain final-decision authority. See `docs/v6-strategy-llm-layer-2026-10-11.md`.

## 2026-10-11 — Exploratory final counter, live P10 diagnostic (ONE PRACTICE SESSION)

- Hypothesis: after disabling the repeatedly timed-out opening adviser, the source-linked final reviewer can select one legal counter and the explicit no-deal loss envelope can permit it to reach the supplier. Acceptance and score were unknown before the run.
- Source/config: local candidate byte identity `a8c9293baa3b68eb3aa058ab4ebaffea64a2f8e658b40fd3773916873c956e96`, config `configs/score-push-v6-final-explore.json` SHA-256 `74fd997bd3dfd687a5709f97f5a837abf52527836c9b6408e45cac1e717cc9f9`, captured dirty-source patch SHA-256 `5da8ee81829f339d392a2176617c83d3dd714d05745f1276dfee3b83e0d880cf`, supplied data SHA-256 `d5088ef05eb836b9b818f00adc584252d01362b28f73af964d9fac15a61f33dd`. Serial Lab runner, `gpt-6-sol`, practice P10. This is a combined change in opening-adviser call allocation and final-counter risk policy; their separate effects are not identified by this one run.
- Budget/evidence: user explicitly accepted one exploratory P10 counter with unknown walk probability. One practice session opened: run `6ddfcb54-5f8c-49e7-89ac-7e35cd46a64e`, session `54955c958d59d8c2`, attempt `case:P10:1`, completed Lab revision 7. Original outcome: `/home/ugur/harve-y/tacto-negotiator/experiments/runs/6ddfcb54-5f8c-49e7-89ac-7e35cd46a64e/run.json`; decision trace: `/tmp/v6-p10-final-explore-practice-20261011-trace/trace.jsonl`. Final shared quota snapshot: 255/750 left; other agents use the key, so its delta does not measure this run's consumption.
- Outcome: **0.6472939821** score, valid deal, must-haves met, zero Arena timeouts, three rounds, 19.01-second attempt. Opening adviser made zero calls. Final reviewer made one 2.90-second call (1,420 input/201 output tokens), cited the supplier's lead-time premium, and selected the legal EUR31.90/56-day buyer counter. The explicit no-deal screen logged EUR55,912.80 modeled gain if accepted, EUR587,839.20 possible loss relative to the case-priced no-deal fallback, and 8.69% binary break-even walk probability; actual walk probability remained unknown. The buyer sent that counter, supplier agreed, and the buyer accepted. Complete deal cost was EUR1,541,808.00.
- Comparison/decision: the prior one-session `select-v1` diagnostic accepted EUR33.80/42 days at score 0.5546564482 and cost EUR1,597,720.80. This run is +0.0926375339 score and EUR55,912.80 lower modeled cost on this exposed P10 reply. Keep `explore-v1` opt-in and unpromoted: one supplier acceptance does not calibrate walk probability, establish a win rate, or satisfy the plan's latency and commercial gates. No second session was started.

## 2026-10-11 — Explicit no-alternative final-counter exploration (LOCAL ONLY)

- Hypothesis: the P10 final reviewer can send its legal, source-linked counter when a user explicitly accepts exploratory no-deal risk, while preserving bounded execution and visible downside.
- Source/config: current local byte identity `a8c9293baa3b68eb3aa058ab4ebaffea64a2f8e658b40fd3773916873c956e96` in `experiments/v6-candidate-source-manifest.json`; isolated config `configs/score-push-v6-final-explore.json` SHA-256 `74fd997bd3dfd687a5709f97f5a837abf52527836c9b6408e45cac1e717cc9f9`. The default V6 and the prior `select-v1` candidate are unchanged in behavior. The new config suppresses the opening adviser call that timed out in the prior live run; it is a different experimental factor from the final risk mode.
- Case/evidence: exposed saved P10 supplier reply, case buyer fields and synthetic cases. Code prices no deal from the case's published fallback unit price and risk; the result is a scenario, not an executable alternative or calibrated walk probability. `explore-v1` requires a legal cited counter, positive buyer cost gain, at least 20 seconds closing reserve, at most one final counter, and a configured loss limit of 40% of standing cost. P10's break-even walk probability in the saved-thread local replay is about 8.6%; actual supplier walk probability remains unknown.
- Validation: 72 focused tests passed, Ruff and diff check passed. A fake-provider replay of the saved live supplier reply selected and pre-dispatch validated EUR31.90/56 days, with zero opening adviser calls. Its cost figures omit PDF defaults in the saved thread and are not a hosted outcome. No provider call or Arena session was opened for this change; there is no score or acceptance result.
- Decision: retain both default V6 and the conservative `select-v1` mode. The new `explore-v1` config is a separately labeled practice candidate for an explicit risk-tolerant test, not a promotion or expected-value claim.

## 2026-10-11 — V6 final-offer adviser, live P10 diagnostic (ONE PRACTICE SESSION)

- Hypothesis: the source-linked final-offer reviewer can recognize P10's cheaper lead-time variant in a real supplier reply and propose a legal counter, with code retaining closing authority.
- Source/config: local candidate identity `e71233c7445ba770dc093576d6f279d31851a1bb6b749481e5d23b0333d96412` was byte-checked before launch; `configs/score-push-v6-final-advice.json` SHA-256 `e8930458348205600d85e68b633b7805d2ae31c4b6f3990e82a1c8537d80f3f0`; captured dirty-source patch SHA-256 `1b04d00bfc6535c1713dd8115d5d87635d8c9f2ec6b7984d47dac2ee5d8e787d`; supplied data SHA-256 `d5088ef05eb836b9b818f00adc584252d01362b28f73af964d9fac15a61f33dd`. Serial Lab runner, `gpt-6-sol`, practice P10. Shared Lab recommendation and findings were read before launch; this standalone run did not promote a checkpoint.
- Budget/evidence: one session, run `59c67205-59ca-4dba-b187-b1de4eeb0c39`, session `9f8060c60c5d4648`, attempt `case:P10:1`, completed revision 7. Original result: `/home/ugur/harve-y/tacto-negotiator/experiments/runs/59c67205-59ca-4dba-b187-b1de4eeb0c39/run.json`; agent decision trace: `/tmp/v6-p10-final-advice-practice-20261011-trace/trace.jsonl`. Final shared quota snapshot was 276/750 left; other agents share the account, so the quota delta is not attributed to this session.
- Outcome: score **0.5546564482**; valid deal and must-haves, zero Arena timeouts, two rounds, 13.40-second attempt. Opening capacity adviser timed out after 8.01 seconds and fell back to the prepared EUR28.34/42-day offer. Final adviser completed in 2.50 seconds (1,420 input/224 output tokens), cited the supplier's EUR31.90/54-day variant, and selected the code-generated **EUR31.90/56-day buyer counter**. The risk gate rejected dispatch with `no_comparable_executable_alternative` (`c_alt` absent), so the buyer accepted the valid standing EUR33.80/42-day offer, 23,400/year for 24 months, complete deal cost EUR1,597,720.80. The proposed counter's modeled cost was EUR1,541,808.00; it was never offered, and supplier acceptance is unknown.
- Decision: the live test confirms source-linked recognition and counter selection, but no commercial effect under the current no-outside-alternative policy. Keep the opt-in candidate unpromoted. The opening adviser timeout remains a separate failure to address; no second practice session was started.

## 2026-10-11 — V6 final-offer LLM review (LOCAL ONLY)

- Hypothesis: a small source-linked review can flag a legal final counter before the deterministic accept path, while code retains closing authority and its independent risk gate.
- Source/config: opt-in `configs/score-push-v6-final-advice.json` (SHA-256 `e8930458348205600d85e68b633b7805d2ae31c4b6f3990e82a1c8537d80f3f0`); candidate byte identity `e71233c7445ba770dc093576d6f279d31851a1bb6b749481e5d23b0333d96412` in `experiments/v6-candidate-source-manifest.json`. Implementation and limits: `docs/v6-final-offer-advice-implementation-2026-10-11.md`. V6 default unchanged.
- Cases/evidence: synthetic capacity final replies and the saved P10 final reply are development evidence. The P10 reply produces one legal 56-day/EUR31.90 buyer-counter candidate; the supplier's 54-day sheet itself is outside the allowed options. The supplied data package has four scoped dossier notes for this supplier. No clean holdout claim.
- Validation: 68 focused tests passed with the supplied package; Ruff and diff check passed. A fake-provider dry run used the actual P10 dossier and saved final reply (4,117-byte context, three scoped notes, one legal counter). The broader run reached the known sandbox async worker-crash stall. No provider calls or Arena sessions were opened for this change; no new score or latency result.
- Decision: keep the reviewer opt-in and V6 default. P10 has no executable outside alternative, so a model-selected counter remains a logged recommendation and the deterministic accept stands. The next live practice is a separate tracked experiment; no rollout or promotion is claimed.

## 2026-10-11 — V6 P10 selection candidate, live diagnostic (ONE PRACTICE SESSION)

- Hypothesis: the reconstructed P10 provider probe may overstate failure on the real hosted P10 request. User authorized one real practice run to check. This is a diagnostic, not the proposed matched-arm screen or an inference-gate override for promotion.
- Source/config: opt-in `select-v1`, `configs/score-push-v6-select.json` SHA-256 `ae6bc0079f460567f5103d5e1f7ad7ec221d7d3b0bbcc1b948f479694b196310`; candidate identity `bcea19954ff7fb95e94de195670df614218fd9f410b570242bef33be6ab56e3d`. Dirty source captured before the run as patch SHA-256 `0812fadf139fed7607b09d05e6670a138a4be3178ed0acb3a7183da99f6b25a1`, lock SHA-256 `a0ec7fe14679fbe9e9c2bc75b87316a4d3026b94a2fc1a590bf20584c193cf7f`, data SHA-256 `d5088ef05eb836b9b818f00adc584252d01362b28f73af964d9fac15a61f33dd`. Serial runner; `gpt-6-sol` provider. Shared Lab recommendation and findings were read before the run; this standalone experiment did not alter the recommendation.
- Budget/evidence: exactly one practice session opened: run `a5132f52-3187-44fa-a4dd-7b6152ce15a0`, session `193e32132c201b49`, attempt `case:P10:1`; Lab revision 7 completed. Owned evidence: `/home/ugur/harve-y/tacto-negotiator/experiments/runs/a5132f52-3187-44fa-a4dd-7b6152ce15a0/run.json`. Live shared quota read 291 left before and 288 after; other agents share the account, so the delta is not attributed to this run.
- Outcome: score **0.5546564482**, valid deal, must-haves met, zero Arena timeouts, two rounds, 10.84-second attempt. Accepted EUR33.80, 42-day lead, 23,400 units/year, 24 months; complete deal cost EUR1,597,720.80. One combined adviser attempt reached its eight-second limit (`TimeoutError`, 8.01 s); no provider usage was reported. The adviser admitted no observation, changed no package and fell back to the prepared V6 opening. The live request had 3,872 context bytes and five candidates. The previous guarded P10 run had the same score and terms, but its exact fallback reason was not retained.
- Decision: the real P10 run confirms a latency failure for this candidate; the offline reconstruction was useful as a warning, although one live attempt cannot establish a failure rate. Keep V6 as default. Revise/measure the combined request before matched-arm screening. No retry or additional session was started.

## 2026-10-11 — V6 reconstructed provider latency probe (30 CALLS, ZERO ARENA)

- Approval: user separately authorized up to 30 provider-only calls. The script enforced exactly six payloads × five repeats, sequentially, with a fresh HTTP client and eight-second request timeout. All 30 slots were consumed; no Arena session opened. Model `gpt-6-sol`, no explicit effort setting. Original complete P10 request was not saved, so this is reconstructed development evidence.
- Source: candidate identity `bcea19954ff7fb95e94de195670df614218fd9f410b570242bef33be6ab56e3d`; probe script SHA-256 `1ec059c75964b0cf4071d75d6a8b6eebb236f1713b526a0e4329debf6f5e3bbd`; report `experiments/v6-provider-probe-2026-10-11.json` SHA-256 `850d7743434d946baf7b192a94dff85f4dd7881c4366a45602356544be1ad5b5`. Request digests and sizes are in the report; no key, raw response or request text is recorded.
- Results: legacy schema 15/15 valid, wall 1.60–3.02 s. Combined assessment schema 10/15 valid. All five reconstructed saved P10 combined calls failed (three invalid JSON, two read timeouts; wall 7.67–8.16 s). The other two combined variants passed 10/10 (2.62–6.00 s). Combined nearest-rank p95 8.16 s. Reported tokens for the 25 valid calls: 30,440 input / 5,054 output; usage unknown for five failed calls. Provider HTTP and parsing are not separately timed; model warm/cold state and finish reasons are unknown.
- Decision: inference gate fails on this exploratory batch, even before representative concurrency. Do not run the proposed 12+18 Arena screening sessions or promote. No further provider calls are covered by this approval. Next iteration should reduce the saved-P10 contract's failure rate, freeze a new source/config identity, then obtain a fresh provider allowance and verify the gate before Arena evaluation.

## 2026-10-11 — V6 P2–P6 local supplier intelligence candidate (NO HOSTED CALLS)

- Hypothesis: independent source admission plus bounded package selection can adapt to different current constraints while preserving V6's prepared move on rejection. Questions and final counters are separate opt-in factors.
- Source: uncommitted worktree based on `279f7a8348f4f94f0de650cb5f990aeaff794ab4`; the P0/P1 worktree edits remain part of this candidate. Local candidate identity `bcea19954ff7fb95e94de195670df614218fd9f410b570242bef33be6ab56e3d` (`experiments/v6-candidate-source-manifest.json`). Config hashes: shadow `acd83bb5b09ffcb7361bab96bc6efac75ec6f1782bfaf19ec0b72ac57ea8afd5`, selection `ae6bc0079f460567f5103d5e1f7ad7ec221d7d3b0bbcc1b948f479694b196310`, questions `c1f3f15ab2a4131c4dd509f35780e4278378d4123014e9a92dea1fd566555488`, final review `f351a3f03454fe3e330bdee39383062e30710191f488781fec2b6d35f92223f3`. Full paths and gate status: `docs/v6-p2-p6-implementation-2026-10-11.md`.
- Cases/evidence: checked-in capacity/renewal fixtures and synthetic source/restart/final scenarios are development evidence. The exposure manifest makes no clean hosted holdout claim. Relevant regression: 112 passed (111 in sandbox and one local socket test after permitted unsandboxed rerun); Ruff passed. A full-suite attempt reached a test requiring absent `uv`, then other tests requiring absent `data/package`; an async simulator test stalled in this sandbox. This local implementation itself made no provider or Arena call and no new commercial score; the separate 30-call provider probe is logged above.
- Decision: V6 remains default. Shadow, selection, question and final-review configs are reviewable arms, not a launch approval. The 30-call latency proposal, 12+18 Arena comparison and separate question/final budgets remain unspent pending explicit allowances, frozen source/model/data and a usable holdout.

## 2026-10-11 — One guarded V6 P10 practice run (ONE SESSION)

- Hypothesis: bounded source-linked capacity advice can change P10 to a supported cost-neutral package while keeping V6's fallback and closing behavior safe.
- Source/config: local dirty worktree based on `279f7a8`, captured patch SHA-256 `779df891b32da726d2ab987811a137731eaecf892761ce4e6b17c937c0d40875`; `configs/score-push-v6-guarded.json` SHA-256 `ee82a755f7945e0bc0e480e7d1149c080db459aa88a1e1948408e7dcdff41903`; supplied data SHA-256 `d5088ef05eb836b9b818f00adc584252d01362b28f73af964d9fac15a61f33dd`. Serial runner, provider `openai`, model `gpt-6-sol`. The standalone run recorded no lockfile hash because `--repo` pointed at the worktree root; the captured source patch remains available locally.
- Budget/evidence: exactly one practice session, run `993256b3-4c90-4b17-8a62-31861dd6e467`, session `7de508c85d766d1f`, attempt `case:P10:1`. Shared quota 312 → 311 left of 750. The completed revision 7 is present in the shared Lab. Original local evidence is `experiments/runs/993256b3-4c90-4b17-8a62-31861dd6e467/run.json` in the tooling checkout.
- Outcome: score **0.5546564482**, valid deal, must-haves met, zero Arena timeouts, two rounds, 9.97-second attempt. Accepted standing offer: EUR33.80, 42-day lead, 23,400 units/year, 24 months. Complete recorded deal cost EUR1,597,720.80. The adviser made one call (6.99 seconds; 1,799 input and 714 output tokens), changed no package, and fell back to the prepared V6 move. ModelAssist made zero calls. The standalone metrics did not retain the precise fallback reason, so this run cannot attribute it to schema, semantic admission, or another provider error.
- Decision: keep V6 default and make no commercial claim from one unpaired P10 result. After the run, local adviser metrics were extended to retain bounded outcome reasons for future runs; that change was **not** part of this session and was not retested live. No second session is authorized or started.

## 2026-10-11 — V6 P0/P1 guarded advice integration (LOCAL ONLY)

- Hypothesis: a bounded opt-in adviser can be attached to one V6 serial capacity move while preserving the prepared move on keep/failure and preventing stale or expired sends.
- Source/control: base `279f7a8`, `configs/score-push-v6.json` (SHA-256 `d093a41d23b0a8e4b9c08046ae5eaf9ed74b85b16646e82f586878b5aa56591d`); candidate `configs/score-push-v6-guarded.json` (SHA-256 `ee82a755f7945e0bc0e480e7d1149c080db459aa88a1e1948408e7dcdff41903`). Implementation is an uncommitted worktree change. P10 saved trace and all checked-in practice cases are development exposure, recorded in `experiments/v6-exposure-manifest.json`.
- Cases/quota/scores: saved P10 and synthetic capacity replies only; zero Arena sessions, zero provider calls, no new scores. The dry-run provider probe emits six reconstructed request digests and a 30-call proposal, without executing it.
- Validation/failures: 91 focused tests and Ruff pass. One async model test stalls, one dashboard test needs a forbidden local socket, and two policy tests need an absent data package; see the implementation record. Unsupported, malformed, stale, expired and delayed advice are covered by local tests.
- Decision: retain V6 as default. Keep this candidate local until provider allowance, latency measurement and later assessment/action stages are reviewed; no promotion or launch change.

## 2026-10-10 — Shared-lab ingestion compatibility hotfix (DEPLOYMENT CHECK)

- Hypothesis: registering a matching supplied package should refresh feedback for versioned runs while skipping historical imports that have no provenance. The first deployed ingest stopped on such an import before refresh; the original runs and recommendation were unchanged.
- Change: skip a run whose provenance is absent when selecting version-matched refreshes. A regression fixture includes an imported run without provenance alongside a matched tracked run.
- Validation: nine focused learning tests, 595 full Python tests and Ruff passed. No Arena session or practice quota. The matching supplied package was transferred to the trusted team lab and fingerprint-checked before ingest. A pre-deployment SQLite backup passed integrity check.
- Decision: deploy the compatibility fix and retry the same data ingest. Do not infer negotiation-score improvement or promote a checkpoint from this operational fix.

## 2026-10-10 — Supplier learning loop, local integration (UNPROMOTED)

- Hypothesis: versioned supplied data and terminal run uploads can refresh separate public-fact and episodic stores, produce cited feedback, and create a reviewable configuration candidate without changing active sessions or the recommended checkpoint.
- Source: `codex/combined-latest-updates` based on `883a272`; local uncommitted implementation in `src/negotiator/lab/learning.py`, `knowledge.py`, `loop_store.py`, and related API/CLI/tests. Configuration changes are registry-bounded; code-change findings remain engineering work.
- Evidence: kit-data ingest projected 10,356 public facts; offline replay of saved practice run `385bee17-1dac-45a4-bb88-25477127355a` produced one ready report and no candidate proposal (zero recorded timeouts). The explicit async local simulator rehearsal used 12 sessions, zero timeouts, and completed its temporary comparison; toy scores are not hosted evidence. Focused learning tests, full Python/Node tests, and Ruff are recorded in the development report. No Arena sessions or practice quota consumed; no real provider calls or cost estimate.
- Decision: retain as a local integration candidate. No shared-lab deployment, recommended-checkpoint promotion, or memory/model policy enablement. Hosted lab feedback/learning endpoints still return 404 on the deployed revision. Next: deploy after team review, verify migration/endpoints, then authorize a budgeted held-out async hosted comparison and inspect every gate.

Follow-up on the same local candidate: the prior practice run's P02, P05, P10 and P18 each
had a valid deal, zero recorded timeouts, a score below 50/100 and price cost above 75% of
the recorded deal cost. Objective feedback now cites those four attempts and proposes one
bounded `anchor=0.16` comparison. This is a price-opening hypothesis, not an identified
cause or measured improvement. It does not change the recommended checkpoint. Supplier
memory retrieval now excludes other cases, stale source revisions cannot register or
promote a proposal, and teammate review must use a different author. The shared lab's
authenticated feedback/learning routes were rechecked and still returned 404. No additional
hosted sessions or practice quota were used.

## 2026-10-10 — Combined branch, all hosted practice suppliers (MEASURED HOSTED)

- Hypothesis: the combined package/evidence policy completes every currently hosted practice supplier with valid outcomes and measurable scores. This is one unpaired exploratory sweep, not promotion evidence.
- Source: `codex/combined-latest-updates` at `883a272`; `configs/candidate.json` passed as `PackageAgent(policy=...)`; pinned kit data `1b5516b`; serial `negotiator lab run`. Model assistance and optional supplier-memory snapshot were off. Run: `experiments/runs/385bee17-1dac-45a4-bb88-25477127355a/run.json` (also uploaded to the team lab).
- Arena returned 19 practice case IDs, of which exactly ten were marked `hosted: true`: P01–P05, P07–P08, P10–P11, P18. An initial 19-case lab plan was rejected before any session opened (`f1fd4e45-bae7-4fd6-90a9-432e6deab557`); the actual run used a strict ten-session ceiling and one repetition.
- Scores (/100): P01 92.53, P02 29.47, P03 89.98, P04 86.04, P05 36.04, P07 74.30, P08 59.30, P10 45.32, P11 79.02, P18 45.31. Mean 63.73; sum 637.31. All ten attempts completed with deals, must-haves satisfied, session IDs, no recorded attempt errors and zero recorded timeouts. Practice quota moved from 88 used / 512 left to 98 used / 502 left (limit 600) during this sweep.
- The initial publisher left a stale `running` lab revision; an idempotent upload of the final saved snapshot was acknowledged and GET verified `completed`. Hosted `/api/feedback/<run-id>` returned 404, so automatic hosted feedback could not be verified. The run file is the primary outcome evidence.
- Next: inspect low-scoring P02, P05, P10 and P18 against the full saved transcripts, then test a single specific change in a paired, repeated comparison before promotion. This run does not validate async execution, model interpretation, or supplier memory.

## Supplier memory merge and data/feedback separation — local integration, 10 October 2026

- Hypothesis: Barış's cited, immutable supplier memory can coexist with bounded email
  interpretation and current public-data graph projection, without allowing fresh data
  to rewrite conversation history or automatically change negotiation policy.
- Source/config: `codex/combined-latest-updates` merges `origin/codex/supplier-memory`
  at `975c15e`; immutable memory and model assistance are separate explicit options.
  Fresh facts are projected only when a versioned public package is supplied.
- Cases: local synthetic graph, feedback, checkpoint and memory-policy tests. The data
  projection test changes a supplier scorecard between releases and checks that episodic
  node IDs remain stable. A terminal lab upload test checks persisted feedback and retained
  original run data. Validation: 585 Python tests passed, Ruff clean; 21 lab Node
  checks passed and nine DOM-dependent checks skipped in this local environment.
- Hosted sessions/quota: 0. Model calls: 0. Scores: unmeasured. Decision: retain as an
  opt-in integration candidate; no default policy promotion or main deployment.

## Combined latest-updates branch — local integration, 10 October 2026

- Hypothesis: the verified evidence branch can retain its standalone index evidence while
  adopting the newer async runtime, bounded model interpretation, lab feedback, and
  `main`'s context/claim checks and measured opt-in policies without breaking contracts.
- Config/source: `codex/combined-latest-updates`; merged
  `codex/verified-negotiation-evidence`, `codex/bounded-model-memory`, and `origin/main`
  at `3653046`. Historical evidence tests expecting acceptance of non-standing sheet IDs
  were archived in `experiments/legacy-package-regressions.py.txt`; the current hosted
  standing-only contract is tested by `test_evaluator.py` and `test_runner.py`.
- Cases: local fixture and simulator tests only. Validation: 419 pytest tests passed,
  Ruff clean, including local lab HTTP tests. The pinned kit data path was supplied
  explicitly. No Arena sessions, model-provider calls, or practice quota were used.
- Result: merge and local regression checks passed. No deal-score estimate or promotion
  claim; model assistance and package advice remain opt-in. A hosted paired comparison,
  model latency/cost check, and final-machine rehearsal are still required.

## Fact-keyed recent index windows — qualification survey (OFFLINE, 0 sessions), 10 October 2026

- Rule (`configs/recent-index-window.json`, scope = all single-supplier types): cite a public index
  window ending at the latest published month only if the series is a listed cost driver of the
  part (weight ≥ 0.10), fell ≥ 1 pp, and the supplier's own letters/quote remarks contain no
  hedge ("covered … fixed prices/until", "hedged"). A hedge sentence naming a material hedges the
  matching series (name stems, e.g. "alloys" ~ "Alloy surcharge"); a generic one ("Material
  covered") hedges all. Nothing qualifies → exactly the configured default evidence (none for
  raw_material). Case IDs and types are not used.
- Survey of hosted cases (latest 12-month window; most recent buyer window):
  - P01 (PPI-C241 0.26 +6.5, LCI-C 0.32 +2.7, PPI-D351 0.06 −3.7): only PPI-D351 falls (−6.1%
    11/25→08/26), but it is below the weight floor and has risen 4 months running. Not qualifying.
  - P02 (CU-NOTATION 0.20 +47.7 and rising every month to 09/26; PPI-C241 0.16 +6.5 rising; LCI-C
    0.21 +2.7): **no falling window at all**. Not qualifying. The P02 screen was not run.
  - P03 (PPI-C2611 +13.5, CU +47.7, LCI-C), P04 (PPI-C2815 +0.8, LCI-C), P07 (PPI-C2594 +1.7, LCI-C),
    P10 (PPI-C2219 +3.9, LCI-C): all rising at the latest month. Not qualifying.
  - P11: same drivers as P01 (PPI-D351 0.06). Not qualifying.
  - P05 (RFQ, 3 suppliers): AS-14404 0.16 −5.5% and PPI-C2431 0.19 −2.3% qualify, no hedge found
    for 70210/70240/70250. But evidence here is single-supplier only, and P05 is owned by
    `codex/score-push-p05` (now 0.7723 with `rfq_data_claims`). Not screened, to avoid overlap.
  - P08: AS-14404/PPI-C2431 fall as in P18, but 70710's letter `doc:20260706-70710-M1` ("nickel and
    alloys … covered at fixed prices until March 2027") and its quote remark ("Material covered until
    March 2027") hedge both. 70710 is a bar stockholder, so the bars (PPI-C2431) are its material.
    Excluded. This matches fullcost `e3f1f373` (0.3606, rebutted).
  - P18: both qualify (no hedge for 70740). Only case changed (tested: enrich output differs from the
    retained config for P18 only).
- Prior art found: `codex/score-push-fullcost` screened the same two windows on P18 (`8444d792`,
  `fc54cd39`: 0.4531 ×2) and P08 (`e3f1f373`: 0.3606). That run was on the clause-variant base and
  added a scorecard claim. On the retained package base without the scorecard, this branch gets
  0.5200 ×2. The base policy and claim mix matter: the screen below is not the first index-window
  test on P18, but it is the first on this base.
- P02 interaction: the fullcost-rel cost-posterior worker owns P02 (0.7115 ×2). The lever does not
  qualify there anyway, so there is no interaction.
- Validation: 375 passed + known preflight failure; ruff clean. Sessions: 0.

## P18 recent index windows — REPEAT: 0.5200 confirmed, 10 October 2026

- Run `5223242a-a174-4870-85e3-5eb47c68ebec`, session `7dd75ee1f6308fd6`: **0.5200438598**, identical
  path (6.10 → 5.50 "acknowledging the recent index decreases you verified" → 5.40 → 5.30 final, agreed,
  AS-14404 db0 / 90d / 24m). 1 session, no expiry. `lab sync`: uploaded 2, failed 0.

## P18 recent index windows — REPEAT (pre-registration), 10 October 2026

- Same config/commit lineage as the KEEP entry below (`configs/p18-recent-index-window.json`).
  Nothing differs; purpose is to confirm 0.5200 is reproducible rather than one favourable
  supplier draw. 1 session, no replacement unless expired.

## P18 recent buyer-favourable index windows on retained package — KEEP 0.5200, 10 October 2026

- Baseline/comparator: retained P18 policy `configs/retained-package-policy.json`,
  0.4530612521 (`b2922dc3`, session `e7f60b71102745a0`; 5.40 / 90d / 24m / deadband 0).
- Single change: the first buyer counter adds two verified public index claims over windows
  ending at the latest published month: AS-14404 2026-06→2026-09 (-5.5%) and PPI-C2431
  2026-06→2026-08 (-2.3%). Packages, prices, clause and message order are otherwise identical.
  No scorecard, quote, PO, scope or internal-estimate claims.
- What differs from earlier attempts: P18 evidence screens cited the scorecard (verified,
  no movement, 0.3861), a public quote (irrelevant) or scope (0.3861); none cited falling
  index windows, because the default picker drops rising 12-month windows and cherry-pick was
  off. The P08 alloy-hedge letter (`aaac8af4`, tie) is a different lever. P08's index-window
  test (`7fdf0fce`) ran on the full-cost policy, not this package, and its AS-14404 claim was
  rejected only because P08's supplier says it is hedged until 03/2027. P18's supplier 70740
  has no such hedge in its notice or case documents, and its own breakdown attributes 45% of
  cost to AS-14404 and 38% to PPI-C2431.
- Why it could work: the supplier justifies +11% with 12-month rises. Latest-month windows
  show both drivers now falling, which is current, public and checkable. Unlike a stale
  cherry-picked window, it disputes the trend the supplier is pricing forward.
- Fairness: the windows use only public index facts. No hidden outcomes, `C_best` or other
  teams' prices are used in pricing.
- Plan: offline replay (only first counter body/refs may change), then one hosted P18 run.
  Keep if > 0.4531 and the claims are verified/used; otherwise preserve as failed. Budget: up to
  2 sessions (1 run + 1 replacement only if it expires), reserve 40 untouched.
- Offline: replay vs retained thread — only first counter body/refs change; all 5 term sheets
  and actions identical. 374 passed except the known claim-data preflight test; ruff clean.
- Hosted: `f1af63e1-0f3d-4cce-8e61-c80c31304a2f`, session `193fd257d7a43c1e`, commit `83a32b0`.
  Score **0.5200438598** vs 0.4530612521 (+0.0669826077 on P18; +0.0067 ten-case mean).
  Deal 5.30 / 90d / 24m / AS-14404 deadband 0 (baseline 5.40, same clause). Both claims
  `verified`; supplier: "Acknowledging the recent index decreases you verified, we are pleased
  to offer a revised unit price of EUR 5.50" (baseline first counter-offer: 5.70/5.60), then
  conceded to a 5.30 final. It still restated its 12-month rises ("That remains").
- Sessions: 1 (no expiry, no replacement). Quota 443→440 during the run (others shared it).
- Decision: KEEP as P18 candidate (new best 0.5200). Single sample: the supplier is likely
  deterministic for identical messages, so a repeat would mostly confirm caching, not
  variance. Transfer to other raw-material/price-increase cases is unmeasured; P08's hedge
  rebuttal shows the lever depends on supplier context.

## Packaged runtime negotiation guidance — local integration, 10 October 2026

- Hypothesis: explicit conditional package wording communicates the exchange more clearly
  while preserving validated terms; score benefit remains unmeasured.
- Config/source: working tree, packaged `src/negotiator/AGENTS.md`, runtime-settings v1.
  Custom CLI serial/async play/run (including final) now load the guidance and record
  its SHA-256 and effective settings. Missing/invalid guidance stops launch.
- Existing numerical heuristics remain baseline values. Default CLI wording now makes
  multi-issue offers conditional on the proposed price. Explicit experiment policies,
  estimates and generic MESO activation retain existing controls; no candidate promotion.
- Direct `PackageAgent` construction used by comparison tools retains its previous defaults.
  Starter `arena --agent llm` is a separate implementation and does not load this guidance.
- Cases: local synthetic RFQ decision comparison and both final CLI dispatch paths.
  Integration tests verify changed guidance affects prices, conditional wording preserves
  term sheets, arbitrary-cwd loading, trace provenance and launch failure on invalid guidance.
- Validation: negotiation-only branch: 115 tests passed; combined checkout: 166 tests
  passed; ruff clean. Wheel built offline, contains the guidance, and loads successfully
  after extraction outside the source checkout.
- Hosted sessions/quota: 0. Scores: unmeasured. Full final readiness remains outstanding.
- Decision: runtime integration implemented; no claim of improved negotiation outcomes.

## 2026-10-10 — Readable experiment reports (UI VALIDATION)

- Hypothesis: outcome summaries, labeled terms, cost bars and per-supplier conversations make
  saved experiments easier to inspect than configuration/message JSON. No agent behavior changed.
- Data/config: existing lab run `ee284ea2-76b7-4100-a03f-27fce795f7cc` (D01/D02), unchanged.
  Raw JSON and fingerprints remain accessible under collapsed technical details.
- Validation: ten JavaScript tests pass. An isolated DOM check rendered all 37 messages across
  three suppliers and verified terms, scores, escaping, retained expanded sections/scroll, and
  imported, failed, recovered and truncated evidence states. Ruff and JS syntax checks pass.
- Limit: in-app browser control timed out, so desktop/mobile appearance was not visually verified.
- Quota/scores: no new arena sessions; previous measured results retained. Decision: use the report
  for inspection, preserving partial scores and operational failures explicitly.

## 2026-10-10 14:43 — First shared-lab baseline (MEASURED HOSTED SANDBOX)

- Hypothesis: establish the current PackageAgent's D01/D02 reference and verify the lab records
  and publishes complete results from the host laptop.
- Run: `ee284ea2-76b7-4100-a03f-27fce795f7cc`, **Package v0.2 — first lab baseline**;
  commit `1a18dc0e17f9137deedf52f6db18bd77a006039f`, dirty checkout explicitly allowed.
  Patch SHA256 `fcf7cbc45c297efffc95039868f8b3fe2db7fd785a391928fb83b3ddc68277fb`.
- Config: anchor 0.12, rounds 5, close_gap 0.005, final_hold_s 40, p_walk 0.25;
  claims=false, meso=false, estimates={}. Official kit serial play interface; no wave deadline.
  No local data package, so its fingerprint is null. No provider-model calls.
- Cases: D01/D02, one attempt each, maximum two sessions, explicit sandbox environment.
  D01 **90.48/100**, C=EUR 412,451.25, 26.12s, 7 counted sends/closes;
  D02 **46.09/100**, C=EUR 187,768.00, 7.52s, 10 counted sends/closes.
  Two-case mean **68.28/100**. Both deals satisfy must-haves; zero recorded timeouts/failures.
- Sessions/replays: [D01](https://arena.tacto.ai/replay/0303d7a8e61f034a),
  [D02](https://arena.tacto.ai/replay/ad3bb1c328d166d7).
- Quota: both starts used sandbox cases. Shared practice snapshot changed from 19 used / 181 left
  to 20 used / 180 left while the run was active; the shared counter does not attribute that change
  to a caller. Do not count these two sandbox attempts as practice starts or assert the team was idle.
- Verification: the dashboard's stored final record exactly matches the local run snapshot.
  Raw evidence: `experiments/runs/ee284ea2-76b7-4100-a03f-27fce795f7cc/run.json` (ignored).
- Decision: retain this as the first lab baseline. One run per case is insufficient for a strategy
  promotion; compare a named candidate on the same case plan with repeats before drawing conclusions.

## 2026-10-10 — Dashboard sign-in diagnosis (LOCAL TESTS / PUBLIC TUNNEL)

- Trigger: public-tunnel sign-in displayed a generic sign-in prompt after a connection failure.
- Findings: the existing password and cookie authenticated successfully over the supplied HTTPS
  tunnel in an API check; browser-style requests intermittently timed out. A local regression
  also reproduced a race where an outstanding anonymous refresh skipped the post-login refresh.
- Change: serialize the post-login refresh, retain specific timeout/network/cookie errors, and
  reject unexpected non-JSON tunnel responses. No password or authentication-policy changes.
- Validation: five JavaScript regression tests pass, including the reproduced refresh race.
  Hosted arena cases/quota/scores: none; this is dashboard behavior only. User-browser confirmation
  remains needed to determine whether these fixes resolve the reported public-tunnel symptom.

## 2026-10-10 — Shared experiment lab integration (MEASURED LOCAL)

- Hypothesis: an independent runner and shared dashboard can retain experiment provenance,
  failures and case-aligned comparisons while teammates execute on separate laptops.
- Revision/config: work on `codex/experiment-dashboard` from `42c7659`, uncommitted integration
  run explicitly allowed; PackageAgent defaults, official local simulator with its clock disabled.
- Cases: S01/S02, one attempt each. Scores **82.90/100** and **86.09/100**, both completed;
  five and nine rounds respectively. These verify integration, not a new negotiation strategy.
- Quota: two local simulator sessions; zero hosted sessions and no provider-model calls.
- Evidence: atomic snapshots under `/tmp/lab-e2e-runs/8fd28b58-0237-42dd-b5f5-6367d5586131/`;
  dashboard UI checks used a separate synthetic database, never the real team database.
- Failures addressed in review: reject hosted URLs in simulator mode; preserve imported terminal
  evidence when delayed tracked snapshots arrive; retry and reconcile incomplete history imports.
- Decision: use the lab for development tracking. Preserve original operational failures when
  recovering arena outcomes. This does not change the agent or establish final readiness.

## 2026-10-10 13:37 — Hosted sandbox baseline and RFQ probe (MEASURED HOSTED)

- Revision: `e543b5d5d14fff699019bdffb38688c3bee882b7`, kit `1b5516b`; added diagnostic
  scripts `tools/sandbox_baseline.py` and `tools/rfq_timing_probe.py`. PackageAgent default
  anchor 12%, five-step schedule, close gap 0.5%; deterministic templates, no model calls.
- Hypothesis: optimizing complete packages improves the starter; independent RFQ requests
  can reduce idle-thread timeouts. These are separate experiments, not a controlled ablation.
- Data: downloaded `data/package/world.sqlite`, SHA256
  `4d8c896740350218d39f9d1ceada7b937f0d4e3078a155312851b8c09ed172b9`.
  Verified 447 suppliers, 60 parts, 166 cost-driver rows, 2,258 index values, 208 documents.
  Sunday release not yet available. Do not confuse the full supplier table with the active
  suppliers in challenge cases.
- Naive, one run per case: D01 **20.04/100**, C=€440,757.33, 35.85s, zero timeouts;
  D02 **22.95/100**, C=€201,088.00, 75.28s, one timeout on DEMO-J1. Both deals satisfy must-haves.
  Sessions `7ba285e7808110f7`, `92060a989d6ae9e0`.
- PackageAgent clean rerun, one run per case: D01 **93.24/100**, C=€411,339.92, 8.95s;
  D02 **41.89/100**, C=€190,184.00, 25.30s. Both deals satisfy must-haves; zero timeouts.
  Sessions `923ce268740f20fc`, `fcaea618ad0cdf72`. Unweighted two-case mean **67.57/100**
  versus naive **21.49/100**. This small, unrepeated sample is not a generalization estimate.
- One-round concurrent D02 timing probe: both requests started within 1ms; replies at 14.91s
  and 70.30s; zero timeouts in post-reply snapshots. The probe closed at **27.20/100**.
  Session `52a8e87b7ab4899d`. This was a timing test, not the PackageAgent strategy.
  Server serialization/clock-stop mechanism and sustained multi-round safety remain unknown.
  Production must process replies as they arrive: waiting for both left the first thread idle
  for about 55.4s, close to its 60s limit.
- Invalid strategy comparison retained: sessions `a18869e79c54c4fb`, `a794e41d3e700a8c`
  ended at zero/no deal with three timeouts on every thread. macOS power logs confirm clamshell
  sleep at 13:25:32, waking at 13:32:15 (403s). Exclude these from strategy comparison, retain
  as operational failures. Do not attribute the delay solely to the hosted service. Monotonic
  elapsed time understated wall time across sleep. The clean rerun used `caffeinate -i`.
- Quota: all baseline/probe runs used sandbox only (seven sessions total including
  interrupted cases); practice remains **0 used / 200 available**. No provider-model spend.
- Decision: keep PackageAgent v0 as the measured development baseline; do not deploy it to the
  final unchanged. Prioritize RFQ scheduling, coordinated guarded close/reconciliation,
  relationship-cost estimates and evaluation across diverse cases before added model complexity.
  Keep laptop lid open; rehearse the actual final host/network and deadline recovery.
- Validation: 14 tests pass; Ruff passes. These checks do not verify final readiness.

Raw local evidence (ignored by Git):

- `runs/20261010T112335Z-sandbox-naive-2d319f/`
- `runs/20261010T112418Z-D02-concurrent-9b18f4/`
- `runs/20261010T112455Z-sandbox-package-b55adf/` (sleep-interrupted)
- `runs/20261010T113551Z-sandbox-package-4620f4/` (clean rerun)

Reproduce only sandbox runs from repo root, with the lid open:

```bash
caffeinate -i uv run --locked python tools/sandbox_baseline.py --agent naive
caffeinate -i uv run --locked python tools/sandbox_baseline.py --agent package
caffeinate -i uv run --locked python tools/rfq_timing_probe.py
```

<!--
## E0 - baseline (YYYY-MM-DD HH:MM, owner: )
Hypothesis:
Change: commit
Cases × runs:
Result: mean , min , timeouts , contradicted , must-have breaks
Per-case notes:
Decision:
-->

## 2026-10-10 12:40 - E0/v0 on local arena-sim (MEASURED LOCAL, not hosted)

- Setup: arena-sim (kit 1b5516b), data package identical to audited copy (dump hash match).
- E0 naive: S01 0.521, S02 0.513, S03 0.678 -> mean 57.1. Naive works one RFQ thread only and leaves
  non-price terms at plan values.
- v0 PackageAgent (complete-cost best non-price terms, 12 % anchor, 5-round linear schedule,
  re-offer our terms at their price before accepting, one checked close): S01 0.829, S02 0.861,
  S03 0.886 -> mean 85.8. All deals beat alternative; must-haves ok.
- Caveat: the sim supplier is a fixed script that prices nothing but unit_price. Hosted suppliers
  price payment/incoterm/contract terms; the non-price gain will be smaller there. Do not tune
  anchor/schedule on the sim.
- Next: hosted D01/D02 with v0 once the key exists; record timeouts/rounds per RFQ thread.

## 2026-10-10 13:35 - E0/v0 on hosted sandbox D01/D02 (MEASURED HOSTED)

- First attempt: 4 sessions timed out at 0 - launch error (processes killed after opening), not agent.
- naive: D01 0.200, D02 0.229. v0: D01 0.932 (deal 50.50, FCA, 60 d), D02 0.419 (J1 final_offer
  15.70, payment 30 d, accepted). Replays: naive D01 /replay/e496ba4e489d30ff, D02 /replay/265fc0a0a379b326.
- Next: read v0 D02 replay - why J1 went to final_offer early and whether C1 was the better path.

## 2026-10-10 13:41 - v0 on hosted practice P01 (MEASURED HOSTED, 1 session)

- v0: 0.567 (accepted final_offer 143.40 from 2027-04-01, 90 d). House agent 0.97.
- Replay findings: (1) suppliers send several alternative sheets per mail - v0 read only the
  first and missed EUR 136.80 from 2026-11-01; (2) v0 flipped effective_date mid-negotiation and
  the supplier priced it (+6.50); (3) supplier itself cites LCI-C +2.7 % x 30 % and PPI-C241
  +6.5 % x 24 % -> ~2.4 % justified vs 9.5 % asked: claims are the lever; (4) supplier prices
  payment terms (136.20 @30 d vs 138.40 @90 d).
- Fix v0.1: evaluate every sheet in the latest message by C; lock non-price terms after the
  first offer. Sim regression 85.8 unchanged. Next: index claims for price_increase cases.

## 2026-10-10 14:30 - Evidence: claim bank + supplier cost estimates (BUILD, local only, 0 sessions)

- `claims.build_bank(case, package)`: latest-12-month index windows per cost driver (+ indices the
  case cites), cherry-picked buyer windows (flagged, off by default), rival quotes (per receiving
  supplier, `reveals_rival`), scorecard OTD/ppm, letter notice vs. contract notice, should-cost
  (`internal`). Every claim passes `verify` against package + release + case facts.
- `pick` default: <= 3 claims, buyer-side only, no private disclosure, no ID reuse (`claim_keys`).
  P01 default pick: notice (doc:20260911-70110-P01 51 d vs ctr:4600070110), PPI-D351 -3.7 %,
  scorecard OTD 85.2 %. LCI-C +2.7 % and PPI-C241 +6.5 % stay internal (adverse).
- `cost_pressure_estimate`: P01 stated drivers -> 2.37 pp on 54 % coverage (listed drivers: 2.33 pp
  on 64 %); sentence has no IDs, `verified: False`.
- `dossiers.supplier_estimate`: P01 full cost 132.64 (+-5 %) vs current 126.53 -> margin -4.8 %
  at status quo; rate 0.15 (wants_fast_payment). Relationship term is live even at today's price.
- Sunday: `claims.prep(data_dir, out_path, release)` rebuilds dossiers + banks with the overlay.
- Not integrated into agent.py; claims experiment (vs. mechanical baseline) still to run.

## 2026-10-10 14:01 - compare decision v0.2 vs v0.1 (sim) (MEASURED LOCAL SIM)

- Baseline: `42c7659` @ 42c76599
- Candidate: `WORKTREE` @ c743d6b3 dirty diff a2459668c121
- Cases × repeats: case:S01, case:S02, case:S03 × 2 (`negotiator play <case>`), arm order interleaved, seed 0; arena http://127.0.0.1:8010; data 4d8c89674035, uv.lock a0ec7fe14679

| Case | Baseline runs | Base mean | Candidate runs | Cand mean | Δ |
|---|---|---:|---|---:|---:|
| case:S01 | 82.9 82.9 | 82.9 | 82.9 82.9 | 82.9 | +0.0 |
| case:S02 | 86.1 86.1 | 86.1 | 86.1 86.1 | 86.1 | +0.0 |
| case:S03 | 88.6 88.6 | 88.6 | 88.6 88.6 | 88.6 | +0.0 |
- Baseline: mean 85.8 over 6 scored runs, worst case case:S01 82.9, min run 82.9, failures 0, timeouts 0
- Candidate: mean 85.8 over 6 scored runs, worst case case:S01 82.9, min run 82.9, failures 0, timeouts 0
- Raw: `experiments/runs/compare/20261010-140143-sim-decision v0.2 vs v0.1 (sim)/summary.json`
- Decision: (fill in)

## 2026-10-10 14:02 - compare decision v0.2 vs v0.1 D02 sandbox (MEASURED HOSTED SANDBOX)

- Baseline: `42c7659` @ 42c76599
- Candidate: `WORKTREE` @ c95a73ba dirty diff 28f0578cb458
- Cases × repeats: case:D02 × 2 (`negotiator play <case>`), arm order interleaved, seed 0; arena https://arena.tacto.ai; data 4d8c89674035, uv.lock a0ec7fe14679

| Case | Baseline runs | Base mean | Candidate runs | Cand mean | Δ |
|---|---|---:|---|---:|---:|
| case:D02 | 41.9 41.9 | 41.9 | 41.9 41.9 | 41.9 | +0.0 |
- Baseline: mean 41.9 over 2 scored runs, worst case case:D02 41.9, min run 41.9, failures 0, timeouts 0
- Candidate: mean 41.9 over 2 scored runs, worst case case:D02 41.9, min run 41.9, failures 0, timeouts 0
- Raw: `experiments/runs/compare/20261010-140224-sandbox-decision v0.2 vs v0.1 D02 sandbox/summary.json`
- Decision: (fill in)

## 2026-10-10 14:05 - Runtime: async runner vs serial on D02 sandbox (MEASURED HOSTED SANDBOX)

- Hypothesis: one worker per thread + coordinator (`negotiator.runner`, `--runner async`) keeps
  RFQ threads free of timeouts with the same score as the serial loop.
- Config: commit c95a73b + uncommitted runtime (runner/client/state), PackageAgent-v0.2, closes via
  `evaluator.close_decision`; limiter 8 calls/s; 60 s move limit, close wait 20 s, cap margin
  max(90 s, slowest + 15 s). Quota: 0 practice (sandbox only).
- Run A (no send slot, 3 parallel sessions): async 0.419 ×3, thread timeouts 0/0 ×3; wall 59 s.
  Concurrent POSTs on one hosted session each took ~16-18 s (vs ~0.5 s alone), and one close hit
  `422 not a standing offer` (closer read the old offer while the chosen thread's reply was being
  stored) - reconciled and re-decided, deal kept. Fixed: in-flight flag cleared only after the
  reply is in the thread.
- Run B (soft per-session send slot, falls back to concurrent sends 25 s before a thread's
  deadline): async 0.419 ×3 + CLI `negotiator play case:D02 --runner async` 0.419, timeouts 0/0
  ×4, wall 25 s for 3 parallel sessions, no close errors.
- Serial control (`negotiator.play.play_case`, 3 parallel sessions): 0.419 ×3, timeouts 0/0 ×3,
  wall 6 s.
- Reading: D02 hosted replies are mostly fast, so serial does not time out on D02 either; the
  async benefit is only shown where a supplier reply takes 30-70 s (earlier hosted probe: C1 70 s;
  local tests with injected 30/50 s delays: async 0 timeouts, serial waiting costs a 409 late).
  Hosted seems to serialise/penalise concurrent calls on one session -> keep the send slot.
- Raw: `runs/20261010-140107-D02-runner-compare/`, `runs/20261010-140327-D02-runner-compare/`,
  `runs/20261010-140410/`.
- Decision: keep serial default; async passes D02 gate (0 timeouts, same score) and runtime tests.
  Promote after an RFQ with slow replies (practice, budgeted) shows no regression.

## 2026-10-10 14:10 - Runtime: async runner with agent.propose (hold) vs serial, D02 (MEASURED HOSTED SANDBOX)

- Config: 89a4389 + runner hold support (`agent.propose` -> send / close / hold), PackageAgent-v0.2
  with propose, closes via `evaluator.close_decision`; per-session send slot on. Quota: 0 practice.
- Batch 1 (3 parallel async sessions, then 3 parallel serial; hosted replies slow, 13-24 s):
  async 0.116 / 0.461 / 0.116, serial 0.461 ×3. Thread timeouts 0/0 in all 6.
  The two 0.116 runs: identical buyer moves to the serial runs; J1 answered our counter to its
  final offer (same price, our terms) with `walked_away`, so the coordinator accepted C1's final
  17.20. In the third async run J1 kept its final and we got 15.50 (0.461). All three async runs
  sent that counter ~15 s after J1's final (send slot waiting on C1's slow reply); walk vs keep
  differed with the same gap, so this looks like supplier randomness on countering a final offer,
  not a clock effect. Not proven.
- Batch 2 (3 parallel async, hosted fast, 8 s wall): 0.461 ×3, timeouts 0/0 ×3.
- Totals for async on D02 today: 10 runs, 0 thread timeouts; serial 6 runs, 0 timeouts.
- Raw: `runs/20261010-140547-D02-runner-compare/`, `runs/20261010-140838-D02-runner-compare/`.
- Decision: runtime gate "no timeouts on repeated D02" met for async. Keep serial default until
  Decision reviews the counter-to-final walk risk (2/9 async v0.2 runs) and an RFQ with slow
  replies is compared.

## 2026-10-10 14:10 - compare D02 v0.2 final-risk rule: meso off vs on (MEASURED HOSTED SANDBOX)

- Baseline: `WORKTREE` @ a794b3ea dirty diff 8b26a25950df
- Candidate: `WORKTREE` @ a794b3ea dirty diff 8b26a25950df, env {'NEGOTIATOR_MESO': '1'}
- Cases × repeats: case:D02 × 2 (`negotiator play <case>`), arm order interleaved, seed 0; arena https://arena.tacto.ai; data 4d8c89674035, uv.lock a0ec7fe14679

| Case | Baseline runs | Base mean | Candidate runs | Cand mean | Δ |
|---|---|---:|---|---:|---:|
| case:D02 | 46.1 46.1 | 46.1 | 42.8 42.8 | 42.8 | -3.3 |
- Baseline: mean 46.1 over 2 scored runs, worst case case:D02 46.1, min run 46.1, failures 0, timeouts 0
- Candidate: mean 42.8 over 2 scored runs, worst case case:D02 42.8, min run 42.8, failures 0, timeouts 0
- Raw: `experiments/runs/compare/20261010-141019-sandbox-D02 v0.2 final-risk rule: meso off vs on/summary.json`
- Decision: (fill in)

## 2026-10-10 14:20 - compare claims-only-p01 (MEASURED HOSTED PRACTICE)

- Baseline: `WORKTREE` @ 4dfc2935 dirty diff 67cd032f463f, env {'NEGOTIATOR_CLAIMS': '0', 'NEGOTIATOR_ESTIMATES': '0', 'NEGOTIATOR_MESO': '0'}
- Candidate: `WORKTREE` @ 4dfc2935 dirty diff 67cd032f463f, env {'NEGOTIATOR_CLAIMS': '1', 'NEGOTIATOR_ESTIMATES': '0', 'NEGOTIATOR_MESO': '0'}
- Cases × repeats: case:P01 × 2 (`negotiator play <case>`), arm order interleaved, seed 0; arena https://arena.tacto.ai; data 4d8c89674035, uv.lock a0ec7fe14679

| Case | Baseline runs | Base mean | Candidate runs | Cand mean | Δ |
|---|---|---:|---|---:|---:|
| case:P01 | 80.0 80.0 | 80.0 | 92.8 92.8 | 92.8 | +12.8 |
- Baseline: mean 80.0 over 2 scored runs, worst case case:P01 80.0, min run 80.0, failures 0, timeouts 0
- Candidate: mean 92.8 over 2 scored runs, worst case case:P01 92.8, min run 92.8, failures 0, timeouts 0
- Practice quota before/after: {'before': {'used': 5, 'left': 195, 'limit': 200, 'resets_at': '2026-10-11T11:39:03.056071+00:00'}, 'after': {'used': 9, 'left': 191, 'limit': 200, 'resets_at': '2026-10-11T11:39:03.056071+00:00'}}
- Raw: `experiments/runs/compare/20261010-142041-practice-claims-only-p01/summary.json`
- Decision: (fill in)

## Handoff reconciliation and claims experiment — 10 October 2026, 14:24 Berlin

- The three pre-handoff mechanical P01 baseline runs at `8225d16` all scored 80.03/100:
  `63390aa61e6e2687`, `1ac8f6e23bbc8383`, `4499d35e0c2ed088`. Claims/estimates/MESO off,
  serial runner; accepted EUR 137.30, 30 days, effective 2027-04-01. These results existed
  before this continuation and were reconciled from local traces and the authenticated API.
- The estimates-on session `be346505d3153626` ended at zero by timeout. Its last local action
  tried to accept `offer:70110-1-a`. The later standing-offer fix is essential; this failed run
  is not evidence that supplier cost estimates are economically inferior.
- Correction to the early advice: alternative sheets can be evaluated as counteroffer packages,
  but the hosted API accepts only the current standing offer ID. Do not directly accept an
  alternative ID; send its complete terms and obtain a standing offer first.
- New integration at `4dfc293`: optional `NEGOTIATOR_CLAIMS=1` adds verified evidence only to
  single-supplier price-increase offers. Terms, anchor, concession policy and closing evaluator
  remain unchanged. No model calls, cherry-picked windows, private should-cost disclosure,
  rival-quote disclosure or weighted "fair price" assertion. Claim IDs reconstructed on resume
  and reserved on proposal; maximum three checked claims, which may use more than three IDs.
- Controlled P01 comparison: same code/data/serial runner, estimates and MESO off. Baseline
  `be5861930b4426bf`, `b892b7b404698403`: 80.03/100 each. Claims candidate
  `851c4c42585b8575`, `d8cad506359ee966`: 92.79/100 each, an observed +12.76 score points.
  Candidate accepted EUR 136.20, 90 days, effective 2027-04-01. Each candidate response
  verified all three claims (notice, electricity index, OTD); no contradictions or duplicates.
- Evidence saved under `runs/compare/20261010-142041-practice-claims-only-p01/`. Both arms
  recorded the same source/config snapshot and facts hash; only the claims flag changed.
  Later repeats completed much faster with identical outcomes, so do not treat repeats as
  proof of independent supplier randomness or a statistically established effect.
- Decision: promising on P01; keep the global default off pending broader evidence. Use the
  explicit claims flag for price-increase experiments. Practice quota 195 -> 191 (four sessions).
- Runtime review found a separate persistence bug: a torn final journal line was ignored on
  load but not removed before append, which could hide all later records after another restart.
  `11d74e1` preserves the damaged tail and repairs the boundary; mid-file corruption fails closed.

- P01 cost diagnostic: claims candidate C=EUR 1,100,921.13 versus baseline EUR 1,108,192.02
  (EUR 7,270.89 lower). Candidate relationship penalty is EUR 13,608.40 versus baseline
  EUR 1,222.38: improved terms still lower total C, but payment/supplier-health tradeoffs matter.
  Remaining aggregate gap to reported C_best is EUR 4,105.35; this is not a component-level
  optimal-cost decomposition. Calibrate supplier estimates before enabling them globally.

## Hosted restart rehearsal and local regression — 10 October 2026, 14:23 Berlin

- At `11d74e1`, `tools/resume_probe.py` interrupted its D02 child after a persisted send intent,
  restarted with the same journal, and completed session `cee30b71402e03c8`: 46.09/100,
  must-haves passed, zero server-reported timeouts, one open intent/one session, no pending
  journal requests. Raw: `runs/20261010T122302Z-resume-D02-d32f32/`.
- This is one hosted recovery observation, not proof of all disconnect/queue scenarios or
  permission to restart during the final. Practice quota unchanged at 191.
- Integrated local regression against `3c69dec`: S01 82.90, S02 86.09, S03 88.56 in both arms;
  mean 85.85/100. Raw: `runs/compare/20261010-142304-sim-integrated-regression/`.


## Hosted mini-sweep and closing consistency — 10 October 2026

- Frozen runtime source `11d74e1`, claims/estimates/MESO explicitly off; five planned practice
  sessions, quota 191 -> 186. Changes during the sweep were documentation/tests only.
- P03 serial `c0d525e3d5026b65`: 89.98/100, 147.5 seconds, zero server timeouts.
- P05 serial `7b86fd5e5d9a7794`: 36.04/100, 212.2 seconds, TWO server timeouts
  (one each on sup:70210 and sup:70250).
- P05 async `499d117f5572cc78`: 36.04/100, 58.0 seconds, zero server timeouts.
- P07 serial `d1b5e17f1072c6e1`: 74.30/100, 57.0 seconds, zero server timeouts.
- P10 serial `2323becf5b0aeba2`: 45.32/100, 50.0 seconds, zero server timeouts.
- All five returned a deal with must-haves satisfied. Actual timeout counts were fetched from
  authenticated session/thread APIs afterward: the comparison summary's default zero is not
  sufficient evidence of absence. Saved `runs/mini-sweep-20261010-142332/server-evidence.json`.
- P05 observed async avoided idle-thread timeouts; same deal/score. One pair cannot establish
  a latency distribution, especially with possible hosted caching. Promote further RFQ tests
  to async; full multi-case/wave rehearsal remains required before the final.
- Next priority: inspect P05 and P10 replay/economics, then budget a controlled policy comparison;
  expand claims tests across other price-increase cases. P01 success is not broad competitiveness.
- Fixed after the frozen sweep: async coordinator now uses the agent's case estimates when no
  explicit runner override is supplied. Removed obsolete fallback closing policy that could
  accept an alternative-sheet ID and omit relationship economics. Regression covers inherited
  estimates and explicit overrides including empty dict. Estimates remain opt-in: relationship
  penalties can make total cost non-monotonic in price, so inverse-price assumptions need review.


## Remaining hosted coverage and improvement plan — 10 October 2026, 14:40 Berlin

- User requested all untested cases, then planning with P04/Boo as a concrete target.
  Source frozen at `1a18dc0`; no agent source changes. Async, claims/estimates/MESO off,
  up to three concurrent cases, shared six-call/second limiter. Five-session budget.
- P02 `1c87a28d5390f289`: 29.34/100, 53.3s.
- P04 `ae20ddcf43f86237`: 5.64/100, 47.5s.
- P08 `7b1457795e1fbbbd`: 15.62/100, 72.3s.
- P11 `d5371cf52ee9b718`: 31.44/100, 130.8s.
- P18 `ca5c5a2ee6331b7f`: 38.61/100, 72.8s.
- All five returned valid deals satisfying must-haves, zero server-reported thread timeouts.
  Quota 186 -> 181. All ten hosted cases now covered. Nine `hosted:false` cases not opened.
- Recorded configuration facts hash `7dc162f977c0`; SQLite hash is separately stored in
  `experiments/coverage-20261010.json` (comparison harness uses SQLite for its data hash).
  Local complete replays: `experiments/runs/coverage-20261010/`.
- Human-only public board snapshot at 14:40: Boo leads P04 (81.0), P05 (38.1), P08 (22.7),
  P11 (40.6). P18 now held by y/agent (38.6), equal to house at displayed precision.
  Board data is never passed to runtime agents. These are moving benchmarks.
- Offline claim-bank coverage: four price-increase cases build; fifteen other cases throw
  `TypeError` because notice generation calls `float(None)` on missing document days.
  Repair required before enabling evidence on other types; no claim repair implemented yet.
- P04 replay: repeatedly asks for a lower price on the same 12-month package despite dossier
  signal that supplier discounts multi-year agreements. At recorded fixed terms,
  EUR 4.94 / 90 days / 24 months calculates 86.04; this is a target, not an obtained offer.
- P10 previous replay: final-counter risk uses infinite loss without an external quote,
  suppressing a cheaper supplier-proposed package. Official finite fallback semantics must
  be validated before changing this logic. P11's request for faster payment conflicts with
  its negotiable schema; do not follow it.
- Decision: enter planning phase. `docs/12-measured-improvement-plan.md` specifies P04 first,
  followed by package exploration and targeted fixes, with 24 proposed development sessions
  plus 10 regression sessions and a protected 46-session reserve. No additional quota spent.

## Staged package experiment implementation — 10 October 2026

- Implemented optional versioned policy configs, complete-cost package enumeration at opening
  and proposed prices, bounded stagnation trades and history-based reconstruction. Defaults
  preserve the baseline; supplier estimates and generic payment MESOs remain disabled.
- Claims now tolerate missing/non-numeric notice fields; nineteen public case banks verified.
  Quality prioritizes historical ppm; renewal prioritizes performance and index evidence.
- Added no-alternative final-counter opening-improvement proxy behind configuration, limited
  to a cheaper supplier-proposed package. It is not expected normalized score.
- Reports distinguish unknown timeouts; incomplete CLI runs exit nonzero. Run traces include
  resolved policy hash, source revision, actual base and release file hashes and decisions.
- Local validation: 101 tests pass. Added a sequential manifest runner with a 46-session
  reserve and stop gates; first release is four P04/P11 screening sessions only.
- FAQ supplied by user confirms normalized wave means rank, ties use deals then rounds,
  no deal scores the alternative (zero without one), and every case has a fixed Cbest.
  Cooperative wording and verified evidence are supported by the FAQ example, not proof
  that our candidate improves. Jury prize weighting remains unspecified.

### Screening preflight follow-ups (outside frozen candidate source)

- Batch A is frozen at `120558215629388579130703778ad60e6ac5dd84` in isolated checkouts.
  Current working-tree follow-ups do not alter its runtime policy or source mid-batch.
- Fixed the batch reporter to count the hosted API's timeout event lists (including empty
  lists) instead of marking them unknown; added stop-gate tests for contradicted claims and
  unresolved requests. Original results also contain explicit per-thread timeout counts.
- Hardened generic multi-year trades to preserve the quoted annual volume when volume is
  negotiable, and wording to describe the actual volume when it is a negotiated field.
  This does not affect P04, whose annual volume is fixed, or P11, which has no contract field.
- Added malformed-notice preservation coverage and the current staged contract in document 13.

## Batch A — four screening sessions, source 1205582

- P04 package-only: `e2fcc134ecd03d17`, **86.04/100**, EUR 4.94 / 90 days / 24 months.
- P04 package + evidence: `b71d601095c82d96`, **86.04/100**, identical closing package;
  its 85.0% delivery claim was verified. Select simpler package-only.
- P11 package-only: `cc9acf4242059a59`, **31.44/100**, unchanged from historical baseline.
- P11 package + evidence: `88f8a5d21a61c30f`, **39.80/100**. Select evidence for confirmation.
- All four: valid deals, must-haves satisfied, zero authenticated thread timeout events,
  no contradicted claims, no unresolved journal requests, successful exit status.
- Cycle spent four. Shared quota 179 -> 165: ten additional sessions were consumed outside
  this batch. Our ledger uses explicit session IDs, not the shared quota delta.
- Human benchmark refresh: P04 best displayed 86.0, P11 best 62.6 (makeAnother.md).
  These are rounded moving targets; P11 remains below the current competitor.
- Released Batch B: fresh baseline 1551125 and frozen winning screening candidate 1205582
  per case. P04 baseline then candidate; P11 candidate then baseline. Four sessions.
- Local diagnosis: P11 suppliers price chargeback risk and propose cheaper alternatives.
  The experimental stagnation order tightened ppm before reducing chargeback; a local fix
  now tries adjacent lower chargeback first and only relaxes ppm upward. Batch B retains
  original source to test reproducibility. The fix is reserved for later gated refinement.
- Tracked compact evidence: `experiments/staged-cycle-20261010.json`. Full ignored local
  traces/journals/authenticated thread data: `experiments/runs/staged-a-20261010/`.

## Batch B — confirmation

- P04 baseline `6a95b5d68d53a5d0`: 5.64; package candidate `2d99044cccd0f46b`: 86.04.
- P11 evidence candidate `321b3475cf3cf054`: 39.80; baseline `a08f5e8f1f64df2e`: 31.44.
- Zero timeouts, invalid deals, contradicted claims or unresolved requests. Four sessions;
  quota 165 -> 161, cycle total eight. Exact repeated results may be cached/deterministic;
  they establish reproducibility, not statistical significance.
- Release four P11 refinement sessions: two per permitted lower-chargeback variant, with
  quality evidence enabled, ppm 300, payment fixed. Config rank selects one or two permitted
  steps below the highest chargeback, not a case ID or a leaderboard-derived price.
- Skip P04 optional refinements: candidate matches the refreshed displayed leading score.
- Refinement source also fixes stagnation to consider adjacent lower chargeback before ppm,
  with ppm switches only upward within the must-have. Initial concession schedule unchanged.

### P10 offline gate and replay artifact

- Reproduced P10's recorded opening: 19,890 units/year versus must-have >=22,230.
  The experimental opening-relative proxy has no compliant opening input, so it safely retains
  the standing offer. Added an actual-case regression and an explicit unavailable-input log.
  Skip P10's four hosted comparison allocations unless that prerequisite becomes available.
  Do not inject historical Copen/Cbest or reinterpret finite fallback cost as no-deal score.
- Generated a shareable measured P04 HTML replay with actual terms, verified delivery evidence
  and complete costs. Package-only tied this evidence arm; the claim's incremental effect is zero
  in this screen. `experiments/replays/p04-package-evidence.html`.
- Local suite: 109 passed; ruff clean. Sunday release and final host rehearsal remain separate.

## P11 refinement — source 37fe085

- Lower chargeback rank 1: `2a2e85e2f0372c98` and `49fc8d01470de13a`, both **63.38**.
- Lower chargeback rank 2: `c6869765602972cc` and `f4b2804c5cfda349`, both **70.99**.
- All four satisfy must-haves, zero thread timeouts, no contradicted claims or unresolved
  requests. Historical 2,376 ppm and electricity change claims were verified. Payment stayed
  at the fixed 60 days. Source/terms/costs retained in each authenticated replay.
- Select rank 2. This exceeds the last observed public leader's 62.6, subject to refresh.
  Repeated results are reproducibility observations, not significance tests.
- Quota 161 ->157; cycle total 12. Released 12 broader comparisons: P08 packages, P02 claims
  only, P05 supplier-standard faster payment, each versus baseline twice. P10 skipped at
  the missing-input gate. P04 optional refinements skipped; maximum planned cycle now 44
  if all remaining gates pass, below the 52 ceiling.

### Combined-policy and regression runner preparation

- Added per-case-type package preferences so a combined quality chargeback policy does not
  replace an independently measured RFQ payment policy. No case IDs or target prices enter
  policy configuration. Local test verifies renewal, quality and RFQ preference separation.
- The subset runner loads the selected source checkout, shares one AsyncArena across all cases,
  and fails when requested results are missing. Final comparison can run five baseline cases,
  all ten candidate cases concurrently, then the other five baseline cases. This alternates
  baseline/candidate order by case while exercising candidate concurrency with one limiter.
- Local suite: 111 tests passed, ruff clean. Final comparison has not started or spent quota.

### P02 clause/payment investigation after unchanged claims scores

At the observed EUR 373.65 / 90-day package, local complete cost is EUR 2,268,972.94.
A copper clause at the same price raises cost; equal-cost prices are approximately EUR
367.00 (zero deadband), 369.19 (3% deadband), and 370.66 (5% deadband). Paying in 30 days
requires about EUR 368.70 to be cost-neutral. These figures are human diagnostic calculations
from published terms and rates, never runtime targets. No hosted clause benefit established;
keep that unmeasured policy out of the combined candidate.

## Broader development — twelve sessions, source 807aebb vs 1551125

- P08: baseline **15.62**, candidate **59.30**, both repeated. Enable raw-material package policy.
- P02: baseline and claims candidate **29.34**, repeated. No incremental claim benefit here.
  Price-increase evidence remains a combined candidate hypothesis because prior controlled P01
  runs improved to 92.79 and P02 did not regress; final regression must verify both.
- P05: baseline and supplier-standard payment candidate **36.04**, repeated. Omit the extra
  RFQ package policy from the combined candidate. Rival claims remain disabled.
- All twelve: valid deals, zero actual timeouts, no contradicted claims or unresolved requests.
- Shared quota 157 ->140 (five additional external sessions); cycle total 24.
- Freeze `configs/candidate.json`: packages for renewal/quality/raw-material; evidence for
  price-increase/quality; quality starts two permitted chargeback steps down. Risk remains legacy.
  No runtime leaderboard, historical Cbest or case-specific target prices.
- Before promotion: free D01/D02 crash/recovery rehearsal, then the budgeted twenty-session
  paired ten-case regression. Stop on safety failures. Maximum cycle remains 52; planned use44.

## Free recovery rehearsal and quota checkpoint

- Frozen candidate source `ec56b38`, `configs/candidate.json`, D01 and D02 concurrently,
  one shared client/limiter. Injected SIGKILL after the first journalled send, then restarted
  the same journal. Exactly two sessions across restart; both completed valid deals.
- D01 `ca71bef0a414bc54`, score 91.92; D02 `e415cfd2dafb22ae`, score 46.09.
  Zero actual timeouts, no contradicted claims or unresolved requests. This is runtime
  recovery evidence, not a practice persuasion benchmark or full wave-cap rehearsal.
- Practice quota unchanged: **140 before and after**. Cycle practice total remains **24**.
- User asked about progress and conserving requests. No further practice starts while the
  choice is pending. The final **20-session** paired comparison has NOT started.
- Prepared `experiments/final-comparison-manifest.json`: five baseline cases, all ten candidate
  cases concurrently, then the other five baseline cases. It alternates arm order by case.
  Running it would bring this cycle to 44/52 sessions; always recheck shared quota/reserve.
- Combined candidate is NOT promoted. Ten-case mean and regression thresholds remain untested.
  Sunday release validation and final-machine/wave readiness remain outstanding.

- User subsequently chose **stop after the free check and preserve quota**. No more practice
  sessions started. Final comparison is explicitly deferred until the user asks to resume.

## 2026-10-10 — MEASURED LOCAL: immutable full-project experiment loop rehearsal

Hypothesis: normal anchored rounds improve kit simulator S01/S02 score over a deliberately
weak one-round, zero-anchor control. This tests loop integration with scripted toy suppliers;
it is not hosted performance evidence or a proposed production strategy change.

- Source: current public project bytes and exact uv.lock captured into a temporary isolated Git
  repository; baseline checkpoint `c1585d66a11d4b228eb24a2f87ea5f8a`, candidate
  `24a77b1e71f74e3c9f957c0e712374e3`. Both were published only to a temporary local bare remote.
- Config: baseline anchor=0, rounds=1; candidate anchor=0.12, rounds=5. Both final_hold_s=0,
  claims=false, meso=false, estimates={}; serial runner, no dossier inputs.
- Cases/quota: actual bundled arena_kit.sim S01/S02; three repeats per case per arm,
  all 12 planned sessions completed through real CLI and restored-source worker subprocesses.
  Two separate worktrees each used `uv sync --locked --offline` and independent environments.
  No hosted sessions, hosted quota, actual origin pushes or actual dashboard DB writes.
- Scores (0–100): S01 14.5102 → 82.9021; S02 14.5243 → 86.0854. Overall gain 69.9764;
  zero within-case spread, all three repetition blocks won; baseline/candidate timeouts 0/0.
- Decision: temporary lab policy verdict **promoted**; all gates passed, no evidence gaps.
  Deterministic scripted responses explain zero spread; this establishes local execution fidelity,
  not generalized negotiation readiness. Real CLI evidence references and immutable finding saved.
- Recovery/invariants: real CLI restore fetched candidate from temporary remote on second clone,
  verified every tracked byte/lock hash, and preserved active untracked work. Separate synthetic
  policy SQLite verified rejection, simultaneous same-generation completion (exactly one promotion,
  one baseline_superseded), idempotent completion and recommendation rollback generation 2→3.
- Failures: harness-only fixes for literal fixture credential secret-scan rejection, incorrect
  artifact worktree path and CLI response envelope in fixture suite. No production defect found.
- Validation: Python 232 passed, 19 existing research-data skips; Ruff passed; Node helper/DOM
  checks passed. DOM smoke now requires explicit LAB_UI_DOM_MODULE and reports skip when absent.
- Artifacts: `/tmp/tacto-loop-rehearsal-itmo0e21/summary.json`, `cli-results.json`, `lab.sqlite`,
  `loop/measured/` immutable worktrees/request journals/final outcomes, second-clone and restored.
  Reproduce with `uv run --locked --offline python tools/rehearse_loop.py`; retained-artifact checks
  use `--verify-existing /tmp/tacto-loop-rehearsal-itmo0e21`. Original local cache and loopback socket
  permission are required; fetching remains offline. Detailed task-5-report.md/checks.log in SDD.

- Final independent review follow-up: host promotion now requires original ended-session evidence;
  CLI restore request-ID retries remain idempotent; precreated family budgets and practice protections
  survive smaller campaign ceilings. Five regression cases reproduced before fixes. Final full suite:
  237 passed, 19 existing data skips; Ruff clean; retained simulator evidence reverified without new
  sessions. Direct UI checks: 19 tests plus one actual-page DOM smoke passed.
- Live dashboard restarted with saved credentials and existing database. Secure-cookie login, bearer
  reads, new loop overview, retained original experiment and public tunnel loop.js asset verified.
  Initial shared recommendation remains explicitly unseeded; no real checkpoint publication or hosted
  campaign was launched. Browser crash prevents visual layout QA.

## 2026-10-10 — Lab setup: nested-project checkpoint verification

- Hypothesis: checkpoint publication and restoration must verify the entire repository when the
  negotiator lives below its root and the arena kit is a sibling submodule.
- Change: inspect Git trees with `--full-tree`; retain root-relative submodule and private-file checks.
  Negotiation policy/configuration is unchanged. The coding-agent workflow is in `LAB_PLAYBOOK.md`.
- Failure: initial real-repository restore rejected the valid sibling kit as a submodule manifest
  mismatch. A nested-project, sibling-submodule, second-clone regression reproduced it before the fix.
- Validation: all 27 checkpoint tests passed after the fix, including publication and isolated restore
  from a second clone. No arena cases, hosted sessions or quota consumed; no performance score claimed.
- Decision: use the corrected source for the initial shared baseline; seeding identifies a starting
  checkpoint and does not imply measured promotion or improved negotiation performance.

## 2026-10-10 — MEASURED SANDBOX: Baris Test

- Scope/hypothesis: user-authorized single D01 smoke test of the shared recommended baseline;
  no candidate change or comparative performance claim. Budget: one sandbox session, no practice run.
- Run: `95dca638-82b5-4f07-b88c-1bb15c3813ce`; arena session `0f0ad2bb6dd309b5`.
- Checkpoint: `e1d931e4fcce49fb8fd341c40052953a`; clean verified source
  `f325fcb12c09ef2590cd9496a90dddd73e714648`, locked dependencies, serial package agent.
- Config: anchor=0.12, rounds=5, close_gap=0.005, final_hold_s=40, p_walk=0.25,
  meso=false, claims=false, estimates={}. Original manifest retains lock/data hashes.
- Result: ended deal, 91.9231/100, must-haves satisfied, zero reported timeouts,
  seven recorded moves, approximately five seconds negotiation time.
- Setup issue: the first preflight rejected the restore metadata as untracked; no session opened.
  Temporarily moved only that metadata into ignored storage, then restored it after execution.
- Decision: retain the recommendation; this single sandbox observation is not evidence of an
  improvement. Tracked result and original supplier messages are saved in the lab.


## 2026-10-10 — Lab browsing: score history, pagination and ordering

- Hypothesis: chronological supplier/case evidence and consistent list ordering make prior
  results easier to inspect; this is a lab UX change, not a negotiator strategy experiment.
- Change: authenticated compact history projection, selected-supplier charts and filters,
  session deduplication, explicit recovered/missing outcomes, and sortable paginated experiments.
- Configuration/cases/quota: existing recorded/imported results only; no new arena sessions.
- Verification: regression coverage for numeric sorting across pages, filter/page refresh behavior,
  zero versus missing scores, supplier attribution, campaign/import duplicates and recovery shapes;
  actual DOM checks cover navigation, chart drill-down, escaping and late response cleanup.
- Review fixes: normalized recovered campaign scores and ordered same-time repetitions numerically.
  No performance gain claimed and no change to the shared recommended checkpoint.

## Shared Evidence context — local contract validation, 10 October 2026

- Hypothesis: a shared, inspectable context can preserve existing price-increase claim selection
  and message economics while linking selected claims to scoped sources and input versions.
- Source: working branch `feat/evidence-context`; pinned kit
  `1b5516bb95ef28e37f69aa446dc62168864bca53`; no activation/config changes.
- Inputs: local `negotiation-arena-kit/data`, manifest v1.0.0, declared snapshot 2026-09-30;
  saved P01 practice metadata. Export command and responsibilities: docs/16-evidence-context.md.
- P01: existing bank/pick preserved; initial notice 51/90 days, PPI-D351 -3.7%, OTD 85.2%.
  LCI-C +2.7%, PPI-C241 +6.5% and 712 ppm remain existing candidates. Private estimates stay
  internal. Context gaps expose unknown index units and existing signal-overlay limitations.
- Local checks cover term preservation, private exclusion, failed checks, missing-data fallback,
  source/version export, reservations, resumed buyer refs and PackageAgent integration.
- Hosted sessions/quota consumed: **0**. Scores and persuasion effects: **not measured**.
  No runtime or negotiation-readiness claim; existing verifier/loader limits remain documented.
- Decision: hand off the shared interface and proposed hosted checklist for team review.
  The paused practice comparison stays paused; hosted work requires a separate instruction.
- Validation: `uv run --locked pytest -q` with explicit `ARENA_DATA`: **120 passed**;
  `uv run --locked ruff check .`: **passed**. Local asyncio suite ran outside the restricted
  execution sandbox after sandboxed runner tests stalled; no hosted transport was used.

## Claim verification and relevance — local follow-up, 10 October 2026

- Hypothesis: reject unsupported/semantically inconsistent evidence and prioritize indices named
  in the supplier explanation while preserving message economics and disclosure/usage rules.
- Source/config: working branch `feat/evidence-context`, same pinned kit and local data manifest
  as the shared-context batch; no policy activation changes. No hosted sessions or quota used.
- Added canonical claim rendering and verification of sentence/figure agreement, units,
  finite numbers, index direction/window/source compatibility, price bases/currency, disclosure,
  supplier-wide scorecards and requested-date OTD. Notices require supplier/part/date applicability
  and genuinely short notice; ambiguous/missing applicability is excluded. Notice preparation
  now works without a scorecard.
- Relevance: latest supplier message's known series IDs, then trigger/case citations, then listed
  part drivers. Supplier text cannot change claim eligibility/disclosure. Selection traces expose
  reasons and remaining slots; existing message refs conservatively consume the three-claim budget.
- Audit: compared banks and selected kinds/IDs/figures with a saved pre-change local snapshot for
  all 19 practice fixtures. P02's 109-day and P17's 104-day notice claims (90-day requirements)
  are removed; they were previously unselected. P02's requested effective date is also outside the
  recorded contract interval. Initial selections, including relevance ranking, stay unchanged for
  all 19 fixtures. P01 stays 51/90 days, -3.7% PPI-D351, 85.2% OTD; scorecard wording is explicit.
- Validation: **162 passed** with `uv run --locked pytest -q` and explicit `ARENA_DATA`;
  `uv run --locked ruff check .` passed. Local P01 export was regenerated successfully.
  Tests include false notice comparisons, wrong/expired/ambiguous scope, no-scorecard notices,
  sentence tampering, units/direction, privacy, relevance, final message budget and resumed usage.
- Decision: ready for local/team review; hosted persuasion and scores remain **unmeasured**.
  Prices, term sheets, closing decisions, rival disclosure and cost-pressure integration remain
  outside this batch. The existing paused hosted comparison remains paused.

## 2026-10-10 — Lab hosting: Azure VM deployment path

- Hypothesis: one always-on Azure VM with SQLite on its managed disk removes the developer-tunnel
  timeout and latency problems while preserving the existing laptop workflow.
- Change: environment-backed server defaults, a versioned service startup file, and an operator
  runbook for HTTPS, secrets, locked deployment, database migration, verification and rollback.
- Configuration/cases/quota: infrastructure only; no negotiator configuration or recommendation
  changed, no Arena case opened, and no sandbox or practice quota consumed.
- Decision: do not use App Service's network-mounted filesystem because Microsoft documents that it
  cannot support SQLite exclusive locks. Deploy one offer-eligible Linux VM and keep SQLite on its
  managed disk. Cut over only after history, loop state, authentication and upload verification.

## Inference/Lab setup — prepared only, 10 October 2026

- Hypothesis for a future probe: the Tacto endpoint can return an allowed closing-style ID
  without changing deterministic prices, terms, evidence or closing decisions.
- Added opt-in `negotiator.inference:InferenceProbeAgent` for standalone serial `lab run`;
  generic optional agent metrics are sanitized into saved/uploaded attempt results.
- Credential placement: ignored local `.env`, separate LLM/Arena/Lab keys. Lab URL comes
  from LAB_PLAYBOOK.md. Tacto URL, model ID and protocol confirmation remain outstanding.
- Proposed case: D01, one session, only after separate authorization. No budget granted here.
- Tests and lint: prepared but **not run**, per the user's instruction. Endpoint/Lab access
  was not checked; no services started, no uploads, no inference calls and no Arena sessions.
- Decision: unvalidated setup for review; no performance or connection-success claim.

### Azure deployment verification

- Host: Azure for Students VM `ehl-experiment-lab-vm`, France Central, Ubuntu 22.04,
  Standard B2ats_v2; static hostname
  `ehl-experiment-lab-vm.francecentral.cloudapp.azure.com`.
- Runtime: lab binds only to VM loopback on port 8000; Caddy 2.11.7 terminates HTTPS on 443 and
  redirects port 80. Both systemd services are enabled and active. SSH is restricted to the
  deployment IP; port 8000 is not exposed.
- Migration: SQLite backup API copy passed integrity checking with 110 runs and eight loop records.
  Public login returned a Secure cookie; `Baris Test` retained its completed 0.919230949 score;
  one recommendation, finding and campaign remained visible. Laptop sync uploaded two saved
  snapshots with zero failures and opened no Arena sessions.
- Setup failure: Ubuntu's enabled repositories lacked Caddy, and Caddy's signed package mirror
  returned HTTP 402 from the VM. The final installation uses Caddy's official static Linux binary
  and a dedicated unprivileged systemd account.
- Quota/decision: no Arena case, sandbox session or practice session was opened. The Azure URL is
  now the lab endpoint for this laptop; teammates can cut over with the existing upload token.


## 2026-10-10 — Port the measured P10 delivery tie-break onto current main

Hypothesis: when multiple legal opening packages have exactly the same complete buyer
cost, offering more delivery flexibility can improve the supplier's price. This port
contains only the opt-in delivery tie-break originally introduced in `de3e49a`.
`configs/cost-neutral-delivery.json` is the existing `configs/candidate.json` plus
`cost_neutral_lead_time: true`; no other strategy is introduced or activated by the port.
The default remains off. P10 is outside the configured package-policy types, so its
opening uses the shared optimizer and selects 42 days instead of 35 at equal cost.

Previously completed, fully reviewed hosted evidence (no new session consumed here):
- Controls `79c3a047f6c4a906`, `2323becf5b0aeba2`: score 0.4531834162,
  EUR 35.10, 35-day delivery, 23,400 units/year, 24 months; cost EUR 1,658,966.40.
- Run `a3a18b67-3ba8-43a0-a6b4-3baba11672dd`, session `77190d3ecf714944`, source
  `de3e49a`; run `0ac38ae5-de1d-4a53-93f5-fa7428577f36`, session `81c99adf8b88f7be`,
  source `fd423a6`: both score 0.5546564482, EUR 33.80, 42-day delivery,
  23,400 units/year, 24 months; cost EUR 1,597,720.80. Both valid, must-haves kept,
  zero timeouts. Estimates and MESOs were off; LLM advice was off.
- Each candidate saved EUR 61,245.60 against the recorded controls. The two supplier
  replies were identical, so this is repeated hosted evidence, not independent
  stochastic confirmation or a newly measured ten-case fixed-policy mean.

Decision: retain this isolated measured improvement behind its explicit policy flag.
Do not infer that current main plus its newer runtime wording reproduces these scores:
this port is verified locally, not a new hosted comparison. LLM package selection,
relationship experiments, RFQ changes, longer commitments and runtime recovery changes
are excluded. No lab recommendation is promoted by this port.

Local validation: delivery-cost equality, must-haves, costly-lead rejection, default
35-day opening, configured 42-day opening, control fixtures and boolean configuration
validation. All seven new tests pass; full suite: 342 passed, one existing failure in
`test_worker_preflight_rejects_unloadable_claim_data_before_open` (an empty explicit
package path falls back to locally available data). The same failure reproduces with
unchanged main production modules; no unrelated fix is included. `ruff check .` passes.

## 2026-10-10 — Retain the measured capacity package-adviser improvement

Hypothesis: use the model to interpret a supplier's delivery constraint and choose among
complete, legal packages whose prices are calculated by code to preserve the scheduled
buyer-cost ceiling. This port retains the package-selector implementation from `0b3e2fb`
and its serial integration. It does not include the earlier generic reply decorator.
The bounded-call helper is now local to `package_advisor.py`; timeout and fallback
behavior are unchanged. The model returns only an approved package ID and an exact
supporting quotation; no generated prose or numbers are sent to the supplier.

Hosted exploratory run `d612dda9-42f6-4863-bace-965dcdfd5d0a`, session
`2b0e734b37274c07`, P10, completed with score **0.6550995999**, valid must-haves and
zero timeouts. The complete transcript was reviewed by the experiment coordinator.
The previous delivery-only sessions scored 0.5546564482. Final terms changed from
EUR 33.80 / 42-day delivery / 24 months to EUR 31.80 / 56-day delivery / 24 months,
with unchanged 23,400 units per year. Complete cost fell from EUR 1,597,720.80 to
EUR 1,537,096.80, a further EUR 60,624 saving; this includes EUR 33,600 late-delivery
cost. This is one hosted observation, not a replicated effect or a fresh ten-case mean.

The two model calls took 3.46 and 1.94 seconds. The first selected the code-priced
EUR 27.62 / 56-day / 24-month opening; the second kept the scheduled package. Model:
`gpt-6.1-sol`, effort `low`; estimates and MESOs were off. The original run's policy
also listed raw-material cases for advice, but only capacity was exercised. This port's
`configs/package-advice.json` deliberately enables advice for **capacity only** and
otherwise matches `configs/cost-neutral-delivery.json`. No raw-material improvement
is claimed. This evidence does not promote the lab recommendation or default policy.

Activation requires the serial runner, this explicit policy config and local
`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` settings (optional `LLM_EFFORT`). Missing
credentials, invalid output or the eight-second call limit preserve the scheduled
move. The async runner rejects this mode before opening a session. Final offers,
closing actions, evidence-bearing or multiple-sheet moves, and fewer than 20 seconds
remaining skip advice. Role context includes the arena's `from_name`; public notes
are supplied without internal estimates or reservation costs. Previously proposed
packages are excluded in code; interpreting other refusals remains model judgment.

No additional hosted sessions or model calls were consumed to port this change.

Port validation: full suite **363 passed, one existing preflight failure** described
in the preceding entry; the same failure reproduces with the unchanged current
`origin/main` production modules. All 22 focused delivery/adviser tests pass.
`ruff check .` passes. No unrelated preflight fix is included.

## 2026-10-10 — Score push Phase 1: factory port + offline triage (no sessions)

- Branch `codex/score-push-20261010` from origin/main `3653046` (no teammate commits since).
- Ported `negotiator.agent:configured_agent` + `PolicyConfig.from_dict` (no default policy change),
  tests in `tests/test_configured_agent.py`. Full suite 367 passed, 1 known preflight failure; ruff clean.
- Quota read-only: practice 79/200 used, 121 left, 0 active sessions. Hosted best P05 is 0.4168
  (`fc0baf478c14eebb`, no local transcript).
- Offline triage of all saved runs (no quota). Ranked hypotheses for Phase 2:
  1. P02: once supplier accepts the CU 5%-deadband clause package (run 5eccc847), counter at the
     relationship-cost argmin (~361, calibrated from the supplier's own no-index alternative sheet),
     not the lowest price. Local kit fit reproduces server C within 2 EUR; est. 0.29 -> ~0.70. Medium.
  2. P05 (`rfq`): a non-leading thread's "gap closed" must hold, not close the case (0.3604 runs
     closed on sup:70250 and accepted 70210 at 32.50; best run continued to 32.00). Pair with
     `rfq_close_guard` (d8a0b0b). Est. +0.05. Medium-high.
  3. P08: cost-neutral 36-month tie-break for raw_material (`longer_tenor` outside multi_year_only).
     Est. +0.05, weak-moderate.
  4. P18: early equal-cost index_clause deadband variants, adopt supplier-revealed spread. Est.
     +0.03-0.06, weak-medium.
  P11 "faster payment" ask is not executable (payment_days not negotiable). Decision: implement 1-2 first.

## P10 package-advice replication + P02 expected-C clause target (branch codex/score-push-p10p02, 2026-10-10)

### P10 replication — run 3b0588df-1f6d-4558-aa1b-176bd028fd8d (`configs/package-advice.json` via configured_agent, aa5fb3c)
- Attempt 1, session c6daa8ddecf71416: **0.6551**, EUR 31.80 / 56 d / 24 mo / 23,400 pcs, 0 timeouts, 3 rounds.
  Exactly reproduces d612dda9 (0.6551).
- Attempt 2, session 29c667f997fb006e: **0.0**. The agent process crashed (platform error), so no buyer
  message was sent. The supplier issued a final offer and then walked away (`end_reason: timeout`).
  Infrastructure loss, not policy evidence. Verified owned (session ID recorded by the runner) and ended;
  the outcome was reconciled into `reconciliation.json` and the original attempt evidence was preserved.
- Verdict: P10 0.6551 replicates (n=2 clean, incl. d612dda9). No change.

### P02 expected-C target — new opt-in `cost_target_types` + `cost_target_index_clause` (`configs/p02-cost-target.json`)
- Triage: price-only bargaining at 90 d with no clause hits the supplier floor (~373.6); below a 0.5 %
  supplier margin the kit adds a relationship cost of up to ~EUR 140k (see 5eccc847: 349.37 → 0.087).
  The supplier accepts a lower price for the CU clause.
- Change: for single-supplier relationship cases with a public dossier full-cost estimate, value each
  permitted package by expected C over a uniform 41-point grid on the public `full_cost_range`
  (356.20–393.70). Target = the expected-C-minimising package, restricted to clause packages when the
  flag is set. The longest payment term wins near-ties. Offers never go below the target price; the agent
  accepts when the standing sheet on our package meets our offer by expected C. There is one counter to a
  final offer. Uses no hidden c_best or historical scores. Target: **366.23 / 90 d / CU 5 % deadband**.
- Tests: `tests/test_cost_target.py` (8). Full suite 375 passed + 1 known preflight failure; Ruff clean.
- Screen 1, run eb38bb1b, session 9d8f14858aa93c6d: agent KeyError before the first move. Hosted quote
  standard terms lack `payment_days`. Fixed by merging them with the dossier standard terms (commit 2).
  Session later timed out at **0.0** (no deal, no buyer move). Reconciled as owned + ended. Wasted session.
- Screen 1b, run 609f2b93, session 49fe810f2e30a206: **0.5993**. The supplier agreed to 366.23 / 90 d /
  CU 5 % immediately. c_deal 2,254,487 (relationship 12,647, index risk 17,901, payment −14,918). 0 timeouts, 2 rounds.
- Repeat, run 3e377fb3, sessions e1d31ee67f3036aa / 4dead4329811769a: **0.5993 / 0.5993**, identical terms.
- Verdict: **P02 0.2934 → 0.5993 (n=3, deterministic)**. Merge candidate. Next lever (not screened):
  the supplier accepted the opening without countering, so a lower opening (e.g. ~361, the min-C
  price under lower-fc scenarios) may still be accepted. Risk: it raises relationship cost if fc is high.

### Follow-up: P10 attempt 2 root cause (session 29c667f997fb006e) — no session used
- Evidence: the tracer stops at 17:04:44 UTC, right after the round-1 `offer` decision and before the
  `package_advice` log (the LLM call is wall-clock bounded to 8 s by `bounded_call`). No serial `intent`
  follows, and `run.json` is left at `running` with no `error`. The stderr log `/tmp/p10p02/p10.log` is empty.
  A Python exception would have printed a traceback and the runner's `except`/`finally` would have marked
  the attempt `failed`. That cannot have happened, so an external signal killed the process.
- Cause: the crashed coordinator started the run as a detached `( uv run … lab run … & ) ; sleep 8`
  inside one tool call. The process died about 1 s after that call returned, about 11 s after start, so the
  harness tore down the tool call's process group. Attempt 1 happened to finish inside the window.
  P10 does not reach the `cost_target` path, so the missing-`payment_days` bug is not involved.
  The same code completed P10 in c6daa8dd and d612dda9.
- Verdict: an operator/harness issue, not a code bug. No code change and no confirm session.
  Rule: run tracked `lab run` in the foreground of a long-blocking tool call (or via `nohup`/`setsid`).
  Never use a detached subshell that the tool call can reap.

### Follow-up: P02 lower-opening (anchor) hypothesis — computed locally, NOT screened
- Same CU 5 % / 90 d package, public expected-C (uniform 41-point grid on fc 356.20–393.70), target 366.23:
  | opening/final | ΔE[C] vs target | ≈ score-equiv |
  |---|---|---|
  | 366.23 (target) | 0 | 0 |
  | 357.44 (−1 schedule step, 2.4 %) | +10,278 | −0.22 |
  | 348.65 (−2 steps) | +37,504 | −0.79 |
  | 351.26 (min-C at low-end fc 356.20) | +28,112 | −0.59 |
- The supplier accepted 366.23 at once, so any anchor-then-concede path with a 366.23 cap closes at or below
  366.23. Under the public model every price below the target raises expected C: the relationship penalty
  is quadratic, then linear, in the margin gap, and it outweighs the spend saving. Expected gain < risk, so
  no screen. (A diagnostic using a back-solved fc, not available at runtime, shows −1 step slightly up
  and −2 steps collapsing to ~0.06. That asymmetry is exactly the risk.)
- Verdict: keep 366.23 / 0.5993.

### Lab sync
- `negotiator lab sync` retried at 21:10: uploaded 0, failed 4. The `LAB_URL` dev tunnel times out (curl 000 after 15 s).
  Local run snapshots and reconciliations are intact; rerun sync when the host is back.


### Cost-target generalisation (branch codex/score-push-costgen) — offline only, 0 sessions
- Tool: `tools/expected_cost_report.py` (+ `tests/test_expected_cost_report.py`, 2). Feature-gated exactly like
  `cost_target.active` (relationship goal + `relationship_eur_per_point` + `sustainable_margin_pct` + dossier fc);
  public fixture + dossier only, no c_best / revealed breakdowns.
- Structural finding: the non-monotone term (relationship) exists only for `stabilise`/`secure_supply` goals.
  P18, P08 (raw_material), P11 (quality), P05 (rfq) are `leverage`/`quality_first`: relationship = 0, C is
  monotone in price, so the expected-C target degenerates to "lowest price" — the insight cannot raise them.
  | case | closed (best) | E[C]/notes | expected-optimal | predicted gain |
  |---|---|---|---|---|
  | P18 .4196 | 5.45 / db0 / 90d / 24m, C 264,745 | no relationship term; equal-C: db5 5.572, db3 5.523, none 5.623 | lowest legal price (db0 cheapest per € price) | 0 from this lever (supplier rejects db5 ≤5.46, LOG H18c) |
  | P08 .5930 | 5.31 / db0 / 90d / 24m, C 1,031,778 | no relationship term; equal-C: db5 5.429, db3 5.381 | same as P18 | 0 from this lever |
  | P10 .6551 | 31.80 / 56d / 24m, C 1,537,097, rel 0 | margin at 31.80 ≈ +23 % ≫ 10 % sustainable; penalty only below ≈27 | 26.36 / 35d / 24m (E[C] 1,274,360) | not reachable: supplier final 31.80; target is a price floor, not a structural package — 0 |
  | P11 .7099 | 45.50 / ppm300 / cb0 | quality_first: no relationship term | n/a | 0 |
  | P05 .4119 (.7208 on p05 branch) | 32.00 → 29.00 | leverage rfq: no relationship term | n/a | 0 |
  | P02 .5993 | 366.23 / 90d / CU db5 | E[C] 2,320,234 (= target) | clause pkg 366.23 already optimal | 0 |
- Other relationship-goal cases (not in scope; candidates for later): P03 closed 433.08 vs E[C]-target 423.79
  (ΔE[C] −14k, relationship already ~0 → pure price gap), P01 133.70 vs 132.57/14d (−5k). No runs for P06/P09/P14/P17.
- P02 reconciliation (teammate's 361.33 / −6,443): reproduced exactly as a POINT estimate at fc = 366.73.
  That fc is back-solved from the hosted breakdown (relationship 12,647 at 366.23) = hidden-model leakage,
  not the public estimate. Public point fc 374.95 → min-C price 369.17; public expected (uniform 356.20–393.70)
  → 366.23. E[C](361.33) − E[C](366.23) = +3,231 (worse). Per-fc ΔC(361.33 vs 366.23): −29k @356.2, −11k @365,
  +1.8k @370, +13k @374.95, +17k @393.7 — penalty side is long. Same penalty formula; the difference is the fc
  assumption (revealed vs public). Verdict: no screen; 361.33 would be a hidden-data-tuned target.
- P02 no-clause 366.41 has lower E[C] (2,301,137, no index risk) but price-only bargaining floors at 373.65
  (6 sessions); the clause is what buys the lower price. Not screened.
- Overfitting guard: no flags/configs added; nothing keyed by case ID. `cost_target_types` remains validated on
  one case only (P02, n=3+1). Suite: 376 passed + known preflight failure + 1 timing flake
  (`test_two_thread_rfq_slow_replies_no_timeouts[1]`, passes on rerun). Ruff clean.
- Sessions used: 0 / 8. Merge verdict: merge tool + tests (harmless); no policy change.

## 2026-10-10 — Score push Phase 1: factory port + offline triage (no sessions)

- Branch `codex/score-push-20261010` from origin/main `3653046` (no teammate commits since).
- Ported `negotiator.agent:configured_agent` + `PolicyConfig.from_dict` (no default policy change),
  tests in `tests/test_configured_agent.py`. Full suite 367 passed, 1 known preflight failure; ruff clean.
- Quota read-only: practice 79/200 used, 121 left, 0 active sessions. Hosted best P05 is 0.4168
  (`fc0baf478c14eebb`, no local transcript).
- Offline triage of all saved runs (no quota). Ranked hypotheses for Phase 2:
  1. P02: once supplier accepts the CU 5%-deadband clause package (run 5eccc847), counter at the
     relationship-cost argmin (~361, calibrated from the supplier's own no-index alternative sheet),
     not the lowest price. Local kit fit reproduces server C within 2 EUR; est. 0.29 -> ~0.70. Medium.
  2. P05 (`rfq`): a non-leading thread's "gap closed" must hold, not close the case (0.3604 runs
     closed on sup:70250 and accepted 70210 at 32.50; best run continued to 32.00). Pair with
     `rfq_close_guard` (d8a0b0b). Est. +0.05. Medium-high.
  3. P08: cost-neutral 36-month tie-break for raw_material (`longer_tenor` outside multi_year_only).
     Est. +0.05, weak-moderate.
  4. P18: early equal-cost index_clause deadband variants, adopt supplier-revealed spread. Est.
     +0.03-0.06, weak-medium.
  P11 "faster payment" ask is not executable (payment_days not negotiable). Decision: implement 1-2 first.

## 2026-10-10 — Score push P18/P08 screens (branch `codex/score-push-p18p08`)

Legal-options check: P18/P08 fixtures list index_clause ∈ {none, AS-14404 db 0/3/5}, payment
{14..90}, tenor {12,24,36}. No cap and no index-start deferral, so neither was used.
Code: `8eb3138` adds opt-in `clause_variant_types` (equal-cost deadband sheets after the supplier makes the clause
mandatory; adopt the supplier's clause) and the `longer_tenor` cost-neutral tie-break in `TradePolicy.initial`.
Configs: `configs/p18-clause-variants.json`, `configs/p08-longer-tenor.json`. Both are opt-in; defaults unchanged.

| run | session | case | hypothesis | score | terms | timeouts |
|---|---|---|---|---|---|---|
| 6eff2557 | 3acf459143f4acdd | P18 | H18 clause variants | 0.0 (invalid: process killed by shell exit after probe) | walked | 2 (harness) |
| 1f8908d4 | 53a3d0a1b793c038 | P08 | H08 longer tenor | none (process killed; session left open) | — | — |
| c5eb289f | 41f9ee98996b79bb | P18 | H18 clause variants | **0.4196** | 5.45 / db0 / 90d / 24m | 0 |
| dc8e0a8c | 6ddf266d690d2113 | P08 | H08 longer tenor | 0.5376 | 5.36 / db0 / 90d / 36m | 0 |
| 0bbb404e | 32e38ffae33fe908 | P18 | H18 repeat | **0.4196** | 5.45 / db0 / 90d / 24m | 0 |
| f5c5c311 | b1c606cf7453017d | P18 | H18c follow revealed db5 track (e40b120, reverted 6b8dc1e) | 0.3191 | 5.60 / db0 / 90d / 24m | 0 |
| 415974c2 | 195209b411efcbe0 | P18 | H18d clause variants + rounds=7 | 0.3191 | 5.60 / db0 / 90d / 24m | 0 |
| b39c09c4 | 16bc0e15a9cf938c | P08 | H08b package-advice + rounds=7 | 0.5598 | 5.34 / db0 / 90d / 24m | 0 |

Findings:
- P18: the supplier always makes the clause mandatory at 24m and quotes db0 5.60 / db5 5.70. Our 3-sheet probe at
  equal cost (db5 5.43 / db3 5.38 / db0 5.31) gets a hold at db0 5.60. In both repeats it then accepted our db0
  counter at 5.45 (+0.0134 vs local .4062 best). If we stay on db5 (5.46) or counter lower on db0 (5.42), it goes
  final at 5.60 and we take it (.3191). Its accept threshold is about 5.45 db0 / 90d. Hosted best .4531
  (= 5.40 db0 90d 24m) is not in local runs.
- P08: 36m makes the supplier insist on the clause too and concede more slowly (5.36 vs 5.31). With rounds=7 it
  stops at 5.34. Dropped both (2 non-improving).
- Sessions: 8 practice sessions; quota 103 -> ~119 used/600 because other agents share it.
Decision: P18 `configs/p18-clause-variants.json` is a measured win vs local .4062 (n=2, identical), but below the hosted
best .4531. It is mergeable as an opt-in config only. P08: no change.
- Next hypothesis: break ties between EXACT equal-cost contract commitments toward 36 months.
  P10 and P18 have 24/36-month equal modeled buyer cost; retain must-haves and the delivery gain.
  configs/cost-neutral-commitment.json changes only this choice from the delivery config. One P10
  screen planned after checks and publication; LLM and supplier-fit behavior stay off.
- New PackageAdvisor prototype lets the model select one code-approved, costed package. It checks
  an exact supplier quote, legal options, must-haves and cost ceiling, and limits switches/time.
  Offline P10 chose legal 56 days / EUR27.62 vs 42 days / EUR28.34, compensating late cost; P18
  kept its scheduled package. Wiring checks only, no hosted efficacy. Not activated yet.
- Relationship helpers handle the nonmonotonic cost curve and report public-estimate sensitivity;
  latest quote defaults override master data per field. P02's central target EUR363.05 at 14 days
  is uncertain (public-range optima EUR345.44–380.62), not a hard floor or score forecast.
- Rival evidence decorator validates current-session standing offers and exact qualifiers, with
  no hidden costs/targets. Prototypes remain unactivated pending integration and review.
- Integrated validation before publication: 453 tests passed; Ruff and git diff checks clean.

## 2026-10-10 — tracked async RFQ runtime preparation (no hosted sessions)

Hypothesis: independent supplier workers and a bounded coordinator close can preserve an RFQ final offer while another supplier POST takes longer than its 60-second response window. This addresses the observed P05 run `663873a0-ff50-4f24-a4bb-e08919e5149b`, where a 65.58-second rival call preceded a failed acceptance and supplier withdrawal.

Added `negotiator lab run --runner async` for exactly one explicitly budgeted attempt, preserving the configured agent factory, policy config, source/data fingerprint, quota checks, publisher and owned-session evidence collection. Runner selection is recorded as reserved `_lab_runner` metadata. Session identity is journalled and saved before documents or buyer moves; a failed or ambiguous attempt is not automatically restarted. Existing serial runs remain the default. Campaign/checkpoint schemas are unchanged.

Local regressions use real `PackageAgent` plus the simulator with a 66-second rival response and check timely final acceptance under both soft single-send and concurrent execution. A separate regression exposed acceptance of a stale cheaper offer from an in-flight supplier after the close wait; closing now excludes those sheets. When every reply is pending at the wave-cap close, the coordinator waits within its reserved closing window for a current sheet. Both model adviser attributes are rejected before async session creation.

Validation: `uv run --locked pytest -q` passed 461 tests with the main public package data; `uv run --locked ruff check .` passed. Budget used: zero practice and zero sandbox sessions. This is runtime preparation, not a measured score improvement or a promotion; full hosted async RFQ behavior still needs the planned single-session experiment and complete replay review.

## 2026-10-10 — P05 screen 1: non-leading convergence hold (async)

Run `74d3bf74-b5c5-48db-86ce-c109c9bffe0d`, session `a9a16a1231994e51`, commit `8e6a7fa`,
config `configs/p05-nonleading-hold.json` (cost-neutral-delivery + `rfq_nonleading_hold`),
`--runner async`. Score **21.28** (worse than 36.04 baseline): accepted sup:70250 EUR 34.00 /
35 d / 30 d payment, 113 s, zero timeouts. Transcript: sup:70210 led (32.50, then 32.00 in its
next reply); hold fired correctly on sup:70250 for ~40 s, but the `>20 s own deadline` fallback
then let 70250's "gap closed" through while 70210's reply was in flight; the coordinator
excludes in-flight sheets, so the only live sheet was the losing 34.00. Fix (`agent.py`): keep
holding while the leader is open and has moves left, regardless of the loser's deadline.
Regression updated. Tests 377 passed + known preflight failure; ruff clean.

## 2026-10-10 — P05 screen 2: non-leading hold without own-deadline fallback (async)

Run `ca2cade9-a914-4c6c-b556-4fe39a06ce1d`, session `ef13f675e65e7676`, commit `0bd7080`, same
config. Score **41.19** (vs 36.04 traced baseline, ties prior best .4119): sup:70210 EUR 32.00 /
35 d / 30 d, 50.7 s, zero timeouts. sup:70250's 34.00 convergence held; 70210 went 32.50 → 32.00
→ final 32.00; 70240 final 33.50/45 d; coordinator accepted 70210's final at once. Lead time
35 d (<= 42), no 56-day counter, no early payment. Next: repeat once for replication.

## 2026-10-10 — P05 screen 3: replicate non-leading hold (async)

Run `bee8da3d-93be-417e-93bf-fb79f7ec55c8`, session `e7dd5622c1234a45`. Score **41.19** again:
sup:70210 EUR 32.00 / 35 d / 30 d final accepted, 12.3 s, zero timeouts; identical transcript.
Replicated 2/2 after fix. Next: hold + `preferences.rfq = standard_payment`
(`configs/p05-hold-standard-payment.json`) — earlier standard-payment screens were masked
by the gap-closed exit.

## 2026-10-10 — P05 screen 4: hold + rfq standard_payment (inert)

Run `046127b6-2113-49dc-ac7b-2247ac95cb45`, session `2b9eb01f4eb4f8ec`. Score **41.19**, identical
transcript (still 90-day counters): the preference only applies to `package_types`, which
excluded rfq. Not a test of the hypothesis. Next: same config with `rfq` in package_types.
- Follow-up (no session): even with rfq in package_types, `standard_payment` resolves to the
  buyer's standard (90 d), so offline the first counter stays 31.68/90 d; the line cannot test
  supplier-standard payment and is dropped. The earlier "supplier-standard payment 36.04"
  result on the goal branch was likewise inert and masked by the gap-closed exit.
- Decision: merge candidate = async runner + `rfq_nonleading_hold` (2/2 at 41.19, +5.15 vs
  36.04 traced baseline, zero timeouts, 35 d lead, 30 d payment). Remaining gap to arena best
  .4168 is ~EUR 400 (consistent with 32.00 at 45 d), ~0.0005 on the ten-case mean; not pursued.
  `rfq_final_guard` stays off (serial-only protection; async covers the 65 s rival case).
  Sessions consumed by this P05 work: 4.

## 2026-10-10 — Recover serial comparison and test the async feedback proposal

Recovered `ece-payment-response-20261010-01` from its original local state and reserved
12-session sandbox family. The two prior D01 results were preserved; ten never-started
cells completed. All original outcomes ended as valid deals with zero timeouts. The
payment-response candidate scored 91.92 versus 91.92 on D01 and 41.89 versus 46.09
on D02 (candidate versus baseline, three repeats each). Gain, case-regression and
repeat-win gates failed. The serial recommendation stayed unchanged. Cited lab finding:
`ece-payment-response-20261010-01-completed-regression`.

Hypothesis for the next bounded test: raising only the opening anchor from 0.12 to
0.16 would improve async D01/D02 complete-deal scores without a material case
regression. The integrated `b66b0b4` source was captured in two published async
checkpoints with the same source tree, runner and empty data manifest; only `anchor`
differs. Baseline `0159f25330e9459787096cd3a2a34ccd`, candidate
`d17c131a44514cc7a3f5924db6665495`. The candidate was registered to the
feedback proposal `a10d8787f6f066ac49079fa9c856dc279403df6852cf708e3722a85fdbe23128`.
Suite/family/campaign: `d01-d02-sandbox-async-anchor-20261010`,
`ece-async-anchor-20261010-01`, `ece-async-anchor-20261010-01`.
User-approved ceiling: 12 sandbox sessions; zero practice allowance.

All 12 async attempts completed as valid deals with zero timeouts and no model
fallbacks (model assistance and runtime memory off). D01 candidate mean 87.24
versus 91.92 baseline (−4.68); D02 candidate mean 52.39 versus 46.09 (+6.30).
Overall mean gain +0.81, below the required +1.00. Each repeat gained +0.81,
but the D01 regression exceeded the 2-point gate. Checkpoint, complete-sample,
must-have, timeout-evidence, timeout-comparison and repeat-win gates passed;
gain and case-regression gates failed. The lab rejected the candidate and retained
the async baseline. Mean elapsed attempt time was 8.13 s baseline versus 50.68 s
candidate; two slow candidate repeats dominated that difference. Provider/model
cost was zero for this model-off comparison. Cited lab finding:
`ece-async-anchor-20261010-01-case-tradeoff`.

Decision: do not promote either candidate. The next hypothesis is to inspect the
D01/D02 reply sequence and test one bounded response-conditioned economic change
that preserves D01 while targeting D02, under a separately approved held-out budget.
The proposed 99/100 target is aspirational; these two fixed sandbox cases do not
establish generalization. Local evidence remains in ignored `experiments/loop/`;
original hosted outcomes and gates are in the shared lab.

## 2026-10-10 — Conditional multi-supplier anchor candidate (blocked sandbox comparison)

Hypothesis: the prior 0.16 anchor's D02 gain and D01 loss may reflect supplier-roster
context. Apply 0.16 only when the case contains multiple suppliers; retain the 0.12
opening in single-supplier cases. This is inferred from repeatedly used D01/D02 cases,
not a held-out finding. The case roster is fixed at session start, so active-thread
changes cannot alter the anchor mid-negotiation. Deterministic closing and term checks
remain unchanged. Model assistance and supplier memory stay off.

Candidate source branch: `codex/competitive-anchor-candidate`. The paired async
sandbox comparison has a separate user-approved maximum of 12 sessions and zero
practice allowance. Checkpoint IDs, per-case scores, gates, failures, and disposition
will be recorded after the lab campaign. Local tests: targeted agent/checkpoint tests
passed; full suite had 598 passes and one timing-sensitive model-assisted simulator
timeout assertion, which passed immediately in isolation; Ruff passed. At that
candidate commit, no sandbox sessions had started.

Follow-up: published feature-capable baseline `019a78caef124846ad7f972eae431add`
and candidate `f017d55148d046cda80f86a32f9a7065`, sharing the exact source tree;
registered async suite `d01-d02-sandbox-async-competitive-anchor-20261010` and
family/campaign `ece-competitive-anchor-20261010-01` at a strict 12-session sandbox
ceiling. An initial offline-cache preflight failed before session start; resuming the
same family with the correct absolute cache reached the first D01 baseline open,
which ended **ambiguous with no returned session ID**. Its original result remains
saved, and the other eleven attempts remain pending. The Arena's owned sandbox
session listing showed no session created after the campaign began, but absence
from that listing is not accepted as definitive not-created evidence by the lab.
The campaign therefore remains blocked and has **no score comparison or promotion
verdict**. Do not start the remaining cells or reuse the reserved budget until
the start is reconciled under the lab's original-outcome rules.

Mitigation for future checkpoint sources: the async lab worker now makes two
additional transport retries using the same journaled `X-Move-Id` and records only
the exception class if all retries fail. This cannot rewrite or validate the
already ambiguous original attempt. No practice sessions were used.

## 2026-10-10 — Move the learning loop onto the shared lab VM

- User requested a real VM process and persistent 99/100 goal, replacing the Codex heartbeat.
- Implemented a systemd Python worker, durable SQLite goal/events, bounded feedback retries,
  registry-backed configuration candidates, local tests and immutable publication before
  budgeted async execution. The existing Experiments table displays a compact worker status.
- Initial scope remains the reserved 12-session competitive-anchor sandbox family. No practice,
  new family, automatic recommendation changes, or 99/100 success claim is authorized.
- Added exact-move recovery for the ambiguous original start with a separate journal and receipt;
  original failures remain promotion-ineligible. Tests cover ownership rejection, crash/retry
  without a second logical start, budget exhaustion, freeze, restart, and review safeguards.
- Installation and hosted outcome must be verified separately; see docs/21-vm-learning-worker.md.
## 2026-10-10 — P05 offline cost decomposition (no session)

Session `ef13f675` deal sup:70210 32.00/35 d/30 d: C = 271,720.96 (price 268,800; payment
financing 1,792; quality 1,129). Scoring: c_open 305,544.96, c_best 223,424.17, so score/EUR
of unit price = **0.103** (EUR 8,456 per EUR 1). Levers at fixed price: 90 d payment −3,584
(+0.044), 60 d −1,792, 45 d −896; lead 28 d = 0, 42 d +1,400 (−0.017). Score 1.0 needs
≈EUR 26.70 at 35/90. **Price dominates** (gap ≈ EUR 5.3/unit); payment ≤0.044; lead time is
cost, not value, except as a trade for price. Supplier choice: sup:70240 (Hrvelec) opened
31.50 at 52 d and explicitly priced 35 d as "expensive overtime" (+3.50); it alone offered 90 d.
70240 at 42 d/90 d scores 0.50 @31.50, 0.55 @31.00, 0.66 @30.00 — the bolder lever. Every
prior run countered 70240 at 35 d (overtime premium), so it never got below 33.50.
Lever verification: payment options {14,30,45,60,90} (90 legal, 14 banned by rule); lead
{28,35,42,56} with must-have ≤42 → 42 allowed, 56 never; awarding 70240 legal; rival
disclosure would require claim plumbing for RFQ (not built; held for later screens).

Hypothesis A (`rfq_supplier_lead_time`, `configs/p05-supplier-lead.json`): when a supplier
quotes a lead time beyond ours, counter at the longest legal option ≤ its quote (42 d for
70240), so it can drop its overtime premium. Offline first counters: 70240 27.72/90/42; others
unchanged. Unit test added; suite 378 passed + known preflight failure; ruff clean.

## 2026-10-10 — P05 screen 5: supplier-fit 42-day lead time (hypothesis A)

Run `f42acd21-85d2-4840-9c01-2a2a9e5c96f3`, session `fee923108e98924c`, commit after `rfq_supplier_lead_time`.
Score **41.19** (no change): sup:70210 32.00/35/30 final, 96.5 s, zero timeouts. Transcript:
70240 accepted 42 d at once ("happy to speed up the lead time to 42 days") and dropped its
opening from 35.00@35 d to 33.00@42 d, then 32.50/90 d, alt 32.00/60 d (C 271,517 ≈ +0.002,
countered rather than taken), final 32.50/42/90 (score-equivalent 0.401). 70240's floor at
42 d ≈ 70210's; no overtime-premium windfall. 56 d never offered. Line: 1 non-improving.

Hypothesis B (screen 6, `configs/p05-rival-offer.json` = A + `rfq_rival_offer`): category
goal is leverage; cite the cheapest must-have-valid standing rival offer from this session
("Another supplier has offered part at EUR X per unit (offer:id)") to a supplier whose own
standing price is higher, once per offer ID per supplier. Code takes figure and ID from the
live sheet (verifiable). Unit test added; suite + ruff clean except the known preflight test.

## 2026-10-10 — P05 screen 6: rival-offer disclosure (hypothesis B, on A + hold)

Run `ebd84380-7d68-49d1-9fd9-2ff3d3059b91`, session `914b145b75d7015a`. Score **41.19** (no
change): sup:70210 32.00/35/30 final, 56.6 s, zero timeouts. Two claims sent, both to sup:70250
(offer:70210-0 @36.00, offer:70210-1 @33.00), both **verified**; 70250 acknowledged ("checked
the rival quote data you cited; it holds") but stayed 34.50 → 34.00 exactly as without claims.
No claim reached 70210 (it always led) or 70240 (its 42 d prices never exceeded a valid rival
standing price strictly). 70240 path identical to screen 5. Disclosure does not move floors here.
Lead-time line: 2 non-improving (screens 5, 6) → dropped. Disclosure: 1 non-improving.

Hypothesis C (screen 7, `configs/p05-supplier-payment.json` = hold + `rfq_supplier_payment`):
70210 refused 90 d in all four replies ("need the cash in 30 days"); deals close at its 30 d
anyway. Concede to the supplier's stated payment (never < 30 d) so the concession counts as
our move and later rounds are price-only. Offline: 70210 counters 31.78/30 d, 31.88/30 d.

## 2026-10-10 — P05 screen 7: concede to supplier-stated payment (hypothesis C) — worse

The tool retried the launch command, so **two** sessions ran with the same config/commit:
- Run `cfdafb15-9300-484f-8950-cd6a3d92e137`, session `a18a4bbf41f3245b`: **21.28**. 70250
  *agreed* to our 34.00/30 d counter (we had conceded to its 30 d); the coordinator closed on
  "sup:70250 agreed" while 70210's reply (32.50) was in flight, so it accepted 34.00.
- Run `826f495d-3a81-4247-b40e-4e58c95f533d`, session `ad9529ebb8e766b5`: **36.04**, 70210
  32.50/35/30. Once we offered 30 d, 70210 said "I can drop to 32.50, but that's where it
  stops" and went final at 32.50 after three replies (vs 32.00 after five when we kept asking 90 d).
Zero timeouts in both. The refused 90 d request was effectively a trade chip: 70210 compensated
with price ("if we agree on 30 days, I'll drop the price to 32.00"). Hypothesis C dropped.
Robustness finding: an "agreed" non-leader can still close the case on its own price while the
leader is in flight (same in-flight exclusion as screen 1); harmless on the hold base so far.

Hypothesis D (screen 8, `configs/p05-rival-history.json` = hold + `rfq_rival_offer` +
`rfq_rival_offer_history`): disclosure line, second try aimed at the leader. Cite the lowest
priced rival sheet from anywhere in this session (e.g. offer:70240-0 @31.50) when it
undercuts the receiving supplier's standing price; figure and ID taken from the sheet.

## 2026-10-10 — P05 screen 8: session-wide rival-price disclosure (hypothesis D) — WIN

Run `97f3fdbf-7c78-4be3-a19b-1bfe13408d17`, session `d52efd4374aaf110`, commit `9c5f6ed`. Score
**72.08** (vs 41.19; arena best .4168): sup:70210 EUR **29.00** / 35 d / 30 d, 167.8 s.
Six claims, all **verified**. To 70210: offer:70240-0 @31.50 → "We did not know that - a fair
point … come down to €32.00", "need to clarify this internally" (boss approval), then "Your
data on the market was solid … 29.00 EUR"; we matched 29.00, gap closed, accepted. 70250 went
34.00 → 32.00 → 31.00 under the same claims; 70240 34.50 → final 34.00. Timeouts: one on the
losing 70240 (its send waited behind a 58 s POST in the soft send slot); none on the winner.
Must-haves held (35 d), no 56 d, no 14 d. Next: repeat once.

## 2026-10-10 — P05: reconcile interrupted repeat `p05-rival-history-2`

Run `704039ed-9bd6-4b42-95a0-8df15e33c6bb`, session `6c3717e8dc3eaed5` (journalled in the run;
owned). The worker process was killed ~9 s after start (last journal record 19:21:29 UTC, buyer
counter 29.00 to 70210 sent as intent). Arena status: `ended`, `end_reason: timeout`, no deal,
score 0.00. Replay: 70210 again reached **29.00/35/30** (round 3), then final, then withdrew;
70250 33.00/30 final, 70240 34.00/90 final; all withdrew after unanswered timeouts. Partial
replication of the 29.00 floor. Recovered outcome attached with `save_reconciliation` for this
one session only (no blanket import); original attempt evidence preserved; `lab sync` uploaded.
Expired attempt counts as one session; not resumable.
Teammate P05 work read (main LOG/BENCHMARK_HANDOFF, origin/codex/benchmark-goal-20261010): 14-day
early cash + capacity opening (.3854, rejected), supplier-standard payment (inert). Not repeated.

## 2026-10-10 — P05 screen 9 plan: replicate screen 8 config (no change)

Differs from previous: nothing; `configs/p05-rival-history.json` at HEAD. Purpose: confirm the
72.08 from session-wide rival-price disclosure (70210 31.50 claim → "boss approval" → 29.00).
Runner `async`, launched under nohup so the process survives the shell.

## 2026-10-10 22:35 — Score-push integration: final combined config, ten-case confirmation (MEASURED HOSTED PRACTICE)

- Branch `codex/score-push-integrate`, runtime commit `ed1474c` (clean). Merged `origin/main` at
  `d73f6af` (main has since moved to `b7a0646`; not merged, to keep the confirmed provenance), `origin/codex/score-push-p18p08`, `origin/codex/score-push-p05` and the confirmed P05
  rival-history commit `5dc584b`; ported only `standard_payment_types` from `score-push-p07p11`
  (no P07 deep anchor, no P03 cost target, no longer-tenor).
- Config `configs/score-push.json` (factory kwargs `configs/score-push-run.json`: `estimates={}`,
  `meso=false`), agent `negotiator.agent:configured_agent`, runner `auto`. Changes vs the dead run's
  config: **removed** `clause_variant_types: [raw_material]` (P18 measured .4196 x2 vs retained
  package policy .4531 x2, runs `c5eb289f`/`0bbb404e` vs `b2922dc3`/historical `336d373e78ee87f1`);
  added `standard_payment_types: [price_increase]` (P01 .9602 x2, `ca6a784`) and
  `rfq_rival_offer` + `rfq_rival_offer_history` (P05 .7208 x3: `97f3fdbf`, `d1fea8bb`, `237f5adb`).
  P11 .7902 (`0f657d76`, `957c300`) and P18 .4531 (`b2922dc3`, `d070c01`) came from the base/package-advice
  policy on main-era code; both are compatible (no extra flags needed) and reproduced below.
- Dead run `22b6c60b` (`score-push-confirm`, `ea4d7be`) preserved as evidence: P01 .9253, P02 .5993;
  P03 session `a9ad60d5e055b7d9` verified owned (journal paths + manifest) and ended server-side by
  `timeout`, score 0, no deal (worker killed after buyer round 4). Recovered outcome attached to that
  one attempt; run marked `interrupted`; `lab sync` uploaded. P04–P18 never started. Not resumable.
- Fresh run `b9ad733d-aae8-4b5d-a60e-8332948c403a` (`score-push-final-confirm`), 10 cases x 1, max 10.
  All completed, deals, must-haves ok, 0 timeouts. Every transcript read.

| case | session | score | best | delta | final |
|---|---|---|---|---|---|
| P01 | 7d3efa5162b9e0a7 | .9602 | .9602 | 0 | 133.70 / 30d / Apr-2027 |
| P02 | ed797d2ca3d1b583 | .5993 | .5993 | 0 | 366.23 / 90d / CU 5% |
| P03 | 5d313d36b827605e | .8998 | .8998 | 0 | 433.08 / 90d / 36m |
| P04 | 334c334675927b2e | .8604 | .8604 | 0 | 4.94 / 90d / 24m |
| P05 | 11640b125cc1400d | .7208 | .7208 | 0 | 70210 29.00 / 30d / 35d |
| P07 | 5ff2286d148fec03 | .7430 | .7430 (.7470 n=1 bundling evidence, not included) | 0 | 5.38 / 60d / 24m |
| P08 | db8a3177ce4a77fb | .5930 | .5930 | 0 | 5.31 / 90d / AS db0 |
| P10 | bace291c141592a7 | .6551 | .6551 | 0 | 31.80 / 56d / 24m |
| P11 | 65aaf739bbbc3c2c | .7902 | .7902 | 0 | 45.02 / 300ppm / cb0 |
| P18 | 36322b9872ddc79d | .4531 | .4531 | 0 | 5.40 / 90d / AS db0 |

- **Fresh ten-case mean .7275** (one repetition). Historical best-per-case mean is also .7275 with these
  bests; this run is the first single fixed config to reach all of them together. Most sessions took
  3–10 s: replies were identical to earlier sessions, likely deterministic/cached supplier behavior,
  so this is reproduction, not independent stochastic confirmation.
- Sandbox regression (free, `--runner auto`): combined `511a2526` D01 .9192 x2, D02 .5239 x2; recommended
  baseline config (e1d931e4 kwargs on current code) `f8465f16` D01 .9192 x2, D02 .4609 x2. No regression.
- Runner decision: one launch path, `--runner auto`: `rfq` cases use the async runner (needed by the P05
  hold/rival levers); every other case uses serial (package advice, expected-C target). The package
  adviser is detached only on async attempts whose case type is outside `package_advice_types`.
  Limitation: package advice on an `rfq` case is still unsupported (async rejects it).
- P02 requirement (choose indexed vs unindexed by expected C, indexed only if the supplier's stated
  constraints exclude unindexed): implemented offline as an unindexed price floor at the supplier's own
  lowest unindexed quote, then **reverted**. On P02's recorded opening (370.96/30d, no clause) the local
  expected-C model ranks unindexed@370.96/90d (2,303,857) and even @373.6 (2,307,879) below the indexed
  366.23 target (2,319,043), so it would abandon the measured clause deal. The server C for that deal is
  2,254,487 vs local 2,299,891: the local relationship/index model is not calibrated enough to make this
  choice. Kept `cost_target_index_clause` (risk-sharing mode, inert where no clause option, e.g. P01).
- Overfitting guard: no case IDs or case-specific numbers in runtime code; behavior is derived from
  term options, must-haves, quote standard terms, supplier sheets and computed costs. But each lever is
  gated by case type and each type has one practice case, so these are single-case validations:
  `standard_payment_types` (P01 only; P02 bypasses it via the cost target), `cost_target_types` +
  `cost_target_index_clause` (P02 only), `rfq_rival_offer(_history)` + `rfq_nonleading_hold` (P05 only;
  D02 sandbox +.063 is a second rfq observation), `package_advice_types: [capacity]` (P10 only).
  `cost_neutral_lead_time` has P10 + D01/D02 neutral evidence. Final cases of the same types may differ.
- Offline replay of recorded best threads (fetched owned threads, attachments re-read) with the combined
  config: P01, P02, P04, P07, P08, P18 identical; P03/P11 diverge at one late move identically on their
  own source commits (harness limitation: model/claims context not replayed); P10 diverges only because
  the LLM adviser is stubbed. Tests: `pytest` 638 passed; `ruff` clean.
- Sessions: 10 practice (this run), 8 sandbox. Live practice 161 used before, 174 after (other agents
  share the key; a teammate P05 session was active at start). Decision: publish this config on the
  branch; no main merge, no recommendation change.

## 2026-10-10 — P05 screens by parallel worker (same worktree; recorded here for completeness)

A second agent shared this worktree and `/tmp/p05` from ~22:05; its runs are part of this P05 budget:
- `57b90d1e` `p05-rival-history-3`, session `09f597f13bebed64`: launched 22:05 then abandoned
  (process gone); ended `timeout`, score 0.00, no deal; 70210 was at 32.00 after the first claim.
  Reconciled for this one verified owned, ended session; `lab sync` uploaded.
- `d1fea8bb` `p05-rival-history-4`, session `2b8fbe3260167f15`: **72.08**, 70210 29.00/35/30, 0 timeouts.
- `237f5adb` `p05-rival-history-4`, session `69acb4ae63e23c8c` (mine): **72.08**, 70210 29.00/35/30,
  9.8 s, 0 timeouts. Identical 70210 path: 31.50 claim → 32.00 + "clarify internally" → 29.00.
- `376427e0` `p05-undercut-reanchor-1` (hypothesis E, commit 5770caf), session `2ffdd9c5ee8c2b9d`:
  **72.08**, 0 timeouts. Counter 27.26 after 29.00 → "I already gave you a massive drop … stay
  there" → final 29.00, accepted. Anchor line: 1 miss. 29.00 looks like 70210's floor under rival
  pressure alone.
Replicated 3/3 (plus 2 expired). Lever confirmed.

## 2026-10-10 — P05 screen 10 plan: one verified data fact on counters with no rival claim (F)

Differs from previous: E config (undercut re-anchor) + `rfq_data_claims` (`configs/p05-data-claims.json`);
E's lower ask is kept because on the D base we counter at 29.00 itself and a claim cannot lower it. Until now
RFQ cases sent no data claims at all: `evidence_types` excludes rfq and `EvidencePolicy` gates to
single-supplier cases. Only rival-offer citations went out. Once 70210 led at 29.00, no rival
undercut it, so later counters carried no argument and it held 29.00 (E showed that a lower
ask without new information fails). Category goal names "competition **and data**"; 70210 itself
responded to "your data on the market was solid". F appends exactly one fresh verified public or
supplier-own fact (scorecard OTD/PPM, latest index windows) to an RFQ counter only when no rival
claim was added. Should-cost (internal estimate) excluded; no hidden outcomes are used.
Offline replay: at 70210's 29.00 the counter carries scorecard sc:70210@2026Q3 OTD 80.8 %.

## 2026-10-10 — P05 (parallel worker B): repeat + screen E (undercut re-anchor) — miss

Note: two workers ran in this worktree at once (B did not know about A's `5dc584b`). B stops here
to avoid duplicate sessions; A owns the next screen (its uncommitted `rfq_data_claims` is untouched).
- Lever (from the full transcript of `d52efd4374aaf110`): `rfq_rival_offer_history` cites the
  lowest rival sheet from the *whole session*, including must-have-invalid ones, so the leader
  70210 receives 70240's opening 31.50 @ 52 d (offer:70240-0) in its first counter (verified) →
  "clarify internally" → 36.00 → 32.00 → **29.00**. Screen 6 (valid sheets only) never cited to 70210.
- Run `57b90d1e` / session `09f597f13bebed64`: process killed seconds after a nohup start (the shell
  call reaping background jobs); ended by timeout, 0.00, reconciled for that one session only. 1 session.
- Run `d1fea8bb` / session `2b8fbe3260167f15`, commit `5770caf`'s parent config
  `configs/p05-rival-history.json`, foreground: **72.08**, 70210 29.00/35/30, 24.3 s, 0 timeouts.
  Identical path to screen 8. Replicated (with A's `237f5adb` = 3/3 completed at 72.08).
- Screen E `rfq_undercut_reanchor` (`configs/p05-undercut-reanchor.json`, commit `5770caf`), run
  `376427e0` / session `2ffdd9c5ee8c2b9d`: **72.08** (no change), 97 s, 0 timeouts. Counter 27.26
  after the 29.00 drop; 70210: "price stays … already gave you a massive drop to 29.00", then
  final 29.00/30 d; accepted. Price-floor line: 1 miss. 29.00 looks like 70210's floor under the
  single 31.50 claim; payment (90 d refused) and lead-time lines already closed.
- Sessions used by B: 3 (one killed). Gap to .92 ≈ EUR 1.9/unit; remaining untested lever is a
  verified data claim to the leader (A's in-progress `rfq_data_claims`).

## 2026-10-10 — P05 screen 10: one verified data fact on RFQ counters (F) — WIN

Run `c3054e99-df92-4a96-9d94-9b83035d79bc`, session `a7298b34c1e012d6`, config
`configs/p05-data-claims.json` (E + `rfq_data_claims`). Score **77.23** (vs 72.08 ×3):
sup:70210 EUR **28.50** / 35 d / 30 d, 183 s, zero timeouts. 70210 path: 31.50 rival claim →
32.00 + "clarify internally"; counter 31.74 + scorecard OTD 80.8 % (verified) → "clarified
internally … I checked the delivery scorecard … dropping the price to €28.50 to make up for it
and the other quote"; re-anchor 26.79 + PPI-D351 −3.7 % (verified) → "you are right about the
drop … already went as low as I can go … 28.50 final"; accepted. 70240 took the 45 d
alternative path (32.50/45 final); 70250 32.00/30. No 56 d, no 14 d, lead 35 d. Data line: 1 hit.

## 2026-10-10 — P05 screen 11 plan: stack the data fact with the rival claim (G)

Differs from screen 10: `rfq_data_claims_stack` also adds the data fact to counters that already
carry a rival claim (`configs/p05-data-claims-stack.json`). In F, 70210's first counter had only
the rival claim; each verified claim appears to buy one internal-clarification drop. Front-loading
OTD with the rival claim may move the 32.00 reply lower, leaving PPM 1863 and PPI-D351 for later
counters. Offline first counters: 70210 rival 31.50 + OTD 80.8 %; 70250 rival + OTD 88.0 %;
70240 OTD 62.5 % only. Risk: 70250's 88 % OTD is mildly favorable to it.

## 2026-10-10 — P05 screen 11: stacked data + rival claim (G) — tie at old level

Run `a160f212-66f3-4e52-9c0d-2b287ba4cce0`, session `6f46f0195a05816a`. Score **72.08**: 70210
29.00/35/30, 228 s, zero timeouts. First counter carried rival 31.50 + OTD 80.8 % (both
verified) → one reply, 32.00 + "clarify internally" (one drop for two claims). Second counter:
PPI-D351 −3.7 % → 29.00. Third counter 27.26 had **no** claim (PPM shares id
sc:70210@2026Q3 with OTD, so dedup blocks it) → "calculated tightly … 29.00" → final. Stacking
spends a claim slot without a matching drop. Stack line: 1 miss; `rfq_data_claims_stack` stays off.

## 2026-10-10 — P05 screen 12 plan: replicate F

Differs from screen 11: stack off, i.e. exactly screen 10's `configs/p05-data-claims.json`.
Purpose: confirm 77.23 (28.50) is not a single-sample draw versus 29.00 in G/E.

## 2026-10-10 — P05 screen 12: replicate F — WIN replicated

Run `5918e884-4983-41ae-b5b3-44c36a7fe366`, session `d48049c4678d0466`: **77.23**, sup:70210
28.50/35/30, 10.8 s, zero timeouts; transcript identical to screen 10 (OTD → "clarified
internally … 28.50"; PPI-D351 → "as low as I can go … 28.50 final"). F 2/2.

Decision / merge verdict: merge candidate = `configs/p05-data-claims.json` (async runner;
hold + rival offer + rival history + undercut re-anchor + `rfq_data_claims`), 77.23 ×2, zero
timeouts, lead 35 d (≤42), 30 d payment, no 56 d counter, no 14 d / early cash. All new
flags are opt-in; defaults unchanged. Drop: stack (1 miss), standalone re-anchor (tie, kept only
as F's carrier). 70210 states 28.50 is its floor; remaining gap to ~.92 (≈EUR 27.1) is not
reachable by more claims on this path. Next untested lines: 42 d lead time traded for price with
70210, and the teammate's 24-month commitment (both price-for-term trades, none screened).
Sessions in this task: 7 (2b8fbe32, 69acb4ae, 2ffdd9c5, a7298b34, 6f46f019, d48049c4 completed;
09f597f1 expired, launched by a parallel worker in this worktree) plus 1 inherited expired
(6c3717e8). Shared-team quota also fell from other teams' P05/other runs during this window.
Validation: `pytest -q` 382 passed, 1 known failure (preflight); ruff clean.


## 2026-10-10 — Restore the measured P18 package baseline

Recovered original agent-visible thread for owned session336d373e78ee87f1
(score0.4530612521, final5.40/90days/24months/AS-14404 deadband0).
The previous best was not in local run manifests and had been overlooked when
evaluating the0.4195698792 clause-variant candidate.

Existing configs/package-advice.json with estimates={} and meso=false reproduces
all FIVE buyer messages, term sheets and final acceptance exactly on that history.
configs/retained-package-policy.json provides those exact factory kwargs. Runtime
logic is unchanged; no case-specific prices or new flags. The original thread is
an agent-visible regression fixture. In particular, clauses are not accepted into
our counters early; the supplier's indexed standing offer can still be accepted.

Plan: one hosted confirmation via negotiator.agent:configured_agent from own
budget24/30, reserve40. This protects a historical gain; it is not a new best-of
score or proof of unseen-case performance. No default changes or main merge.

Validation:371 tests passed, only the known pre-existing claim-data preflight
test failed; Ruff passed. The new exact historical replay passed.

Hosted confirmation: b2922dc3-6036-4a59-9c29-c75afc4af0e2,
sessione7f60b71102745a0, sourced070c01. Score0.4530612521, zero timeouts,4.11s.
All11 original messages (body, terms, refs, actions, statuses, claim results)
match the recovered historical thread exactly; likely deterministic/cache reuse.
Retain this policy over the0.4195698792 clause-variant config. Delta+0.0334913728
on P18, equivalent+0.0033491373 on ten-case mean. No new historical-best claim.
Own budget24/30;6 remain. Result uploaded to lab automatically.


## 2026-10-10 — P02 in-session supplier-cost posterior (branch `codex/score-push-fullcost-rel`)

Hypothesis (coordinator): the instant accept of 366.23 / 90 d / CU db5 is runtime evidence that the
supplier's cost sits below the public prior midpoint 374.95, so the cost target should adapt.

Offline (no session; `/tmp/fc2/p02_post.py`, public dossier prior fc ~ U[356.20, 393.70]):
- Likelihood: the supplier accepts an offer worth v to it (`supplier_value`) iff v >= fc·(1−s),
  s ~ U[0, s_max] (how far below full cost it will sell). 366.23/90d is worth 361.35 to it.
- Posterior after an accept at 366.23, and the E[C]-optimal price on the same package:
  s_max .10 → E[fc] 370.3, opt 362.10; .125 → 371.6, 363.05; **.15 → 372.3, 363.65**; .20 → 373.1,
  364.35; .30 → 373.8, 365.00. The accept is weak evidence. The supplier also sold the same package
  at 349.37 in 5eccc847 (worth 344.71 to it), so acceptance alone does not bound fc from below.
  It only says s is large (≥ 6 % at fc 366.7).
- Score range at fc points (local model; hosted was ~.026 below local at 366.23). Price 363.37 vs 366.23:
  fc 356 +1.25/+0.89, fc 362 +1.10/+0.86, fc 366.7 **+0.74/+0.63**, fc 375 −0.47/−0.34,
  fc 385 −2.36/−2.17. Wrong-posterior risk: each EUR 1 below the relationship optimum costs ~.04
  score at fc ≈ 375 and ~.05 at fc ≈ 385. A refusal-driven posterior would also over-concede: one
  counter at 363.37 lifts E[fc] to 382 and the optimum to 375. So refusals may only bring us back to
  the prior optimum, never above it.
- The clause db5 package caps the score at ≈ .76 local even at the best price (~361). **.85 is not
  reachable on this package**. No-clause 90 d is floored by the supplier at 373.65 (.29).
- P10: not applicable. The margin at 31.80 is ≈ 23 % ≫ 10 % sustainable, so the relationship term
  (and hence fc) does not bind above ≈ 27. Whether 31.80 is a bluff is a reservation-price question,
  not a cost-posterior one. Countering a final offer has caused `walked_away` before (D02, line ~264).
  No P10 session.

What differs from previous P02 attempts (5eccc847 cost-driver, p02-cost-target 366.23 → .5993):
opt-in `cost_target_posterior` (s_max 0.15, `configs/p02-cost-posterior.json`). Same package
(90 d / CU db5). It opens at the self-consistent price p = argmin E[C | refusals, p accepted]
(**363.37**) instead of the prior optimum 366.23. If the supplier refuses, it rises toward the prior
optimum, never above it. It accepts a supplier sheet on our package at or below that price.
Expected: accept → hosted ≈ .70 (+.10). Refuse → back to 366.23 (≈ .60).
Plan: 1 P02 screen, repeat once if ≥ .62. Max 2 practice sessions.

Results (source `1cae3b0`, `configured_agent` + `configs/p02-cost-posterior.json`, estimates/MESO off, serial):

| run | session | score | terms | rounds | timeouts |
|---|---|---|---|---|---|
| c18148c9 | 936622ab15fb9214 | **0.7115** | 363.37 / 90 d / CU db5 / 12 m | 1 (instant accept) | 0 |
| 887281c9 | 7874cdcfaa174eb6 | **0.7115** | identical | 1 (instant accept) | 0 |

- Hosted breakdown: price 2,220,190.70, payment −14,801, index_risk 17,762, quality 1,191,
  relationship 24,834 (was 12,647 at 366.23). +.1121 vs the .5993 best, n=2 identical.
- Full transcript read: the supplier agreed in round 1 with "Our price reflects our costs". No refusal,
  so the posterior was never updated after the opening. The instant accept at 363.37 is a second accept.
  Under the same model it lowers E[fc] further, but this agent stops after an accept (close).
- Not reached: .85. This package is capped near .76 local. A deeper next step (lower s_max → ~361) is
  worth about +.02–.04 if fc ≈ 366.7, and loses ~.04/EUR if fc ≥ 375. Not screened.
- Sessions: 2 practice (quota 174 → 176 used/600 at start/end of this block; other agents share it).
Decision: P02 opt-in `configs/p02-cost-posterior.json` is a replicated win (.5993 → .7115). Defaults unchanged.
P10: no session (see the offline note above).

## 2026-10-10 — P07/P11/P01 score push (branch codex/score-push-p07p11)

- Code: opt-in `longer_tenor_types` (cost-equal longer `contract_months` tie-break + no free
  tenor concession) and `standard_payment_types` (adopt quote-standard `payment_days` if legal;
  protect it in free concessions/package switch). Configs: `p07-longer-tenor`, `p07-standard-payment`,
  `p01-standard-payment`, `p11-chargeback-zero`. Tests: `tests/test_tenor_payment_policy.py`.
- Practice runs (configured_agent, 0 timeouts each):
  - P07 longer-tenor `8daf33e5` / `064283abb3864b33`: 0.7405 (5.42, 90d, 36m; final at r5). Drop
    (worse than 0.7430; also the rejected 36m-without-gain pattern).
  - P01 standard-payment `b8875ca5` / `dff8db6b184aa534`: **0.9602** (133.70, 30d, eff 2027-04-01;
    relationship 9.4k vs ~larger at 90d). Repeat `0171c5d9` / `8ff60c359f65cef7`: **0.9602** identical.
    Winner (+0.032 vs 0.9279).
  - P11 chargeback-zero `9cc1cbb5` / `294733b34a3e8667`: 0.7099 (45.50, 300ppm, cb 0) = best. Supplier
    floor 45.50 at r4; holds through r7, only faster payment (fixed term) moves it. Drop.
  - P07 standard-payment `b9c3510b` / `511eafb58b9545bf`: 0.7430 (5.38, 60d, 24m) = baseline; flag
    no-op (no quote standard parsed); supplier declares final at r5. Drop P07.
- Sessions consumed: 6/12. Verdict: merge `p01-standard-payment` (`standard_payment_types:
  ["price_increase"]`); note it also affects P02 (owned elsewhere) if adopted globally — scope to
  P01 owners' review or verify P02 before promoting.

## 2026-10-10 — P07/P11/P01 line stopped (reconcile only, no new sessions)

- Line stopped on request (overlap with another team agent). No new sessions started by this worker.
- Reconciled run `2406aa57` (P07 deep anchor `anchor_by_type bundling 0.2`, session
  `1a25cd75923030db`): it was left `running` after its attempt completed. Session verified owned and
  ended; collected thread detail (0 timeouts), marked completed, `lab sync` ok. Score **0.7015**
  (5.48, 90d, 24m). The supplier declared final at r3 after a 4.59 opening. Drop deep anchor.
- Unlogged earlier run `c6416c3b` (P07 bundling OTD-scorecard evidence, session `8b8354f07cd83a87`):
  **0.7470** (5.41, 90d, 24m, final at r5, 0 timeouts). That is +0.004 vs 0.7430 at n=1, within noise; not repeated.
- Previous worker total: 8 practice sessions. Branch is behind origin/main (memory/model_assist), so
  rebase before any merge. Merge candidate: `p01-standard-payment` only (0.9602 x2).

## 2026-10-10 22:xx — P07 bundle-volume argument (hypothesis, before screen 1)

- Prior P07 work reviewed (read-only): main `LOG.md`/runs (imports `af00461c` 0.7340, `d1b5e17f`
  0.7430), `origin/codex/benchmark-goal-20261010` (no P07 entries), this branch (anchor 0.7015,
  tenor 0.7405, std-pay 0.7430, OTD evidence 0.7470). Teammate MESO/estimates/evidence not repeated.
- Diagnosis: every run concedes ~0.04-0.08/round from 5.59-5.60 to a round-5 final at 5.38-5.43,
  whatever the terms. Our messages never mention the bundle itself; the only cited fact (OTD) was
  "verified, does not change our calculation". Post-hoc only (never used at runtime): 0.81 implies
  a final ≈EUR 0.10/unit lower (≈5.31 at 90d/24m).
- Difference: new opt-in `bundle_volume_types` adds a cited, deterministic volume argument from
  public data only: kit memo quantities x need (2.07 M pcs/yr), supplier's current `sourcing` quota
  -> 1.308 M pcs/yr moved from other suppliers, latest `fc:` forecasts for the two parts moving most,
  and the supplier's own `idle_capacity` note (doc M3). Terms/prices/closing unchanged (unit test).
- Why it could work: a volume/capacity reason is the bundling lever (playbook; trait idle_capacity
  "volume fills capacity -> price"); the supplier responds to verified data it values, OTD is not it.
- Config `configs/p07-bundle-volume.json` = candidate + `bundle_volume_types: ["bundling"]`.
  Pass: > 0.7470 with 0 contradicted claims, 0 timeouts. Budget: 10 sessions for this line.
- Screen 1 `2320ed30` / session `00e07274bb4eaa48` (+1 run `31272ed7` failed pre-open, HTTP 401
  from missing env, no session opened): **0.7535** (5.40, 90d, 24m, final r5, 0 timeouts). Supplier
  "checked the volume change data; it holds" (no contradiction) but "already taken into account";
  concessions 5.59→5.50→5.44→5.40. Best P07 so far (+0.0105 vs 0.7430, +0.0065 vs OTD), n=1.

## 2026-10-10 — P07 concession speed (hypothesis, before screen 2)

- Pattern over all 5 P07 traces: supplier step ≈0.8× our previous step (0.11→0.09, 0.07→0.06,
  0.05→0.04), and it declares final at r5 (r2-r3 after a deep anchor). Our linear schedule
  `k/rounds` with rounds=5 still has ~0.12 of its own room left when the supplier's final arrives,
  so the supplier's reciprocal moves are cut off. Never tested: anchor depth was tested (0.2 → early
  final, worse), the schedule length never was.
- Difference: new opt-in `rounds_by_type` (bundling: 3); same 5.05 opening, larger early steps,
  so the supplier gives more reciprocal room before its final round. Bundle volume stays on.
  Prices still come only from our C schedule of quoted terms; no hidden outcome is used.
- Risk: under a pure time-based supplier schedule we only pay more. Pass: > 0.7535.
- Screen 2 `01cf4cef` / session `8dc700cdef9319e6`: **0.7145** (5.46, 90d, 24m; supplier "agreed"
  at our r4 5.46; 0 timeouts). Ours 5.05/5.23/5.36/5.46 vs theirs 5.59/5.52/5.46/5.46. Drop
  rounds=3. Lesson: the supplier's end point tracks our last offer (slow schedules: final ≈ our
  r4 + 0.11-0.12), not a fixed floor reached by reciprocity.

## 2026-10-10 — P07 slower schedule (hypothesis, before screen 3)

- Difference: `rounds_by_type: {"bundling": 10}` (rounds 5 → 10; steps ≈0.054 instead of 0.108),
  with bundle volume on. Our r4 is ≈5.21 instead of 5.28. If the supplier's final stays ≈ our r4
  + 0.11, it lands ≈5.32-5.34 (needed for ~0.78-0.80). Supplier still finals at r5; after that we
  keep the existing final-accept check (no new closing logic). No hidden outcome is used.
- Risk: the supplier holds 5.40+ and we accept the same final (≈0.75), or it walks (p_walk guard unchanged).
- Screen 3 `5a3a827d` / session `920807c3a03c6ed2`: **0.7145** (5.46; ours 5.05/5.11/5.15/5.19, theirs
  5.59/5.54/5.50/5.46 final; 0 timeouts). Slower is as bad as faster: both supplier step and final
  depend on our steps. Default rounds=5 stays. Schedule axis closed (3, 5, 10 tested).

## 2026-10-10 — P07 answer the volume question + committee path (hypothesis, before screen 4)

- Observation (screen 1): every supplier reply asks "Which volume can you commit to? A binding higher
  volume would help us and can improve the price." We never answered; our reminder repeats volume
  it says it "already factored in". Supplier dossier also has `pricing_committee` (doc M1: changes
  above 2 % need committee approval); 5.59→5.40 is 3.4 %, never addressed. Neither was tested by
  anyone (main LOG, teammate branch, this branch).
- Difference: opt-in `bundle_commitment_types` (bundling). From round 2 the reminder is replaced by
  a direct answer: binding commitment to the case's fixed volume (30000 kits/yr, no more than the
  need; volume is not negotiable) over the offered term (24 m = 60000 kits), all 2.07 M pcs/yr from
  one supplier, 1.308 M moved; plus, from the supplier's own note, a request to put the package to
  its pricing committee. No new IDs, terms, prices or closing logic (unit test). No hidden outcome.
- Why it could work: the supplier's script names a binding volume as its price lever, and the
  committee note names its approval limit; both answer its stated conditions. Pass: > 0.7535.
- Screen 4 `db8102bc` / session `0a624e505af85d00`: **0.7600** (5.39, 90d, 24m, final r5, 0 timeouts).
  Supplier acknowledged both ("appreciate the binding commitment to 30,000 kits", "presented your
  package to our pricing committee") but steps were unchanged (5.59/5.49/5.42/5.39 vs 5.59/5.50/5.44/5.40).
  +0.0065 vs screen 1 is within n=1 noise (seven P07 runs span 5.38-5.48 with similar schedules).
- Checked and not screened (no lever in public data): PPI-C2594 +1.7 % and LCI-C +2.7 % y/y (rising);
  kit at today's PO prices ≈ EUR 5.95, so 5.39 is already below piece prices; no should-cost for
  these parts; 30d alternative (5.52) ≈ 90d at 5.59 in our C (8 %/yr). No local run in any worktree
  beats 0.76.

## 2026-10-10 — P07 repeat of bundle-commit (before screen 5)

- Same config/commit as screen 4 (`configs/p07-bundle-commit.json`). Purpose: separate signal from noise
  before proposing a merge; no behavior change. Pass to keep: ≥ 0.7535 again.
- Screen 5 `97f6d4cc` / session `c3383857201b8946`: **0.7600** again (identical path 5.59/5.49/5.42/5.39,
  0 timeouts). Reproducible: +0.017 vs 0.7430 baseline, +0.013 vs OTD evidence.
- Line total: 5 practice sessions opened (screens 1-5) + 1 failed run `31272ed7` (HTTP 401 before
  open, no session). Budget 10 → 5 used, 5 left.
- Verdict: merge candidate `configs/p07-bundle-commit.json` (`bundle_volume_types` +
  `bundle_commitment_types` = ["bundling"]); bundling cases P07 and P15 are affected; P15 is unscreened, so verify it (or its owner) before promoting globally.
  Drop `rounds_by_type` (3 and 10 both 0.7145). 0.81 not reached: the supplier's ladder (≈0.20 total
  after its first reply, final at reply 4) did not respond to volume, commitment, committee, or
  schedule changes; the remaining ≈0.08/unit needs a lever not found in public data.

## 2026-10-10 22:55 — score-push v2: merge, interference check, sandbox, ten-case confirmation (MEASURED HOSTED PRACTICE, 10 sessions)

- Main merge: origin/main 0ffb8c0 merged into codex/score-push-integrate (opt-in `multi_supplier_anchor`, lab UI);
  642 passed, ruff clean, offline replay unchanged (P01/P02/P04/P07/P08/P18 exact). Merged to main as c434fad.
- v2 branch codex/score-push-v2 = integrate + origin/codex/score-push-p05 (a913ac3) + alt-p18-buyer-window
  (b354f99, fact-keyed recent index windows) + score-push-fullcost-rel (457c813, cost posterior) +
  score-push-p07p11 (7a9f20d, bundle volume/commitment). `rounds_by_type`/`anchor_by_type` merged but unused.
- configs/score-push-v2.json = score-push.json + rfq_undercut_reanchor, rfq_data_claims,
  recent_index_window_types (all single-supplier types), cost_target_posterior 0.15, bundle_volume_types and
  bundle_commitment_types [bundling]. Run wrapper configs/score-push-v2-run.json. Runtime commit 536959b.
- Offline interference (v1 vs v2 full messages on run b9ad733d transcripts): only P02 (opening 366.23 -> 363.37,
  same as posterior runs), P07 (kit volume + commitment text), P18 (AS-14404 / PPI-C2431 recent windows) change.
  P01/P03/P04/P08/P10/P11 identical; P08 excluded by hedge, P02 by rising copper. P05: 11 snapshots, v2 decisions
  identical to configs/p05-data-claims.json (recent windows never fire on RFQ; no duplicate data claims).
- Tests 678 passed, ruff clean. Sandbox 8b3a4efe: D01 .9192 x2, D02 .5239 x2 (identical to v1 511a2526).
- Practice 6b162c54 (10 sessions, 0 timeouts, 10 deals, all must-haves ok): P01 .9602, P02 .7115, P03 .8998,
  P04 .8604, P05 .7723, P07 .7600, P08 .5930, P10 .6551, P11 .7902, P18 .5200. Mean .7522 = best-per-case mean.
- Risks: bundle commitment untested on P15 (bundling, not practice); every v2 lever validated on one case;
  supplier side appears deterministic so repeats test reproducibility, not robustness.

## 2026-10-10 — Close mean85 experiment branches; retain ordering fix only

User requested merging or closing this chat's branches. Seven hosted sessions were used
from the authorized 50: one P08 open-book probe and six P10 screens. All have original
completed outcomes and zero timeouts. No P04/P11 hosted session was started.

- P08 open-book run5b7c832f/sessionba461b3457a3773f:0.4822863008 versus0.5929541836.
  Supplier declined detailed cost disclosure and settled5.41 instead of5.31; reject.
- P10 evidence run e52fa461/sessionaa60cb837f218a98:0.5546564482. A real integration
  bug put evidence refs on a move before the advisor; refs caused package advice to skip,
  leaving42-day delivery. Source7442289 defers serial evidence until after package selection.
- P10 corrected-order run f0195237/session06fe3a0014016d96:0.6550995999, restored
  baseline31.80/56days/24months; the verified delivery fact itself produced no gain.
- Committee request1c06d18576134bd7, moderate anchorb962151bc046a5fb, and binding
  clarificationc52f869e9ac3cbad each tied0.6550995999; reject strategy changes.
- One final-counter screen46270b1deaea0d4a ended with score0.0; reject that risk policy.

Merge only the evidence/advice ordering fix and its regression test onto current main.
No new strategy flag or experimental config is promoted; existing v2 settings remain intact.
Close codex/mean85, codex/mean85-capacity and codex/mean85-quality. Their source bundle,
original runs, journals, traces, budget and logs are preserved outside the archived worktrees
in experiments/loop/mean85-closed-20261010 in the primary checkout. The 0.85 goal is not achieved.

Cleanup merge validation on current main: 686 passed, 2 skipped in90.38s; Ruff passed.
No new hosted sessions were consumed for cleanup. All seven owned sessions were confirmed
ended through the owned-session API. The retained fix restores supported feature composition;
it is not a new score improvement or a fresh full-suite evaluation.

## 2026-10-10 score-push-v3 (integration, 0 practice sessions)

- Config `configs/score-push-v3.json` = v2 minus quality `lower_chargeback` preference, plus
  `fast_payment_types: [price_increase]` (P01 .9702 x2, ported from `codex/score-push-small` f882d18 —
  fast-payment code only; `multi_year_tenor_types` and `evidence_after_advice` not ported) and
  `value_swap_types: [quality]`, holds 1, split 0.5 (P11 .8771 x2, `codex/score-push-behavior` a0b6665+2e40805;
  committee escalation f1e7e3d not ported).
- Offline replay v2 vs v3 on the v2-confirm transcripts of all ten cases plus the winning runs: decisions differ
  only on P01 (payment 30→14) and P11 (value swap); v3 reproduces the P01 and P11 winning transcripts with
  0 diffs; P03/P04 (and the P04 v3-l1b regression run) are unchanged by dropping `lower_chargeback`.
- `negotiator lab run` now fails loudly when `--data` is not a directory and exports it as `ARENA_DATA`.
- `tools/compare_breakdown.py` merged from `codex/score-push-fullcost-rel` (offline diagnostic).
- Projected mean .7619 from per-case validated scores; not a fresh ten-case run.

## 2026-10-11 — Supplier workspace (interface only)

- Intent: make saved negotiation evidence accessible by supplier, with attributable
  simulation savings and visible policy/memory provenance.
- Isolated branch: `codex/supplier-workspace-20261011`, based on main `a655f3d`.
- Added `/workspace` and authenticated read-only projections over existing saved runs
  and campaigns; no negotiation policy/config changes and no hosted sessions or model calls.
- Seven new workspace API/metric regressions passed. Automated desktop/mobile browser
  checks passed on a separate local copy of saved project data; no JavaScript errors.
- Savings and record boundaries, remaining controls and full verification procedure:
  [Supplier workspace](../docs/22-supplier-workspace.md).
- Full local suite: **709 passed**, full Ruff passed, 22 existing frontend checks passed.
  The first full run had one async simulator timing failure (708 passed); its isolated
  rerun and the second full run passed. Validated all 15 supplier pages against a local
  copy of the VM backup (384 deduplicated sessions).
- Browser checks additionally cover environment switching and supplier deep-link reload.
  Current runners primarily upload conversation evidence at completion; per-message
  streaming and policy editing remain follow-up work. No score gain claimed.
- VM backup passed integrity check before deployment; rollout result is recorded in
  the shared project handoff and local deployment evidence.

### 2026-10-11 — Supplier intelligence workspace (no Arena experiment)

- Added Tacto-inspired orange/neutral styling and a supplier knowledge graph across
  saved runs/agent configurations, supplied facts, parts, performance and news.
- Dataset fingerprints isolate new releases and repeated IDs. Source times, citations,
  conflicting evidence and unregistered versions remain explicit. Ingestion enriches
  supplier/part master metadata and supports dataset labels and freshness checks.
- External news/company feeds are an explicitly non-working interface concept;
  synthetic suppliers are not searched online. Runtime memory/policy is unchanged.
- Focused graph/workspace/learning tests and local Chrome desktop/mobile checks passed;
  full regression validation and VM rollout recorded in the deployment evidence.

### 2026-10-11 — Supplier brief and readability (interface only)

- Added source-linked supplier history briefs, structured-offer recaps, remembered facts,
  suggested approaches and next steps. Analysis is isolated per dataset and arena.
- Reworked chat history with session search, outcome/role filters, expandable messages,
  offer changes and direct links from report evidence to original messages.
- Simplified the default view and hierarchy using official Impeccable guidance; retained
  the existing orange design. No new framework, model calls or hosted sessions.
- New reports are deterministic projections, not runtime policy changes or measured
  negotiation improvements. Full suite, browser checks and VM deployment evidence are
  recorded in the project handoff and supplier workspace documentation.
- Validation before publish: **722 tests passed**, full Ruff passed and **22 frontend
  checks passed**. Local desktop/mobile browser checks passed with zero JS errors.

### 2026-10-11 — Five random V6 supplier intelligence practice runs

- Hypothesis: an exploratory five-case screen would show ended, valid practice outcomes
  while exposing model admission and fallback behavior. This was not a paired comparison.
- Tracked lab run `56309be0-e434-4d95-a2f3-faa5c14cad94`, using the local dirty
  `codex/v6-supplier-intelligence-plan` candidate at base commit `279f7a8348f4f94f0de650cb5f990aeaff794ab4`
  and recorded patch SHA-256 `9c33af4821a342cb4c279acdf0cea73ce7674f217410ebca791456d516ef19f1`.
  Config: `configs/score-push-v6-all-cases.json` as `PackageAgent.policy`, auto runner
  (all selected cases used serial), Sunday release overlay, OpenAI `gpt-6-sol`.
- Five distinct cases were uniformly sampled without replacement from the ten hosted
  practice IDs: P03, P10, P04, P07, P08. Ceiling and actual use: five Arena sessions,
  one repetition per case. Authoritative practice quota moved from 210 to 205 of 750.
- Original outcomes, in sampled order: P03 **89.98%** (7 rounds), P10 **55.47%**
  (2), P04 **86.04%** (4), P07 **74.70%** (5), P08 **70.36%** (5).
  Mean across this sample: **75.31%**. All five ended as valid deals, with must-haves
  satisfied and zero recorded timeouts or attempt errors.
- The shared per-session model ledger recorded 11 calls in total. P03/P10/P04 used
  three calls each, P07 two, P08 zero. All admitted strategy decisions kept the
  deterministic package. P03 rejected one strategy response for
  `quotation_without_constraint`; P10 rejected final advice for
  `unsupported_citation`. Accepted buyer prose appeared in four cases.
- Lab sync reported one upload and zero failures. Decision: retain this as an
  exploratory screen only. No baseline was run, no causal score gain is claimed,
  and the shared recommendation was not changed. P10's 42-day, 33.80-unit close
  and final-advice citation fallback merit inspection before any separately
  authorized comparison. Original attempt details and journals are in
  `experiments/runs/56309be0-e434-4d95-a2f3-faa5c14cad94/`.

### 2026-10-11 — Source-linked alternative and validation repair (0 new sessions)

- Hypothesis: admitting explicit supplier alternatives with checked fields, then
  giving a rejected suggestion one separate validation-model review, reduces
  avoidable deterministic fallbacks without bypassing economic or dispatch gates.
- The saved P03 and P10 original model answers were replayed locally against their
  original supplier threads. P03 now selects the legal 60-day, EUR 392.48 buyer
  counter; P10 selects the legal 56-day, EUR 31.90 buyer counter derived from a
  quoted 54-day supplier alternative. No supplier response or new score is inferred.
- A `validation-repair-v1` model role is called once after a semantic rejection or
  primary provider failure, using a separate strict schema and the same final
  decision checks. The session ledger reserves one six-second repair allowance;
  an independent endpoint is optional. Tests cover successful repair, invalid
  repair, provider-timeout takeover, risk rejection, source fields and budget
  charging. The prior all-case policy values and hosted run are unchanged.
- Focused tests: 66 passed. Full regression suite: 994 passed, 2 failed solely
  because the `uv` executable is absent in this environment; those two lab
  subprocess tests invoke `uv lock --offline`. Ruff passed. No Arena sessions,
  hosted provider calls, publication or recommendation change for this revision.
- Decision: retain as a local candidate pending an explicitly budgeted hosted
  comparison. The validator cannot guarantee a safe counter when source support,
  time, budget or provider availability is missing. Candidate identity:
  `9c078e79ea316655daa8cb7877d11643abc0125d73847a34c37dd75d9df8644b`
  in `experiments/v6-validation-repair-source-manifest.json`.

### 2026-10-11 — Full ten-case hosted practice screen of V6 validation repair

- Hypothesis: the committed V6 candidate would complete all ten hosted practice
  cases with valid outcomes while exposing remaining model fallback paths. This
  was one exploratory session per case, not a paired comparison or promotion test.
- Tracked Lab run `f69d2cba-c6ca-4544-941f-38cb72f63933` used clean commit
  `ae4990f341a7b10e96804b2a5b9f8c31698fbb87`, opt-in policy
  `configs/score-push-v6-all-cases.json` SHA-256
  `3e526e4ad6c691c37ef49a1d9032dcb29096a1631cc66f95fb0f3752b51e6779`,
  Sunday release overlay, auto runner and `gpt-6-sol`. The combined data
  fingerprint was `eccf11a79ba1d0afcbc4c839eaddf3e1335c3790cc84da8d47ee4272d15988ad`.
- Preflight confirmed the ten hosted IDs, zero open practice sessions and
  201/750 remaining. Exactly ten sessions opened, one each for P01–P05,
  P07–P08, P10–P11 and P18. Final authoritative quota was 191/750 remaining.
- Original scores: P01 **99.08%**, P02 **73.51%**, P03 **89.98%**,
  P04 **86.04%**, P05 **81.36%**, P07 **74.70%**, P08 **70.36%**,
  P10 **64.73%**, P11 **87.71%**, P18 **58.70%**. Mean **78.62%**.
  All ten attempts completed with `ended: true`, `must_haves_ok: true`,
  valid deals and zero recorded Arena timeouts or attempt errors. P05 used
  the async RFQ runner; the others used serial.
- The shared model ledger recorded 18 calls: ten accepted model-written buyer
  responses, five strategy calls, one final-advice call, one validation-repair
  call and one buyer-writer call that timed out. P10's admitted final advice
  selected an exploratory counter and closed at 64.73%; its earlier sampled
  P10 result was 55.47%, but single runs do not identify a causal gain.
- P03 still fell back on one strategy decision: the primary provider returned
  empty output, then the validation model proposed an alternative rejected as
  `quotation_without_constraint`. Its later buyer-writer timeout also used
  deterministic prose. Thus the validator was invoked as intended but did
  not always produce an admissible counter. P08 and P18 made no eligible model
  calls under the configured gates.
- The current run was individually uploaded to the shared Lab successfully.
  Original evidence remains in the ignored `experiments/runs/` directory;
  private provider request/response files were not committed. Decision:
  retain this as an exploratory screen, do not promote or claim final-case
  readiness, and investigate the P03 repair rejection locally before any
  separately authorized hosted retest.

### 2026-10-11 — Two-wave final rehearsal and hosted 403 wait (LOCAL SIM)

- Hypothesis: the committed V6 final runner starts each case once after its
  wave opens, follows `seconds_left`, closes before the cap, and remains alive
  across the break. This is a mechanics rehearsal on scripted demo suppliers,
  not evidence about hidden final negotiation outcomes.
- Pulled arena kit `tacto-ai/negotiation-arena-kit` to `273a9bc` and synced
  `starter-kit/` with its lockfile and simulator extra. Ran its new
  `arena-sim serve --final-rehearsal` on localhost, using the supplied package
  and six demo cases across two waves. V6 source was clean commit `ba15fff`;
  policy was the opt-in `configs/score-push-v6-all-cases.json`, auto runner,
  Sunday overlay. Simulator keys stayed local; no hosted practice or final
  session was opened by these rehearsals.
- First pass used the simulator's default 240-second cap (120-second initial
  wait, 30-second break), with the kit `arena run --set final --waves 2`
  and V6 runner on separate local teams. Both waited through initial 403s,
  started three cases per wave, and returned after wave 2 closed. All six V6
  cases ended as valid deals with no `wave_cap`; mean simulator score 14.26%.
  Four V6 decisions immediately invoked the time guard and accepted opening
  offers: `TIME_GUARD_ROUNDS=2` × `ROUND_ESTIMATE_S=120` equals the shortened
  240-second wave. The kit's naive runner scored 57.0 points per wave in this
  short-cap pass. These scores describe different policies on a scripted sim.
- Second pass used the actual 480-second cap (60-second initial wait,
  30-second break) with V6 only. It waited for both wave starts and exited
  after the second cap. All six original cases ended as valid deals with
  `must_haves_ok: true`, no `wave_cap`, and one session start per case.
  Four cases took the serial path and two the async path. Scores: wave 1
  R1-S01 **69.55%**, R1-S02 **86.09%**, R1-S03 **88.56%**; wave 2 R2-S01
  **69.55%**, R2-S02 **68.20%**, R2-S03 **88.56%**. Mean **78.42%**.
  Serial cases made four or five offers before accepting; their results
  appeared in the trace when the two-wave run returned. The two async
  cases reported zero supplier-thread timeouts.
- A separate one-minute read-only hosted final preflight saw 403 before
  launch and after intentional stop; the V6 runner remained alive for the
  full minute and the hosted final session count stayed **0 → 0**. The
  earlier authorized ten-case practice screen supplied the practice-path
  check; this preflight consumed no additional practice quota.
- Evidence: local traces under `/tmp/v6-final-rehearsal-runs/` and
  `/tmp/v6-final-rehearsal-8min-runs/`, and hosted wait log
  `/tmp/v6-hosted-final-wait.log`. Decision: preserve the 90-second kit
  close constant and existing V6 time guard; use the eight-minute cap for
  policy rehearsal because the four-minute shortcut invokes that guard at
  wave start. The simulator's quick scripted replies do not test long
  provider or supplier latency, and no final policy promotion follows.
