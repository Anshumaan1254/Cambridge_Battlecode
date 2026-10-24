#!/usr/bin/env python3
"""Download replays of our platform games (rate-limited CLI): python tools/live/fetch_replays.py OUT_DIR --since ISO [--labels a,b] [--max N]
Takes our games from experiments/live/lists/groups_matches.jsonl (unranked groups) and lists/us_ranked.jsonl; --labels keeps only
groups recorded under those labels in experiments/live/groups.jsonl. Files: OUT_DIR/<map>_<matchId8>.repl26a (skips existing)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli
a = sys.argv[1:]
out = a[0]
since = a[a.index("--since") + 1] if "--since" in a else ""
labels = set(a[a.index("--labels") + 1].split(",")) if "--labels" in a else None
mx = int(a[a.index("--max") + 1]) if "--max" in a else 10 ** 9
os.makedirs(out, exist_ok=True)
gl = {}
for l in open("experiments/live/groups.jsonl", encoding="utf-8"):
    r = json.loads(l)
    g = r["resp"].get("groupId") or r["resp"].get("id")
    gl[g] = r.get("label")
ms, seen = [], set()
for f in ("experiments/live/lists/groups_matches.jsonl", "experiments/live/lists/us_ranked.jsonl"):
    if not os.path.exists(f):
        continue
    for l in open(f, encoding="utf-8"):
        m = json.loads(l)
        if m["matchId"] in seen or m.get("status") != "finished" or m["createdAt"] < since:
            continue
        if labels is not None and gl.get(m.get("groupId")) not in labels:
            continue
        seen.add(m["matchId"])
        ms.append(m)
n = 0
for m in ms[:mx]:
    path = os.path.join(out, f"{m['map']}_{m['matchId'][:8]}.repl26a")
    if os.path.exists(path):
        continue
    rc, o, e = cli.run(["matches", "download", m["matchId"], "-o", path])
    n += rc == 0 and os.path.exists(path)
print("downloaded", n, "of", len(ms))
