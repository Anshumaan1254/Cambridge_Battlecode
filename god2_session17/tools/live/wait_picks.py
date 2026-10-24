#!/usr/bin/env python3
"""Block until one of our matches created after --after starts its draft with the given pick prefix (draft ids, in pick order).
python tools/live/wait_picks.py 1,11 --after ISO [--timeout 2400]   (e.g. god2: Vesper then Heart of Ruin)"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli
want = [int(x) for x in sys.argv[1].split(",")]
after = sys.argv[sys.argv.index("--after") + 1]
tmo = int(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 2400
t0 = time.time()
while time.time() - t0 < tmo:
    rc, o, e = cli.run(["matches", "list", "--team", "me", "--limit", "15", "--json"])
    if rc == 0:
        for m in json.loads(o)["matches"]:
            if m["createdAt"] < after:
                continue
            us = next(t for t in m["teams"] if t["name"] == "HouseOfCoders")
            if (us.get("draftPicks") or [])[: len(want)] == want:
                print("LIVE", m["createdAt"], m["map"], us.get("draftPicks"), flush=True)
                sys.exit(0)
    time.sleep(30)
print("TIMEOUT")
sys.exit(1)
