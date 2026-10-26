"""Paired per-map margin of candidates against a base bot, for one opponent and pool (release ledger rows), bootstrap 95% over maps.
    python3 -I paired.py BASE OPP POOL CAND..."""
import glob, os, random, sys
sys.path.insert(0, '/home/claude/cambridge_battlecode/tools')
import ledger
ROOT = '/home/claude/cambridge_battlecode'
base, opp, pool = sys.argv[1:4]
maps = {os.path.splitext(os.path.basename(m))[0] for p in pool.split(',') for m in glob.glob(os.path.join(ROOT, p))}
mg = lambda v: v['gems'][0] - v['gems'][1]
B = {k: v for k, v in ledger.current_rows(base, opp, True).items() if k[0] in maps}
for c in sys.argv[4:]:
    R = {k: v for k, v in ledger.current_rows(c, opp, True).items() if k[0] in maps}
    per = {}
    for k, v in R.items():
        if k in B:
            per.setdefault(k[0], []).append(mg(v) - mg(B[k]))
    vals = [sum(x) / len(x) for x in per.values()]
    if not vals:
        print(c, 'no rows'); continue
    rnd = random.Random(7)
    bs = sorted(sum(rnd.choice(vals) for _ in vals) / len(vals) for _ in range(4000))
    w = sum(v['win'] for v in R.values())
    print(f"{c:8s} vs {opp:6s} {w:3d}/{len(R):3d}  paired margin to {base}: {sum(vals) / len(vals):+6.1f} [{bs[100]:+6.1f}, {bs[3899]:+6.1f}] over {len(vals)} maps")
