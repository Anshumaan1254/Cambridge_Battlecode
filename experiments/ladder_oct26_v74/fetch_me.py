#!/usr/bin/env python3
"""Read-only: list our team's matches (ranked + unranked) with `cambc matches list --team me --json`, merged by matchId into matches_me.jsonl.
    python fetch_me.py [--pages 20]   (never submits anything)"""
import json, subprocess, sys, os, time
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "matches_me.jsonl")
have = {}
if os.path.exists(out):
    for l in open(out, encoding="utf-8"):
        l = l.strip()
        if l:
            m = json.loads(l); have[m["matchId"]] = m
pages = int(sys.argv[sys.argv.index("--pages") + 1]) if "--pages" in sys.argv else 20
cur = None; new = 0
for p in range(pages):
    cmd = ["cambc", "matches", "list", "--team", "me", "--limit", "100", "--json"] + (["--cursor", cur] if cur else [])
    for attempt in range(10):
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0: break
        sys.stderr.write(r.stderr[:200] + "\n"); time.sleep(3 + attempt * 2)
    else:
        break
    d = json.loads(r.stdout)
    for m in d["matches"]:
        if m["matchId"] not in have: new += 1
        have[m["matchId"]] = m
    cur = d.get("nextCursor")
    if not cur: break
rows = sorted(have.values(), key=lambda m: m["createdAt"], reverse=True)
with open(out, "w", encoding="utf-8") as f:
    for m in rows: f.write(json.dumps(m) + "\n")
print(len(rows), "matches,", new, "new ->", out)
