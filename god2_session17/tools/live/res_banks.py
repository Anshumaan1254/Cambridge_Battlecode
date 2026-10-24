#!/usr/bin/env python3
"""Tributes per team from res_replay.mjs output: count, bag, channel rounds, distance last capture -> altar, rounds from capture to
tribute, altar distance from spawn, banks right after a recall arrival; deaths with bags.   python tools/live/res_banks.py"""
import collections, json, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from res_replay_agg import meta_index, DRAFT

idx = meta_index()
F = {"ours": ["C:/battlecode/cache/an_resources/rr_bb4D.jsonl", "C:/battlecode/cache/an_resources/rr_ft52D.jsonl"], "top": ["C:/battlecode/cache/an_resources/rr_top.jsonl"]}
T = collections.defaultdict(lambda: collections.defaultdict(list))
for kind, files in F.items():
    for f in files:
        if not os.path.exists(f):
            continue
        for l in open(f, encoding="utf-8"):
            try:
                g = json.loads(l)
            except Exception:
                continue
            m = idx.get(g["file"].split("_")[-1].split(".")[0])
            if not m:
                continue
            sides = {t["side"]: t for t in m["teams"]}
            ta, tb = sides["a"], sides["b"]
            if sorted(DRAFT[int(c)] for c in ta["characters"]) != sorted(g["drafts"][0]):
                ta, tb = tb, ta
            for b in g["bodies"]:
                t = ta if b["team"] == 0 else tb
                keys = [t["name"], "ALL-TOP" if t["name"] != "HouseOfCoders" else "OURS"]
                if t["name"] != "HouseOfCoders":
                    keys.append("TOP-in-tvt" if kind == "top" else "TOP-vs-us")
                ok = [x for x in b["tributes"] if x.get("res") == "ok" and "bag" in x]
                arrs = [rc["arr"] for rc in b["recalls"] if rc["res"] == "ok" and rc.get("arr") is not None]
                for k in keys:
                    D = T[k]
                    D["bodies"].append(1)
                    D["n"].append(len(ok))
                    D["n100"].append(100 * len(ok) / max(1, g["final"]))
                    D["chan"].append(sum(x.get("dur", 0) for x in ok))
                    D["chan_pct"].append(100 * sum(x.get("dur", 0) for x in ok) / max(1, g["final"]))
                    for x in ok:
                        D["bag"].append(x.get("gems", 0))
                        if x.get("capD") is not None:
                            D["capD"].append(x["capD"]); D["since"].append(min(300, x["sinceCap"])); D["capDh"].append(x["capDh"])
                        D["altarHome"].append(x["altarHome"])
                        D["afterRecall"].append(1 if any(0 <= x["r"] - a <= 25 for a in arrs) else 0)
                        D["near"].append(1 if x.get("capD") is not None and x["capD"] <= 8 else 0)
                    D["dbag"].extend(d["bag"] for d in b["deaths"])
                    D["lost"].append(sum(d["bag"] for d in b["deaths"]))
                    D["deaths"].append(len(b["deaths"]))
m = lambda v: st.mean(v) if v else float("nan")
md = lambda v: st.median(v) if v else float("nan")
print(f"{'team':28s} {'bodies':>6s} {'trib':>5s} {'/100r':>6s} {'bag':>5s} {'medbag':>6s} {'chan%':>6s} {'capD':>5s} {'since':>6s} {'mSince':>6s} {'altH':>5s} {'capDh':>5s} {'near%':>6s} {'afterRc%':>8s} {'deaths':>6s} {'lost':>6s} {'bagDeath%':>9s}")
for n, D in sorted(T.items(), key=lambda x: -len(x[1]["bodies"])):
    print(f"{n[:28]:28s} {len(D['bodies']):6d} {m(D['n']):5.2f} {m(D['n100']):6.2f} {m(D['bag']):5.1f} {md(D['bag']):6.0f} {m(D['chan_pct']):6.2f} {md(D['capD']):5.0f} {md(D['since']):6.0f} {m(D['since']):6.1f} {md(D['altarHome']):5.0f} {md(D['capDh']):5.0f} "
          f"{100 * m(D['near']):6.1f} {100 * m(D['afterRecall']):8.1f} {m(D['deaths']):6.2f} {m(D['lost']):6.1f} {100 * m([1 if x >= 20 else 0 for x in D['dbag']]):9.1f}")
