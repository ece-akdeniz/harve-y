"""Reconstruct three development adviser requests; network calls require explicit allowance.

This is a provider-only exploratory probe. The P10 source did not retain the exact
provider request, so every payload is labelled as a reconstruction. No Arena
session is opened, and no request text, credentials or raw provider reply is logged.
"""

import argparse
import copy
import hashlib
import json
import os
import time
from pathlib import Path

from negotiator.advice import CapacityAdvisor
from negotiator.package_advisor import PackageAdvisor, complete


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def payloads():
    root = Path(__file__).resolve().parents[1]
    saved = json.loads((root / "tests/fixtures/p10-capacity-advice-repair.json").read_text())
    cases = json.loads((root / "tests/fixtures/practice_cases.json").read_text())
    case = next(c for c in cases if c["case_id"] == "case:P10")
    variants = (
        ("saved_p10_opening", None),
        ("capacity_delivery", "Our production schedule needs 56 days of lead time for this volume."),
        ("conditional_commitment", "Additional capacity is available only against a binding 36-month commitment."),
    )
    for name, body in variants:
        threads = {saved["supplier_id"]: [copy.deepcopy(saved["messages"][0])]}
        if body is not None:
            threads[saved["supplier_id"]][0]["body"] = body
        for contract, factory, answer in (
            ("legacy", PackageAdvisor, {"selected_id": "keep", "supporting_quote": ""}),
            ("capacity-advice-v2", lambda fn: CapacityAdvisor(fn, concession=.01),
             {"selected_id": "keep", "observations": [], "support_index": -1,
              "acknowledgement": "none"}),
        ):
            captured = []

            def capture(context, timeout, *, _captured=captured, _answer=answer):
                _captured.append(copy.deepcopy(context))
                return _answer

            factory(capture).select(case, threads, copy.deepcopy(saved["scheduled_move"]),
                                    public_notes=saved["public_notes"], remaining_s=60)
            if len(captured) != 1:
                raise RuntimeError(f"cannot reconstruct {name}/{contract}")
            yield name, contract, captured[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="make provider calls")
    parser.add_argument("--allow-calls", type=int, default=0)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output", type=Path, help="write metadata and measurements as JSON")
    parser.add_argument("--env-file", type=Path, help="read local provider settings without recording the key")
    args = parser.parse_args(argv)
    if args.env_file:
        if not args.env_file.is_file():
            parser.error("--env-file does not exist")
        from dotenv import load_dotenv

        load_dotenv(args.env_file, override=False)
    requests = list(payloads())
    expected = len(requests) * args.repeats
    if args.repeats < 1 or (args.execute and (args.allow_calls != expected or args.output is None)):
        parser.error("execution requires --output and --allow-calls equal to the request count")
    report = {"source": "reconstructed P10 development requests; exact original provider request unavailable",
              "mode": "provider_only" if args.execute else "dry_run", "planned_calls": expected,
              "execution_order": "sequential", "transport_setup": "new HTTP client per call",
              "model": os.environ.get("LLM_MODEL") if args.execute else None,
              "effort": os.environ.get("LLM_EFFORT") if args.execute else None,
              "timing_gap": "provider HTTP and response parsing are measured together",
              "calls": [], "requests": []}

    def save():
        serialized = json.dumps(report, indent=2) + "\n"
        if args.output:
            args.output.write_text(serialized)
        else:
            print(serialized, end="")

    for name, contract, context in requests:
        encoded = json.dumps(context, sort_keys=True, ensure_ascii=False)
        report["requests"].append({"variant": name, "contract": contract,
                                   "sha256": _digest(context), "context_bytes": len(encoded.encode()),
                                   "supplier_messages": len(context.get("supplier_messages",
                                                                        context.get("recent_messages", []))),
                                   "candidates": len(context["approved_packages"])})
    if args.execute:
        save()  # own an explicit zero-call ledger before any provider attempt
        for name, contract, context in requests:
            for repeat in range(args.repeats):
                start = time.monotonic()
                row = {"variant": name, "contract": contract, "repeat": repeat + 1,
                       "status": "attempting", "transport": "fresh_http_client"}
                report["calls"].append(row)  # a crashed/unknown attempt still consumes its slot
                save()
                try:
                    result = complete(context, 8.0)
                    row["provider_and_parse_s"] = round(time.monotonic() - start, 4)
                    row["status"] = "ok"
                    usage = result.usage
                    row["usage"] = ({key: usage[key] for key in ("prompt_tokens", "completion_tokens")}
                                    if all(type(usage.get(key)) is int and usage[key] >= 0
                                           for key in ("prompt_tokens", "completion_tokens")) else "unknown")
                    validation_start = time.monotonic()
                    raw = result.response
                    if contract == "legacy":
                        if (not isinstance(raw, dict) or set(raw) != {"selected_id", "supporting_quote"}
                                or raw["selected_id"] not in {"keep", *context["approved_packages"]}
                                or not isinstance(raw["supporting_quote"], str)):
                            raise ValueError("invalid legacy schema")
                    else:
                        CapacityAdvisor._validate(raw, context["supplier_messages"],
                                                  context["approved_packages"], context["scheduled_terms"],
                                                  context["current_supplier_packages"],
                                                  context["public_dossier_notes"])
                    row["schema_valid"] = True
                    row["validation_s"] = round(time.monotonic() - validation_start, 4)
                except Exception as exc:
                    row["status"] = type(exc).__name__
                    row.setdefault("usage", "unknown")
                    row["schema_valid"] = False
                row["total_wall_s"] = round(time.monotonic() - start, 4)
                save()
                print(f"provider probe {len(report['calls'])}/{expected}: {row['status']} "
                      f"{row['total_wall_s']:.2f}s", flush=True)
    else:
        save()


if __name__ == "__main__":
    main()
