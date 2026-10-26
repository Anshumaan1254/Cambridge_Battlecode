"""Deaths by victim type: context 3 rounds before (enemies/allies within 6, local hp ratio, last action, dash use).
python3 -I deaths.py SIDES.json DECFILES..."""
import gzip, json, sys, collections
sides = json.load(open(sys.argv[1]))
cheb = lambda a, b: max(abs(a[0]-b[0]), abs(a[1]-b[1]))
A = {w: collections.defaultdict(collections.Counter) for w in ('us', 'them')}
ng = 0
for f in sys.argv[2:]:
    key = f.rsplit('/', 1)[-1].replace('.json.gz', '')
    if key not in sides: continue
    ours = sides[key]['ours']; ng += 1
    d = json.load(gzip.open(f))
    cpos = set((c['x'], c['y']) for c in d['meta']['camps'])
    R = {s['r']: s for s in d['rounds']}
    name = {b['index']: b['type'] for b in d['meta']['bodies']}
    team = {b['index']: b['team'] for b in d['meta']['bodies']}
    ev = collections.defaultdict(list)
    for e in d['events']:
        if 'who' in e: ev[e['who']].append(e)
    for e in d['events']:
        if e['k'] != 'Death' or 'who' not in e: continue
        b = e['who']; r = e['r']; w = 'us' if team[b] == ours else 'them'; t = name[b]
        s = R.get(r - 3) or R.get(r - 2)
        if not s: continue
        me = [c for c in s['ch'] if c[0] == b][0]
        en = [q for q in s['ch'] if q[1] != team[b] and q[7] and cheb((q[3], q[4]), (me[3], me[4])) <= 6]
        al = [q for q in s['ch'] if q[1] == team[b] and q[0] != b and q[7] and cheb((q[3], q[4]), (me[3], me[4])) <= 6]
        ratio = (me[5] + sum(q[5] for q in al)) / max(1, sum(q[5] for q in en))
        acts = [x for x in ev[b] if r - 6 <= x['r'] <= r]
        champ_hits = sum(1 for x in acts if x['k'] in ('Attack', 'Cast ability') and x.get('to') and tuple(x['to']) not in cpos)
        camp_hits = sum(1 for x in acts if x['k'] in ('Attack', 'Cast ability') and x.get('to') and tuple(x['to']) in cpos)
        casts = sum(1 for x in acts if x['k'] == 'Cast ability')
        by = e.get('by'); killer = name.get(by, 'camp') if by is not None and by in name else 'camp'
        for k in (t, 'ALL'):
            C = A[w][k]
            C['n'] += 1; C['hp_lt_0.8'] += ratio < 0.8; C['hp_gt_1.2'] += ratio >= 1.2; C['alone'] += not al
            C['en>=2'] += len(en) >= 2; C['fighting'] += champ_hits > 0; C['farming'] += camp_hits > 0 and champ_hits == 0
            C['by_camp'] += killer == 'camp'; C['bag'] += e.get('bag', 0)
print('games', ng)
for w in ('us', 'them'):
    for k, C in sorted(A[w].items(), key=lambda kv: -kv[1]['n']):
        n = C['n']
        print(f"{w:4s} {k:12s} deaths/g {n/ng:4.2f} | " + ' '.join(f"{x} {C[x]/n:.2f}" for x in ('alone', 'en>=2', 'hp_lt_0.8', 'hp_gt_1.2', 'fighting', 'farming', 'by_camp')) + f" bag {C['bag']/n:.0f}")
