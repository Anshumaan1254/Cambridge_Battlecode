"""Per-team style/efficiency metrics over decoded games. python -I teamstats.py [MINGAMES]"""
import gzip, json, sys, os, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools', 'analysis'))
import choice_model as cm
G = json.load(open(os.path.join(HERE, 'games.json'))); cheb = cm.cheb
T = collections.defaultdict(lambda: collections.Counter()); LST = collections.defaultdict(lambda: collections.defaultdict(list))
for mid, g in G.items():
    d = json.load(gzip.open(os.path.join(HERE, 'dec', mid + '.json.gz')))
    camps = d['meta']['camps']; cl, ncl = cm.clusters_of(camps); cpos = {(c['x'], c['y']): i for i, c in enumerate(camps)}
    R = {s['r']: {c[0]: c for c in s['ch']} for s in d['rounds']}; rs = sorted(R)
    team = {b['index']: b['team'] for b in d['meta']['bodies']}
    acts = {}; hits = collections.defaultdict(list)
    for e in d['events']:
        if 'who' in e and e['k'] in ('Attack', 'Cast ability') and e.get('to'):
            t = tuple(e['to']); acts[(e['r'], e['who'])] = 'camp' if t in cpos else 'champ'
            if t in cpos: hits[e['who']].append((e['r'], cl[cpos[t]]))
    for ti, tm in enumerate(g['teams']):
        side = 0 if tm['side'] == 'a' else 1; nm = tm['name']; c = T[nm]
        c['games'] += 1; c['wins'] += tm['result'] == 'win'
        c['bodies'] += sum(1 for b in d['meta']['bodies'] if b['team'] == side)
        c['banked'] += d['rounds'][-1]['sub'][side]
        c['rounds'] += d['meta']['finalRound']
        for e in d['events']:
            if 'team' in e and e['team'] == side:
                if e['k'] == 'CaptureGems': c['capev'] += 1; c['capgems'] += e['gems']
                elif e['k'] == 'Death': c['deaths'] += 1
        gaps = []; neps = 0
        for w, hs in hits.items():
            if team.get(w) != side: continue
            hs.sort(); eps = []
            for r, q in hs:
                if eps and eps[-1][0] == q and r - eps[-1][2] <= 12: eps[-1][2] = r
                else: eps.append([q, r, r])
            neps += len(eps)
            gaps += [b[1] - a[2] for a, b in zip(eps, eps[1:])]
        c['eps'] += neps; LST[nm]['gap'] += gaps
        # near enemy behaviour
        for w in [b['index'] for b in d['meta']['bodies'] if b['team'] == side]:
            hist = []
            for r in rs[1:]:
                a = R.get(r - 1, {}).get(w); b = R.get(r, {}).get(w)
                if not a or not b or not a[7] or not b[7]: hist = []; continue
                pa = (a[3], a[4]); pb = (b[3], b[4])
                en = [q for q in R[r - 1].values() if q[1] != side and q[7]]
                if not en: hist = []; continue
                near = min(en, key=lambda q: cheb((q[3], q[4]), pa)); dn = cheb((near[3], near[4]), pa)
                if dn > 8: hist = []; continue
                dn2 = cheb((near[3], near[4]), pb)
                kind = 'hit' if (r, w) in acts else ('still' if pa == pb else ('toward' if dn2 < dn else ('away' if dn2 > dn else 'side')))
                hist.append((pb, kind)); c['ne'] += 1; c['ne_' + kind] += 1
                if len(hist) >= 2 and {hist[-2][1], hist[-1][1]} == {'toward', 'away'}: c['flip'] += 1
                if len(hist) >= 3 and hist[-1][0] == hist[-3][0] and hist[-2][0] != hist[-3][0] and hist[-1][1] not in ('hit', 'still') and hist[-2][1] not in ('hit', 'still'): c['aba'] += 1
mn = int(sys.argv[1]) if len(sys.argv) > 1 else 15
print('%-26s %4s %4s | %5s %5s %5s %5s %4s | %5s %5s %5s | %5s %5s %5s %5s' % ('team', 'gms', 'win%', 'capev', 'capgm', 'deaths', 'bank', 'bod', 'ep/b', 'gap', 'medgap', 'hit%', 'still', 'flip%', 'aba%'))
for nm, c in sorted(T.items(), key=lambda kv: -kv[1]['wins'] / max(1, kv[1]['games'])):
    if c['games'] < mn: continue
    n = c['games']; ne = max(1, c['ne'])
    print('%-26s %4d %4.0f | %5.1f %5.0f %5.1f %5.0f %4.1f | %5.1f %5.1f %5.0f | %5.0f %5.0f %5.1f %5.1f' % (nm[:26], n, 100 * c['wins'] / n, c['capev'] / n, c['capgems'] / n, c['deaths'] / n, c['banked'] / n, c['bodies'] / n,
          c['eps'] / c['bodies'], st.mean(LST[nm]['gap']), st.median(LST[nm]['gap']), 100 * c['ne_hit'] / ne, 100 * c['ne_still'] / ne, 100 * c['flip'] / ne, 100 * c['aba'] / ne))
