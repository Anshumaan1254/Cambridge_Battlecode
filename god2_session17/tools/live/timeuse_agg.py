#!/usr/bin/env python3
"""Aggregate tools/live/timeuse.mjs over replays named <map>_<matchId8>.repl26a, split us / them using the match lists.
python tools/live/timeuse_agg.py DIR A B [--us HouseOfCoders]"""
import glob, json, os, subprocess, sys, collections, statistics as st
d, A, B = sys.argv[1], sys.argv[2], sys.argv[3]
us = sys.argv[sys.argv.index("--us") + 1] if "--us" in sys.argv else "HouseOfCoders"
side = {}
for f in glob.glob("experiments/live/lists/*.jsonl") + ["experiments/live/matches_us.jsonl"]:
    for l in open(f, encoding="utf-8"):
        if l.strip():
            m = json.loads(l)
            for t in m["teams"]:
                if t["name"] == us:
                    side[m["matchId"][:8]] = 0 if t["side"] == "a" else 1
files = sorted(glob.glob(os.path.join(d, "*.repl26a")))
out = subprocess.run(["node", "tools/live/timeuse.mjs", A, B] + files, capture_output=True, text=True, env=dict(os.environ))
agg = {"us": collections.defaultdict(list), "them": collections.defaultdict(list)}
for line in out.stdout.splitlines():
    r = json.loads(line)
    if "err" in r: continue
    mid = os.path.basename(r["file"]).rsplit("_", 1)[1][:8]
    if mid not in side: continue
    s = side[mid]
    for t, lab in ((str(s), "us"), (str(1 - s), "them")):
        for k, v in r["teams"][t].items():
            agg[lab][k].append(v)
for lab in ("us", "them"):
    print(lab, len(agg[lab]["dead"]), " ".join(f"{k}={st.mean(v):.3f}" for k, v in agg[lab].items()))
