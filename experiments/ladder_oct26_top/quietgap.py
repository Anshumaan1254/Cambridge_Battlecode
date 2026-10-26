"""Quiet gaps (no enemy within 8 at any round, no death, no champion hit): length, moves, net displacement, kind (shop/bank/none) per team. python -I quietgap.py [--us SIDES DECDIR]"""
import gzip, json, sys, os, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools', 'analysis'))
import choice_model as cm
cheb = cm.cheb
def run(games, decdir):
    T = collections.defaultdict(lambda: collections.defaultdict(list))
    for mid, side, nm in games:
        d = json.load(gzip.open(os.path.join(decdir, mid + '.json.gz')))
        camps = d['meta']['camps']; cl, ncl = cm.clusters_of(camps); cpos = {(c['x'], c['y']): i for i, c in enumerate(camps)}
        team = {b['index']: b['team'] for b in d['meta']['bodies']}
        R = {s['r']: {c[0]: c for c in s['ch']} for s in d['rounds']}
        hits = collections.defaultdict(list); champ = collections.defaultdict(set); other = collections.defaultdict(lambda: collections.defaultdict(list))
        for e in d['events']:
            if 'who' not in e or team.get(e['who']) != side: continue
            if e['k'] in ('Attack', 'Cast ability') and e.get('to'):
                if tuple(e['to']) in cpos: hits[e['who']].append((e['r'], cl[cpos[tuple(e['to'])]]))
                else: champ[e['who']].add(e['r'])
            elif e['k'] in ('Shop', 'Submit gems', 'Teleport complete', 'Death', 'Recall'):
                if e['k'] != 'Recall': other[e['who']][e['k']].append(e['r'])
        for w, hs in hits.items():
            hs.sort(); eps = []
            for r, q in hs:
                if eps and eps[-1][0] == q and r - eps[-1][2] <= 12: eps[-1][2] = r
                else: eps.append([q, r, r])
            for a, b in zip(eps, eps[1:]):
                if a[0] == b[0] or b[1] - a[2] > 200: continue
                if any(a[2] < r < b[1] for r in champ[w]) or other[w]['Death'] and any(a[2] < r < b[1] for r in other[w]['Death']): continue
                quiet = True; path = []
                for r in range(a[2], b[1] + 1):
                    cur = R.get(r, {}).get(w)
                    if cur is None or not cur[7]: quiet = False; break
                    path.append((cur[3], cur[4]))
                    if any(q[1] != side and q[7] and cheb((q[3], q[4]), (cur[3], cur[4])) <= 8 for q in R[r].values()): quiet = False; break
                if not quiet or len(path) < 3: continue
                kind = 'shop' if any(a[2] < r < b[1] for r in other[w]['Shop']) else ('bank' if any(a[2] < r < b[1] for r in other[w]['Submit gems']) else 'plain')
                moves = sum(1 for p, q in zip(path, path[1:]) if p != q); net = cheb(path[0], path[-1])
                t = T[nm]; t[kind + '_len'].append(b[1] - a[2]); t[kind + '_net'].append(net); t[kind + '_mv'].append(moves)
        T[nm]['games'].append(1)
    return T
G = json.load(open(os.path.join(HERE, 'games.json')))
games = [(mid, 0 if t['side'] == 'a' else 1, t['name']) for mid, g in G.items() for t in g['teams'] if t['name'] in ('Intercontinental Fish', 'Mite', 'prism best girl', 'willow best girl', 'hello', 'Sponge(Albert and Bob)')]
T = run(games, os.path.join(HERE, 'dec'))
if '--us' in sys.argv:
    i = sys.argv.index('--us'); S = json.load(open(sys.argv[i + 1])); T.update(run([(k, v['ours'], 'US v74') for k, v in S.items()], sys.argv[i + 2]))
m = lambda x: '%5.1f' % st.mean(x) if x else '  -  '
for nm, t in T.items():
    g = len(t['games'])
    print('%-24s' % nm[:24], ' | '.join('%s n/g %4.1f len %s net %s mv %s' % (k, len(t[k + '_len']) / g, m(t[k + '_len']), m(t[k + '_net']), m(t[k + '_mv'])) for k in ('plain', 'shop', 'bank')))
