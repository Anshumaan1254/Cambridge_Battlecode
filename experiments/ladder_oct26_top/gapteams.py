"""Gap composition per team (rounds between a body's farm episodes: dead / champ fight / walk near enemy / walk / stand), plus excess moves. python -I gapteams.py [MINGAMES] [--us SIDES.json DECDIR]"""
import gzip, json, sys, os, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools', 'analysis'))
import choice_model as cm
cheb = cm.cheb
def run(games, decdir):
    """games: list of (matchId, side, label). returns label -> Counter"""
    T = collections.defaultdict(collections.Counter)
    for mid, side, nm in games:
        d = json.load(gzip.open(os.path.join(decdir, mid + '.json.gz')))
        camps = d['meta']['camps']; cl, ncl = cm.clusters_of(camps); cpos = {(c['x'], c['y']): i for i, c in enumerate(camps)}
        team = {b['index']: b['team'] for b in d['meta']['bodies']}
        R = {s['r']: {c[0]: c for c in s['ch']} for s in d['rounds']}; rs = sorted(R)
        acts = {}; hits = collections.defaultdict(list)
        for e in d['events']:
            if 'who' in e and e['k'] in ('Attack', 'Cast ability') and e.get('to'):
                t = tuple(e['to']); acts[(e['r'], e['who'])] = 'camp' if t in cpos else 'champ'
                if t in cpos: hits[e['who']].append((e['r'], cl[cpos[t]]))
        spawn = [(c[3], c[4]) for c in R[rs[0]].values() if c[1] == side]
        c = T[nm]; c['games'] += 1
        for w, hs in hits.items():
            if team.get(w) != side: continue
            hs.sort(); eps = []
            for r, q in hs:
                if eps and eps[-1][0] == q and r - eps[-1][2] <= 12: eps[-1][2] = r
                else: eps.append([q, r, r])
            for a, b in zip(eps, eps[1:]):
                if b[1] - a[2] > 400: continue
                c['gaps'] += 1; c['len'] += b[1] - a[2] - 1
                path = []
                for r in range(a[2], b[1] + 1):
                    cur = R.get(r, {}).get(w); prev = R.get(r - 1, {}).get(w)
                    path.append((cur[3], cur[4]) if cur else None)
                    if r == a[2] or not cur or not prev: continue
                    if r >= b[1]: continue
                    if not cur[7]: cat = 'dead'
                    elif acts.get((r, w)) == 'champ': cat = 'champ'
                    else:
                        en = any(q[1] != side and q[7] and cheb((q[3], q[4]), (cur[3], cur[4])) <= 8 for q in R[r].values())
                        moved = (prev[3], prev[4]) != (cur[3], cur[4])
                        if moved: cat = 'walkE' if en else 'walk'
                        elif min(cheb(p, (cur[3], cur[4])) for p in spawn) <= 2: cat = 'home'
                        else: cat = 'standE' if en else 'stand'
                    c[cat] += 1
    return T
if __name__ == '__main__':
    mn = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 15
    G = json.load(open(os.path.join(HERE, 'games.json')))
    games = [(mid, 0 if t['side'] == 'a' else 1, t['name']) for mid, g in G.items() for t in g['teams']]
    T = run(games, os.path.join(HERE, 'dec'))
    if '--us' in sys.argv:
        i = sys.argv.index('--us'); S = json.load(open(sys.argv[i + 1])); dd = sys.argv[i + 2]
        U = run([(k, v['ours'], 'US v74 (vs top10)') for k, v in S.items()], dd); T.update(U)
    print('%-26s %4s | %5s %5s | %5s %5s %5s %5s %5s %5s' % ('team', 'gms', 'gaps', 'len', 'dead', 'champ', 'walkE', 'walk', 'stand', 'standE'))
    for nm, c in sorted(T.items(), key=lambda kv: kv[1]['len'] / max(1, kv[1]['gaps'])):
        if c['games'] < mn or not c['gaps']: continue
        n = c['gaps']
        print('%-26s %4d | %5.1f %5.1f | %5.1f %5.1f %5.1f %5.1f %5.1f %5.1f' % (nm[:26], c['games'], c['gaps'] / c['games'], c['len'] / n, c['dead'] / n, c['champ'] / n, c['walkE'] / n, c['walk'] / n, c['stand'] / n, c['standE'] / n))
