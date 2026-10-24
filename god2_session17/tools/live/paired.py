#!/usr/bin/env python3
"""Paired comparison of two labels' group games (same opponent, map, side): python tools/live/paired.py LABEL_A LABEL_B"""
import json, os, sys, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze import team_stats, side, COMPACT
A, B = sys.argv[1], sys.argv[2]
groups = [json.loads(l) for l in open("experiments/live/groups.jsonl", encoding="utf-8")]
gid = lambda r: r["resp"].get("groupId") or r["resp"].get("id")
lab = {gid(r): r["label"] for r in groups}
ms = [json.loads(l) for l in open("experiments/live/lists/groups_matches.jsonl", encoding="utf-8")]
key = {}
for m in ms:
    l = lab.get(m.get("groupId"))
    if l not in (A, B): continue
    us = next(t for t in m["teams"] if t["name"] == "HouseOfCoders"); op = next(t for t in m["teams"] if t["name"] != "HouseOfCoders")
    key.setdefault((op["name"], m["map"], us["side"]), {})[l] = m["matchId"]
rows = []
for k, v in sorted(key.items()):
    if A in v and B in v and all(os.path.exists(os.path.join(COMPACT, v[x] + ".json")) for x in (A, B)):
        ra =json.load(open(os.path.join(COMPACT, v[A] + ".json"), encoding="utf-8")); rb = json.load(open(os.path.join(COMPACT, v[B] + ".json"), encoding="utf-8"))
        sa = team_stats(ra, side(ra, "HouseOfCoders")); sb = team_stats(rb, side(rb, "HouseOfCoders"))
        oa = team_stats(ra, "teamB" if side(ra, "HouseOfCoders") == "teamA" else "teamA"); ob = team_stats(rb, "teamB" if side(rb, "HouseOfCoders") == "teamA" else "teamA")
        same_opp = oa["draft"] == ob["draft"]
        rows.append((k, sa, sb, oa, ob, same_opp))
wa = sum(r[1]["win"] for r in rows); wb = sum(r[2]["win"] for r in rows)
print(f"{len(rows)} paired games: {A} {wa} wins, {B} {wb} wins; flips {A}->{B}: +{sum(1 for r in rows if r[2]['win'] and not r[1]['win'])} -{sum(1 for r in rows if r[1]['win'] and not r[2]['win'])}")
print(f"opponent draft identical in {sum(r[5] for r in rows)}/{len(rows)}")
for k in ("gems", "opp_gems", "g200", "og200", "gold", "deaths", "kills", "clears", "spent"):
    print(f"  {k:10s} {A} {st.mean(r[1][k] for r in rows):7.1f}  {B} {st.mean(r[2][k] for r in rows):7.1f}")
for k, sa, sb, oa, ob, same in rows:
    if sa["win"] != sb["win"]:
        print(f"  flip {k}: {A} {'W' if sa['win'] else 'L'} {sa['gems']}-{sa['opp_gems']} -> {B} {'W' if sb['win'] else 'L'} {sb['gems']}-{sb['opp_gems']}")
