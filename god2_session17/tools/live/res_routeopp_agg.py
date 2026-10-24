#!/usr/bin/env python3
"""Aggregate res_routeopp.mjs: share of captures taken by Vesper / Marcella, captures taken by others while Vesper (Marcella) stood within
2 / 4 / 6 tiles (routable rewards), the bonus gold those would have paid, and allies standing on the capture with the capturer.
  python tools/live/res_routeopp_agg.py [ours.jsonl] [top.jsonl]"""
import collections, json, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from res_replay_agg import meta_index, DRAFT

idx = meta_index()
ours = sys.argv[1] if len(sys.argv) > 1 else "C:/battlecode/cache/an_resources/ro_bb4D.jsonl"
top = sys.argv[2] if len(sys.argv) > 2 else "C:/battlecode/cache/an_resources/ro_top.jsonl"
A = collections.defaultdict(lambda: collections.defaultdict(list))
games = collections.Counter()
games_v = collections.Counter()
games_m = collections.Counter()
for kind, f in (("ours", ours), ("top", top)):
    if not os.path.exists(f):
        continue
    for l in open(f, encoding="utf-8"):
        g = json.loads(l)
        m = idx.get(g["file"].split("_")[-1].split(".")[0])
        if not m:
            continue
        sides = {t["side"]: t for t in m["teams"]}
        ta, tb = sides["a"], sides["b"]
        if sorted(DRAFT[int(c)] for c in ta["characters"]) != sorted(g["drafts"][0]):
            ta, tb = tb, ta
        names = {0: ta["name"], 1: tb["name"]}
        for team in (0, 1):
            grp = "OURS" if names[team] == "HouseOfCoders" else ("OPP" if kind == "ours" else "TOP")
            games[grp] += 1
            has_v = "VesperVale" in g["drafts"][team]
            has_m = "Marcella" in g["drafts"][team]
            games_v[grp] += has_v
            games_m[grp] += has_m
            for r, t, champ, gems, gold, dv, dm, waiting in g["caps"]:
                if t != team:
                    continue
                D = A[grp]
                D["waiting"].append(waiting)
                if has_v:
                    D["v_caps"].append(1 if champ == "VesperVale" else 0)
                    if champ != "VesperVale":
                        for k in (2, 4, 6):
                            D[f"v_near{k}"].append(1 if dv is not None and 0 <= dv <= k else 0)
                        D["v_gold_near4"].append(gold * 0.33 if dv is not None and 0 <= dv <= 4 else 0)
                if has_m:
                    D["m_caps"].append(1 if champ == "Marcella" else 0)
                    if champ != "Marcella":
                        for k in (2, 4, 6):
                            D[f"m_near{k}"].append(1 if dm is not None and 0 <= dm <= k else 0)
                        D["m_gems_near4"].append(gems * 2 if dm is not None and 0 <= dm <= 4 else 0)
m = lambda v: st.mean(v) if v else float("nan")
order = [g for g in ("OURS", "OPP", "TOP") if A[g]]
print("games (sides): " + ", ".join(f"{g} {games[g]} (Vesper {games_v[g]}, Marcella {games_m[g]})" for g in order))
print(f"{'metric':52s}" + "".join(f"{g:>9s}" for g in order))
rows = [("captures (with gems) per side", lambda g: len(A[g]["waiting"]) / max(1, games[g]), "9.1f"),
        ("allies within 1 of the capturer (mean)", lambda g: m(A[g]["waiting"]), "9.2f"),
        ("captures with an ally waiting on it %", lambda g: 100 * m([1 if w > 0 else 0 for w in A[g]["waiting"]]), "9.1f"),
        ("Vesper drafted: captures taken by Vesper %", lambda g: 100 * m(A[g]["v_caps"]), "9.1f"),
        ("  others' captures with Vesper alive within 2 %", lambda g: 100 * m(A[g]["v_near2"]), "9.1f"),
        ("  ... within 4 %", lambda g: 100 * m(A[g]["v_near4"]), "9.1f"),
        ("  ... within 6 %", lambda g: 100 * m(A[g]["v_near6"]), "9.1f"),
        ("  Vesper bonus missed within 4 (gold / Vesper game)", lambda g: sum(A[g]["v_gold_near4"]) / max(1, games_v[g]), "9.0f"),
        ("Marcella drafted: captures taken by Marcella %", lambda g: 100 * m(A[g]["m_caps"]), "9.1f"),
        ("  others' captures with Marcella alive within 4 %", lambda g: 100 * m(A[g]["m_near4"]), "9.1f"),
        ("  Marcella bank gold missed within 4 (/ Marcella game)", lambda g: sum(A[g]["m_gems_near4"]) / max(1, games_m[g]), "9.0f")]
for name, f, fmt in rows:
    print(f"{name:52s}" + "".join(format(f(g), fmt) for g in order))
