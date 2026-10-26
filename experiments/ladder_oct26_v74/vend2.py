"""For deaths of TYPE (ours / theirs): what was the body doing in the 8 rounds before: fighting champions, hitting camps, walking; where relative to camps/spawn.
python -I vend2.py SIDES.json TYPE DECFILES..."""
import gzip, json, sys, collections
sides = json.load(open(sys.argv[1])); TYPE = sys.argv[2]
cheb = lambda a, b: max(abs(a[0]-b[0]), abs(a[1]-b[1]))
C = {'us': collections.Counter(), 'them': collections.Counter()}; N = {'us': 0, 'them': 0}
ex = []
for f in sys.argv[3:]:
    key = f.replace(chr(92), '/').rsplit('/', 1)[-1].replace('.json.gz', '')
    if key not in sides: continue
    o = sides[key]['ours']; d = json.load(gzip.open(f)); R = {s['r']: s for s in d['rounds']}
    cpos = {(c['x'], c['y']) for c in d['meta']['camps']}
    ev = collections.defaultdict(list)
    for e in d['events']: ev[e['r']].append(e)
    for e in d['events']:
        if e['k'] != 'Death' or e.get('champ') != TYPE: continue
        side = 'us' if e['team'] == o else 'them'; N[side] += 1; r = e['r']
        att_c = att_k = casts = moves = 0; first_en = None
        for rr in range(r - 8, r + 1):
            s = R.get(rr)
            for x in ev.get(rr, []):
                if x.get('who') != e['who']: continue
                if x['k'] in ('Attack', 'Cast ability'):
                    t = tuple(x['to'])
                    if t in cpos: att_k += 1
                    else: att_c += 1
                    if x['k'] == 'Cast ability': casts += 1
                if x['k'] == 'Move': moves += 1
        s = R.get(r - 1) or R.get(r); me = [c for c in s['ch'] if c[0] == e['who']][0]
        pos = (me[3], me[4])
        en_hp = sum(c[5] for c in s['ch'] if c[1] != e['team'] and c[7] and cheb((c[3], c[4]), pos) <= 6)
        al_hp = sum(c[5] for c in s['ch'] if c[1] == e['team'] and c[7] and cheb((c[3], c[4]), pos) <= 6)
        camp_near = sum(1 for p in cpos if cheb(p, pos) <= 4)
        kind = 'champ-fight' if att_c > 0 else ('camp-only' if att_k > 0 else 'no-attack')
        C[side][kind] += 1
        C[side]['camp_near_' + ('y' if camp_near else 'n')] += 1
        C[side]['outnumbered(en_hp>2*al_hp)'] += en_hp > 2 * al_hp
        C[side]['alone(al_hp==self)'] += al_hp <= me[5] + 1
        C[side]['dash_cast'] += casts > 0
        C[side]['early<150'] += r < 150
        C[side]['bag>0'] += me[8] > 0
for s in ('us', 'them'): print(s, N[s], {k: v for k, v in sorted(C[s].items())})
