"""Per champion type time budget (body-rounds per game): dead, camp hit, champ hit, walk (enemy within 8 / not), stand, on spawn.
python3 -I budget.py SIDES.json DECFILES..."""
import gzip, json, sys, collections
sides = json.load(open(sys.argv[1]))
cheb = lambda a, b: max(abs(a[0]-b[0]), abs(a[1]-b[1]))
B = {w: collections.defaultdict(collections.Counter) for w in ('us', 'them')}
ng = 0
cats = ['dead', 'camp', 'champ', 'walkE', 'walk', 'standE', 'stand', 'spawn']
for f in sys.argv[2:]:
    key = f.rsplit('/', 1)[-1].replace('.json.gz', '')
    if key not in sides: continue
    ours = sides[key]['ours']; ng += 1
    d = json.load(gzip.open(f))
    cpos = set((c['x'], c['y']) for c in d['meta']['camps'])
    R = {s['r']: s for s in d['rounds']}
    name = {b['index']: b['type'] for b in d['meta']['bodies']}
    act = {}
    for e in d['events']:
        if e['k'] in ('Attack', 'Cast ability') and 'who' in e and e.get('to'):
            k = (e['r'], e['who'])
            if tuple(e['to']) in cpos: act.setdefault(k, 'camp')
            else: act[k] = 'champ'
    s1 = R[min(R)]
    spawn = {}
    for c in s1['ch']: spawn.setdefault(c[1], []).append((c[3], c[4]))
    rs = sorted(R)
    for i in range(1, len(rs)):
        r0, r1 = rs[i-1], rs[i]
        if r1 != r0 + 1: continue
        P0 = {c[0]: c for c in R[r0]['ch']}
        for c in R[r1]['ch']:
            w = 'us' if c[1] == ours else 'them'; t = name[c[0]]
            o = P0.get(c[0])
            if not c[7]: cat = 'dead'
            elif (c[0], ) and act.get((r1, c[0])): cat = act[(r1, c[0])]
            else:
                en = any(q[1] != c[1] and q[7] and cheb((q[3], q[4]), (c[3], c[4])) <= 8 for q in R[r1]['ch'])
                moved = o is not None and (o[3], o[4]) != (c[3], c[4])
                if moved: cat = 'walkE' if en else 'walk'
                elif min(cheb(p, (c[3], c[4])) for p in spawn[c[1]]) <= 2: cat = 'spawn'
                else: cat = 'standE' if en else 'stand'
            B[w][t][cat] += 1; B[w]['ALL'][cat] += 1
print('games', ng, '(body-rounds per game)')
types = sorted(set(B['us']) | set(B['them']), key=lambda t: -(B['us'][t]['camp'] + B['them'][t]['camp']))
print(f"{'type':12s} " + ' '.join(f'{c:>13s}' for c in cats))
for t in types:
    print(f"{t:12s} " + ' '.join(f"{B['us'][t][c]/ng:6.0f}/{B['them'][t][c]/ng:<6.0f}" for c in cats))
