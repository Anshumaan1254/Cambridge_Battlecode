#!/usr/bin/env python3
"""Reward routing: share of team captures / collected gems / banked gems / gold taken by each champion type (Marcella banks 2 gold per gem,
Vesper +33% gold, Prism +1.5 focus per carried gem). Groups as res_compact.py.   python tools/live/res_routing.py"""
import collections, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from res_compact import load_groups, integ

A = collections.defaultdict(lambda: collections.defaultdict(list))
for r, sides in load_groups():
    for tk, grp, tg in sides:
        win = r["outcome"] == tk
        gl = [grp] + ([("TOPW" if win else "TOPL")] if grp == "TOP" else [])
        ch = [c for c in r["champs"] if c["team"] == tk]
        n = len(ch)
        tcol = sum(c["m"]["collectedGems"] for c in ch) or 1
        tsub = sum(c["m"]["submittedGems"] for c in ch) or 1
        tgold = sum(c["m"]["earnedGold"] for c in ch) or 1
        colls = [x for x in r["colls"] if x[1] == tk and x[4] == "campGroup"]
        tcap = len(colls) or 1
        for c in ch:
            t = c["name"]
            caps = sum(1 for x in colls if x[3] == c["id"])
            subs = [int(x[6] or 0) for x in r["subs"] if x[1] == tk and x[3] == c["id"]]
            gt = r["champ_tl"].get(f"{c['id']}:gems", [])
            for g in gl:
                D = A[(g, t)]
                D["n"].append(n)
                D["cap_share"].append(caps / tcap)
                D["col_share"].append(c["m"]["collectedGems"] / tcol)
                D["sub_share"].append(c["m"]["submittedGems"] / tsub)
                D["gold_share"].append(c["m"]["earnedGold"] / tgold)
                D["subs"].append(len(subs))
                D["bag"].extend(subs)
                D["carried"].append(integ(gt, 0, r["rounds"]))
                D["banked"].append(c["m"]["submittedGems"])
                D["fair"].append(1 / n)
order = ["OURS", "OPP", "TOP", "TOPW", "TOPL"]
m = lambda v: st.mean(v) if v else float("nan")
for t in ["Vesper Vale", "Marcella", "Prism", "Vendetta", "Heart of Ruin", "Ryth", "Tavi", "Varg"]:
    print(f"\n-- {t}  (fair share = 1/bodies)")
    print(f"  {'grp':5s} {'n':>5s} {'fair':>6s} {'caps%':>6s} {'coll%':>6s} {'bank%':>6s} {'gold%':>6s} {'subs':>5s} {'bag':>6s} {'carried':>8s} {'banked':>7s}")
    for g in order:
        D = A[(g, t)]
        if len(D["n"]) < 5:
            continue
        print(f"  {g:5s} {len(D['n']):5d} {100 * m(D['fair']):6.1f} {100 * m(D['cap_share']):6.1f} {100 * m(D['col_share']):6.1f} {100 * m(D['sub_share']):6.1f} "
              f"{100 * m(D['gold_share']):6.1f} {m(D['subs']):5.1f} {m(D['bag']):6.1f} {m(D['carried']):8.1f} {m(D['banked']):7.0f}")
