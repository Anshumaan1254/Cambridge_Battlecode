"""Shared loaders for the IC study (decoded replays from tools/top2/gap/deccache.mjs + the map dumps of tools/mapintel/dump_maps.py).

    import icx
    for g in icx.games('/tmp/claude-0/ic_all.json'): ...   # g.ours (0/1), g.ic, g.map, g.set, g.R (round -> snapshot), g.ev, g.groups ...

Snapshot rows (g.R[r]['ch']): [idx, team, type, x, y, hp, maxHp, alive, gems, gold, kills?, items] (decode.mjs). Groups come from the map
dump (gems, gold, respawn, camp tiles); team A of the replay is the dump's 'ally' side."""
import gzip, json, os, collections

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
DUMP = os.path.join(ROOT, 'experiments/results/mapintel/dump')
KIND = {0: 'wolf', 1: 'elk', 2: 'gem', 3: 'gold', 4: 'golem', 5: 'monolith'}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def dump(mapname):
    for n in (mapname.replace('_', '-'), mapname):
        f = os.path.join(DUMP, n + '.txt')
        if os.path.exists(f):
            break
    else:
        return None
    D = {'groups': [], 'altars': [], 'spawn': {}}
    for line in open(f):
        if line.startswith('MI spawn'):
            p = line.split()
            x0, y0, x1, y1 = map(int, p[3:7])
            D['spawn'][0 if p[2] == 'ally' else 1] = ((x0 + x1) / 2, (y0 + y1) / 2)
        elif line.startswith('MI G '):
            parts = line.split('|')
            h = parts[0].split()
            camps = [tuple(map(int, c.split())) for c in parts[1:] if c.strip()]
            D['groups'].append({'id': int(h[2]), 'gems': int(h[4]), 'gold': int(h[6]), 'respawn': int(h[8]),
                                'camps': [(KIND.get(c[0], str(c[0])), c[1], c[2]) for c in camps]})
        elif line.startswith('MI w') or line.startswith('MI fp'):
            p = line.split()
            if 'w' in p:
                D['w'] = int(p[p.index('w') + 1]); D['h'] = int(p[p.index('h') + 1])
        elif line.startswith('MI bb altars'):
            D['altar_hex'] = line.split()[3]
    for g in D['groups']:
        xs = [c[1] for c in g['camps']]; ys = [c[2] for c in g['camps']]
        g['center'] = (sum(xs) / len(xs), sum(ys) / len(ys))
        g['kinds'] = collections.Counter(c[0] for c in g['camps'])
        g['harmless'] = all(c[0] in ('gem', 'gold') for c in g['camps'])
    D['tile_group'] = {(c[1], c[2]): g['id'] for g in D['groups'] for c in g['camps']}
    return D


class Game:
    pass


def games(index_path, sets=None):
    idx = json.load(open(index_path))
    for path, v in sorted(idx.items()):
        if sets and v.get('set') not in sets:
            continue
        d = json.load(gzip.open(path))
        g = Game()
        g.path, g.map, g.set, g.ours = path, v['map'], v.get('set', ''), v['ours']
        g.ic = 1 - g.ours
        g.res = v['res'][g.ours]
        g.meta = d['meta']
        g.R = {r['r']: r for r in d['rounds']}
        g.rounds = sorted(g.R)
        g.ev = d['events']
        g.team = {b['index']: b['team'] for b in d['meta']['bodies']}
        g.name = {b['index']: b['type'] for b in d['meta']['bodies']}
        g.D = dump(g.map)
        g.final = d['meta']['finalRound']
        yield g


def who_side(g, team):
    return 'us' if team == g.ours else 'ic'
