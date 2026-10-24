# verify_economy shared loader (independent of tools/top2/economy): match index, map geometry with own BFS, fight dump +
# own vdump per game, captures by camp group, group cycles, tributes. Used by the v_*.py verification scripts.
import gzip, json, os, glob, math
from collections import defaultdict, deque

CACHE = 'C:/battlecode/cache'
KEYS = ['pbg', 'ifish', 'pantheon', 'coo', 'cm', 'nyx']
TEAMID = {'pbg': '38e6d8c4', 'ifish': '1890540d', 'pantheon': '547efb5b', 'coo': '1570a113', 'cm': 'ad5474c2', 'nyx': '6f7fd199'}
CAMPT = ['wolf', 'elk', 'gem', 'gold', 'monolith', 'golem']
GEMS = {'wolf': 4, 'elk': 15, 'gem': 7, 'gold': 0, 'monolith': 200, 'golem': 36}
GOLD = {'wolf': 40, 'elk': 90, 'gem': 0, 'gold': 20, 'monolith': 300, 'golem': 160}
RESP = {'wolf': 40, 'elk': 60, 'gem': 50, 'gold': 50, 'monolith': 150, 'golem': 80}


def load_index():
    """basename(.repl26a) -> {'row': platform row, 'keys': [study keys whose folder holds it]}"""
    idx = {}
    for k in KEYS:
        p = f'{CACHE}/t2/{k}/index.jsonl'
        files = {os.path.basename(f) for f in glob.glob(f'{CACHE}/t2/{k}/*.repl26a')}
        for l in open(p, encoding='utf-8'):
            j = json.loads(l)
            b = f"{j['map']}_{j['matchId'][:8]}.repl26a"
            if b not in files:
                continue
            e = idx.setdefault(b, {'row': j, 'keys': [], 'folder': k})
            e['keys'].append(k)
    return idx


def team_of_key(row, key):
    """team index (0 = side a) of a study team in a platform row, or None"""
    for t in row['teams']:
        if t['teamId'].startswith(TEAMID[key]):
            return 0 if t['side'] == 'a' else 1
    return None


def winner_index(row):
    for t in row['teams']:
        if t['result'] == 'win':
            return 0 if t['side'] == 'a' else 1
    return None


# ---------------- map geometry ----------------
_GEO = None


def bfs(grid, W, H, sources):
    INF = -1
    d = [INF] * (W * H)
    dq = deque()
    for x, y in sources:
        if 0 <= x < W and 0 <= y < H:
            d[y * W + x] = 0
            dq.append((x, y))
    while dq:
        x, y = dq.popleft()
        dd = d[y * W + x] + 1
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if not dx and not dy:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and d[ny * W + nx] < 0 and grid[ny][nx] not in '#oA':
                    d[ny * W + nx] = dd
                    dq.append((nx, ny))
    return d


def load_geo():
    """map -> {W, H, grid, spawn[2], dist[2] (own BFS from each team's spawn tiles), altars[(x, y)]}"""
    global _GEO
    if _GEO is not None:
        return _GEO
    _GEO = {}
    for l in open(f'{CACHE}/an_strategy/mapgeo2.jsonl', encoding='utf-8'):
        j = json.loads(l)
        W, H, grid = j['W'], j['H'], j['grid']
        sp = [[tuple(p) for p in j['spawnA']], [tuple(p) for p in j['spawnB']]]
        alt = [(a[0], a[1]) for a in j['altars']]
        _GEO[j['map']] = {'W': W, 'H': H, 'grid': grid, 'spawn': sp, 'dist': [bfs(grid, W, H, sp[0]), bfs(grid, W, H, sp[1])], 'altars': alt}
    return _GEO


def altar_dist_map(geo):
    """per altar: BFS distance field from the 8 tiles around the altar (stand within Chebyshev 1)"""
    if 'adist' in geo:
        return geo['adist']
    W, H, grid = geo['W'], geo['H'], geo['grid']
    res = []
    for ax, ay in geo['altars']:
        src = [(ax + dx, ay + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx or dy) and 0 <= ax + dx < W and 0 <= ay + dy < H and grid[ay + dy][ax + dx] not in '#oA']
        res.append(bfs(grid, W, H, src))
    geo['adist'] = res
    return res


# ---------------- per game ----------------
def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


