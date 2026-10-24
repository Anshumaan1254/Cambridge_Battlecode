#!/usr/bin/env python3
"""Second pass over compact records (same groups as res_compact.py): gold routing (who earns the team's gold, split captures),
carried-gem exposure, banked / collected, tribute bag sizes, per-capture gold by body type.
  python tools/live/res_compact2.py [--tag NEW|OLD|ALL]"""
import collections, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from res_compact import load_groups, at, integ

tag = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else "ALL"
games = load_groups()
A = collections.defaultdict(lambda: collections.defaultdict(list))


def mean(v):
    v = [a for a in v if a is not None]
    return st.mean(v) if v else float("nan")


for r, sides in games:
    for tk, grp, tg in sides:
        if tag != "ALL" and tg != tag:
            continue
        win = r["outcome"] == tk
        gl = [grp] + ([("TOPW" if win else "TOPL")] if grp == "TOP" else [])
        ch = [c for c in r["champs"] if c["team"] == tk]
        end = r["rounds"]
        earned = {c["id"]: c["m"]["earnedGold"] for c in ch}
        tot = sum(earned.values()) or 1
        names = {c["id"]: c["name"] for c in ch}
        top_share = max(earned.values()) / tot
        ves = sum(v for k, v in earned.items() if names[k] == "Vesper Vale") / tot if "Vesper Vale" in names.values() else None
        mar = sum(v for k, v in earned.items() if names[k] == "Marcella") / tot if "Marcella" in names.values() else None
        # captures (gem collections from camp groups): split = more than one ally collecting the same group in the same round
        colls = [x for x in r["colls"] if x[1] == tk and x[4] == "campGroup"]
        by_key = collections.defaultdict(list)
        for x in colls:
            g = x[5][3] if isinstance(x[5], list) else None
            by_key[(x[0], g)].append(x)
        caps = len(by_key)
        split = sum(1 for v in by_key.values() if len(v) > 1)
        # who takes captures, by type
        capper = collections.Counter()
        for v in by_key.values():
            for x in v:
                capper[x[2]] += 1 / len(v)
        # carried gems exposure (team sum of carried gems, mean over windows)
        carried = [0.0, 0.0, 0.0]
        for c in ch:
            gt = r["champ_tl"].get(f"{c['id']}:gems", [])
            carried[0] += integ(gt, 0, min(300, end)) or 0
            carried[1] += (integ(gt, 300, min(600, end)) or 0) if end > 350 else 0
            carried[2] += (integ(gt, 600, end) or 0) if end > 650 else 0
        collected = sum(c["m"]["collectedGems"] for c in ch)
        submitted = sum(c["m"]["submittedGems"] for c in ch)
        subs = [int(x[6] or 0) for x in r["subs"] if x[1] == tk]
        for g in gl:
            D = A[g]
            D["top_share"].append(top_share)
            D["ves_share"].append(ves)
            D["mar_share"].append(mar)
            D["caps"].append(caps)
            D["caps_per100"].append(100 * caps / max(1, end))
            D["split"].append(split / max(1, caps))
            D["carried0_300"].append(carried[0])
            if end > 350:
                D["carried300_600"].append(carried[1])
            if end > 650:
                D["carried600"].append(carried[2])
            D["sub_ratio"].append(submitted / max(1, collected))
            D["collected"].append(collected)
            D["bags"].extend(subs)
            D["ves_capshare"].append(sum(v for k, v in capper.items() if k == "Vesper Vale") / max(1, caps) if "Vesper Vale" in names.values() else None)
            # gems per capture by body type
            for x in colls:
                D["gpc_" + x[2]].append(int(x[6] or 0))
            D["gpc_all"].extend(int(x[6] or 0) for x in colls)
order = [g for g in ["OURS", "OPP", "TOP", "TOPW", "TOPL"] if A[g]["caps"]]
print(f"tag={tag}  " + ", ".join(f"{g} {len(A[g]['caps'])}" for g in order))
print(f"{'metric':26s}" + "".join(f"{g:>10s}" for g in order))
for k, f in [("top earner share", "top_share"), ("Vesper share of gold", "ves_share"), ("Vesper share of captures", "ves_capshare"),
             ("Marcella share of gold", "mar_share"), ("captures / game", "caps"), ("captures / 100 rounds", "caps_per100"),
             ("split captures %", "split"), ("carried gems 0-300", "carried0_300"), ("carried gems 300-600", "carried300_600"),
             ("carried gems 600+", "carried600"), ("collected / game", "collected"), ("banked / collected", "sub_ratio"),
             ("gems per collection", "gpc_all")]:
    mul = 100 if k.endswith("%") or "share" in k else 1
    print(f"{k:26s}" + "".join(f"{mul * mean(A[g][f]):10.2f}" for g in order))
print("\ntribute bag distribution (% of tributes)")
edges = [(1, 10), (11, 20), (21, 30), (31, 50), (51, 80), (81, 120), (121, 10 ** 6)]
for lo, hi in edges:
    print(f"  {lo:3d}-{hi if hi < 10 ** 6 else '':>4}" + " " * 14 + "".join(f"{100 * sum(1 for b in A[g]['bags'] if lo <= b <= hi) / max(1, len(A[g]['bags'])):10.1f}" for g in order))
print("\ngems per collection by type")
for t in ["Vesper Vale", "Vendetta", "Heart of Ruin", "Ryth", "Marcella", "Prism", "Varg", "Tavi"]:
    print(f"  {t:24s}" + "".join(f"{mean(A[g]['gpc_' + t]):10.1f}" for g in order) + "   n=" + ",".join(str(len(A[g]['gpc_' + t])) for g in order))
