#!/usr/bin/env python3
"""Block until one of our matches created after --after has draft id DRAFT_ID in our picks (e.g. 5 = Prism), then exit 0.
python tools/live/wait_draft.py DRAFT_ID --after ISO [--timeout 1800]"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cli
did = int(sys.argv[1])
after = sys.argv[sys.argv.index("--after") + 1]
tmo = int(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 1800
t0 = time.time()
while time.time() - t0 < tmo:
    rc, o, e = cli.run(["matches", "list", "--team", "me", "--limit", "15", "--json"])
    if rc == 0:
        for m in json.loads(o)["matches"]:
            if m["createdAt"] < after:
                continue
            us = next(t for t in m["teams"] if t["name"] == "HouseOfCoders")
            if did in (us.get("draftPicks") or []):
                print("LIVE", m["createdAt"], m["map"], us.get("draftPicks"), flush=True)
                sys.exit(0)
    time.sleep(30)
print("TIMEOUT"); sys.exit(1)
