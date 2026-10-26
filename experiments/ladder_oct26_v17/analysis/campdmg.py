"""Camp damage per team and per champion type: camp hp drops attributed to the attackers that round.
python3 -I campdmg.py SIDES.json DECFILES..."""
import gzip, json, sys, collections
sides = json.load(open(sys.argv[1]))
cheb = lambda a, b: max(abs(a[0]-b[0]), abs(a[1]-b[1]))
D = {w: collections.Counter() for w in ('us', 'them')}
H = {w: collections.Counter() for w in ('us', 'them')}
ng = 0
for f in sys.argv[2:]:
    key = f.rsplit('/', 1)[-1].replace('.json.gz', '')
    if key not in sides: continue
    ours = sides[key]['ours']; ng += 1
    d = json.load(gzip.open(f))
    camps = d['meta']['camps']; cpos = [(c['x'], c['y']) for c in camps]
    R = {s['r']: s for s in d['rounds']}
    name = {b['index']: b['type'] for b in d['meta']['bodies']}
    team = {b['index']: b['team'] for b in d['meta']['bodies']}
    hits = collections.defaultdict(list)
    for e in d['events']:
        if e['k'] in ('Attack', 'Cast ability') and 'who' in e and e.get('to'):
            hits[e['r']].append((e['who'], tuple(e['to'])))
    rs = sorted(R)
    for i in range(1, len(rs)):
        r0, r1 = rs[i-1], rs[i]
        if r1 != r0 + 1: continue
        h0, h1 = R[r0]['campHp'], R[r1]['campHp']
        for c in range(len(cpos)):
            dl = h0[c] - h1[c]
            if dl <= 0: continue
            att = [w for (w, t) in hits.get(r1, []) if cheb(t, cpos[c]) <= 1]
            direct = [w for (w, t) in hits.get(r1, []) if t == cpos[c]]
            who = direct or att
            if not who: continue
            for w in who:
                side = 'us' if team[w] == ours else 'them'
                D[side][name[w]] += dl / len(who); D[side]['ALL'] += dl / len(who)
        for (w, t) in hits.get(r1, []):
            if t in cpos:
                side = 'us' if team[w] == ours else 'them'
                H[side][name[w]] += 1; H[side]['ALL'] += 1
print('games', ng)
for k in sorted(set(D['us']) | set(D['them']), key=lambda k: -D['us'][k]):
    print(f"{k:12s} dmg/g us {D['us'][k]/ng:8.0f} them {D['them'][k]/ng:8.0f} | camp hits/g us {H['us'][k]/ng:6.1f} them {H['them'][k]/ng:6.1f} | dmg/hit us {D['us'][k]/max(1,H['us'][k]):6.1f} them {D['them'][k]/max(1,H['them'][k]):6.1f}")
