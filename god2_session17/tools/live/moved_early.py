#!/usr/bin/env python3
"""Did our bodies move in rounds 1-3 of our newest match (v12's resumable init walks; v11 stood until round 4)?
python tools/live/moved_early.py [--after ISO]"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli
after = sys.argv[sys.argv.index("--after") + 1] if "--after" in sys.argv else ""
rc, o, e = cli.run(["matches", "list", "--team", "me", "--limit", "10", "--json"])
ms = [m for m in json.loads(o)["matches"] if m["status"] == "finished" and m["createdAt"] >= after]
if not ms:
    print("no finished match yet"); sys.exit(2)
m = ms[0]
us = next(t for t in m["teams"] if t["name"] == "HouseOfCoders")
out = f"C:/battlecode/cache/repl/check_{m['matchId'][:8]}.repl26a"
cli.run(["matches", "download", m["matchId"], "-o", out])
js = """import fs from 'node:fs'; import { decode } from 'file:///C:/battlecode/Cambridge_Battlecode/tools/replay/decode.mjs';
const d = await decode(fs.readFileSync(process.argv[2])); const t = +process.argv[3];
const p = (r) => d.rounds[r].ch.filter((c) => c[1] === t).map((c) => c[3] + ',' + c[4]).join(' ');
console.log(p(1) + ' | ' + p(3));"""
open("tools/live/_me.mjs", "w").write(js)
env = dict(os.environ, CAMBC_CACHE="C:/Users/Anjali Gupta/AppData/Local/cambc/assets")
r = subprocess.run(["node", "tools/live/_me.mjs", out, "0" if us["side"] == "a" else "1"], capture_output=True, text=True, env=env)
os.remove("tools/live/_me.mjs")
a, b = r.stdout.strip().split(" | ")
print(m["createdAt"], m["map"], "r1:", a, "r3:", b, "MOVED" if a != b else "STILL")
