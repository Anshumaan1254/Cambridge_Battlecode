"""Walking efficiency in the gaps between farm episodes: moves vs the straight-line distance actually covered, back-and-forth steps,
tiles walked twice. python -I detour.py SIDES.json DECDIR"""
import gzip, json, sys, os, collections, statistics as st
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools', 'analysis'))
import choice_model as cm
S = json.load(open(sys.argv[1])); dec = sys.argv[2]; cheb = cm.cheb
for lab, flip in (('us', 0), ('them', 1)):
    M = []; NET = []; REV = []; TWICE = []; EXC = []; stat = collections.Counter(); n = 0
    for k, v in S.items():
        d = json.load(gzip.open(os.path.join(dec, k + '.json.gz'))); side = v['ours'] ^ flip
        camps = d['meta']['camps']; cl, ncl = cm.clusters_of(camps); cpos = {(c['x'], c['y']): i for i, c in enumerate(camps)}
        team = {b['index']: b['team'] for b in d['meta']['bodies']}
        R = {s['r']: {c[0]: c for c in s['ch']} for s in d['rounds']}
        hits = collections.defaultdict(list); other = collections.defaultdict(list)
        for e in d['events']:
            if 'who' in e and team.get(e['who']) == side and e['k'] in ('Attack', 'Cast ability') and tuple(e.get('to', (0, 0))) in cpos:
                hits[e['who']].append((e['r'], cl[cpos[tuple(e['to'])]]))
            elif 'who' in e and team.get(e['who']) == side and (e['k'] in ('Death', 'Shop', 'Teleport complete', 'Submit gems') or (e['k'] in ('Attack', 'Cast ability') and e.get('to') and tuple(e['to']) not in cpos)):
                other[e['who']].append(e['r'])
        for w, hs in hits.items():
            hs.sort(); eps = []
            for r, c in hs:
                if eps and eps[-1][0] == c and r - eps[-1][2] <= 12: eps[-1][2] = r
                else: eps.append([c, r, r])
            for a, b in zip(eps, eps[1:]):
                if a[0] == b[0] or b[1] - a[2] > 150: continue
                if any(a[2] < r < b[1] for r in other[w]): continue
                path = []
                for r in range(a[2], b[1] + 1):
                    c = R.get(r, {}).get(w)
                    if c is None or not c[7]: path = None; break
                    path.append((c[3], c[4]))
                if not path or len(path) < 3: continue
                n += 1
                moves = sum(1 for p, q in zip(path, path[1:]) if p != q)
                net = cheb(path[0], path[-1])
                rev = sum(1 for i in range(2, len(path)) if path[i] == path[i - 2] and path[i] != path[i - 1])
                seen = set(); twice = 0
                for p in path:
                    if p in seen: twice += 1
                    seen.add(p)
                M.append(moves); NET.append(net); REV.append(rev); TWICE.append(twice); EXC.append(moves - net)
                stat['still'] += (len(path) - 1) - moves
                stat['rounds'] += len(path) - 1
    print('%-5s gaps %5d: rounds %.1f = moves %.1f + still %.1f | net displacement %.1f | excess moves %.1f (%.0f%% of moves) | reversals %.1f | tiles revisited %.1f' % (
        lab, n, stat['rounds'] / n, st.mean(M), stat['still'] / n, st.mean(NET), st.mean(EXC), 100 * st.mean(EXC) / st.mean(M), st.mean(REV), st.mean(TWICE)))
