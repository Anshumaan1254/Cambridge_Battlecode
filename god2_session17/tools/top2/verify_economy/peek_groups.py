import gzip, json, sys
from collections import defaultdict
d = json.load(gzip.open(sys.argv[1]))
camps = d['meta']['camps']
pos = {(c[3], c[4]): c[0] for c in camps}
par = {c[0]: c[0] for c in camps}
def f(a):
    while par[a] != a:
        par[a] = par[par[a]]; a = par[a]
    return a
for c in camps:
    for dx, dy in ((1, 0), (0, 1)):
        o = pos.get((c[3] + dx, c[4] + dy))
        if o is not None: par[f(c[0])] = f(o)
comp = defaultdict(list)
for c in camps: comp[f(c[0])].append(c[0])
comps = sorted(comp.values(), key=min)
print(len(comps), 'components;', d['meta']['ngroups'], 'engine groups')
T = ['wolf', 'elk', 'gem', 'gold', 'monolith', 'golem']
for i, cs in enumerate(comps):
    print(i, [(camps[c][3], camps[c][4], T[camps[c][2]]) for c in cs])
# map engine group -> camp via reward flip coincidence
byq = defaultdict(list)
for x in d['C']: byq[x[0]].append(x)
m = defaultdict(set)
for g in d['G']:
    if g[3] == 1:
        for x in byq.get(g[0], []):
            if x[3] == 0: m[g[2]].add(x[2])
cid = {c: i for i, cs in enumerate(comps) for c in cs}
for k in sorted(m): print('engine group', k, '-> comps', sorted({cid[c] for c in m[k]}))
