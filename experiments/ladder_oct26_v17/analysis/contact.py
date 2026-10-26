"""Contact while farming: a body that hit a camp last round and now has an enemy within 6 that was not within 6 last round.
Response over the next 5 rounds and outcome over 12 rounds. python3 -I contact.py SIDES.json DECFILES..."""
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
    cpos = set((c['x'], c['y']) for c in d['meta']['camps'])
    R = {s['r']: s for s in d['rounds']}
    team = {b['index']: b['team'] for b in d['meta']['bodies']}
    camp_hit = set(); champ_hit = set(); died = {}; caps = collections.defaultdict(list)
    for e in d['events']:
        if e['k'] in ('Attack', 'Cast ability') and 'who' in e and e.get('to'):
            (camp_hit if tuple(e['to']) in cpos else champ_hit).add((e['r'], e['who']))
        if e['k'] == 'Death' and 'who' in e: died.setdefault(e['who'], []).append(e['r'])
        if e['k'] == 'CaptureGems' and 'who' in e: caps[e['who']].append(e['r'])
    last_contact = {}
    for r in sorted(R):
        if r < 30 or (r - 1) not in R: continue
        s0, s1 = R[r - 1], R[r]
        P0 = {c[0]: c for c in s0['ch']}
        for c in s1['ch']:
            b = c[0]
            if not c[7] or (r - 1, b) not in camp_hit: continue
            if last_contact.get(b, -99) > r - 15: continue
            o = P0.get(b)
            if not o: continue
            near1 = [q for q in s1['ch'] if q[1] != c[1] and q[7] and cheb((q[3], q[4]), (c[3], c[4])) <= 6]
            near0 = [q for q in s0['ch'] if q[1] != c[1] and q[7] and cheb((q[3], q[4]), (o[3], o[4])) <= 6]
            if not near1 or near0: continue
            last_contact[b] = r
            w = 'us' if c[1] == ours else 'them'
            al = [q for q in s1['ch'] if q[1] == c[1] and q[0] != b and q[7] and cheb((q[3], q[4]), (c[3], c[4])) <= 6]
            ratio = (c[5] + sum(q[5] for q in al)) / max(1, sum(q[5] for q in near1))
            rk = 'adv' if ratio >= 1.2 else 'even' if ratio >= 0.8 else 'dis'
            ch = sum((rr, b) in camp_hit for rr in range(r, r + 5))
            fh = sum((rr, b) in champ_hit for rr in range(r, r + 5))
            # displacement from contact position after 5 rounds
            s5 = R.get(r + 5); moved = 0
            if s5:
                c5 = [q for q in s5['ch'] if q[0] == b][0]
                moved = cheb((c5[3], c5[4]), (c[3], c[4])) if c5[7] else -1
            resp = 'farm' if ch >= 3 else 'fight' if fh >= 1 else 'leave' if moved >= 3 else 'other'
            dead = any(r <= x <= r + 12 for x in died.get(b, []))
            cap = any(r <= x <= r + 15 for x in caps[b])
            for k in (rk, 'ALL'):
                A[w][(k, 'n')] += 1; A[w][(k, resp)] += 1; A[w][(k, resp, 'dead')] += dead; A[w][(k, resp, 'cap')] += cap
print('games', ng)
for w in ('us', 'them'):
    for k in ('ALL', 'adv', 'even', 'dis'):
        n = A[w][(k, 'n')]
        print(f"{w:4s} {k:4s} contacts/g {n/ng:5.1f} | " + ' '.join(f"{x}: {A[w][(k,x)]/max(1,n):.2f} (die {A[w][(k,x,'dead')]/max(1,A[w][(k,x)]):.2f} cap {A[w][(k,x,'cap')]/max(1,A[w][(k,x)]):.2f})" for x in ('farm', 'fight', 'leave', 'other')))
