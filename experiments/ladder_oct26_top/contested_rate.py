"""CONTESTED efficiency: over alive body-rounds with an enemy champion within 12 tiles: share of rounds hitting camps / walking / standing, by team. python -I quietrate.py [--us SIDES DECDIR]"""
import gzip, json, sys, os, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools', 'analysis'))
import choice_model as cm
cheb = cm.cheb
def run(games, decdir):
    T = collections.defaultdict(collections.Counter)
    for mid, side, nm in games:
        d = json.load(gzip.open(os.path.join(decdir, mid + '.json.gz')))
        cpos = {(c['x'], c['y']) for c in d['meta']['camps']}
        R = {s['r']: {c[0]: c for c in s['ch']} for s in d['rounds']}; rs = sorted(R)
        acts = {}
        for e in d['events']:
            if 'who' in e and e['k'] in ('Attack', 'Cast ability') and e.get('to'): acts[(e['r'], e['who'])] = 'camp' if tuple(e['to']) in cpos else 'champ'
        spawn = [(c[3], c[4]) for c in R[rs[0]].values() if c[1] == side]
        body = [b['index'] for b in d['meta']['bodies'] if b['team'] == side]
        c = T[nm]; c['games'] += 1
        for r in rs[1:]:
            for w in body:
                cur = R[r].get(w); prev = R.get(r - 1, {}).get(w)
                if not cur or not prev or not cur[7]: continue
                if not any(q[1] != side and q[7] and cheb((q[3], q[4]), (cur[3], cur[4])) <= 12 for q in R[r].values()): continue
                c['q'] += 1
                a = acts.get((r, w))
                if a == 'champ': c['champ'] += 1
                elif a == 'camp': c['hit'] += 1
                elif (prev[3], prev[4]) != (cur[3], cur[4]): c['walk'] += 1
                elif min(cheb(p, (cur[3], cur[4])) for p in spawn) <= 2: c['home'] += 1
                else: c['stand'] += 1
    return T
G = json.load(open(os.path.join(HERE, 'games.json')))
games = [(mid, 0 if t['side'] == 'a' else 1, t['name']) for mid, g in G.items() for t in g['teams'] if t['name'] in ('Intercontinental Fish', 'Mite', 'prism best girl', 'willow best girl', 'hello', 'Sponge(Albert and Bob)')]
T = run(games, os.path.join(HERE, 'dec'))
if '--us' in sys.argv:
    i = sys.argv.index('--us'); S = json.load(open(sys.argv[i + 1])); T.update(run([(k, v['ours'], 'US v74') for k, v in S.items()], sys.argv[i + 2]))
for nm, c in T.items():
    q = c['q']; print('%-24s quiet body-rounds/game %5.0f | hit %.3f champ %.3f walk %.3f stand %.3f home %.3f' % (nm[:24], q / c['games'], c['hit'] / q, c['champ'] / q, c['walk'] / q, c['stand'] / q, c['home'] / q))
