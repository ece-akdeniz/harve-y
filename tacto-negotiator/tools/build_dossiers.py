"""Build a dossier per detailed supplier and print a compact overview.

Output: experiments/dossiers.json (gitignored). Uses negotiator.dossiers, so the Sunday release
(ARENA_RELEASE or a `release-sunday` folder) is included.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from negotiator.dossiers import build, load_package  # noqa: E402


def main():
    package = load_package()
    out = []
    for d in build(package).values():
        out.append({"id": d.supplier_id, "name": d.name, "country": d.country, "category": d.category,
                    **{k: d.master.get(k) for k in ("payment_days", "incoterm", "abc_class")},
                    "intel": d.intel, "news": d.news, "scorecard": d.scorecard,
                    "payment_lateness_days": d.payment_lateness_days, "history": d.history, "notes": d.notes,
                    "traits": sorted(d.traits)})

    dest = Path("experiments/dossiers.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    for o in out:
        ci = o["intel"]
        print(f"{o['id']} {o['name'][:34]:34} {o['country']} {o['category'][:14]:14} "
              f"credit {ci.get('credit_index_12m_ago')}->{ci.get('credit_index')} "
              f"sc {o['scorecard'].get('colour')} late {o['payment_lateness_days']}d | {', '.join(o['traits'])}")
    print(f"\n{len(out)} dossiers -> {dest} (release: {package.release})")


if __name__ == "__main__":
    main()