class Game:
    def __init__(self, base, ent, geo_all):
        self.base = base
        self.row = ent['row']
        self.keys = ent['keys']
        self.map = self.row['map']
        k = ent['folder']
        self.fd = json.load(gzip.open(f'{CACHE}/t2dump/{k}/{base[:-8]}.json.gz'))
        vp = f'{CACHE}/vecon/d/{base[:-8]}.json.gz'
        self.vd = json.load(gzip.open(vp)) if os.path.exists(vp) else None
        self.geo = geo_all.get(self.map)
        m = self.fd['meta']
        self.final = m['finalRound']
        self.bodies = {b['index']: b for b in m['bodies']}
        self.team = {b['index']: b['team'] for b in m['bodies']}
        self.btype = {b['index']: b['type'] for b in m['bodies']}
        self.camps = m['camps']
        self.win = winner_index(self.row)
        # per-round state: R[r] -> {body: (x, y, hp, maxHp, alive, gems, gold, kills, stunned)}
        self.R = {}
        for rr in self.fd['R']:
            self.R[rr[0]] = {b[0]: tuple(b[1:]) for b in rr[3]}
        self.sub = {rr[0]: (rr[1], rr[2]) for rr in self.fd['R']}
        self._groups()

    def state(self, r):
        """state at the end of round r (falls back to the closest earlier round)"""
        while r not in self.R and r > 0:
            r -= 1
        return self.R.get(r, {})

    def _groups(self):
        camps = self.camps
        pos = {(c['x'], c['y']): c['index'] for c in camps}
        par = {c['index']: c['index'] for c in camps}

        def f(a):
            while par[a] != a:
                par[a] = par[par[a]]
                a = par[a]
            return a
        for c in camps:
            for dx, dy in ((1, 0), (0, 1)):
                o = pos.get((c['x'] + dx, c['y'] + dy))
                if o is not None:
                    par[f(c['index'])] = f(o)
        comp = defaultdict(list)
        for c in camps:
            comp[f(c['index'])].append(c['index'])
        comps = sorted(comp.values(), key=min)
        cby = {c['index']: c for c in camps}
        self.groups = []
        self.camp_group = {}
        for gi, cs in enumerate(comps):
            types = [str(cby[c]['type']) for c in cs]
            types = ['golem' if t == '5' else t for t in types]
            tiles = [(cby[c]['x'], cby[c]['y']) for c in cs]
            g = {'i': gi, 'camps': cs, 'types': types, 'tiles': tiles,
                 'gems': sum(GEMS[t] for t in types), 'gold': sum(GOLD[t] for t in types), 'resp': max(RESP[t] for t in types)}
            if 'monolith' in types:
                g['cls'] = 'monolith'
            elif 'golem' in types:
                g['cls'] = 'golem'
            elif 'elk' in types:
                g['cls'] = 'elk'
            elif 'wolf' in types:
                g['cls'] = 'wolf'
            elif 'gem' in types:
                g['cls'] = 'gem'
            else:
                g['cls'] = 'gold'
            if self.geo:
                W = self.geo['W']
                dA = [self.geo['dist'][0][y * W + x] for x, y in tiles]
                dB = [self.geo['dist'][1][y * W + x] for x, y in tiles]
                dA = [d for d in dA if d >= 0]
                dB = [d for d in dB if d >= 0]
                if dA and dB:
                    a, b = min(dA), min(dB)
                    g['fA'] = a / (a + b) if a + b else 0.5
                    g['dA'], g['dB'] = a, b
            self.groups.append(g)
            for c in cs:
                self.camp_group[c] = gi

    def zone(self, g, team):
        """'own' / 'mid' / 'enemy' of group g for team, or None"""
        if 'fA' not in g:
            return None
        f = g['fA'] if team == 0 else 1 - g['fA']
        return 'own' if f < 0.4 else ('enemy' if f > 0.6 else 'mid')

    def captures(self):
        """list of captures from the vdump: {q, r, g (group index), team, gains {body: (gold, gems)}}"""
        if self.vd is None:
            return None
        if hasattr(self, '_caps'):
            return self._caps
        byq = defaultdict(list)
        for x in self.vd['D']:
            if x[6] == 2:
                byq[x[0]].append(x)
        caps = []
        for gq in self.vd['G']:
            q, r, gi, reward, cteam, kind = gq[:6]
            if kind == 2 and reward == 0:
                gains = {}
                for x in byq.get(q, []):
                    gains[x[2]] = (x[3], x[4])
                teams = {self.team[b] for b in gains}
                team = teams.pop() if len(teams) == 1 else None
                caps.append({'q': q, 'r': r, 'g': gi, 'team': team, 'gains': gains})
        self._caps = caps
        return caps

    def respawns(self):
        """group index -> sorted list of rounds at which its camps came back alive (camp alive transitions at step kind 1)"""
        if self.vd is None:
            return None
        if hasattr(self, '_resp'):
            return self._resp
        res = defaultdict(set)
        for q, r, ci, alive, kind in self.vd['C']:
            if alive == 1:
                res[self.camp_group[ci]].add(r)
        self._resp = {g: sorted(v) for g, v in res.items()}
        return self._resp

    def camp_hits(self):
        """group index -> sorted list of (round, body) champion hits on any of its camps (fight dump cdmg)"""
        if hasattr(self, '_hits'):
            return self._hits
        h = defaultdict(list)
        for q, r, a, ci, amt in self.fd['cdmg']:
            if ci in self.camp_group:
                h[self.camp_group[ci]].append((r, a, amt, q))
        for g in h:
            h[g].sort(key=lambda t: t[3])
        self._hits = h
        return h
