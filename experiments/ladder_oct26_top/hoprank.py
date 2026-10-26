"""At each farm hop: distance to the chosen cluster vs the nearest living cluster (rank by distance, ratio). Per team. python -I hoprank.py [--us SIDES DECDIR]"""
import gzip, json, sys, os, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools', 'analysis'))
import choice_model as cm
cheb = cm.cheb
def run(games, decdir):
    T = collections.defaultdict(lambda: collections.defaultdict(list))
    for mid, side, nm in games:
        d = json.load(gzip.open(os.path.join(decdir, mid + '.json.gz')))
        camps = d['meta']['camps']; cl, ncl = cm.clusters_of(camps)
        eps, cl, ncl = cm.episodes(d, side)
        R = {s['r']: s for s in d['rounds']}
        mem = collections.defaultdict(list)
        for i, c in enumerate(camps): mem[cl[i]].append(i)
        cc = {k: (sum(camps[i]['x'] for i in v) / len(v), sum(camps[i]['y'] for i in v) / len(v)) for k, v in mem.items()}
        for (w, c, r0, dep) in eps:
            sd = R.get(dep); sa = R.get(r0)
            if not sd or not sa: continue
            me = [x for x in sd['ch'] if x[0] == w]
            if not me: continue
            pos = (me[0][3], me[0][4])
            alive = [k for k, v in mem.items() if any(sa['campHp'][i] > 0 for i in v)]
            if c not in alive or len(alive) < 3: continue
            ds = sorted(cheb(pos, cc[k]) for k in alive)
            dc = cheb(pos, cc[c]); rank = ds.index(dc)
            t = T[nm]; t['rank'].append(rank); t['ratio'].append(dc / max(1, ds[0])); t['dist'].append(dc); t['nearest'].append(ds[0]); t['top1'].append(rank == 0); t['top3'].append(rank < 3)
    return T
G = json.load(open(os.path.join(HERE, 'games.json')))
games = [(mid, 0 if t['side'] == 'a' else 1, t['name']) for mid, g in G.items() for t in g['teams'] if t['name'] in ('Intercontinental Fish', 'Mite', 'prism best girl', 'willow best girl', 'hello', 'Sponge(Albert and Bob)')]
T = run(games, os.path.join(HERE, 'dec'))
if '--us' in sys.argv:
    i = sys.argv.index('--us'); S = json.load(open(sys.argv[i + 1])); T.update(run([(k, v['ours'], 'US v74') for k, v in S.items()], sys.argv[i + 2]))
for nm, t in T.items():
    print('%-24s hops %5d | chosen dist %.1f (nearest alive %.1f) | nearest chosen %.0f%%  in 3 nearest %.0f%% | mean rank %.1f | median ratio %.2f' % (nm[:24], len(t['rank']), st.mean(t['dist']), st.mean(t['nearest']), 100 * st.mean(t['top1']), 100 * st.mean(t['top3']), st.mean(t['rank']), st.median(t['ratio'])))
