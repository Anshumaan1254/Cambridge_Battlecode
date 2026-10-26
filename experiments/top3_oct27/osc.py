"""Back-and-forth (A-B-A) walking per team from decoded replays: for every alive body and round r, pos(r+2) == pos(r) != pos(r+1).
Split by whether an enemy body is within 6 (Chebyshev) at round r. Also the share of rounds standing still with an enemy within 6 and
not attacking / casting. Rates per 1000 body-rounds.
    python3 -I osc.py INDEX.json [set ...]"""
import collections, gzip, json, sys


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


idx = json.load(open(sys.argv[1]))
want = set(sys.argv[2:])
agg = collections.defaultdict(lambda: collections.Counter())
for path, v in sorted(idx.items()):
    st = v.get('set', '')
    if want and st not in want:
        continue
    d = json.load(gzip.open(path))
    R = {r['r']: r for r in d['rounds']}
    acted = collections.defaultdict(set)
    for e in d['events']:
        if e['k'] in ('Attack', 'Cast ability', 'Capture', 'CaptureGems', 'Shop', 'Place ward') and e.get('who') is not None:
            acted[e['r']].add(e['who'])
    rounds = sorted(R)
    pos = {r: {c[0]: (c[1], c[3], c[4], c[7], c[5], c[6]) for c in R[r]['ch']} for r in rounds}
    for i in range(len(rounds) - 2):
        r0, r1, r2 = rounds[i], rounds[i + 1], rounds[i + 2]
        if r1 != r0 + 1 or r2 != r0 + 2:
            continue
        P0, P1, P2 = pos[r0], pos[r1], pos[r2]
        for b, (team, x, y, alive, hp, mhp) in P0.items():
            if not alive or b not in P1 or b not in P2 or not P1[b][3] or not P2[b][3]:
                continue
            who = 'us' if team == v['ours'] else 'them'
            near = any(t2 != team and a2 and cheb((x, y), (x2, y2)) <= 6 for b2, (t2, x2, y2, a2, _, _) in P0.items())
            k = (st, who, 'near' if near else 'far')
            c = agg[k]
            c['n'] += 1
            a, b1, b2 = (x, y), (P1[b][1], P1[b][2]), (P2[b][1], P2[b][2])
            if b2 == a and b1 != a:
                c['aba'] += 1
            if b1 == a and b not in acted[r1] and near:
                c['still'] += 1
print(f"{'set':6s} {'who':5s} {'zone':5s} {'body-rounds':>11s} {'ABA/1000':>9s} {'idle-near/1000':>15s}")
for k in sorted(agg):
    c = agg[k]
    print(f"{k[0]:6s} {k[1]:5s} {k[2]:5s} {c['n']:11d} {1000 * c['aba'] / max(1, c['n']):9.1f} {1000 * c['still'] / max(1, c['n']):15.1f}")
