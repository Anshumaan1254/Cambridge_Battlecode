#!/usr/bin/env python3
"""Which of our builds played our newest matches: first purchases per champion (fingerprint of the build order).
python tools/live/whichver.py [--n 4] [--after ISO]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli
from summ import fetch_one, COMPACT
n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 4
after = sys.argv[sys.argv.index("--after") + 1] if "--after" in sys.argv else ""
rc, o, e = cli.run(["matches", "list", "--team", "me", "--limit", "30", "--json"])
ms = [m for m in json.loads(o)["matches"] if m["status"] == "finished" and m["createdAt"] >= after][:n]
for m in ms:
    fetch_one(m)
    r = json.load(open(os.path.join(COMPACT, m["matchId"] + ".json"), encoding="utf-8"))
    tk = next(t["team"] for t in r["teams"] if t["name"] == "HouseOfCoders")
    first = {}
    for x in r["buys"]:
        if x[1] == tk and x[2] not in first:
            first[x[2]] = x[5][2] if isinstance(x[5], list) else x[5]
    print(m["createdAt"][11:19], m["kind"], m["map"], first)
