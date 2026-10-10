"""Export a local P01 EvidenceContext; no client, session or send operations."""

import argparse
import json
from pathlib import Path

from negotiator.claims import index_relevance, pick
from negotiator.context import build_context
from negotiator.dossiers import load_package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="Unpacked base package root")
    parser.add_argument("--release", help="Optional unpacked release")
    parser.add_argument("--cases", type=Path, default=Path("tests/fixtures/practice_cases.json"))
    parser.add_argument("--out", type=Path, default=Path("/tmp/p01-evidence-context.json"))
    args = parser.parse_args()
    case = next(c for c in json.loads(args.cases.read_text()) if c["case_id"] == "case:P01")
    package = load_package(args.data, args.release)
    context = build_context(case, package)
    context.export(args.out)
    priorities, reasons = index_relevance(context.candidates, case, package)
    selected = pick(context.candidates, set(), supplier_id=case["suppliers"][0], case_type=case["type"],
                    index_priorities=priorities)
    print(json.dumps({"out": str(args.out), "context_version": context.version,
                      "selected": [{"kind": c.kind, "ids": c.ids, "figure": c.figure, "unit": c.unit}
                                   for c in selected],
                      "index_relevance": reasons, "gaps": len(context.gaps),
                      "failed_checks": context.failed_checks}, indent=2))


if __name__ == "__main__":
    main()
