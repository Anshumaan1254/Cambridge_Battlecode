#!/usr/bin/env python3
"""Block until our newest finished match shows a build fingerprint (substring of a first purchase), e.g. 'Treasure'.
python tools/live/wait_live.py FINGERPRINT [--after ISO] [--timeout 3600]"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli
from summ import fetch_one, COMPACT
fp = sys.argv[1]
after = sys.argv[sys.argv.index("--after") + 1] if "--after" in sys.argv else ""
tmo = int(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 3600
t0 = time.time()
seen = set()
while time.time() - t0 < tmo:
    rc, o, e = cli.run(["matches", "list", "--team", "me", "--limit", "10", "--json"])
    if rc == 0:
        ms = [m for m in json.loads(o)["matches"] if m["status"] == "finished" and m["createdAt"] >= after and m["matchId"] not in seen]
        for m in ms[:2]:
            seen.add(m["matchId"])
            fetch_one(m)
            p = os.path.join(COMPACT, m["matchId"] + ".json")
            if not os.path.exists(p):
                continue
            r = json.load(open(p, encoding="utf-8"))
            tk = next(t["team"] for t in r["teams"] if t["name"] == "HouseOfCoders")
            first = [x[5][2] for x in r["buys"] if x[1] == tk and isinstance(x[5], list)][:3]
            print(m["createdAt"], m["map"], first, flush=True)
            if any(fp in f for f in first):
                print("LIVE", m["createdAt"], flush=True)
                sys.exit(0)
    time.sleep(60)
print("TIMEOUT")
sys.exit(1)
