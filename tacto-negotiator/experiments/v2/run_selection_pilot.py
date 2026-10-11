"""Explicit offline fake-response composition; no provider transport or credentials."""

import argparse
import asyncio
import hashlib
import json
from pathlib import Path

from negotiator.v2.core.serialization import semantic_hash
from tests.v2.integration.test_grounded_selection import decision

from .evaluate_selection import evaluate


async def run(output):
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((root / "tests/fixtures/v2/selection-pilot.json").read_text())
    schedule = json.loads((root / "tests/fixtures/v2/selection-pilot-fake-responses.json").read_text())
    heldout = [e for e in manifest["examples"] if e["split"] == "held-out"]
    digest = hashlib.sha256(json.dumps(heldout, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if digest != manifest["held_out_sha256"]:
        raise ValueError("held-out subset changed")
    fake = {r["id"]: r for r in schedule["responses"]}
    relationship = json.loads((root / "tests/fixtures/v2/relationship.json").read_text())
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for example in manifest["examples"]:
        universes = []
        scripted = fake[example["id"]]
        for arm in ("minimum", "direct", "grounded"):
            trace, _ = await decision(
                relationship,
                example["text"],
                arm=arm,
                amount=example["amount"],
                choice=scripted["choice"],
                kind=scripted["kind"],
                fault=scripted["fault"],
            )
            trace.verify()
            universes.append(semantic_hash(trace.evaluations))
            selected = next(
                i for i in trace.evaluations.items if i.candidate.candidate_id == trace.decision.candidate_id
            )
            contents = selected.candidate.contents
            if contents.kind == "question":
                action = contents.question_id
            else:
                bindings = {t.field: t.value for t in contents.packages[0].bindings}
                action = (
                    "delivery"
                    if bindings["lead_time_days"] == 49
                    else ("commitment" if bindings["contract_months"] == 12 else "minimum")
                )
            label = example["id"].replace(":", "-")
            (output / f"{label}-{arm}.json").write_text(trace.model_dump_json(indent=2) + "\n")
            records.append(
                {
                    "example_id": example["id"],
                    "arm": arm,
                    "action": action,
                    "admitted": trace.validation.kind == "valid",
                    "fallback": trace.decision.fallback_code is not None,
                    "fallback_code": trace.decision.fallback_code,
                    "grounded_departure": action != "minimum"
                    and bool(trace.decision.citations)
                    and trace.decision.fallback_code is None,
                    "calls": sum(c.charged_tokens > 0 for c in trace.model_calls),
                    "charged_tokens": sum(c.charged_tokens for c in trace.model_calls),
                    "unknown_usage_calls": sum(
                        c.usage.input_tokens is None or c.usage.output_tokens is None for c in trace.model_calls
                    ),
                    "latency_s": sum(float(c.elapsed_s) for c in trace.model_calls),
                    "batch_hash": trace.evaluations.batch_hash,
                    "trace_hash": trace.trace_hash,
                }
            )
        if len(set(universes)) != 1:
            raise ValueError("strategy arms received different economic candidate universes")
    report = evaluate(manifest, records)
    report.update(
        held_out_sha256=digest, total_model_call_ceiling=2, token_ceiling=2048, model_time_ceiling_s=1, records=records
    )
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "records"}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args().output))
