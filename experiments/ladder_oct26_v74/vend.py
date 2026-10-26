"""Deaths of one champion type: round, local strength balance, last actions. python -I vend.py SIDES.json TYPE DECFILES..."""
import gzip, json, sys, collections
sides = json.load(open(sys.argv[1])); TYPE = sys.argv[2]
cheb = lambda a, b: max(abs(a[0]-b[0]), abs(a[1]-b[1]))
out = {'us': [], 'them': []}
for f in sys.argv[3:]:
    key = f.replace(chr(92), '/').rsplit('/', 1)[-1].replace('.json.gz', '')
    if key not in sides: continue
    ours = sides[key]['ours']; d = json.load(gzip.open(f)); R = {s['r']: s for s in d['rounds']}
    ev = collections.defaultdict(list)
    for e in d['events']: ev[e['r']].append(e)
    for e in d['events']:
        if e['k'] != 'Death' : continue
        if e.get('champ') != TYPE: continue
        side = 'us' if e['team'] == ours else 'them'
        r = e['r']; s = R.get(r - 1) or R.get(r)
        if not s: continue
        me = [c for c in s['ch'] if c[0] == e['who']]
        if not me: continue
        me = me[0]; pos = (me[3], me[4])
        en = [c for c in s['ch'] if c[1] != e['team'] and c[7] and cheb((c[3], c[4]), pos) <= 6]
        al = [c for c in s['ch'] if c[1] == e['team'] and c[7] and c[0] != e['who'] and cheb((c[3], c[4]), pos) <= 6]
        # previous actions of this body
        acts = []
        for rr in range(r - 5, r + 1):
            for x in ev.get(rr, []):
                if x.get('who') == e['who'] and x['k'] in ('Attack', 'Cast ability', 'Move', 'Recall', 'Capture'):
                    acts.append((rr - r, x['k'][:3] + ('%d' % x.get('slot', 0) if x['k'] == 'Cast ability' else '')))
        out[side].append({'r': r, 'hp': me[5], 'gems': me[8], 'en': [c[2] for c in en], 'al': [c[2] for c in al], 'enhp': sum(c[5] for c in en), 'alhp': sum(c[5] for c in al) + me[5], 'acts': acts, 'game': key, 'pos': pos})
for side in ('us', 'them'):
    L = out[side]; n = len(sides)
    print(side, 'deaths', len(L), 'per game', round(len(L) / max(1, len([1 for k in sides])), 2))
    if not L: continue
    rb = collections.Counter(min(x['r'] // 100, 9) for x in L); print(' by round/100', sorted(rb.items()))
    print(' mean hp before', round(sum(x['hp'] for x in L) / len(L)), 'gems lost', sum(x['gems'] for x in L))
    print(' enemies within 6: ', collections.Counter(len(x['en']) for x in L), ' allies within 6:', collections.Counter(len(x['al']) for x in L))
    ratio = [x['alhp'] / max(1, x['enhp']) for x in L if x['en']]
    print(' local hp ratio (ours/theirs) median', sorted(ratio)[len(ratio)//2] if ratio else None)
    cast = sum(1 for x in L if any(a[1] == 'Cas1' for a in x['acts'])); print(' dash/cast1 within 5 rounds before death:', cast, '/', len(L))
    atk = sum(1 for x in L if any(a[1] == 'Att' for a in x['acts'])); print(' attacked within 5 rounds:', atk)
    print(' killers near (enemy types):', collections.Counter(t for x in L for t in x['en']).most_common(8))
