#!/usr/bin/env python3
"""Decode work/replays/*.repl26a (from tools/mapintel/ladder_fetch.py) to dec/<matchId>.json.gz; build games.json (matchId -> map, teams, results, sides).
    python decode_top.py [--jobs 6]"""
import gzip, json, os, subprocess, sys, concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
jobs = int(sys.argv[sys.argv.index("--jobs") + 1]) if "--jobs" in sys.argv else 4
sel = {}
for l in open(os.path.join(HERE, "work", "selection.jsonl"), encoding="utf-8"):
    m = json.loads(l); sel[m["matchId"][:8]] = m
os.makedirs(os.path.join(HERE, "dec"), exist_ok=True)
files = sorted(f for f in os.listdir(os.path.join(HERE, "work", "replays")) if f.endswith(".repl26a"))
def one(f):
    h = f.rsplit("_", 1)[1][:8]; m = sel.get(h)
    if not m: return "nosel"
    dp = os.path.join(HERE, "dec", m["matchId"] + ".json.gz")
    if os.path.exists(dp): return "have"
    rp = os.path.join(HERE, "work", "replays", f)
    r = subprocess.run(["node", os.path.join(ROOT, "tools", "replay", "decode.mjs"), rp, "--out", dp + ".tmp"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0: return "fail " + r.stderr[-120:]
    with open(dp + ".tmp", "rb") as a, gzip.open(dp, "wb", 6) as b: b.write(a.read())
    os.remove(dp + ".tmp"); return "ok"
res = {}
with cf.ThreadPoolExecutor(jobs) as ex:
    for f, r in zip(files, ex.map(one, files)): res[r.split()[0]] = res.get(r.split()[0], 0) + 1; (print(f, r) if r not in ("ok", "have") else None)
print(res)
G = {}
for h, m in sel.items():
    if os.path.exists(os.path.join(HERE, "dec", m["matchId"] + ".json.gz")):
        G[m["matchId"]] = {"map": m["map"], "kind": m["kind"], "teams": [{"name": t["name"], "teamId": t["teamId"], "side": t["side"], "result": t["result"], "picks": t["draftPicks"]} for t in m["teams"]]}
json.dump(G, open(os.path.join(HERE, "games.json"), "w")); print(len(G), "games")
