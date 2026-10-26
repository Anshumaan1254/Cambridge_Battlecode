"""Time structure of farm episodes: travel (dep -> first hit), hitting span, rounds from last hit to next departure; us vs them. python -I epi_time.py SIDES.json DECDIR"""
import gzip, json, sys, os, collections, statistics as st
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools', 'analysis'))
import choice_model as cm
S = json.load(open(sys.argv[1])); dec = sys.argv[2]
for lab, flip in (('us', 0), ('them', 1)):
    T = []; L = []; G = []; n = 0; bodies = 0
    for k, v in S.items():
        d = json.load(gzip.open(os.path.join(dec, k + '.json.gz'))); side = v['ours'] ^ flip
        camps = d['meta']['camps']; cl, ncl = cm.clusters_of(camps); cpos = {(c['x'], c['y']): i for i, c in enumerate(camps)}
        team = {b['index']: b['team'] for b in d['meta']['bodies']}
        hits = collections.defaultdict(list)
        for e in d['events']:
            if 'who' in e and e['k'] in ('Attack', 'Cast ability') and tuple(e.get('to', (0, 0))) in cpos and team.get(e['who']) == side:
                hits[e['who']].append((e['r'], cl[cpos[tuple(e['to'])]]))
        bodies += sum(1 for b in d['meta']['bodies'] if b['team'] == side)
        for w, hs in hits.items():
            hs.sort(); eps = []
            for r, c in hs:
                if eps and eps[-1][0] == c and r - eps[-1][2] <= 12: eps[-1][2] = r; eps[-1][3] += 1
                else: eps.append([c, r, r, 1])
            for a, b in zip(eps, eps[1:]): G.append(b[1] - a[2])    # gap between last hit of one and first of next
            for e in eps: L.append(e[2] - e[1] + 1); T.append(e[3])
            n += len(eps)
    print('%-5s episodes/game %.1f  per body %.1f | episode span %.1f rounds (median %d), hits/episode %.1f | gap last hit -> next first hit: mean %.1f median %d' % (
        lab, n / len(S), n / bodies, st.mean(L), st.median(L), st.mean(T), st.mean(G), st.median(G)))
