#!/usr/bin/env python3
"""Tributes split by route: after a recall home (a completed recall between the last capture and the tribute) or direct from the field;
capture-recall profile (bag / gold / hp at start, bag on arrival).   python tools/live/res_bankvia.py [ours.jsonl,...] [top.jsonl]"""
import collections, json, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from res_replay_agg import meta_index, DRAFT

SPAM = {":3", "Pantheon", "EMPEROR Tung"}
idx = meta_index()
ours = sys.argv[1].split(",") if len(sys.argv) > 1 else ["C:/battlecode/cache/an_resources/rr_bb4D.jsonl", "C:/battlecode/cache/an_resources/rr_ft52D.jsonl"]
top = sys.argv[2].split(",") if len(sys.argv) > 2 else ["C:/battlecode/cache/an_resources/rr_top.jsonl"]
T = collections.defaultdict(lambda: collections.defaultdict(list))
for kind, files in (("ours", ours), ("top", top)):
    for f in files:
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
            for b in g["bodies"]:
                t = ta if b["team"] == 0 else tb
                grp = "OURS" if t["name"] == "HouseOfCoders" else ("OPP" if kind == "ours" else "TOP")
                cls = "OURS" if grp == "OURS" else ("SPAM" if t["name"] in SPAM else "NONSPAM")
                arrs = [rc["arr"] for rc in b["recalls"] if rc["res"] == "ok" and rc.get("arr") is not None]
                for x in b["tributes"]:
                    if x.get("res") != "ok" or x.get("sinceCap") is None:
                        continue
                    lc = x["r"] - x["sinceCap"]
                    via = any(lc <= a <= x["r"] for a in arrs)
                    D = T[grp]
                    D["via"].append(1 if via else 0)
                    k = "via" if via else "dir"
                    D["since_" + k].append(min(300, x["sinceCap"]))
                    D["capD_" + k].append(x["capD"])
                    D["bag_" + k].append(x["gems"])
                    D["rec_after"].append(1 if any(0 <= rc["r"] - x["r"] <= 10 and rc["res"] == "ok" for rc in b["recalls"]) else 0)
                C = T["cr_" + cls]
                C["bodies"].append(1)
                for rc in b["recalls"]:
                    if rc["res"] != "ok" or not rc["cap"]:
                        continue
                    C["n"].append(1); C["hpf"].append(rc["hpf"]); C["gold"].append(rc["gold"]); C["bag"].append(rc["gems"]); C["bagArr"].append(rc.get("gemsArr") or 0)
md = lambda v: st.median(v) if v else float("nan")
m = lambda v: st.mean(v) if v else float("nan")
for g in ["OURS", "OPP", "TOP"]:
    D = T[g]
    print(f"{g:5s} tributes {len(D['via']):5d}  via-recall {100 * m(D['via']):5.1f}%  rounds after capture: via {md(D['since_via']):4.0f} direct {md(D['since_dir']):4.0f}  "
          f"tiles capture->altar: via {md(D['capD_via']):4.0f} direct {md(D['capD_dir']):4.0f}  bag: via {m(D['bag_via']):5.1f} direct {m(D['bag_dir']):5.1f}  "
          f"recall<=10r after bank {100 * m(D['rec_after']):5.1f}%")
for c in ["OURS", "NONSPAM", "SPAM"]:
    C = T["cr_" + c]
    print(f"capture-recalls {c:8s} per body {len(C['n']) / max(1, len(C['bodies'])):5.2f}  hp med {md(C['hpf']):.2f}  gold@start {m(C['gold']):5.0f}  bag@start {m(C['bag']):5.1f}  bag@arrival {m(C['bagArr']):5.1f}")
