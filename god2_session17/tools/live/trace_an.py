#!/usr/bin/env python3
"""Analyse LEGEND_TRACE stdout (extracted with tools/strategy_v2/s13/stdout.mjs): task shares, moving vs standing per task,
target switches (count, why codes, A-B-A flips), per champion.
python tools/live/trace_an.py LOG [LOG...] [--to ROUND]"""
import collections, re, sys
TASKS = ['none', 'farm', 'capture', 'wait', 'tribute', 'home', 'fight', 'flee']
NAMES = ['Ryth', 'Vesper', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HoR']
WHY = {0: 'better target', 1: 'monolith', 2: 'opening rule', 3: 'unreachable', 4: 'reward: lower claimer', 5: 'respawn too far', 6: 'join limit',
       7: 'too heavy', 8: 'no pair', 9: 'steal hp', 10: 'enemy force', 11: 'blacklisted', 12: 'reward: ally on it', 13: 'join reach', 14: 'follow leader'}
to = int(sys.argv[sys.argv.index("--to") + 1]) if "--to" in sys.argv else 10 ** 9
files = [a for a in sys.argv[1:] if not a.startswith("--") and not a.isdigit()]
TR = re.compile(r"T r=(\d+) (\d+) task=(\d+) g=(-?\d+) pos=\((\d+),(\d+)\) hp=(\d+) gems=(\d+) gold=(\d+)")
SWR = re.compile(r"SW r=(\d+) (\d+) old=(-?\d+) new=(-?\d+) sold=(-?[\d.]+) snew=(-?[\d.]+) stold=(\d+) dold=(-?\d+) dnew=(-?\d+) since=(\d+) why=(\d+)")
for f in files:
    txt = open(f, errors="replace").read()
    rec = collections.defaultdict(list)
    for m in TR.finditer(txt):
        r, t, task, g, x, y = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6))
        if r <= to:
            rec[t].append((r, task, g, x, y, int(m.group(7)), int(m.group(8))))
    sw = collections.defaultdict(list)
    for m in SWR.finditer(txt):
        r = int(m.group(1))
        if r <= to:
            sw[int(m.group(2))].append((r, int(m.group(3)), int(m.group(4)), int(m.group(11)), int(m.group(8)), int(m.group(9)), int(m.group(10))))
    print(f"== {f}")
    for t, rows in sorted(rec.items()):
        rows.sort()
        task_n = collections.Counter(); task_mv = collections.Counter()
        for (r0, k0, g0, x0, y0, h0, b0), (r1, k1, g1, x1, y1, h1, b1) in zip(rows, rows[1:]):
            task_n[k1] += 1
            if (x1, y1) != (x0, y0):
                task_mv[k1] += 1
        tot = sum(task_n.values()) or 1
        s = sw[t]
        flips = sum(1 for a, b in zip(s, s[1:]) if b[2] == a[1] and b[0] - a[0] <= 30)
        whys = collections.Counter(WHY.get(x[3], x[3]) for x in s)
        print(f"  {NAMES[t] if t < len(NAMES) else t:8s} turns {tot:4d} | " + " ".join(f"{TASKS[k]} {100 * v / tot:4.1f}% (mv {100 * task_mv[k] / max(1, v):3.0f}%)" for k, v in sorted(task_n.items())))
        print(f"           switches {len(s)} (A-B-A within 30r: {flips}) why: {dict(whys.most_common(6))}")
