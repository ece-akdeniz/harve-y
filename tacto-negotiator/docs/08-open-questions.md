# 08 - Open questions for the Tacto desk

Ask at the deep dive or next office hours. Record the answer, organizer name, time, source
and implementation consequence. An empty answer is unresolved, not implicit permission.

Prioritize Q1, Q2, Q3 and Q13–Q16. Continue independent work while answers are pending.

| # | Question | Why it matters | Answer |
|---|---|---|---|
| Q1 | How do the Live Final score and the jury combine for places 1-3? Jury criteria? | Time split between agent and pitch | |
| Q2 | While we wait for supplier A's reply in an RFQ, do threads B/C collect timeouts every 60 s like `arena-sim`? | Scheduler design; test whether concurrent sends queue by session | |
| Q3 | Does the 60 s clock start when the reply is delivered to us, or when it's created? | Latency budget | |
| Q4 | Are FX series (ECB-*) or index windows we choose freely accepted as relevant claims? | Claim bank design | |
| Q5 | Hidden cases: suppliers from the 46 in the data, or new companies with their own `facts`? | Dossier vs. runtime reading | |
| Q6 | Can the supplier's quote PDF standard terms differ from `suppliers.csv` defaults? | Closing-term correctness | |
| Q7 | Are attachments we send (md/csv/json) weighed like claims, or only read? | Whether to attach decompositions | |
| Q8 | Does the number of rounds used matter beyond tie-breaks? | Speed vs. depth | |
| Q9 | When does Tacto stop answering on Saturday night? | Plan questions before then | |
| Q10 | Is the house agent's practice score visible? What is it? | Baseline target | |
| Q11 | Wave themes - one case type per wave, or mixed? | Per-wave policy switches | |
| Q12 | Is using a strong LLM offline to pre-compute supplier dossiers fine? (assume yes: "everything else counts") | Prep pipeline | |

## Additional design-critical questions

| # | Question | Decision affected | Status |
|---|---|---|---|
| Q13 | Are RFQ calls serialized within a session? When does the buyer clock stop for a queued/in-flight request? | Per-thread scheduling and timeout safety | Unanswered |
| Q14 | Does inference/queue time count against the wave cap, and can acceptance queue behind another reply? | Closing margin and pending-request policy | Unanswered |
| Q15 | For prices per 100/1,000 units, are case need/volume already normalized to those price units? | Cost dimensional consistency; compare hosted result | Unanswered |
| Q16 | What criteria select the overall EHL champion, and how do track outcomes feed that decision? | Overall-prize strategy and pitch | Unanswered |
| Q17 | Which source wins if case facts conflict with base/release facts? | Provenance and runtime fact resolution | Unanswered |
| Q18 | After freeze, is restarting the identical runner allowed? May final results/replays be shown without changing slides? | Recovery and pitch operations | Unanswered |

## Answer record

For each response append: question ID; exact answer or clearly labeled paraphrase; organizer;
Europe/Berlin timestamp; source; affected document/module; decision; owner; verification run.
Do not silently substitute organizer answers for measured hosted behavior or vice versa.
