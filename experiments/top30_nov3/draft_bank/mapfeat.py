"""Map features for the 86-map pool (maps/s4) from the map JSON pool + the engine's camp groups.
   import mapfeat; mapfeat.features('00ambush') -> dict; mapfeat.groups('00ambush', meta) -> full groups (mapgroups.full_groups)
   Map JSON: /home/claude/data/mapjson_pool/<map>.json (width, height, sym, champs, spawnA/B, rows, camps)
   Half groups: ladder_nov2/map_fail/half_groups.json + v88_bugs/half_groups_ext.json + draft_bank/out/half_groups_more.json"""
import json, os, sys
from collections import deque
BASE = '/home/claude/cambridge_battlecode/experiments'
sys.path.insert(0, f'{BASE}/ladder_nov2/map_fail')
import mapgroups  # noqa: E402
for f in (f'{BASE}/ladder_nov2/v88_bugs/half_groups_ext.json', f'{BASE}/top30_nov3/draft_bank/out/half_groups_more.json'):
    if os.path.exists(f):
        for k, v in json.load(open(f)).items():
            mapgroups.HALF.setdefault(k, v)
POOL = '/home/claude/data/mapjson_pool'
_cache = {}


def mapjson(name):
    return json.load(open(f'{POOL}/{name}.json'))


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def bfs(rows, starts, w, h):
    dist = [[-1] * w for _ in range(h)]
    dq = deque()
    for x, y in starts:
        dist[y][x] = 0
        dq.append((x, y))
    while dq:
        x, y = dq.popleft()
        d = dist[y][x]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and dist[ny][nx] < 0 and rows[ny][nx] not in '#oA':
                    dist[ny][nx] = d + 1
                    dq.append((nx, ny))
    return dist


def groups(name, meta=None):
    """full groups; meta (decoded replay meta) gives camp indices; without it a synthetic meta from the map JSON"""
    mj = mapjson(name)
    if meta is None:
        meta = {'width': mj['width'], 'height': mj['height'], 'camps': [{'index': i, 'x': c['x'], 'y': c['y'], 'type': c['type']} for i, c in enumerate(mj['camps'])]}
    return mapgroups.full_groups(name, meta, mj['sym'])


def features(name):
    if name in _cache:
        return _cache[name]
    mj = mapjson(name)
    w, h, rows = mj['width'], mj['height'], mj['rows']
    G = groups(name)
    altars = [(x, y) for y in range(h) for x in range(w) if rows[y][x] == 'A']
    spA = [tuple(p) for p in mj['spawnA']]
    spB = [tuple(p) for p in mj['spawnB']]
    dA = bfs(rows, spA, w, h)
    dB = bfs(rows, spB, w, h)

    def dist(dm, p):
        best = 99999
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                x, y = p[0] + dx, p[1] + dy
                if 0 <= x < w and 0 <= y < h and dm[y][x] >= 0:
                    best = min(best, dm[y][x])
        return best
    spawn_altars = sum(1 for a in altars if min(dist(dA, a), dist(dB, a)) <= 6)
    passable = sum(1 for y in range(h) for x in range(w) if rows[y][x] not in '#oA')
    gem_groups = [g for g in G if g['gems'] > 0]
    mono = sum(1 for g in G for t in g['types'] if t == 'monolith')
    golem = sum(1 for g in G for t in g['types'] if t == 'golem')
    sx, sy = spB[0]
    f = {'map': name, 'w': w, 'h': h, 'area': w * h, 'passable': passable, 'champs': mj['champs'], 'altars': len(altars),
         'spawn_altars': spawn_altars, 'field_altars': len(altars) - spawn_altars, 'groups': len(G), 'gem_groups': len(gem_groups),
         'gems': sum(g['gems'] for g in G), 'gold': sum(g['gold'] for g in G), 'mono': mono, 'golem': golem,
         'max_group_gems': max((g['gems'] for g in G), default=0), 'big_groups': sum(1 for g in G if g['gems'] >= 40),
         'spawn_dist': dA[sy][sx], 'merged_groups': sum(1 for g in G if g['merged']),
         'camps': len(mj['camps'])}
    f['size_class'] = 'S' if f['area'] <= 40 * 40 else 'M' if f['area'] <= 70 * 70 else 'L'
    f['altar_class'] = ('spawn' if f['field_altars'] == 0 else 'field' if f['spawn_altars'] == 0 else 'mixed')
    _cache[name] = f
    return f


if __name__ == '__main__':
    import csv
    names = sorted(f[:-7] for f in os.listdir('/home/claude/cambridge_battlecode/maps/s4'))
    rows = [features(n) for n in names]
    with open(f'{BASE}/top30_nov3/draft_bank/out/map_features.csv', 'w') as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    for r in rows:
        print(r['map'], r['champs'], r['size_class'], r['altars'], r['altar_class'], 'groups', r['groups'], 'gems', r['gems'], 'gold', r['gold'], 'mono', r['mono'])
