#!/usr/bin/env python3
"""Read-only: download replays (`cambc matches download`) for the matches in a jsonl list and decode them (tools/replay/decode.mjs) to dec/<matchId>.json.gz.
    python fetch_dec.py LIST.jsonl [--since ISO] [--jobs 3] [--kinds ranked,unranked] [--limit N]"""
import json, subprocess, sys, os, gzip, time, argparse, concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ap = argparse.ArgumentParser(); ap.add_argument("list"); ap.add_argument("--since", default=""); ap.add_argument("--jobs", type=int, default=3)
ap.add_argument("--kinds", default="ranked,unranked"); ap.add_argument("--limit", type=int, default=100000); ap.add_argument("--dir", default=HERE)
a = ap.parse_args()
os.makedirs(os.path.join(a.dir, "replays"), exist_ok=True); os.makedirs(os.path.join(a.dir, "dec"), exist_ok=True)
rows = [json.loads(l) for l in open(a.list, encoding="utf-8") if l.strip()]
rows = [m for m in rows if m["status"] == "finished" and m["createdAt"] >= a.since and m["kind"] in a.kinds.split(",")][: a.limit]
def one(m):
    mid = m["matchId"]; rp = os.path.join(a.dir, "replays", mid + ".repl26a"); dp = os.path.join(a.dir, "dec", mid + ".json.gz")
    if os.path.exists(dp): return "have"
    if not os.path.exists(rp):
        for t in range(8):
            r = subprocess.run(["cambc", "matches", "download", mid, "-o", rp], capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode == 0 and os.path.exists(rp): break
            time.sleep(2 + 3 * t)
        else: return "dlfail " + r.stderr[:100]
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "replay", "decode.mjs"), rp, "--out", dp + ".tmp"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0: return "decfail " + r.stderr[-200:]
    with open(dp + ".tmp", "rb") as f, gzip.open(dp, "wb", 6) as g: g.write(f.read())
    os.remove(dp + ".tmp"); return "ok"
n = {}
with cf.ThreadPoolExecutor(a.jobs) as ex:
    for i, res in enumerate(ex.map(one, rows)):
        n[res.split()[0]] = n.get(res.split()[0], 0) + 1
        if res not in ("ok", "have"): print(rows[i]["matchId"], res)
        if i % 20 == 0: print(i, len(rows), n, flush=True)
print(n)
