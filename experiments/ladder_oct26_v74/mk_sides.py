#!/usr/bin/env python3
"""Build sides json (key = matchId) for the analysis scripts of ../ladder_oct26_v17/analysis from matches_me.jsonl.
    python mk_sides.py OUT.json [--since ISO] [--opp-rank-max N] [--result loss|win|any] [--opp NAMEPART]"""
import json, sys, os, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--since", default="2026-10-26T10:41:19"); ap.add_argument("--until", default="9")
ap.add_argument("--opp-rank-max", type=int, default=9999); ap.add_argument("--result", default="any"); ap.add_argument("--opp", default=""); ap.add_argument("--kind", default="")
a = ap.parse_args()
ME = "5a103c90-b00b-4d46-8ace-6a3bb058dc72"
L = json.load(open(os.path.join(HERE, "ladder.json"), encoding="utf-8"))["teams"]
rank = {r["teamId"]: i + 1 for i, r in enumerate(L)}
S = {}
for l in open(os.path.join(HERE, "matches_me.jsonl"), encoding="utf-8"):
    m = json.loads(l)
    if m["createdAt"] < a.since or m["createdAt"] > a.until or m["status"] != "finished": continue
    if a.kind and m["kind"] != a.kind: continue
    if not os.path.exists(os.path.join(HERE, "dec", m["matchId"] + ".json.gz")): continue
    ti = [i for i, t in enumerate(m["teams"]) if t["teamId"] == ME][0]; me = m["teams"][ti]; op = m["teams"][1 - ti]
    if rank.get(op["teamId"], 999) > a.opp_rank_max: continue
    if a.result != "any" and me["result"] != a.result: continue
    if a.opp and a.opp.lower() not in op["name"].lower(): continue
    S[m["matchId"]] = {"opp": op["name"], "ours": 0 if me["side"] == "a" else 1, "res": [t["result"] for t in m["teams"]], "map": m["map"], "kind": m["kind"], "group": m["groupId"]}
json.dump(S, open(a.out, "w")); print(len(S), "games ->", a.out)
