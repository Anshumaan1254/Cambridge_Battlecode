#!/usr/bin/env python3
"""Report on match lists (no summaries needed): records among top teams, drafts per team, first picks, team sizes.
Usage: python tools/live/lists_report.py [--top 20] [--since ISO]"""
import argparse, collections, glob, json, os
CH = ["Ryth", "Vesper", "Vendetta", "C&I", "Stellar", "Prism", "Marcella", "Willow", "Ren", "Varg", "Tavi", "HoR"]
ap = argparse.ArgumentParser(); ap.add_argument("--top", type=int, default=20); ap.add_argument("--since", default="")
a = ap.parse_args()
top = [l.rstrip("\n").split("\t") for l in open("experiments/live/top40.tsv", encoding="utf-8")]
rank = {t[1]: int(t[0]) for t in top}
names = {t[1]: t[2] for t in top}
US = "5a103c90-b00b-4d46-8ace-6a3bb058dc72"
ms = {}
for f in glob.glob("experiments/live/lists/*.jsonl") + ["experiments/live/matches_us.jsonl"]:
    for l in open(f, encoding="utf-8"):
        if l.strip():
            m = json.loads(l)
            if m.get("status") == "finished" and m.get("createdAt", "") >= a.since:
                ms[m["matchId"]] = m
print(len(ms), "finished matches loaded; span", min(m["createdAt"] for m in ms.values()), "->", max(m["createdAt"] for m in ms.values()))
# per-team draft habits (ranked only)
pick = collections.defaultdict(collections.Counter); first = collections.defaultdict(collections.Counter)
rec = collections.defaultdict(lambda: [0, 0]); h2h = collections.defaultdict(lambda: [0, 0])
size_draft = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
for m in ms.values():
    if m["kind"] != "ranked": continue
    t = m["teams"]
    for i, x in enumerate(t):
        y = t[1 - i]; tid = x["teamId"]
        if tid not in rank and tid != US: continue
        w = x["result"] == "win"
        rec[tid][0 if w else 1] += 1
        if y["teamId"] in rank and rank[y["teamId"]] <= a.top:
            h2h[tid][0 if w else 1] += 1
        dp = x.get("draftPicks") or []
        for c in dp: pick[tid][CH[c]] += 1
        if dp: first[tid][CH[dp[0]]] += 1
        size_draft[tid][len(dp)][",".join(CH[c] for c in dp)] += 1
order = sorted([k for k in rec if (k in rank and rank[k] <= a.top) or k == US], key=lambda k: rank.get(k, 99))
for tid in order:
    w, l = rec[tid]; hw, hl = h2h[tid]
    n = sum(first[tid].values())
    print(f"\n#{rank.get(tid,'us')} {names.get(tid,'HouseOfCoders')}: ranked {w}-{l} ({100*w/max(1,w+l):.0f}%), vs top{a.top} {hw}-{hl}")
    print("   first pick:", ", ".join(f"{c} {100*v/n:.0f}%" for c, v in first[tid].most_common(5)))
    print("   picked:", ", ".join(f"{c} {100*v/n:.0f}%" for c, v in pick[tid].most_common(8)))
    for sz in sorted(size_draft[tid]):
        top3 = size_draft[tid][sz].most_common(3); tot = sum(size_draft[tid][sz].values())
        print(f"   size {sz} ({tot}):", " | ".join(f"{d} x{v}" for d, v in top3))
