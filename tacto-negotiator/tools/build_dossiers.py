"""Build a dossier per detailed supplier and print a compact overview.

Output: experiments/dossiers.json (gitignored). Prototype for negotiator.dossiers.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from _data import connect, package_dir  # noqa: E402

from negotiator.traits import NEWS_TRAITS, NOTE_TRAITS  # noqa: E402

SKIP = {"Holiday shutdown", "New contact person", "ISO 9001 certificate", "Packaging", "Trade fair invitation"}


def main():
    db, root = connect(), package_dir()
    q = lambda s, *a: [dict(r) for r in db.execute(s, a)]  # noqa: E731
    out = []
    for s in q("SELECT id, name, country, category, payment_days, incoterm, abc_class FROM suppliers "
               "WHERE detail = 'full' ORDER BY id"):
        sid = s["id"]
        intel = (q("SELECT * FROM supplier_intel WHERE supplier_id = ?", sid) or [{}])[0]
        news = q("SELECT id, date, topic, headline FROM news WHERE supplier_id = ?", sid)
        sc = (q("SELECT * FROM scorecards WHERE supplier_id = ? ORDER BY quarter DESC LIMIT 1", sid) or [{}])[0]
        late = q("SELECT round(AVG(julianday(paid_date) - julianday(due_date)), 1) d FROM invoices "
                 "WHERE supplier_id = ? AND paid_date IS NOT NULL", sid)[0]["d"]
        hist = q("SELECT date, part_id, type, asked_pct, settled_pct, note FROM negotiation_history "
                 "WHERE supplier_id = ? ORDER BY date", sid)
        notes = []
        for d in q("SELECT id, date, kind, subject, file FROM documents WHERE supplier_id = ? ORDER BY date", sid):
            if d["subject"] in SKIP:
                continue
            f = root / "correspondence" / Path(d["file"] or "").name
            text = f.read_text(encoding="utf-8").split("\n", 3)[-1].strip() if f.is_file() else ""
            notes.append({**d, "text": text})
        traits = sorted(
            {t for t, p in NOTE_TRAITS.items() for n in notes if p.search(n["text"])}
            | {n["topic"] for n in news if n["topic"] in NEWS_TRAITS}
        )
        out.append({**s, "intel": intel, "news": news, "scorecard": sc, "payment_lateness_days": late,
                    "history": hist, "notes": notes, "traits": traits})

    dest = Path("experiments/dossiers.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    for o in out:
        ci = o["intel"]
        print(f"{o['id']} {o['name'][:34]:34} {o['country']} {o['category'][:14]:14} "
              f"credit {ci.get('credit_index_12m_ago')}->{ci.get('credit_index')} "
              f"sc {o['scorecard'].get('colour')} late {o['payment_lateness_days']}d | {', '.join(o['traits'])}")
    print(f"\n{len(out)} dossiers -> {dest}")


if __name__ == "__main__":
    main()
