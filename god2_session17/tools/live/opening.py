#!/usr/bin/env python3
"""Opening / tempo profile per team: gold earned, gems collected, clears, buys, deaths at checkpoints.
python tools/live/opening.py NAME [NAME ...] [--since ISO] [--vs-top N] [--wins-only]"""
import argparse, collections, glob, json, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import load, side, at, top_ranks
CPS = [50, 100, 150, 200, 300, 400, 600]
ap = argparse.ArgumentParser(); ap.add_argument("names", nargs="+"); ap.add_argument("--since", default="")
ap.add_argument("--vs-top", type=int, default=0); ap.add_argument("--wins-only", action="store_true"); ap.add_argument("--losses-only", action="store_true")
ap.add_argument("--min-size", type=int, default=3); ap.add_argument("--max-size", type=int, default=5)
a = ap.parse_args()
rs = load(a.since)
rk = top_ranks()
def prof(r, tk):
    ids = [c["id"] for c in r["champs"] if c["team"] == tk]
    P = {}
    for cp in CPS:
        P[f"gold@{cp}"] = sum(at(r["champ_tl"].get(f"{i}:earnedGold", []), cp) for i in ids)
        P[f"gemsC@{cp}"] = sum(at(r["champ_tl"].get(f"{i}:collectedGems", []), cp) for i in ids)
        P[f"bank@{cp}"] = at(r["team_tl"].get(f"{tk}:submittedGems", []), cp)
        P[f"clears@{cp}"] = sum(1 for x in r["clears"] if x[1] == tk and x[0] <= cp)
        P[f"spent@{cp}"] = sum(float(x[7] or 0) for x in r["buys"] if x[1] == tk and x[0] <= cp)
        P[f"deaths@{cp}"] = sum(1 for x in r["deaths"] if x[1] == tk and x[0] <= cp)
        P[f"campdeaths@{cp}"] = sum(1 for x in r["deaths"] if x[1] == tk and x[0] <= cp and x[4] != "champion")
    cl = [x[0] for x in r["clears"] if x[1] == tk]
    P["first_clear"] = cl[0] if cl else 2000
    P["third_clear"] = cl[2] if len(cl) > 2 else 2000
    sb = [x[0] for x in r["subs"] if x[1] == tk]
    P["first_bank"] = sb[0] if sb else 2000
    by = [x[0] for x in r["buys"] if x[1] == tk]
    P["first_buy"] = by[0] if by else 2000
    return P
for name in a.names:
    rows = []
    for r in rs:
        tk = side(r, name)
        if not tk: continue
        opp = next(t for t in r["teams"] if t["team"] != tk)
        n = len(next(t for t in r["teams"] if t["team"] == tk)["draft"])
        if not (a.min_size <= n <= a.max_size): continue
        if a.vs_top and rk.get(opp["name"], 999) > a.vs_top: continue
        win = r["outcome"] == tk
        if a.wins_only and not win: continue
        if a.losses_only and win: continue
        rows.append(prof(r, tk))
    if not rows:
        print(name, "no games"); continue
    print(f"\n== {name}: {len(rows)} games")
    print("first clear %.0f | third clear %.0f | first bank %.0f | first buy %.0f" % tuple(st.median([x[k] for x in rows]) for k in ("first_clear", "third_clear", "first_bank", "first_buy")))
    print(f"{'round':>8s}" + "".join(f"{cp:>8d}" for cp in CPS))
    for k in ("gold", "gemsC", "bank", "clears", "spent", "deaths", "campdeaths"):
        print(f"{k:>8s}" + "".join(f"{st.mean([x[f'{k}@{cp}'] for x in rows]):8.1f}" for cp in CPS))
