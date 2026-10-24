#!/usr/bin/env python3
"""Where a traced GOD game's walking goes (LEGEND_TRACE 'T' lines, NULs stripped): per body, rounds with a position change by
task (and by farm target), target switches, and a per-body timeline of (round range, task, group, steps).
  python tools/live/trace_walk.py TRACE.clean [R_MAX]"""
import re, sys, collections
TN = ["none", "farm", "capture", "wait", "tribute", "home", "fight", "flee"]
f, rmax = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 300
rows = collections.defaultdict(dict)
for l in open(f, encoding="utf-8", errors="replace"):
    m = re.match(r"T r=(\d+) (\d+) task=(\d+) g=(-?\d+) pos=\((\d+),(\d+)\) hp=(\d+) gems=(\d+)", l)
    if m:
        r, ty, t, g, x, y, hp, gems = map(int, m.groups())
        if r <= rmax:
            rows[ty][r] = (t, g, x, y, hp, gems)
tot = collections.Counter()
for ty, rs in sorted(rows.items()):
    moved = collections.Counter(); segs = []
    prev = None; cur = None
    for r in sorted(rs):
        t, g, x, y, hp, gems = rs[r]
        mv = prev is not None and (x, y) != prev
        key = (TN[t], g if t in (1, 2, 3) else -1)
        if mv:
            moved[TN[t]] += 1
        if cur is None or cur[0] != key:
            if cur: segs.append(cur)
            cur = [key, r, r, 0]
        cur[2] = r; cur[3] += 1 if mv else 0
        prev = (x, y)
    if cur: segs.append(cur)
    tot.update(moved)
    print(f"body type {ty}: moved {sum(moved.values())} of {len(rs)} rounds:", dict(moved))
    print("   ", " | ".join(f"{a}-{b} {k[0]}{'' if k[1] < 0 else ' G' + str(k[1])} steps {s}" for k, a, b, s in segs if b - a >= 2 or s > 0)[:1500])
print("TOTAL moved by task:", dict(tot))
