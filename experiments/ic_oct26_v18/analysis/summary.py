"""Candidate table: vs GOD v18 on the big pool (s3 + var17 + gen2) and vs the pack bot _pk3 on s3, with the paired difference to v18's
own games against _pk3 (v18's side of _pk3 vs god18 rows). Bootstrap 95% over maps.
    python3 -I summary.py CAND..."""
import glob, os, random, sys
sys.path.insert(0, '/home/claude/cambridge_battlecode/tools')
import ledger
ROOT = '/home/claude/cambridge_battlecode'


def names(pat):
    return {os.path.splitext(os.path.basename(m))[0] for p in pat.split(',') for m in glob.glob(os.path.join(ROOT, p))}


BIG = names('maps/s3/*.map26a,maps/var17/*.map26a,maps/gen2/*.map26a')
S3 = names('maps/s3/*.map26a')
mg = lambda v: v['gems'][0] - v['gems'][1]


def boot(per):
    vals = [sum(x) / len(x) for x in per.values()]
    if not vals:
        return 0, 0, 0
    rnd = random.Random(7)
    bs = sorted(sum(rnd.choice(vals) for _ in vals) / len(vals) for _ in range(4000))
    return sum(vals) / len(vals), bs[100], bs[3899]


base = ledger.current_rows('_pk3', 'god18', True)
for c in sys.argv[1:]:
    r = {k: v for k, v in ledger.current_rows(c, 'god18', True).items() if k[0] in BIG}
    per = {}
    for (m, s), v in r.items():
        per.setdefault(m, []).append(mg(v))
    w = sum(v['win'] for v in r.values())
    mu, lo, hi = boot(per)
    p = {k: v for k, v in ledger.current_rows(c, '_pk3', True).items() if k[0] in S3}
    pw = sum(v['win'] for v in p.values())
    pp = {}
    for (m, s), v in p.items():
        o = 'B' if s == 'A' else 'A'
        if (m, o) in base:
            pp.setdefault(m, []).append(mg(v) + mg(base[(m, o)]))
    pmu, plo, phi = boot(pp)
    print(f"{c:9s} vs v18 {w:3d}/{len(r):3d} = {100 * w / max(1, len(r)):4.1f}% {mu:+6.1f} [{lo:+6.1f}, {hi:+6.1f}] | vs pack {pw:3d}/{len(p):3d}  paired-to-v18 {pmu:+6.1f} [{plo:+6.1f}, {phi:+6.1f}]")
