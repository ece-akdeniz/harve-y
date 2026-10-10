"""Index-justified price change per part: Σ cost-driver weight × 12-month index change.

Compare with the asked change in price letters (documents.asked_pct). Weights sum < 1: the rest
is non-indexed cost and margin. Also lists each series' 12-month and from-peak change.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _data import connect  # noqa: E402


def main():
    db = connect()
    series = {}
    for (sid,) in db.execute("SELECT DISTINCT series_id FROM index_values"):
        rows = db.execute("SELECT month, value FROM index_values WHERE series_id = ? ORDER BY month DESC LIMIT 13",
                          (sid,)).fetchall()
        if len(rows) == 13:
            last, prev = rows[0], rows[12]
            peak = max(r["value"] for r in rows[:12])
            series[sid] = {"last": last["month"], "yoy": last["value"] / prev["value"] - 1,
                           "from_peak": last["value"] / peak - 1}

    print("series        last     12m %   from peak %")
    for sid, s in sorted(series.items(), key=lambda kv: kv[1]["yoy"]):
        print(f"{sid:13} {s['last']}  {s['yoy'] * 100:+6.1f}   {s['from_peak'] * 100:+6.1f}")

    asked = {r["part_ids"]: r["asked_pct"] for r in db.execute(
        "SELECT part_ids, asked_pct FROM documents WHERE asked_pct IS NOT NULL")}
    print("\npart          drivers w  justified %  asked %  drivers")
    parts = db.execute("SELECT DISTINCT part_id FROM cost_drivers ORDER BY part_id").fetchall()
    for (pid,) in parts:
        rows = db.execute("SELECT series_id, weight FROM cost_drivers WHERE part_id = ?", (pid,)).fetchall()
        w = sum(r["weight"] for r in rows)
        just = sum(r["weight"] * series.get(r["series_id"], {"yoy": 0})["yoy"] for r in rows) * 100
        a = next((v for k, v in asked.items() if k and pid in k), None)
        drivers = " ".join(f"{r['series_id']}:{r['weight']}" for r in rows)
        print(f"{pid:13} {w:5.2f}     {just:+6.1f}      {'' if a is None else f'{a:+.1f}':>6}   {drivers}")


if __name__ == "__main__":
    main()
