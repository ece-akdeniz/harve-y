"""List saved attempts for cases: score, terms, rounds, per-round sheets.

Usage: python tools/list_attempts.py P02 [P10]"""

import json
import sys
from pathlib import Path

ROOTS = [
    Path("/Users/sametdegirmenci/Downloads/ysamet/tacto-negotiator/experiments/runs"),
    Path("/Users/sametdegirmenci/Downloads/ysamet-run-archive"),
    Path("/Users/sametdegirmenci/Downloads/ysamet-v5/tacto-negotiator/experiments/runs"),
]
for p in Path("/Users/sametdegirmenci/Downloads").glob("ysamet-*/tacto-negotiator/experiments/runs"):
    ROOTS.append(p)
for p in Path("/Users/sametdegirmenci/.codex/worktrees").glob("*/tacto-negotiator/experiments/runs"):
    ROOTS.append(p)


def main():
    cases = {f"case:{c}" if not c.startswith("case:") else c for c in sys.argv[1:]}
    seen = set()
    rows = []
    for root in ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("run.json")):
            try:
                data = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            for att in data.get("attempts") or []:
                if att.get("case_id") not in cases:
                    continue
                sid = att.get("session_id")
                if sid in seen:
                    continue
                seen.add(sid)
                res = att.get("result") or {}
                rows.append((att.get("started_at") or att.get("created_at") or "", data.get("name"), path, att, res))
    rows.sort(key=lambda r: r[0])
    for started, name, path, att, res in rows:
        score = res.get("score")
        terms = res.get("terms")
        print(
            f"\n=== {started[:19]} {att['case_id']} {name} sid={att.get('session_id')} "
            f"score={score} rounds={att.get('rounds')}"
        )
        print(f"    {path}")
        print(f"    terms={json.dumps(terms)} end={res.get('end_reason') or att.get('end_reason')}")
        for sup, thread in (att.get("threads") or {}).items():
            msgs = thread.get("messages") if isinstance(thread, dict) else thread
            for i, m in enumerate(msgs or []):
                who = m.get("from")
                sheets = [s.get("terms") for s in (m.get("term_sheets") or [])]
                act = m.get("action")
                refs = m.get("refs")
                status = m.get("status")
                print(f"    [{i}] {who:8s} {sup} st={status} act={act} refs={refs} sheets={json.dumps(sheets)}")


if __name__ == "__main__":
    main()
