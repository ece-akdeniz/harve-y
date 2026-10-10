# F — Negotiation intelligence research backlog

**Status:** proposed investigations, not implemented strategies or procurement performance claims. [Plan](../21-negotiation-v2-plan-2026-10-10.md) · [Strategy contracts](C-interfaces.md) · [Evaluation](E-evaluation.md).

This workstream does not block M1–M5. First build the grounded capacity loop, then test one isolated strategy hypothesis at a time under the same evidence, economics, validator, runtime and outcome recording. The framework's value is the ability to replace proposal/selection methods without changing those foundations.

## 1. Starting literature and verified relevance

The five supplied URLs were checked against primary publication pages during planning. The short descriptions below are based on publication metadata/abstracts, not a claim of a full-paper replication or validated transfer to our arena. Reading the complete method, assumptions, code/data and licensing is the first task before implementing a paper-inspired treatment.

| Reference | Verified research contribution | Procurement adaptation question |
|---|---|---|
| Bianchi et al., [**How Well Can LLMs Negotiate? NegotiationArena Platform and Analysis**](https://proceedings.mlr.press/v235/bianchi24a.html), ICML 2024 | Platform studies multi-turn resource/trading/price negotiation and sensitivity to behavioral tactics | Can our evaluation detect supplier-agent-specific prompt exploits versus portable commercial improvements? Do not import tactics revealing desperation/urgency |
| Lewis et al., [**Deal or No Deal? End-to-End Learning of Negotiation Dialogues**](https://aclanthology.org/D17-1259/), EMNLP 2017 | Hidden-utility multi-issue dialogue task with dialogue rollouts for considering continuations | Can bounded candidate-level rollouts improve package selection with scarce rounds without treating simulated agreement as real? No training is needed for the first adaptation |
| Chawla et al., [**CaSiNo: A Corpus of Campsite Negotiation Dialogues for Automatic Negotiation Systems**](https://aclanthology.org/2021.naacl-main.254/), NAACL 2021 | Human negotiation corpus with annotated persuasion strategies and strategy recognition | Which utterance labels transfer to procurement requests/refusals/conditional terms, and which need new role/contract labels? |
| Liu et al., [**Scaling Inference-Time Computation via Opponent Simulation: Enabling Online Strategic Adaptation in Repeated Negotiation**](https://proceedings.mlr.press/v306/liu26ef.html), ICML 2026 | Inference-time opponent imitation and best-of-N simulation inspired by smooth fictitious play, tested in repeated negotiation | Do a few procurement turns provide enough repeated interaction to support that opponent model? What happens when role/authority changes? |
| Oh et al., [**MERIT Feedback Elicits Better Bargaining in LLM Negotiators**](https://aclanthology.org/2026.acl-long.1155/), ACL 2026 | Utility-feedback-centered benchmark/metrics and prompting/learning approach to preference alignment and opponent awareness | Which code-derived cost/uncertainty feedback can improve selection without exposing private buyer constraints or relying on inaccessible scoring targets? |

The contributions in the table derive from the linked primary publication pages; transfer questions are our proposed investigations.

Add established automated-negotiation controls before assuming LLM complexity is useful. [Faratin, Sierra and Jennings, Negotiation decision functions for autonomous agents (1998)](https://www.sciencedirect.com/science/article/abs/pii/S0921889098000293) provides a source for offer/counteroffer tactics. [Baarslag et al., Learning about the opponent in automated bilateral negotiation: a comprehensive survey of opponent modeling techniques (2016)](https://homepages.cwi.nl/~baarslag/pub/Learning_about_the_opponent_in_automated_bilateral_negotiation-a_comprehensive_survey_of_opponent_modeling_techniques.pdf) organizes opponent models and their evaluation. Use simple time/behavior and observed-preference models as control treatments; an unknown supplier utility is not a known Nash bargaining input.

## 2. Prioritized research queue

Call counts below are **proposed experimental ceilings**, not measured runtime. Every extra call shares the decision budget and needs inference allowance. Start with zero-call/deterministic controls and one-call interpretation. Reduce candidate count/horizon before increasing the runtime budget.

| ID / priority | Hypothesis and candidate algorithm | Integration point | Observations/assumptions needed | Initial call/latency budget | Required experiment / reject condition |
|---|---|---|---|---|---|
| R0 / P0 | Grounded preference interpretation plus deterministic capacity ranking beats mechanical package repetition | Interpreter + capacity proposal/selector | Requests/refusals/conditions from current reply and valid options; no numerical willingness assumed | One interpreter call, <=8 s, zero selector calls | A–F behavior, labelled grounding, state/restart, then frozen capacity comparison; reject if adaptation increases invalidity/failures or lacks grounded benefit |
| R1 / P0 | Small deterministic issue-premium model improves trade prioritization | Feedback records + proposal/selector bundle | Actual quoted one-field price deltas; multi-field differences stay combined; sparse observations produce intervals/unknowns | Zero model calls after interpretation | Synthetic known-premium suppliers, held-out quotes, ablation vs no model, cost/scenario comparison; reject if it misattributes combined changes or overfits one supplier |
| R2 / P1 | Time/round-aware concession and bounded integrative package search outperform fixed linear concessions | Baseline/proposal hook + CandidateResearch | Authoritative/conservative round/time, legal options, buyer costs; supplier acceptance remains unknown | Zero extra calls; capped candidate count | Compare fixed schedule, conservative deadline policy and issue trades on same fixtures/hosted scope; measure timing and agreement, not just lower asked price |
| R3 / P1 | Clarification chosen by information value reduces rejected trades | Proposal/question candidate + deterministic feedback | Relevant ambiguity and expected possible answers; round/latency costs; known document capability | Zero to one extra model call; initially use deterministic question trigger | Scripted answer/no-answer/refusal scenarios; inquiry-vs-offer ablation; reject if scarce round consumption lowers outcomes or unsupported documents don't change decisions |
| R4 / P1 | Strategy-labelled interpretation improves commercial assessment | Replaceable interpreter using CaSiNo-inspired labels | Procurement-specific reviewed labels; supplier roles, refusal and conditions not covered by generic persuasion taxonomy | Same single interpreter call; no separate classifier service initially | Held-out semantic precision/recall, bilingual/role shifts and downstream decision ablation; reject if more labels do not improve valid behavior |
| R5 / P1 | Relative utility/scenario feedback improves approved candidate selection | Selector with code-derived descriptor projection, MERIT-inspired | Same approved candidate set, observed outcomes, relative costs/uncertainty; no official hidden optimum or target leakage | One selector call <=4 s in addition to interpreter | Deterministic vs model selector and with/without relative feedback; fixed private-data projection; reject if fabricated utility or cost exceeds frozen budget without benefit |
| R6 / P2 | One-step dialogue lookahead improves action choice | Strategy bundle private simulation + CandidateResearch, Deal-or-No-Deal-inspired | Bounded plausible response alternatives; calibrated uncertainty; simulated replies explicitly hypothetical | Begin offline: <=3 candidates x 2 simulated responses; later cap total model calls, not unlimited rollouts | Compare direct ranking vs lookahead at equal call/time spend; held-out real responses/calibration, transport deadline stress; reject if simulated agreement confidence is unsupported |
| R7 / P2 | Online opponent imitation/best-of-N choice helps repeated interactions | Opponent-simulation proposal/selector bundle with namespaced memory | Repeated comparable observations and opponent stability; role changes; insufficient-history fallback | Start offline fixed trace/call budget; live only if <=remaining deadline | Equal-compute best-of-N control, held-out suppliers, adaptation vs reset; reject if paper's repeated-game assumptions do not hold or improvement is cache/agent-specific |
| R8 / P2 | Claim-result and refusal feedback improve evidence/policy ranking | Feedback -> strategic state -> proposal/selection | Known argument-to-claim alignment, relevance/duplicate results, subsequent package observations; no causality inferred from sequence | Zero extra calls first; deterministic counters/preferences | Evidence-outcome ablation, randomized isolated claims when funded, held-out cases; reject if it equates verified with persuasive or punished adverse evidence |
| R9 / P3 | Robust scenario ranking improves relationship-sensitive negotiation | Selection treatment over same scenario-evaluated candidates | Credible cost/rate/basis ranges and estimate provenance; sparse ranges not probabilities | Zero extra calls; bounded scenarios | Nominal-vs-scenario sensitivity and official performance/relationship metrics; reject if pessimistic assumptions force unjustified no-deal or cannot be calibrated |
| R10 / P3 | Account/basket context adds defensible integrative leverage | Evidence relevance/interpretation plus new scoped strategy capability | Correct all-part/account identity, price basis, authorized quantity and commitment | Same bounded interpreter where possible | Separate basket/account fixtures and approval constraints; reject invented future volume or part-to-basket assertions |

R0 is the architectural slice, not a major research implementation. R1–R5 are small bounded extensions. R6–R7 require a full method review, independent computation/latency budget and suitable repeated observations; do not implement them merely because the papers report gains elsewhere. No fine-tuning, reinforcement learning training or persistent cross-session supplier profile is included in the initial roadmap.

## 3. Strategy integration without foundational changes

Preference-based selection, simulation, and adaptive selection all consume immutable NegotiationContext, raw ConversationView, assessment/state revisions, and the same evaluated candidates. They return typed intents and one candidate ID. They can request additional code-generated evaluations via CandidateResearch within the same snapshot/budget. Their model/scenario results are private hypothesis artifacts with source/model provenance, not server events.

Keep observations, standard quote terms, one-field/multi-field deltas and refusal outcomes outside any one interpreter's compressed belief representation. A different interpreter may build a different SupplierAssessment from those records without changing the source store. If a research method needs custom memory, register its strict schema and version within that strategy namespace; the common state store persists the artifact without understanding the algorithm's internals.

Hard boundaries remain unchanged: code produces/prices packages; economics handles all costs and uncertainty scenarios; verifier controls factual assertions; closing coordinator controls accept/walk; validator checks final payload/state; executor owns exact idempotent operation; feedback records actual outcomes. Swapping a strategy does not change the data precedence, endpoint rules or arithmetic to suit the result.

## 4. Research experiment template

```text
Research ID / strategy bundle / contract version:
Paper/method read; primary links; author code/data and license reviewed:
Specific hypothesis and procurement assumption:
Observed vs hypothetical supplier inputs; required history:
Baseline / treatment / equal-compute control:
Candidate/economic/evidence/validator/runtime invariants held constant:
Data/config/prompt/model/source fingerprints:
Local scenarios and held-out split:
Model call/time/token/spend ceiling; fallback and stop rules:
Authorized hosted allowance and complete manifest, or offline only:
Metrics, per-case regression and independence rules:
Results, all failures, uncertainties and generalization limits:
Decision: reject / revise / retain opt-in / scoped promotion:
Evidence links, experiment-log entry and next question:
```

Measure model preference prediction against future quoted behavior when observations permit, not against its own rationale. Track outcome score/cost separately from semantic validity. Compare expensive methods with an equal-inference-spend simple baseline so additional compute is not mistaken for a superior planning algorithm. Do not tune on the held-out supplier set or reuse a single cache-stable trajectory as statistical repeats.

## 5. Open research questions

- Do quoted one-field deltas reflect stable premiums or tactical prices that change with role/round/history?
- How much refusal scope can be reliably inferred from prose, and when is a clarification cheaper than avoiding a useful trade?
- Which adverse drivers should change questions versus price expectations without converting partial cost pressure into a reservation price?
- Does a multi-turn conversation supply enough data for repeated-game opponent simulation, or should its utility be tested only offline initially?
- How does estimate uncertainty change which trade is commercially credible, especially with no executable alternative?
- Which semantic improvements transfer to a held-out supplier/category instead of exploiting a particular hosted role bot?
- Can optional selection/lookahead stay within a real buyer/wave budget after reading/parsing/limiter costs?
- What does additional contract length beyond the evaluated demand horizon mean operationally, even when official buyer cost is unchanged?

These questions are experiments to schedule after a reliable capacity backbone. They are not reasons to expand the foundational architecture or grant the model new action authority now.

## 7. Frozen extension contract; no research implementation in this preparation

Research enters through the existing StrategyProposalPolicy and ActionSelectionPolicy hooks plus read-only CandidateResearch. A future router implements those hooks or selects a vetted registered bundle before the same pipeline. A behavioral model consumes the four assessment collections, cited observations, immutable historical revisions and feedback artifacts; it returns hypotheses or nonbinding intents. It cannot overwrite reported constraints, canonical evidence, candidate economics, standing-offer identity or operation ownership.

Historical learning, behavior estimation, simulated replies, strategy portfolios and research algorithms remain deferred. New treatments get their own schema/config/prompt identifiers and tests. Simulated observations are tagged hypothetical and never become ServerState. Existing core term/evidence/DecisionRecord contracts contain no capacity-policy or provider fields. No generic multi-agent framework or model-chosen plugin loader is needed.

The implementation acceptance criterion for an extension is concrete: substitute a fixture proposal/selection bundle under the same core ports; the recorded-context, official-economic, final-validator and runtime modules do not change. Tests verify batch membership, read-only research budget and record provenance. Before a funded research trial, add specific executable tests to the catalog, independent quality labels, model-output fingerprints and the pre-registered outcome comparison. Preserve the current first-slice policy as the deterministic control.
