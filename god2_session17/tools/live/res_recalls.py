#!/usr/bin/env python3
"""Completed recalls (arrival on spawn) per team: count, purpose at start, what follows. Spam = teams that start a recall almost every turn
and cancel it (start/complete > 5).   python tools/live/res_recalls.py"""
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
                name = t["name"]
                key = name if name == "HouseOfCoders" else name + (" (vs us)" if kind == "ours" else "")
                D = T[name]
                D["bodies"].append(1)
                D["rounds"].append(g["final"])
                ok = [rc for rc in b["recalls"] if rc["res"] == "ok"]
                D["starts"].append(len(b["recalls"]))
                D["ok"].append(len(ok))
                for rc in ok:
                    p = "capture" if rc["cap"] else "hurt" if rc["hpf"] < 0.5 else "bag" if rc["gems"] >= 20 else "shop" if rc["gold"] >= 90 else "other"
                    D["purpose"].append(p)
                    D["hpf"].append(rc["hpf"])
                    D["dh"].append(rc["dh"])
                    D["shop"].append(1 if rc.get("shop") else 0)
                    D["bank"].append(rc.get("bankAfter", 0))
                    D["goldArr"].append(rc.get("goldArr") or 0)
                    D["bagArr"].append(rc.get("gemsArr") or 0)
                    D["early"].append(1 if rc["r"] <= 300 else 0)
                D["ok300"].append(sum(1 for rc in ok if rc["r"] <= 300))
m = lambda v: st.mean(v) if v else float("nan")
print(f"{'team':30s} {'bodies':>6s} {'starts':>7s} {'done':>5s} {'/100r':>6s} {'<=r300':>6s} {'capt%':>6s} {'hurt%':>6s} {'bag%':>5s} {'shop%':>6s} {'oth%':>5s} {'hp':>5s} {'dist':>5s} {'shopd%':>6s} {'bank%':>6s} {'gold':>5s} {'bag':>5s}")
for n, D in sorted(T.items(), key=lambda x: -len(x[1]["bodies"])):
    P = collections.Counter(D["purpose"]); tot = max(1, len(D["purpose"]))
    print(f"{n[:30]:30s} {len(D['bodies']):6d} {m(D['starts']):7.1f} {m(D['ok']):5.1f} {100 * sum(D['ok']) / max(1, sum(D['rounds'])):6.2f} {m(D['ok300']):6.2f} "
          f"{100 * P['capture'] / tot:6.1f} {100 * P['hurt'] / tot:6.1f} {100 * P['bag'] / tot:5.1f} {100 * P['shop'] / tot:6.1f} {100 * P['other'] / tot:5.1f} "
          f"{st.median(D['hpf']) if D['hpf'] else 0:5.2f} {st.median(D['dh']) if D['dh'] else 0:5.0f} {100 * m(D['shop']):6.1f} {100 * m(D['bank']):6.1f} {m(D['goldArr']):5.0f} {m(D['bagArr']):5.1f}")
