#!/usr/bin/env python3
"""Per-team build orders (first 3 emblems) for the main champion types, and the Treasure emblem's payback (gold its +20% returned after
completion vs the 60 gold of extra stats a Bruiser emblem would have given).   python tools/live/res_builds.py"""
import collections, json, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from res_compact import load_groups, at


def short(n):
    f, _, s = n.partition(" Emblem of ")
    return f[:4] + "-" + s[:3]


B = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
PAY = collections.defaultdict(list)
for r, sides in load_groups():
    for tk, grp, tg in sides:
        name = next(t["name"] for t in r["teams"] if t["team"] == tk)
        win = r["outcome"] == tk
        for c in r["champs"]:
            if c["team"] != tk:
                continue
            emb = [(x[0], x[5][2]) for x in r["combos"] if x[1] == tk and x[3] == c["id"] and isinstance(x[5], list)]
            B[c["name"]][name][" > ".join(short(e[1]) for e in emb[:3])] += 1
            eg = r["champ_tl"].get(f"{c['id']}:earnedGold", [])
            tre = [e for e in emb if e[1].startswith("Treasure")]
            if tre:
                t0 = tre[0][0]
                after = at(eg, 10 ** 9) - at(eg, t0)
                base = 1.53 if c["name"] == "Vesper Vale" else 1.2
                bonus = after * 0.2 / base
                key = ("OURS" if name == "HouseOfCoders" else "TOP")
                PAY[(key, c["name"])].append((t0, bonus, r["rounds"]))
for t in ["Vesper Vale", "Vendetta", "Heart of Ruin", "Ryth", "Marcella", "Prism", "Tavi", "Varg"]:
    print(f"\n== {t}")
    for team, C in sorted(B[t].items(), key=lambda x: -sum(x[1].values())):
        n = sum(C.values())
        if n < 8:
            continue
        print(f"  {team[:26]:26s} n={n:3d}  " + " | ".join(f"{s or '-'} {100 * v / n:.0f}%" for s, v in C.most_common(3)))
print("\n== Treasure emblem payback (gold returned by the +20% after completion; Bruiser alternative = +60 gold of stats)")
print(f"  {'grp':5s} {'type':14s} {'n':>4s} {'done r':>7s} {'bonus mean':>10s} {'median':>7s} {'<60 %':>6s} {'<100 %':>7s}")
for (g, t), v in sorted(PAY.items(), key=lambda x: (x[0][1], x[0][0])):
    if len(v) < 10:
        continue
    b = [x[1] for x in v]
    print(f"  {g:5s} {t:14s} {len(v):4d} {st.median([x[0] for x in v]):7.0f} {st.mean(b):10.0f} {st.median(b):7.0f} {100 * sum(1 for x in b if x < 60) / len(b):6.0f} {100 * sum(1 for x in b if x < 100) / len(b):7.0f}")
