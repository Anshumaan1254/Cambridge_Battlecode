#!/usr/bin/env python3
"""Aggregate tools/live/opening_caps.mjs output: us vs them (side from the match lists).
  python tools/live/opening_caps_agg.py caps.jsonl [--us HouseOfCoders]"""
import glob, json, sys, collections, statistics as st
US = "HouseOfCoders"
side_of = {}
for f in glob.glob("experiments/live/lists/*.jsonl"):
    for l in open(f, encoding="utf-8"):
        try:
            m = json.loads(l)
        except Exception:
            continue
        for t in m.get("teams", []):
            if t.get("name") == US:
                side_of[m["matchId"][:8]] = (0 if t["side"] == "a" else 1, next((o["name"] for o in m["teams"] if o["name"] != US), "?"), m["map"], t.get("result"))
def cat(mix):
    mix = mix or {}
    if mix.get("monolith"): return "monolith"
    if mix.get("golem"): return "golem"
    if mix.get("elk"): return f"elk{mix['elk']}"
    if mix.get("wolf"): return "wolf"
    return "cluster"
rows = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]
agg = {"us": collections.defaultdict(list), "them": collections.defaultdict(list)}
cats = {"us": collections.Counter(), "them": collections.Counter()}
per_game = []
for d in rows:
    mid = d["file"].split("_")[-1].split(".")[0]
    if mid not in side_of:
        continue
    us_t, opp, mp, res = side_of[mid]
    g = {}
    for who, t in (("us", us_t), ("them", 1 - us_t)):
        caps = d["teams"][str(t)]
        for cp in (100, 200, 300):
            agg[who][f"caps@{cp}"].append(sum(1 for c in caps if c["r"] < cp))
            agg[who][f"gems@{cp}"].append(sum(c["gems"] for c in caps if c["r"] < cp))
            agg[who][f"gold@{cp}"].append(sum(c["gold"] for c in caps if c["r"] < cp))
        agg[who]["first_cap"].append(min([c["r"] for c in caps] or [300]))
        for c in caps:
            agg[who]["hitters"].append(c["hitters"])
            agg[who]["split"].append(c["split"])
            agg[who]["dist"].append(c["dist"])
            if c["killRounds"] is not None:
                agg[who]["killRounds"].append(c["killRounds"])
            agg[who]["gems_per_cap"].append(c["gems"])
            agg[who]["gold_per_cap"].append(c["gold"])
            agg[who]["contested"].append(1 if c["enemyHitters"] else 0)
            cats[who][cat(c["mix"])] += 1
        g[who] = sum(c["gems"] for c in caps if c["r"] < 200)
    per_game.append((mp, opp, res, g["us"], g["them"]))
print(f"{len(per_game)} games")
for k in agg["us"]:
    a, b = agg["us"][k], agg["them"][k]
    print(f"{k:14s} us {st.mean(a):7.1f}   them {st.mean(b):7.1f}")
for who in ("us", "them"):
    tot = sum(cats[who].values())
    print(who, "capture mix:", ", ".join(f"{k} {100*v/tot:.0f}%" for k, v in cats[who].most_common()))
