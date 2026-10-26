"""Where and how teams bank: Submit gems events, distance of the submitting body from its spawn, bag size at submit, share of gems banked
by altars near spawn vs field altars. python -I banks.py [--us SIDES DECDIR]"""
import gzip, json, sys, os, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools', 'analysis'))
import choice_model as cm
cheb = cm.cheb
def run(games, decdir):
    T = collections.defaultdict(lambda: collections.defaultdict(list))
    for mid, side, nm in games:
        d = json.load(gzip.open(os.path.join(decdir, mid + '.json.gz')))
        R = {s['r']: {c[0]: c for c in s['ch']} for s in d['rounds']}; rs = sorted(R)
        spawn = [(c[3], c[4]) for c in R[rs[0]].values() if c[1] == side]
        team = {b['index']: b['team'] for b in d['meta']['bodies']}
        for e in d['events']:
            if e['k'] == 'Submit gems' and team.get(e.get('who')) == side:
                c = R.get(e['r'], {}).get(e['who'])
                if not c: continue
                ds = min(cheb(p, (c[3], c[4])) for p in spawn)
                t = T[nm]; t['dist'].append(ds); t['bag'].append(c[8]); t['near'].append(ds <= 6)
        T[nm]['games'].append(1)
    return T
G = json.load(open(os.path.join(HERE, 'games.json')))
games = [(mid, 0 if t['side'] == 'a' else 1, t['name']) for mid, g in G.items() for t in g['teams'] if t['name'] in ('Intercontinental Fish', 'Mite', 'prism best girl', 'willow best girl', 'hello', 'Sponge(Albert and Bob)')]
T = run(games, os.path.join(HERE, 'dec'))
if '--us' in sys.argv:
    i = sys.argv.index('--us'); S = json.load(open(sys.argv[i + 1])); T.update(run([(k, v['ours'], 'US v74') for k, v in S.items()], sys.argv[i + 2]))
for nm, t in T.items():
    g = len(t['games']); print('%-24s submits/g %4.1f | dist from spawn mean %.1f median %.0f | at spawn altar (<=6) %.0f%% | bag at submit mean %.0f median %.0f' % (nm[:24], len(t['dist']) / g, st.mean(t['dist']), st.median(t['dist']), 100 * st.mean(t['near']), st.mean(t['bag']), st.median(t['bag'])))
