"""Opening per champion: first move, first camp hit (round, target), first capture (round, gems, gold), r100 cap gems/gold.
python3 -I opening.py SIDES.json DECFILES..."""
import gzip, json, sys, collections
sides = json.load(open(sys.argv[1]))
cheb = lambda a, b: max(abs(a[0]-b[0]), abs(a[1]-b[1]))
tot = {w: collections.Counter() for w in ('us', 'them')}
for f in sys.argv[2:]:
    key = f.rsplit('/', 1)[-1].replace('.json.gz', '')
    if key not in sides: continue
    ours = sides[key]['ours']
    d = json.load(gzip.open(f))
    R = {s['r']: s for s in d['rounds']}
    s1 = R[min(R)]
    team = {c[0]: c[1] for c in s1['ch']}
    name = {b['index']: b['type'] for b in d['meta']['bodies']}
    first = collections.defaultdict(dict)
    capg = collections.Counter(); capgold = collections.Counter(); kills100 = collections.Counter()
    for e in d['events']:
        if 'who' not in e: continue
        b = e['who']; F = first[b]
        if e['k'] == 'Move' and 'move' not in F: F['move'] = e['r']
        if e['k'] in ('Attack', 'Cast ability') and 'hit' not in F and e.get('to'):
            s = R.get(e['r'] - 1) or R.get(e['r'])
            if s and not any(q[1] != team[b] and q[7] and cheb((q[3], q[4]), e['to']) <= 1 for q in s['ch']):
                F['hit'] = e['r']; F['hitat'] = tuple(e['to'])
        if e['k'] == 'CaptureGems':
            if 'cap' not in F: F['cap'] = e['r']; F['capg'] = e['gems']
            if e['r'] <= 150: capg[team[b]] += e['gems']; capgold[team[b]] += e['gold']
        if e['k'] == 'Shop' and 'shop' not in F: F['shop'] = e['r']
        if e['k'] == 'Banked' and 'bank' not in F: F['bank'] = e['r']
    print(f"== {sides[key]['map']} {key[-8:]} final {d['meta']['finalRound']}")
    for t in (ours, 1 - ours):
        w = 'us' if t == ours else 'them'
        sp = [c for c in s1['ch'] if c[1] == t][0]
        row = []
        for b in sorted(x for x in team if team[x] == t):
            F = first[b]
            dist = cheb(F['hitat'], (sp[3], sp[4])) if 'hitat' in F else -1
            row.append(f"{name[b][:4]} mv{F.get('move','-')} hit{F.get('hit','-')}@{dist} cap{F.get('cap','-')}/{F.get('capg','-')} shop{F.get('shop','-')}")
            for k in ('move', 'hit', 'cap'):
                if k in F: tot[w][k] += F[k]; tot[w][k + '_n'] += 1
        print(f"  {w:4s} cap150 {capg[t]:4d}g {capgold[t]:4d}$ | " + ' | '.join(row))
        tot[w]['cap150g'] += capg[t]; tot[w]['cap150gold'] += capgold[t]; tot[w]['games'] += 1
for w in ('us', 'them'):
    T = tot[w]
    print(w, 'mean first move %.1f hit %.1f cap %.1f | cap150 gems %.1f gold %.1f' % (T['move']/T['move_n'], T['hit']/T['hit_n'], T['cap']/T['cap_n'], T['cap150g']/T['games'], T['cap150gold']/T['games']))
