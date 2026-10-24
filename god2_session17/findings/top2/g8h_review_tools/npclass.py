"""Classify no-progress (NP) firings in traced runs: python npclass.py RUNDIR [show]
For each NP firing: the body's path over the 16 rounds before (from its T lines): net Chebyshev change to the target is not known here,
so we report: distinct tiles visited, path length, max displacement from the start, whether it was at home (recall) in between,
task sequence, and the best/now distances printed by NP."""
import collections, glob, os, re, sys

rd = sys.argv[1]
show = int(sys.argv[2]) if len(sys.argv) > 2 else 0
cls = collections.Counter()
examples = collections.defaultdict(list)
for d in sorted(glob.glob(rd + "/*_A")):
    f = d + "/team-a.stdout"
    if not os.path.exists(f):
        continue
    txt = open(f, encoding="utf-8", errors="replace").read()
    T = collections.defaultdict(dict)  # body -> round -> (task, g, x, y, gems, doff)
    for m in re.finditer(r"\bT r=(\d+) b=(\d+) ty=\d+ task=(\d+) g=(-?\d+) pos=(\d+),(\d+) hp=\S+ gems=(\d+) gold=\d+ doff=(-?\d+)", txt):
        r, b = int(m.group(1)), int(m.group(2))
        T[b][r] = (int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6)), int(m.group(7)), int(m.group(8)))
    for m in re.finditer(r"\bNP r=(\d+) b=(\d+) ty=(\d+) task=(\d+) g=(-?\d+) pos=(\d+),(\d+) d=(\d+) best=(\d+) since=(-?\d+) doff=(-?\d+) dash=(-?\d+) home=(\d+)", txt):
        r, b, ty, task, g, x, y, dnow, best, since, doff, dash, home = map(int, m.groups())
        hist = [T[b].get(rr) for rr in range(since, r)]
        hist = [h for h in hist if h]
        tiles = {(h[2], h[3]) for h in hist}
        tasks = [h[0] for h in hist]
        groups = {h[1] for h in hist}
        steps = sum(1 for a, c in zip(hist, hist[1:]) if (a[2], a[3]) != (c[2], c[3]))
        span = max([max(abs(h[2] - x), abs(h[3] - y)) for h in hist] + [0])
        missing = (r - since) - len(hist)  # rounds without a T line (recalling / channel / dead / pre-turn returns)
        # classify
        if dnow - best >= 8:
            c = "came back from far (best was set on an earlier visit)"
        elif len(tiles) <= 3:
            c = "stuck in place (<= 3 tiles)"
        elif span <= 3:
            c = "local dither (span <= 3)"
        elif 6 in tasks or 7 in tasks:
            c = "fight/flee in window"
        else:
            c = "walking, no Chebyshev gain"
        key = c + (" [dash-off set]" if (dash >= 0 and doff < r and home < (1 << 20)) else "")
        cls[key] += 1
        if len(examples[key]) < 4:
            examples[key].append(f"{os.path.basename(d)} r={r} b={b} ty={ty} g={g} d={dnow} best={best} since={since} tiles={len(tiles)} steps={steps} span={span} missing={missing} tasks={''.join(map(str, tasks))[-16:]}")
tot = sum(cls.values())
for k, v in cls.most_common():
    print(f"{v:5d} ({100 * v / tot:4.1f}%) {k}")
    if show:
        for e in examples[k]:
            print("        ", e)
