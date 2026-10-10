"""Index-justified price change per part: Σ cost-driver weight × 12-month index change.

Compare with the asked change in price letters (documents.asked_pct). Weights sum < 1: the rest
is non-indexed cost and margin. Windows are calendar months ending at each series' last month
(negotiator.claims.latest_window); series without a full window are reported, not set to zero.
Includes the Sunday release overlay via negotiator.dossiers.load_package.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from negotiator.claims import latest_window, series_values  # noqa: E402
from negotiator.dossiers import load_package  # noqa: E402


def main():
    package = load_package()
    values = series_values(package.facts)
    series = {}
    for sid, v in values.items():
        if w := latest_window(v):
            last12 = [v[m] for m in v if m > w[0]]
            series[sid] = {"last": w[1], "yoy": v[w[1]] / v[w[0]] - 1, "from_peak": v[w[1]] / max(last12) - 1}

    print("series        last     12m %   from peak %")
    for sid, s in sorted(series.items(), key=lambda kv: kv[1]["yoy"]):
        print(f"{sid:13} {s['last']}  {s['yoy'] * 100:+6.1f}   {s['from_peak'] * 100:+6.1f}")

    asked = {r["part_ids"]: r["asked_pct"] for r in package.query(
        "SELECT part_ids, asked_pct FROM documents WHERE asked_pct IS NOT NULL", limit=10_000)}
    print("\npart          drivers w  justified %  asked %  drivers")
    for (pid,) in package.db.execute("SELECT DISTINCT part_id FROM cost_drivers ORDER BY part_id"):
        rows = package.query("SELECT series_id, weight FROM cost_drivers WHERE part_id = ?", (pid,))
        missing = [r["series_id"] for r in rows if r["series_id"] not in series]
        w = sum(r["weight"] for r in rows if r["series_id"] in series)
        just = sum(r["weight"] * series[r["series_id"]]["yoy"] for r in rows if r["series_id"] in series) * 100
        a = next((v for k, v in asked.items() if k and pid in k), None)
        drivers = " ".join(f"{r['series_id']}:{r['weight']}" for r in rows)
        flag = f"  MISSING {','.join(missing)}" if missing else ""
        print(f"{pid:13} {w:5.2f}     {just:+6.1f}      {'' if a is None else f'{a:+.1f}':>6}   {drivers}{flag}")


if __name__ == "__main__":
    main()
