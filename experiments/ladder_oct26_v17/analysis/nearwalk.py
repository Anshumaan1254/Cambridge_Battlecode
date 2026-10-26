"""Near-enemy behaviour: for each living body with an enemy within 8, what does it do this round and where does it step.
python3 -I nearwalk.py SIDES.json DECFILES..."""
import gzip, json, sys, collections
sides = json.load(open(sys.argv[1]))
cheb = lambda a, b: max(abs(a[0]-b[0]), abs(a[1]-b[1]))
A = {w: collections.Counter() for w in ('us', 'them')}
ng = 0
for f in sys.argv[2:]:
    key = f.rsplit('/', 1)[-1].replace('.json.gz', '')
    if key not in sides: continue
    ours = sides[key]['ours']; ng += 1
    d = json.load(gzip.open(f))
    R = {s['r']: s for s in d['rounds']}
    act = collections.defaultdict(set)
    for e in d['events']:
        if 'who' in e and e['k'] in ('Attack', 'Cast ability'):
            act[(e['r'], e['who'])].add('hit')
        if 'who' in e and e['k'] in ('Submit gems',):
            act[(e['r'], e['who'])].add('trib')
    camps = d['meta'].get('camps') or []
    rs = sorted(R)
    for i in range(1, len(rs)):
        r0, r1 = rs[i-1], rs[i]
        if r1 != r0 + 1: continue
        s0, s1 = R[r0], R[r1]
        P0 = {c[0]: c for c in s0['ch']}
        for c in s1['ch']:
            o = P0.get(c[0])
            if not o or not c[7] or not o[7]: continue
            t = c[1]; w = 'us' if t == ours else 'them'
            if r1 < 150: continue
            ph = 'early' if r1 < 400 else 'mid' if r1 < 800 else 'late'
            en = [q for q in s0['ch'] if q[1] != t and q[7] and cheb((q[3], q[4]), (o[3], o[4])) <= 8]
            if not en: continue
            al = [q for q in s0['ch'] if q[1] == t and q[0] != c[0] and q[7] and cheb((q[3], q[4]), (o[3], o[4])) <= 6]
            ehp = sum(q[5] for q in en); ahp = o[5] + sum(q[5] for q in al)
            ratio = 'adv' if ahp >= 1.2 * ehp else 'even' if ahp >= 0.8 * ehp else 'dis'
            nd0 = min(cheb((q[3], q[4]), (o[3], o[4])) for q in en)
            nd1 = min(cheb((q[3], q[4]), (c[3], c[4])) for q in en)
            moved = (o[3], o[4]) != (c[3], c[4])
            a = act.get((r1, c[0]), set())
            kind = 'hit' if 'hit' in a else 'trib' if 'trib' in a else ('away' if nd1 > nd0 else 'toward' if nd1 < nd0 else 'side') if moved else 'stand'
            A[w][(ph, ratio, kind)] += 1
            A[w][(ph, ratio, 'ALL')] += 1
            A[w][(ph, 'ALL', kind)] += 1
            A[w][(ph, 'ALL', 'ALL')] += 1
print('games', ng)
for ph in ('early', 'mid', 'late'):
    for ratio in ('ALL', 'adv', 'even', 'dis'):
        line = f"{ph:5s} {ratio:4s}"
        for w in ('us', 'them'):
            tot = A[w][(ph, ratio, 'ALL')]
            line += f" | {w} n/g {tot/ng:6.1f} " + ' '.join(f"{k}:{A[w][(ph, ratio, k)]/max(1, tot):.2f}" for k in ('hit', 'trib', 'away', 'toward', 'side', 'stand'))
        print(line)
