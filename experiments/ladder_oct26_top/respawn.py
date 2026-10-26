"""After a death: rounds Death->Respawn, and Respawn->first camp hit (or first Shop), per team. python -I respawn.py [--us SIDES DECDIR]"""
import gzip, json, sys, os, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools', 'analysis'))
import choice_model as cm
def run(games, decdir):
    T = collections.defaultdict(lambda: collections.defaultdict(list))
    for mid, side, nm in games:
        d = json.load(gzip.open(os.path.join(decdir, mid + '.json.gz')))
        camps = d['meta']['camps']; cpos = {(c['x'], c['y']) for c in camps}
        team = {b['index']: b['team'] for b in d['meta']['bodies']}
        ev = collections.defaultdict(lambda: collections.defaultdict(list))
        for e in d['events']:
            if 'who' not in e or team.get(e['who']) != side: continue
            if e['k'] in ('Attack', 'Cast ability') and e.get('to') and tuple(e['to']) in cpos: ev[e['who']]['hit'].append(e['r'])
            elif e['k'] in ('Death', 'Respawn', 'Shop'): ev[e['who']][e['k']].append(e['r'])
        for w, v in ev.items():
            for dr in v['Death']:
                rs = [r for r in v['Respawn'] if r >= dr]
                if not rs: continue
                rr = rs[0]; nh = [r for r in v['hit'] if r > rr]; ns = [r for r in v['Shop'] if r >= rr]
                t = T[nm]; t['dead'].append(rr - dr)
                if nh: t['to_hit'].append(nh[0] - rr)
                if ns: t['to_shop'].append(ns[0] - rr)
                if nh and ns: t['shop_first'].append(ns[0] < nh[0])
    return T
G = json.load(open(os.path.join(HERE, 'games.json')))
games = [(mid, 0 if t['side'] == 'a' else 1, t['name']) for mid, g in G.items() for t in g['teams'] if t['name'] in ('Intercontinental Fish', 'Mite', 'prism best girl', 'willow best girl', 'hello', 'Sponge(Albert and Bob)')]
T = run(games, os.path.join(HERE, 'dec'))
if '--us' in sys.argv:
    i = sys.argv.index('--us'); S = json.load(open(sys.argv[i + 1])); T.update(run([(k, v['ours'], 'US v74') for k, v in S.items()], sys.argv[i + 2]))
for nm, t in T.items():
    print('%-24s deaths %4d | death->respawn %.1f | respawn->first camp hit mean %.1f median %.0f | respawn->shop mean %.1f | shop before first hit %.0f%%' % (nm[:24], len(t['dead']), st.mean(t['dead']), st.mean(t['to_hit']), st.median(t['to_hit']), st.mean(t['to_shop']) if t['to_shop'] else 0, 100 * st.mean(t['shop_first']) if t['shop_first'] else 0))
