#!/usr/bin/env python3
"""Queue many unranked groups, waiting out the 50-per-hour quota: python tools/live/queue_groups.py LABEL_PREFIX [--after ISO]
Sets: A = the groups recorded under label v10 (top 10), B = experiments/live/setB.json, C = experiments/live/setC.json.
Labels: PREFIX, PREFIX+'B', PREFIX+'C'."""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import groups
prefix = sys.argv[1]
after = sys.argv[sys.argv.index("--after") + 1] if "--after" in sys.argv else ""
while after and time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) < after:
    time.sleep(10)
if "--set" in sys.argv:
    todo = [(o, m, s, prefix) for o, m, s, n in json.load(open(sys.argv[sys.argv.index("--set") + 1], encoding="utf-8"))]
else:
    todo = [(r["opp"], r["maps"], r["sides"], prefix) for r in groups.load() if r.get("label") == "v10"]
if "--set" not in sys.argv:
    todo += [(o, m, s, prefix + "B") for o, m, s, n in json.load(open("experiments/live/setB.json", encoding="utf-8"))]
    todo += [(o, m, s, prefix + "C") for o, m, s, n in json.load(open("experiments/live/setC.json", encoding="utf-8"))]
t0 = time.time()
for opp, maps, sides, label in todo:
    while not groups.create(opp, maps, sides, label):
        if time.time() - t0 > 7200:
            sys.exit("gave up")
        time.sleep(60)
    time.sleep(1)
print("queued", len(todo), time.strftime("%H:%M:%S", time.gmtime()))
