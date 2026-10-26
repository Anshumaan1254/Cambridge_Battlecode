"""Distance between consecutive farm episodes (cluster centroids), walking rounds in the gap, same-cluster revisits. python -I gapdist.py SIDES.json DECDIR"""
import gzip, json, sys, os, collections, statistics as st
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools', 'analysis'))
import choice_model as cm
S = json.load(open(sys.argv[1])); dec = sys.argv[2]; cheb = cm.cheb
for lab, flip in (('us', 0), ('them', 1)):
    D = []; Wk = []; same = 0; n = 0; ratio = []; short = collections.Counter()
    for k, v in S.items():
        d = json.load(gzip.open(os.path.join(dec, k + '.json.gz'))); side = v['ours'] ^ flip
        camps = d['meta']['camps']; cl, ncl = cm.clusters_of(camps); cpos = {(c['x'], c['y']): i for i, c in enumerate(camps)}
        mem = collections.defaultdict(list)
        for i, c in enumerate(camps): mem[cl[i]].append(i)
        cc = {q: (sum(camps[i]['x'] for i in m) / len(m), sum(camps[i]['y'] for i in m) / len(m)) for q, m in mem.items()}
        team = {b['index']: b['team'] for b in d['meta']['bodies']}
        moves = collections.defaultdict(list); hits = collections.defaultdict(list)
        for e in d['events']:
            if 'who' not in e or team.get(e['who']) != side: continue
            if e['k'] == 'Move': moves[e['who']].append(e['r'])
            if e['k'] in ('Attack', 'Cast ability') and tuple(e.get('to', (0, 0))) in cpos: hits[e['who']].append((e['r'], cl[cpos[tuple(e['to'])]]))
        for w, hs in hits.items():
            hs.sort(); eps = []
            for r, c in hs:
                if eps and eps[-1][0] == c and r - eps[-1][2] <= 12: eps[-1][2] = r
                else: eps.append([c, r, r])
            mv = sorted(moves[w])
            for a, b in zip(eps, eps[1:]):
                n += 1
                if a[0] == b[0]: same += 1; continue
                dist = cheb(cc[a[0]], cc[b[0]]); D.append(dist)
                mr = sum(1 for r in mv if a[2] < r < b[1]); Wk.append(mr)
                if dist > 0: ratio.append(mr / dist)
                short['<=8'] += dist <= 8; short['9-20'] += 8 < dist <= 20; short['>20'] += dist > 20
    print('%-5s transitions %5d (same-cluster revisits %.0f%%) | centroid distance mean %.1f median %.0f | walking rounds in gap mean %.1f | walking rounds per tile of centroid distance (median) %.2f | dist classes %s' % (
        lab, n, 100 * same / n, st.mean(D), st.median(D), st.mean(Wk), st.median(ratio), {k: round(v / len(D), 2) for k, v in short.items()}))
