"""Contest index of each sprint-3 map from the map dumps: share of the gem value in groups about as near to the enemy spawn as to ours
(|d_us - d_them| <= max(3, 0.15 (d_us + d_them)), Chebyshev from the spawn centres), and the share in groups nearer to us.
    python3 -I contest_idx.py [MAP...]"""
import glob, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icx
ROOT = icx.ROOT
maps = sys.argv[1:] or sorted(os.path.basename(p)[:-7] for p in glob.glob(os.path.join(ROOT, 'maps/s3/*.map26a')))
out = {}
for m in maps:
    D = icx.dump(m)
    if not D or len(D['spawn']) < 2:
        continue
    tot = mid = own = 0.0
    for g in D['groups']:
        v = g['gems'] + 0.15 * g['gold']
        a, b = icx.cheb(g['center'], D['spawn'][0]), icx.cheb(g['center'], D['spawn'][1])
        tot += v
        if abs(a - b) <= max(3, 0.15 * (a + b)):
            mid += v
        elif a < b:
            own += v
    out[m] = (mid / tot if tot else 0, own / tot if tot else 0, len(D['groups']))
if __name__ == '__main__':
    for m, (c, o, n) in sorted(out.items(), key=lambda kv: -kv[1][0]):
        print(f"{m:24s} contest {c:5.2f} own {o:5.2f} groups {n}")
