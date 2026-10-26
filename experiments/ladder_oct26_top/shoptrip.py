"""Shop/home trips: rounds from the last camp hit to the Shop event (going home) and from it to the next camp hit (coming back); bank trips likewise (Submit gems). us vs top teams.
python -I shoptrip.py [--us SIDES.json DECDIR]"""
import gzip, json, sys, os, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools', 'analysis'))
import choice_model as cm
def run(games, decdir):
    T = collections.defaultdict(lambda: collections.defaultdict(list))
    for mid, side, nm in games:
        d = json.load(gzip.open(os.path.join(decdir, mid + '.json.gz')))
        camps = d['meta']['camps']; cl, ncl = cm.clusters_of(camps); cpos = {(c['x'], c['y']): i for i, c in enumerate(camps)}
        team = {b['index']: b['team'] for b in d['meta']['bodies']}
        hits = collections.defaultdict(list); ev = collections.defaultdict(lambda: collections.defaultdict(list))
        for e in d['events']:
            if 'who' not in e or team.get(e['who']) != side: continue
            if e['k'] in ('Attack', 'Cast ability') and e.get('to') and tuple(e['to']) in cpos: hits[e['who']].append(e['r'])
            if e['k'] in ('Shop', 'Submit gems', 'Teleport complete', 'Death'): ev[e['who']][e['k']].append(e['r'])
        for w, hs in hits.items():
            hs = sorted(set(hs))
            for a, b in zip(hs, hs[1:]):
                if b - a <= 12: continue
                inside = {k: [r for r in ev[w][k] if a < r < b] for k in ('Shop', 'Submit gems', 'Teleport complete', 'Death')}
                if inside['Death']: continue
                if inside['Shop']:
                    s = inside['Shop']; T[nm]['shop_out'].append(s[0] - a); T[nm]['shop_back'].append(b - s[-1]); T[nm]['shop_n'].append(len(s)); T[nm]['shop_total'].append(b - a)
                elif inside['Submit gems']:
                    s = inside['Submit gems']; T[nm]['bank_out'].append(s[0] - a); T[nm]['bank_back'].append(b - s[-1]); T[nm]['bank_total'].append(b - a)
        T[nm]['games'].append(1)
    return T
G = json.load(open(os.path.join(HERE, 'games.json')))
games = [(mid, 0 if t['side'] == 'a' else 1, t['name']) for mid, g in G.items() for t in g['teams'] if t['name'] in ('Intercontinental Fish', 'Mite', 'prism best girl', 'willow best girl', 'hello', 'Sponge(Albert and Bob)')]
T = run(games, os.path.join(HERE, 'dec'))
if '--us' in sys.argv:
    i = sys.argv.index('--us'); S = json.load(open(sys.argv[i + 1])); T.update(run([(k, v['ours'], 'US v74') for k, v in S.items()], sys.argv[i + 2]))
f = lambda x: '%5.1f' % st.mean(x) if x else '  -  '
print('%-24s %4s | shop trips/game  out   back  total | bank trips/game  out   back  total' % ('team', 'gms'))
for nm, t in T.items():
    g = len(t['games'])
    print('%-24s %4d | %5.1f          %s %s %s | %5.1f           %s %s %s' % (nm[:24], g, len(t['shop_out']) / g, f(t['shop_out']), f(t['shop_back']), f(t['shop_total']), len(t['bank_out']) / g, f(t['bank_out']), f(t['bank_back']), f(t['bank_total'])))
