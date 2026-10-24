#!/usr/bin/env python3
"""Shopping visits from compact records: shards per visit, gold before, rounds between visits, dead shopping share of spend, consumables.
  python tools/live/res_shop.py"""
import collections, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from res_compact import load_groups

A = collections.defaultdict(lambda: collections.defaultdict(list))
for r, sides in load_groups():
    deaths = collections.defaultdict(list)
    for x in r["deaths"]:
        deaths[(x[1], x[3])].append(x[0])
    for tk, grp, tg in sides:
        win = r["outcome"] == tk
        gl = [grp] + ([("TOPW" if win else "TOPL")] if grp == "TOP" else [])
        for c in r["champs"]:
            if c["team"] != tk:
                continue
            buys = [x for x in r["buys"] if x[1] == tk and x[3] == c["id"]]
            cons = [x for x in r["cons"] if x[1] == tk and x[3] == c["id"]]
            V = collections.OrderedDict()
            for x in sorted(buys + cons, key=lambda y: y[0]):
                v = V.setdefault(x[0], {"sh": 0, "gold": None, "spent": 0, "cons": 0})
                if v["gold"] is None:
                    try:
                        v["gold"] = float(x[4])
                    except Exception:
                        v["gold"] = None
                if x in buys:
                    v["sh"] += int(x[6] or 1)
                else:
                    v["cons"] += 1
                v["spent"] += float(x[7] or 0)
            rounds = list(V.keys())
            dead = [(d, d + 61) for d in deaths[(tk, c["id"])]]
            for g in gl:
                D = A[g]
                for i, (rr, v) in enumerate(V.items()):
                    if v["sh"] == 0:
                        continue
                    D["sh"].append(v["sh"])
                    if v["gold"] is not None:
                        D["gold"].append(v["gold"])
                    isdead = any(a <= rr <= b for a, b in dead)
                    D["dead_spent"].append(v["spent"] if isdead else 0)
                    D["spent"].append(v["spent"])
                    if rr <= 300:
                        D["sh300"].append(v["sh"])
                shr = [rr for rr, v in V.items() if v["sh"] > 0]
                D["gap"].extend(b - a for a, b in zip(shr, shr[1:]))
                D["first"].append(shr[0] if shr else 2000)
order = ["OURS", "OPP", "TOP", "TOPW", "TOPL"]
m = lambda v: st.mean(v) if v else float("nan")
md = lambda v: st.median(v) if v else float("nan")
print(f"{'metric':30s}" + "".join(f"{g:>9s}" for g in order))
rows = [("shard visits (n)", lambda D: len(D["sh"]), "9.0f"), ("shards / visit (mean)", lambda D: m(D["sh"]), "9.2f"),
        ("shards / visit r<=300", lambda D: m(D["sh300"]), "9.2f"),
        ("visits with 1-2 shards %", lambda D: 100 * m([1 if s <= 2 else 0 for s in D["sh"]]), "9.1f"),
        ("visits with 5+ shards %", lambda D: 100 * m([1 if s >= 5 else 0 for s in D["sh"]]), "9.1f"),
        ("gold before (median)", lambda D: md(D["gold"]), "9.0f"), ("gold before >=150 %", lambda D: 100 * m([1 if x >= 150 else 0 for x in D["gold"]]), "9.1f"),
        ("rounds between visits (med)", lambda D: md(D["gap"]), "9.0f"), ("first shard visit (median r)", lambda D: md(D["first"]), "9.0f"),
        ("spend while dead %", lambda D: 100 * sum(D["dead_spent"]) / max(1, sum(D["spent"])), "9.1f")]
for name, f, fmt in rows:
    print(f"{name:30s}" + "".join(format(f(A[g]), fmt) for g in order))
