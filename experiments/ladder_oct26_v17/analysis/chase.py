"""Chase episodes: a body with an enemy within 8 that steps toward the nearest enemy. Episode = consecutive such rounds.
Outcome: champion hit within the episode or 2 rounds after / camp hit / nothing. Also: body hp ratio vs target, bag.
python3 -I chase.py SIDES.json DECFILES..."""
import gzip, json, sys, collections
sides = json.load(open(sys.argv[1]))
cheb = lambda a, b: max(abs(a[0]-b[0]), abs(a[1]-b[1]))
A = {w: collections.Counter() for w in ('us', 'them')}
L = {w: collections.defaultdict(list) for w in ('us', 'them')}
ng = 0
for f in sys.argv[2:]:
    key = f.rsplit('/', 1)[-1].replace('.json.gz', '')
    if key not in sides: continue
    ours = sides[key]['ours']; ng += 1
    d = json.load(gzip.open(f))
    R = {s['r']: s for s in d['rounds']}
    champhit = collections.defaultdict(bool); camphit = collections.defaultdict(bool); kills = collections.defaultdict(bool)
    for e in d['events']:
        if 'who' in e and e['k'] in ('Attack', 'Cast ability') and e.get('to'):
            s = R.get(e['r'] - 1) or R.get(e['r'])
            if not s: continue
            tm = [c for c in s['ch'] if c[0] == e['who']]
            if not tm: continue
            t = tm[0][1]
            if any(q[1] != t and q[7] and (q[3], q[4]) == tuple(e['to']) for q in s['ch']) or any(q[1] != t and q[7] and cheb((q[3], q[4]), e['to']) <= 1 for q in s['ch']):
                champhit[(e['r'], e['who'])] = True
            else:
                camphit[(e['r'], e['who'])] = True
        if e['k'] == 'Death' and 'by' in e:
            kills[(e['r'], e['by'])] = True
    rs = sorted(R)
    run = {}
    for i in range(1, len(rs)):
        r0, r1 = rs[i-1], rs[i]
        if r1 != r0 + 1 or r1 < 150: continue
        s0, s1 = R[r0], R[r1]
        P0 = {c[0]: c for c in s0['ch']}
        for c in s1['ch']:
            o = P0.get(c[0]); b = c[0]
            if not o or not c[7] or not o[7]:
                if b in run: run.pop(b)
                continue
            t = c[1]; w = 'us' if t == ours else 'them'
            en = [q for q in s0['ch'] if q[1] != t and q[7] and cheb((q[3], q[4]), (o[3], o[4])) <= 8]
            toward = False
            if en and not champhit[(r1, b)] and not camphit[(r1, b)]:
                nd0 = min(cheb((q[3], q[4]), (o[3], o[4])) for q in en)
                nd1 = min(cheb((q[3], q[4]), (c[3], c[4])) for q in en)
                toward = (o[3], o[4]) != (c[3], c[4]) and nd1 < nd0
            if toward:
                if b not in run: run[b] = [r1, r1, w, nd0]
                run[b][1] = r1
            elif b in run:
                st, en_r, ww, d0 = run.pop(b)
                L_ = en_r - st + 1
                out = 'champ' if any(champhit[(rr, b)] for rr in range(st, r1 + 3)) else 'camp' if any(camphit[(rr, b)] for rr in range(st, r1 + 3)) else 'none'
                kill = any(kills[(rr, b)] for rr in range(st, r1 + 6))
                ph = 'early' if st < 400 else 'mid' if st < 800 else 'late'
                A[ww][(ph, out)] += 1; A[ww][(ph, out, 'rounds')] += L_; A[ww][(ph, 'ALL')] += 1; A[ww][(ph, 'ALL', 'rounds')] += L_
                A[ww][(ph, out, 'kill')] += kill
print('games', ng)
for ph in ('early', 'mid', 'late'):
    for w in ('us', 'them'):
        n = A[w][(ph, 'ALL')]
        print(f"{ph:5s} {w:4s} episodes/g {n/ng:5.1f} rounds/g {A[w][(ph,'ALL','rounds')]/ng:6.1f} | " + ' '.join(f"{o}: {A[w][(ph,o)]/ng:5.1f} ep {A[w][(ph,o,'rounds')]/ng:5.1f} r kills {A[w][(ph,o,'kill')]/ng:4.2f}" for o in ('champ', 'camp', 'none')))
