"""Per-map win rate of a study team (ranked list) vs static map features (mapgeo2 feat): Spearman correlations, and the loss-heavy maps
   with their features. python tools/top2/weak/mapcorr.py LIST TEAMID8 [MIN_GAMES=4]"""
import json, sys, collections
path, tid = sys.argv[1], sys.argv[2]; MIN = int(sys.argv[3]) if len(sys.argv) > 3 else 4
F = {}
for l in open('C:/battlecode/cache/an_strategy/mapgeo2.jsonl', encoding='utf-8'):
    g = json.loads(l); f = dict(g['feat']); f['area'] = g['W'] * g['H']; F[g['map']] = f
rec = collections.defaultdict(lambda: [0, 0])
for l in open(path, encoding='utf-8'):
    if not l.strip(): continue
    r = json.loads(l)
    if r.get('status') != 'finished': continue
    t = r['teams']; i = 0 if t[0]['teamId'].startswith(tid) else 1 if t[1]['teamId'].startswith(tid) else -1
    if i < 0: continue
    rec[r['map']][0 if t[i]['result'] == 'win' else 1] += 1
maps = [m for m in rec if sum(rec[m]) >= MIN and m in F]
wr = {m: rec[m][0] / sum(rec[m]) for m in maps}
def rank(xs):
    o = sorted(range(len(xs)), key=lambda i: xs[i]); r = [0] * len(xs); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and xs[o[j + 1]] == xs[o[i]]: j += 1
        for k in range(i, j + 1): r[o[k]] = (i + j) / 2
        i = j + 1
    return r
def spear(a, b):
    ra, rb = rank(a), rank(b); n = len(a); ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)); den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return num / den if den else 0
feats = ['s2s', 'area', 'mincut', 'frontierRel', 'walkShare', 'wall', 'hole', 'bush', 'bushMid', 'groups', 'midShare', 'gemRate', 'mono', 'golem', 'elk', 'heavyMid', 'altars', 'altarMid', 'midGems', 'allGems']
res = sorted(((spear([F[m][f] for m in maps], [wr[m] for m in maps]), f) for f in feats), key=lambda x: x[0])
print(f'{len(maps)} maps (>= {MIN} games), total {sum(sum(rec[m]) for m in maps)} games; Spearman(win rate, feature):')
print('  ' + ', '.join(f'{f} {r:+.2f}' for r, f in res))
