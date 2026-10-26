"""Print the longest-detour gaps of our bodies: python -I showpath.py SIDES.json DECDIR [N]"""
import gzip, json, sys, os, collections, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools', 'analysis'))
import choice_model as cm
S = json.load(open(sys.argv[1])); dec = sys.argv[2]; N = int(sys.argv[3]) if len(sys.argv) > 3 else 4; cheb = cm.cheb
cands = []
for k, v in S.items():
    d = json.load(gzip.open(os.path.join(dec, k + '.json.gz'))); side = v['ours']
    camps = d['meta']['camps']; cl, ncl = cm.clusters_of(camps); cpos = {(c['x'], c['y']): i for i, c in enumerate(camps)}
    team = {b['index']: b['team'] for b in d['meta']['bodies']}; typ = {b['index']: b['type'] for b in d['meta']['bodies']}
    R = {s['r']: {c[0]: c for c in s['ch']} for s in d['rounds']}
    hits = collections.defaultdict(list)
    for e in d['events']:
        if 'who' in e and team.get(e['who']) == side and e['k'] in ('Attack', 'Cast ability') and tuple(e.get('to', (0, 0))) in cpos:
            hits[e['who']].append((e['r'], cl[cpos[tuple(e['to'])]], tuple(e['to'])))
    for w, hs in hits.items():
        hs.sort(); eps = []
        for r, c, t in hs:
            if eps and eps[-1][0] == c and r - eps[-1][2] <= 12: eps[-1][2] = r
            else: eps.append([c, r, r, t])
        for a, b in zip(eps, eps[1:]):
            if a[0] == b[0] or b[1] - a[2] > 100: continue
            path = []
            for r in range(a[2], b[1] + 1):
                c = R.get(r, {}).get(w)
                if c is None or not c[7]: path = None; break
                path.append((r, c[3], c[4], c[5]))
            if not path: continue
            moves = sum(1 for p, q in zip(path, path[1:]) if p[1:3] != q[1:3]); net = cheb(path[0][1:3], path[-1][1:3])
            cands.append((moves - net, k, typ[w], a[2], b[1], path, d['meta']['width'], d['meta']['height'], camps))
cands.sort(key=lambda x: -x[0]); random.seed(3)
for ex, k, t, r0, r1, path, W, H, camps in random.sample(cands[:80], N):
    print('=== %s %s body %s rounds %d-%d excess %d moves; net %s' % (k[:8], S[k]['map'], t, r0, r1, ex, [path[0][1:3], path[-1][1:3]]))
    x0 = max(0, min(p[1] for p in path) - 6); x1 = min(W, max(p[1] for p in path) + 7); y0 = max(0, min(p[2] for p in path) - 4); y1 = min(H, max(p[2] for p in path) + 5)
    g = [['.'] * (x1 - x0) for _ in range(y1 - y0)]
    for c in camps:
        if x0 <= c['x'] < x1 and y0 <= c['y'] < y1: g[c['y'] - y0][c['x'] - x0] = '#'
    for i, p in enumerate(path):
        sym = chr(ord('a') + i % 26)
        g[p[2] - y0][p[1] - x0] = sym if g[p[2] - y0][p[1] - x0] != '#' else '@'
    g[path[0][2] - y0][path[0][1] - x0] = 'S'; g[path[-1][2] - y0][path[-1][1] - x0] = 'E'
    for row in g: print(''.join(row))
