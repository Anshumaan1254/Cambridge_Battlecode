#!/usr/bin/env python3
"""Which turn path moves our bodies toward / away from enemies (debug builds of bots/god2b: 'PT' lines, brain.cpp turn()):
    python tools/top2/pathtrace.py team-a.stdout [...]

PT r b path task g x y ex ey hp al: the path that took the turn while an enemy was within 9 (0 none, 1 combat fight, 2 combat other,
3 safety, 4 tribute, 5 home trip, 6 shop, 7 alert answer (rally / opportunity), 8 farm, 9 go home, 10 gank, 11 deny altar, 12 pocket dash,
13 g2 deny). The step is read from the body's next PT line (next round): toward / away / still relative to the enemy's position this
round. Also the G2F rules (fight module) per path."""
import collections, sys

PATH = {0: "none", 1: "combat-fight", 2: "combat-other", 3: "safety", 4: "tribute", 5: "home-trip", 6: "shop", 7: "alert", 8: "farm",
        9: "go-home", 10: "gank", 11: "deny-altar", 12: "pocket", 13: "g2-deny"}
TASK = ["none", "farm", "capture", "wait", "tribute", "home", "fight", "flee"]
tot = collections.Counter()
by = collections.defaultdict(collections.Counter)
bytask = collections.defaultdict(collections.Counter)
rules = collections.Counter()
for f in sys.argv[1:]:
    txt = open(f, "rb").read().replace(b"\x00", b"").decode("utf-8", "replace")
    rows = {}
    g2f = {}
    for l in txt.splitlines():
        if l.startswith("PT "):
            d = dict(kv.split("=") for kv in l.split()[1:] if "=" in kv)
            rows[(int(d["b"]), int(d["r"]))] = d
        elif l.startswith("G2F "):
            d = dict(kv.split("=") for kv in l.split()[1:] if "=" in kv)
            g2f[(int(d["b"]), int(d["r"]))] = d["rule"]
    for (b, r), d in rows.items():
        nx = rows.get((b, r + 1))
        if not nx:
            continue
        x, y, ex, ey = int(d["x"]), int(d["y"]), int(d["ex"]), int(d["ey"])
        x2, y2 = int(nx["x"]), int(nx["y"])
        d0 = max(abs(x - ex), abs(y - ey))
        d1 = max(abs(x2 - ex), abs(y2 - ey))
        mv = "still" if (x, y) == (x2, y2) else ("toward" if d1 < d0 else ("away" if d1 > d0 else "side"))
        p = PATH.get(int(d["path"]), d["path"])
        by[p][mv] += 1
        tot[mv] += 1
        t = int(d["task"])
        bytask[(p, TASK[t] if 0 <= t < len(TASK) else t)][mv] += 1
        if (b, r) in g2f and mv == "toward":
            rules[(p, g2f[(b, r)])] += 1
n = sum(tot.values())
print(f"{n} traced contact turns: " + "  ".join(f"{k} {100 * v / n:.1f}%" for k, v in tot.most_common()))
print("\nper path (share of all contact turns; then the move split):")
for p, c in sorted(by.items(), key=lambda kv: -sum(kv[1].values())):
    s = sum(c.values())
    print(f"  {p:13s} {100 * s / n:5.1f}%  " + "  ".join(f"{k} {100 * v / s:4.0f}%" for k, v in c.most_common()))
print("\ntoward-moves by (path, task), share of all toward moves:")
tw = tot["toward"]
for k, c in sorted(bytask.items(), key=lambda kv: -kv[1]["toward"])[:12]:
    print(f"  {str(k):28s} {100 * c['toward'] / max(1, tw):5.1f}%")
print("\ntoward-moves with a G2F rule (path, rule):", rules.most_common(10))
