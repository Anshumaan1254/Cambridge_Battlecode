"""Fight quality: in rounds where a team hits champions, how many of its bodies hit, whether they hit the same target, the target's hp share; kill
conversion (enemy deaths within 3 rounds of being hit by >=2 bodies). python -I focus.py [--us SIDES DECDIR]"""
import gzip, json, sys, os, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools', 'analysis'))
import choice_model as cm
cheb = cm.cheb
def run(games, decdir):
    T = collections.defaultdict(collections.Counter)
    for mid, side, nm in games:
        d = json.load(gzip.open(os.path.join(decdir, mid + '.json.gz')))
        R = {s['r']: {c[0]: c for c in s['ch']} for s in d['rounds']}
        team = {b['index']: b['team'] for b in d['meta']['bodies']}
        byr = collections.defaultdict(list)
        for e in d['events']:
            if 'who' in e and team.get(e['who']) == side and e['k'] in ('Attack', 'Cast ability') and e.get('to'):
                s = R.get(e['r'], {})
                tgt = [q for q in s.values() if q[1] != side and (q[3], q[4]) == tuple(e['to'])]
                if tgt: byr[e['r']].append((e['who'], tgt[0][0]))
        deaths = {(e['who'], e['r']) for e in d['events'] if e['k'] == 'Death' and team.get(e['who']) != side}
        dr = collections.defaultdict(list)
        for w, r in deaths: dr[w].append(r)
        c = T[nm]; c['games'] += 1
        for r, hs in byr.items():
            bodies = {w for w, _ in hs}; tg = collections.Counter(t for _, t in hs)
            c['rounds'] += 1; c['bodyhits'] += len(bodies)
            c['multi'] += len(bodies) >= 2
            if len(bodies) >= 2: c['same'] += tg.most_common(1)[0][1] == len(hs)
        c['kills'] += len(deaths)
    return T
G = json.load(open(os.path.join(HERE, 'games.json')))
games = [(mid, 0 if t['side'] == 'a' else 1, t['name']) for mid, g in G.items() for t in g['teams'] if t['name'] in ('Intercontinental Fish', 'Mite', 'prism best girl', 'willow best girl', 'hello', 'Sponge(Albert and Bob)')]
T = run(games, os.path.join(HERE, 'dec'))
if '--us' in sys.argv:
    i = sys.argv.index('--us'); S = json.load(open(sys.argv[i + 1])); T.update(run([(k, v['ours'], 'US v74') for k, v in S.items()], sys.argv[i + 2]))
    T.update(run([(k, 1 - v['ours'], v['opp'][:14] + ' vs US') for k, v in S.items()], sys.argv[i + 2]))
for nm, c in T.items():
    g = c['games']; print('%-24s champ-hit rounds/g %5.1f  bodies hitting/round %.2f  multi-body rounds %.0f%%  all on one target %.0f%%  kills/g %.1f  champ-hit rounds per kill %.1f' % (
        nm[:24], c['rounds'] / g, c['bodyhits'] / c['rounds'], 100 * c['multi'] / c['rounds'], 100 * c['same'] / max(1, c['multi']), c['kills'] / g, c['rounds'] / max(1, c['kills'])))
