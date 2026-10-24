# an_economy stage 1: per-game economy facts from tools/top2/economy/econ_dump.mjs dumps (one JSON line per replay file).
#   python tools/top2/economy/econ_game.py KEY [KEY...]  -> C:/battlecode/cache/t2econ/games_<KEY>.jsonl
# KEY = study-team key (pbg, ifish, cm, pantheon, coo, nyx): dumps C:/battlecode/cache/t2econ/<KEY>/*.json.gz, platform rows
# C:/battlecode/cache/t2/<KEY>/index.jsonl (which team index is the study team, who won), map geometry (walking distances,
# altars, spawns) C:/battlecode/cache/an_strategy/mapgeo2.jsonl (tools/live/strat_mapgeo.mjs + strat_mapgroups.mjs).
# Zones: f = d_own / (d_own + d_enemy) by walking distance; own < 0.4, mid 0.4-0.6, enemy > 0.6 (same as an_strategy).
# Per game: teams[t] = income (capture / kill / Marcella gold), spend, gem flow, banked curve, captures (group, class, zone, gems,
# gold, sharers, capturer type), tributes (start, bag, altar, distances, escort, outcome + cause), deaths with bags, objective
# attempts, walking budget per body; groups[] = per group cycles (respawn -> first hit -> dead -> capture -> full), idle rounds,
# holders at respawn.
import gzip, json, math, os, sys, collections
from collections import defaultdict

CACHE = 'C:/battlecode/cache'
GEMS = {'wolf': 4, 'elk': 15, 'gem': 7, 'gold': 0, 'monolith': 200, 'golem': 36}
GOLD = {'wolf': 40, 'elk': 90, 'gem': 0, 'gold': 20, 'monolith': 300, 'golem': 160}
RESP = {'wolf': 40, 'elk': 60, 'gem': 50, 'gold': 50, 'monolith': 150, 'golem': 80}
CP = [100, 200, 300, 400, 500, 600, 800, 1000, 1200, 1500, 2000]
TEAMID = {'pbg': '38e6d8c4', 'ifish': '1890540d', 'pantheon': '547efb5b', 'coo': '1570a113', 'cm': 'ad5474c2', 'nyx': '6f7fd199'}


def cheb(a, b, c, d):
    return max(abs(a - c), abs(b - d))


def load_geo():
    geo = {}
    for l in open(f'{CACHE}/an_strategy/mapgeo2.jsonl', encoding='utf-8'):
        if l.strip():
            g = json.loads(l)
            geo[g['map']] = g
    return geo


class Geo:
    def __init__(self, g):
        self.g = g
        self.W, self.H = g['W'], g['H']
        self.grid = g['grid']
        self.dA, self.dB = g['dA'], g['dB']
        self.spawn = [set(map(tuple, g['spawnA'])), set(map(tuple, g['spawnB']))]
        self.altars = [(a[0], a[1]) for a in g['altars']]
        self._bfs = {}

    def passable(self, x, y):
        return 0 <= x < self.W and 0 <= y < self.H and self.grid[y][x] not in '#oA'

    def d(self, arr, x, y):
        W = self.W
        if 0 <= x < W and 0 <= y < self.H and arr[y * W + x] >= 0:
            return arr[y * W + x]
        best = None
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < self.H and arr[ny * W + nx] >= 0:
                    v = arr[ny * W + nx] + 1
                    best = v if best is None else min(best, v)
        return best

    def f(self, t, x, y):
        a, b = self.d(self.dA, x, y), self.d(self.dB, x, y)
        if a is None or b is None or a + b == 0:
            return None
        f0 = a / (a + b)
        return f0 if t == 0 else 1 - f0

    def dspawn(self, t, x, y):
        return self.d(self.dA if t == 0 else self.dB, x, y)

    def bfs_from(self, x0, y0):
        # walking distance from tiles adjacent to (x0, y0) (altar or any tile), 8-connected, walls / holes / altars blocked
        key = (x0, y0)
        if key in self._bfs:
            return self._bfs[key]
        W, H = self.W, self.H
        d = [-1] * (W * H)
        q = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                nx, ny = x0 + dx, y0 + dy
                if self.passable(nx, ny) and d[ny * W + nx] < 0:
                    d[ny * W + nx] = 0 if (dx or dy) else 0
                    q.append(ny * W + nx)
        h = 0
        while h < len(q):
            k = q[h]; h += 1
            x, y = k % W, k // W
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if not dx and not dy:
                        continue
                    nx, ny = x + dx, y + dy
                    if self.passable(nx, ny) and d[ny * W + nx] < 0:
                        d[ny * W + nx] = d[k] + 1
                        q.append(ny * W + nx)
        self._bfs[key] = d
        return d

    def walk(self, ax, ay, x, y):
        d = self.bfs_from(ax, ay)
        return self.d(d, x, y)

    def on_spawn(self, t, x, y):
        return (x, y) in self.spawn[t]


def zone_of(f):
    if f is None:
        return None
    return 'own' if f < 0.4 else ('enemy' if f > 0.6 else 'mid')


def gclass(types):
    s = set(types)
    for c in ('monolith', 'golem', 'elk', 'wolf', 'gem', 'gold'):
        if c in s:
            return {'monolith': 'mono'}.get(c, c)
    return 'unk'


def load_index(key):
    rows = {}
    for l in open(f'{CACHE}/t2/{key}/index.jsonl', encoding='utf-8'):
        r = json.loads(l)
        rows[r['matchId'][:8]] = r
    return rows


def analyse(path, row, geo):
    d = json.load(gzip.open(path))
    meta = d['meta']
    fname = os.path.basename(path).replace('.json.gz', '.repl26a')
    mapname = fname.rsplit('_', 1)[0]
    G = Geo(geo[mapname])
    tid = TEAMID[row['_key']]
    S = None
    names = {}
    for tm in row['teams']:
        t = 0 if tm['side'] == 'a' else 1
        names[t] = tm['name']
        if tm['teamId'].startswith(tid):
            S = t
            sres = tm['result']
    final = meta['finalRound']
    win = {1: 0, 2: 1}.get(meta['outcome'])
    if win is None:
        win = (S if sres == 'win' else 1 - S)
    bodies = meta['bodies']
    team = {b['index']: b['team'] for b in bodies}
    btype = {b['index']: b['type'] for b in bodies}
    # rounds
    R = {}
    for rr in d['R']:
        R[rr[0]] = rr
    rmax = max(R)
    pos = {b['index']: [None] * (rmax + 2) for b in bodies}
    gems = {b['index']: [0] * (rmax + 2) for b in bodies}
    gold = {b['index']: [0] * (rmax + 2) for b in bodies}
    hpv = {b['index']: [0] * (rmax + 2) for b in bodies}
    mhp = {b['index']: [0] * (rmax + 2) for b in bodies}
    sub = [[0] * (rmax + 2), [0] * (rmax + 2)]
    last = None
    for r in range(0, rmax + 1):
        rr = R.get(r, last)
        if rr is None:
            continue
        last = rr
        sub[0][r], sub[1][r] = rr[1], rr[2]
        for c in rr[3]:
            i = c[0]
            if i not in pos:
                continue
            if c[5]:
                pos[i][r] = (c[1], c[2])
            gems[i][r] = c[6]
            gold[i][r] = c[7]
            hpv[i][r] = c[3]
            mhp[i][r] = c[4]
    P = lambda i, r: pos[i][r] if 0 <= r <= rmax else None
    # groups
    camps = meta['camps']
    cat = {(c['x'], c['y']): c['index'] for c in camps}
    cinfo = {c['index']: c for c in camps}
    par = {c['index']: c['index'] for c in camps}

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a
    for c in camps:
        for dx, dy in ((1, 0), (0, 1)):
            j = cat.get((c['x'] + dx, c['y'] + dy))
            if j is not None:
                par[find(c['index'])] = find(j)
    comp = defaultdict(list)
    for c in camps:
        comp[find(c['index'])].append(c)
    groups = []
    camp2g = {}
    tile2g = {}
    for k, cs in enumerate(comp.values()):
        types = [c['type'] if isinstance(c['type'], str) else 'golem' for c in cs]
        dA = min((G.d(G.dA, c['x'], c['y']) or 10 ** 6) for c in cs)
        dB = min((G.d(G.dB, c['x'], c['y']) or 10 ** 6) for c in cs)
        f0 = dA / (dA + dB) if dA + dB else 0.5
        g = {'i': k, 'camps': [c['index'] for c in cs], 'tiles': [(c['x'], c['y']) for c in cs], 'cls': gclass(types),
             'gems': sum(GEMS.get(t, 0) for t in types), 'gold': sum(GOLD.get(t, 0) for t in types),
             'resp': max(RESP.get(t, 50) for t in types), 'hp': sum(c['hp'] for c in cs), 'f0': round(f0, 3),
             'n': len(cs), 'types': types}
        groups.append(g)
        for c in cs:
            camp2g[c['index']] = k
            tile2g[(c['x'], c['y'])] = k
    gz = lambda t, g: zone_of(g['f0'] if t == 0 else 1 - g['f0'])

    def group_at(p):
        if p is None:
            return -1
        if p in tile2g:
            return tile2g[p]
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (p[0] + dx, p[1] + dy)
                if q in tile2g:
                    return tile2g[q]
        return -1

    def gdist(g, p):
        return min(cheb(p[0], p[1], x, y) for x, y in groups[g]['tiles'])
    # camp hp per round
    nC = len(camps)
    chp = {c['index']: [None] * (rmax + 2) for c in camps}
    C = sorted(d['C'], key=lambda e: e[0])
    curhp = {c['index']: c['hp'] for c in camps}
    ci = 0
    for r in range(0, rmax + 1):
        while ci < len(C) and C[ci][0] <= r:
            curhp[C[ci][1]] = C[ci][2]
            ci += 1
        for c in camps:
            chp[c['index']][r] = curhp[c['index']]
    full0 = {c['index']: c['hp'] for c in camps}
    # hits on groups per round per team
    hitsR = defaultdict(lambda: defaultdict(set))  # g -> r -> set(team)
    hitters = defaultdict(list)  # g -> [(r, body)]
    hits_by_body_r = set()
    for q, r, b, camp, amt in d['cd']:
        g = camp2g.get(camp)
        if g is None:
            continue
        hitsR[g][r].add(team[b])
        hitters[g].append((r, b))
        hits_by_body_r.add((b, r))
    fight_r = set()
    for q, r, a, v, amt, k in d['dm']:
        if a >= 0 and team.get(a) is not None and team.get(v) is not None and team[a] != team[v]:
            fight_r.add((a, r))
    # gold / gem changes
    inc = {t: defaultdict(float) for t in (0, 1)}
    inc_body = defaultdict(lambda: defaultdict(float))
    inc_cp = {t: defaultdict(lambda: [0.0] * len(CP)) for t in (0, 1)}
    spend_cp = {t: [0.0] * len(CP) for t in (0, 1)}
    capraw = defaultdict(lambda: {'gems': 0, 'gold': 0, 'who': []})
    banks = []  # (q, r, body, gems, gold)
    steals = []
    for q, r, b, dg, dgem, kind, ak, ai in d['G']:
        t = team.get(b)
        if t is None:
            continue
        src = None
        if kind == 2:
            src = 'cap'
            p = P(b, r - 1) or P(b, r)
            gi = group_at(p)
            key = (r, t, gi)
            capraw[key]['gems'] += max(0, dgem)
            capraw[key]['gold'] += max(0, dg)
            capraw[key]['who'].append((b, dgem, dg))
        elif kind == 18:
            if dgem < 0:
                banks.append((q, r, b, -dgem, dg))
            if dg > 0:
                src = 'bankgold'
        elif kind in (5, 6, 1, 21, 22, 4):
            if dg > 0:
                src = 'kill'
            if dgem > 0:
                steals.append((q, r, b, dgem))
        elif kind == 13 or kind == 15:
            pass
        if dg > 0:
            s = src or 'other'
            inc[t][s] += dg
            inc_body[b][s] += dg
            for k, cp in enumerate(CP):
                if r <= cp:
                    inc_cp[t][s][k] += dg
        elif dg < 0:
            if kind in (13, 15, 20):
                inc[t]['spend'] += -dg
                inc_body[b]['spend'] += -dg
                for k, cp in enumerate(CP):
                    if r <= cp:
                        spend_cp[t][k] += -dg
            else:
                inc[t]['lossother'] += -dg
    # captures list
    caps = []
    for (r, t, gi), v in sorted(capraw.items()):
        if v['gems'] <= 0 and v['gold'] <= 0:
            continue
        g = groups[gi] if gi >= 0 else None
        who = sorted(v['who'], key=lambda w: -w[1] - w[2])
        near = enear = 0
        if g:
            for i in pos:
                p = P(i, r)
                if p and gdist(gi, p) <= 4:
                    if team[i] == t:
                        near += 1
                    else:
                        enear += 1
        caps.append({'r': r, 't': t, 'g': gi, 'cls': g['cls'] if g else 'unk', 'zone': gz(t, g) if g else zone_of(G.f(t, *(P(who[0][0], r) or (0, 0)))),
                     'gems': v['gems'], 'gold': v['gold'], 'n': len(v['who']), 'who': [w[0] for w in v['who']],
                     'types': [btype[w[0]] for w in v['who']], 'near': near, 'enear': enear,
                     'whoGems': [[btype[w[0]], w[1], w[2]] for w in v['who']]})
    # group cycles
    capsByG = defaultdict(list)
    for c in caps:
        if c['g'] >= 0:
            capsByG[c['g']].append(c)
    cycles = []
    idle = {}
    for gi, g in enumerate(groups):
        cs = g['camps']
        st = 'full'
        tFull = 0
        tHit = hitT = tDead = None
        hcount = [0, 0]
        lastHitT = None
        cl = sorted(capsByG.get(gi, []), key=lambda c: c['r'])
        k = 0
        pend = None
        idle_r = 0
        idle_by_team_side = 0
        for r in range(1, final + 1):
            hp = [chp[c][r] for c in cs]
            full = all(h is not None and h >= full0[c] - 0.5 for h, c in zip(hp, cs))
            dead = all(h is not None and h <= 0 for h in hp)
            hr = hitsR[gi].get(r)
            while st in ('full', 'hit') and k < len(cl) and cl[k]['r'] < tFull:
                k += 1  # stale capture (already resolved before this cycle started)
            capNow = k < len(cl) and cl[k]['r'] <= r
            if st == 'full':
                if hr or capNow:
                    st = 'hit'; tHit = r; hitT = ((0 if 0 in hr else 1) if len(hr) == 1 else -1) if hr else None
                    hcount = [0, 0]
                elif full:
                    idle_r += 1
            if st == 'hit':
                if hr:
                    for t in hr:
                        hcount[t] += 1
                    lastHitT = (0 if 0 in hr else 1) if len(hr) == 1 else -1
                if dead or capNow:
                    st = 'dead'; tDead = r
                elif full and not hr and r > tHit + 1:
                    cycles.append({'g': gi, 'cls': g['cls'], 'f0': g['f0'], 'tFull': tFull, 'tHit': tHit, 'hitT': hitT, 'hc': hcount[:], 'end': 'healed', 'tEnd': r})
                    st = 'full'; tFull = r
            if st == 'dead':
                if k < len(cl) and cl[k]['r'] <= r + 0:
                    c = cl[k]; k += 1
                    pend = {'g': gi, 'cls': g['cls'], 'f0': g['f0'], 'tFull': tFull, 'tHit': tHit, 'hitT': hitT, 'hc': hcount[:], 'lastHitT': lastHitT,
                            'tDead': tDead, 'tCap': c['r'], 'capT': c['t'], 'gems': c['gems'], 'gold': c['gold'], 'end': 'cap'}
                    st = 'resp'
            if st == 'resp':
                if full and r > pend['tCap']:
                    pend['tResp'] = r
                    # holders at respawn: bodies within 4 of the group per team
                    hold = [0, 0]
                    for i in pos:
                        p = P(i, r)
                        if p and gdist(gi, p) <= 4:
                            hold[team[i]] += 1
                    pend['hold'] = hold
                    # presence during the last 20 rounds of the respawn window
                    pres = [0, 0]
                    n = 0
                    for rr in range(max(pend['tCap'] + 1, r - 20), r + 1):
                        n += 1
                        for i in pos:
                            p = P(i, rr)
                            if p and gdist(gi, p) <= 4:
                                pres[team[i]] += 1
                    pend['pres'] = [round(x / max(1, n), 2) for x in pres]
                    cycles.append(pend)
                    pend = None
                    st = 'full'; tFull = r
                    tHit = hitT = tDead = None
        if pend:
            pend['tResp'] = None
            cycles.append(pend)
        if st == 'hit':
            cycles.append({'g': gi, 'cls': g['cls'], 'f0': g['f0'], 'tFull': tFull, 'tHit': tHit, 'hitT': hitT, 'hc': hcount[:], 'end': 'open', 'tEnd': final})
        elif st == 'dead':
            cycles.append({'g': gi, 'cls': g['cls'], 'f0': g['f0'], 'tFull': tFull, 'tHit': tHit, 'hitT': hitT, 'hc': hcount[:], 'tDead': tDead, 'end': 'deadopen', 'tEnd': final})
        idle[gi] = idle_r
    # tributes
    ev = d['ev']
    evb = defaultdict(list)
    for e in ev:
        evb[e['who']].append(e)
    stunsOn = defaultdict(list)
    for q, r, a, v in d['S']:
        stunsOn[v].append((q, r, a))
    deathsOf = defaultdict(list)
    deaths = []
    for q, r, b, t, x, y, bag, killer, kind in d['D']:
        deathsOf[b].append((q, r, bag, killer))
        deaths.append({'q': q, 'r': r, 'who': b, 'type': btype[b], 't': t, 'at': (x, y), 'bag': bag, 'killer': killer,
                       'killerType': btype.get(killer) if killer >= 0 else ('camp' if killer == -1 else 'other'),
                       'zone': zone_of(G.f(t, x, y))})
    locks = [e for e in ev if e['k'] == 'Place altar lock']
    bankq = defaultdict(list)
    for q, r, b, gm, gd in banks:
        bankq[b].append((q, r, gm, gd))
    tribs = []
    for b, es in evb.items():
        t = team[b]
        starts = [e for e in es if e['k'] == 'Submit gems']
        for e in starts:
            q0, r0 = e['q'], e['r']
            altar = tuple(e.get('to') or (-1, -1))
            p0 = P(b, r0) or P(b, r0 - 1)
            bag = gems[b][r0] if r0 <= rmax else 0
            if bag <= 0:
                bag = gems[b][r0 - 1]
            # next start by this body
            nxt = [x for x in starts if x['q'] > q0]
            qn = nxt[0]['q'] if nxt else 10 ** 12
            bk = [x for x in bankq[b] if q0 < x[0] < qn]
            out = {'who': b, 'type': btype[b], 't': t, 'r': r0, 'bag': bag, 'altar': altar, 'at': p0,
                   'subS': sub[t][min(r0, rmax)], 'subO': sub[1 - t][min(r0, rmax)]}
            if bk:
                out['res'] = 'done'; out['rEnd'] = bk[0][1]; out['banked'] = bk[0][2]; out['mgold'] = bk[0][3]
            else:
                # cause: first of death / stun / enemy lock on this altar / own cancel / restart
                cands = []
                for (q, r, bag2, killer) in deathsOf[b]:
                    if q > q0:
                        cands.append((q, 'death', r, btype.get(killer, 'camp'))); break
                for (q, r, a) in stunsOn[b]:
                    if q > q0:
                        cands.append((q, 'stun', r, btype.get(a, 'camp'))); break
                for L in locks:
                    if L['q'] > q0 and team[L['who']] != t and L.get('to') and cheb(L['to'][0], L['to'][1], altar[0], altar[1]) <= 0:
                        cands.append((L['q'], 'lock', L['r'], btype[L['who']])); break
                for x in es:
                    if x['q'] > q0 and x['k'] == 'Cancel channel':
                        cands.append((x['q'], 'cancel', x['r'])); break
                for x in es:
                    if x['q'] > q0 and x['k'] in ('Attack', 'Cast ability', 'Recall', 'Shop', 'Place ward', 'Consumable', 'Place altar lock'):
                        cands.append((x['q'], 'act', x['r'])); break
                if nxt:
                    cands.append((qn, 'restart', nxt[0]['r']))
                if cands:
                    c = min(cands)
                    out['res'] = c[1]; out['rEnd'] = c[2]
                    if len(c) > 3:
                        out['by'] = c[3]
                else:
                    out['res'] = 'open'; out['rEnd'] = final
            # context: altar geometry and people around at the start
            if altar[0] >= 0:
                out['altarF'] = G.f(t, altar[0], altar[1])
                out['altarSpawn'] = G.dspawn(t, altar[0], altar[1])
            allies = enemies = 0
            enemiesStun = 0
            if p0:
                for i in pos:
                    p = P(i, r0)
                    if p and i != b and cheb(p[0], p[1], p0[0], p0[1]) <= 4:
                        if team[i] == t:
                            allies += 1
                        else:
                            enemies += 1
            out['allies4'] = allies
            out['enemies4'] = enemies
            # enemies within 6 at any time during the channel
            emax = 0
            amin = 9
            rEnd = out.get('rEnd', r0)
            for rr in range(r0, min(rEnd, r0 + 60) + 1):
                p1 = P(b, rr)
                if not p1:
                    break
                ne = na2 = 0
                for i in pos:
                    p = P(i, rr)
                    if p and i != b:
                        dd = cheb(p[0], p[1], p1[0], p1[1])
                        if team[i] != t and dd <= 6:
                            ne += 1
                        if team[i] == t and dd <= 4:
                            na2 += 1
                emax = max(emax, ne)
                amin = min(amin, na2)
            out['emax6'] = emax
            out['amin4'] = amin

            # nearest enemy (Chebyshev) at the start, at the end round and the minimum during the channel; fight within 5 rounds after
            def nearest_enemy(rr):
                p1 = P(b, rr)
                if not p1:
                    return None
                ds = [cheb(p[0], p[1], p1[0], p1[1]) for i in pos if team[i] != t for p in [P(i, rr)] if p]
                return min(ds) if ds else None
            rE = out.get('rEnd', r0)
            out['dEs'] = nearest_enemy(r0)
            out['dEe'] = nearest_enemy(max(r0, rE - 1))
            dmin = [nearest_enemy(rr) for rr in range(r0, min(rE, r0 + 80) + 1)]
            dmin = [x for x in dmin if x is not None]
            out['dEmin'] = min(dmin) if dmin else None
            out['fightAfter'] = 1 if any((b, rr) in fight_r for rr in range(rE, rE + 6)) else 0
            out['hpS'] = round(hpv[b][r0] / max(1, mhp[b][r0]), 2)
            # last capture by this body before the start
            lc = [c for c in caps if b in c['who'] and c['r'] <= r0]
            if lc:
                c = lc[-1]
                out['lastCapR'] = c['r']
                cp = P(b, c['r'] - 1) or P(b, c['r'])
                if cp and altar[0] >= 0:
                    out['capAltarWalk'] = G.walk(altar[0], altar[1], cp[0], cp[1])
                    # nearest altar to the capture spot
                    ws = [(G.walk(a[0], a[1], cp[0], cp[1]) or 999, a) for a in G.altars]
                    ws.sort()
                    out['capNearestAltarWalk'] = ws[0][0]
                    out['usedNearest'] = 1 if ws[0][1] == altar or (out['capAltarWalk'] or 999) <= ws[0][0] else 0
            tribs.append(out)
    tribs.sort(key=lambda x: x['r'])
    # bank decision after each capture: bag after the capture, nearest altar walk from the capture spot, did the body start a tribute
    # before its next capture (and how many rounds later), enemies within 8 at the capture
    startsBy = defaultdict(list)
    for tr in tribs:
        startsBy[tr['who']].append(tr['r'])
    capsBy = defaultdict(list)
    for c in caps:
        for b in c['who']:
            capsBy[b].append(c['r'])
    bdec = []
    for c in caps:
        for b in c['who']:
            p = P(b, c['r'] - 1) or P(b, c['r'])
            if not p:
                continue
            bag = gems[b][c['r']]
            ws = [G.walk(a[0], a[1], p[0], p[1]) for a in G.altars]
            ws = [w for w in ws if w is not None]
            na = min(ws) if ws else None
            nc = [r for r in capsBy[b] if r > c['r']]
            ncr = nc[0] if nc else None
            ts = [r for r in startsBy[b] if r >= c['r']]
            tr = ts[0] if ts else None
            dead = next((dd['r'] for dd in deaths if dd['who'] == b and dd['r'] > c['r']), None)
            ne = sum(1 for i in pos if team[i] != team[b] for q2 in [P(i, c['r'])] if q2 and cheb(q2[0], q2[1], p[0], p[1]) <= 8)
            bdec.append({'t': team[b], 'type': btype[b], 'r': c['r'], 'bag': bag, 'alt': na, 'zone': c['zone'], 'ne8': ne,
                         'bankNext': 1 if tr is not None and (ncr is None or tr <= ncr) and (dead is None or tr <= dead) else 0,
                         'delay': (tr - c['r']) if tr is not None and (ncr is None or tr <= ncr) else None,
                         'nextCap': (ncr - c['r']) if ncr else None, 'diedBefore': 1 if dead is not None and (ncr is None or dead < ncr) and (tr is None or dead < tr) else 0})
    # objective attempts (mono / golem / elk): hit episodes per team, gap > 30 splits
    atts = []
    for gi, hs in hitters.items():
        g = groups[gi]
        if g['cls'] not in ('mono', 'golem', 'elk'):
            continue
        for t in (0, 1):
            mine = sorted([h for h in hs if team[h[1]] == t])
            s0 = e0 = None
            who = set()

            def flush():
                if s0 is None:
                    return
                cap = None
                for c in capsByG.get(gi, []):
                    if s0 <= c['r'] <= e0 + 40:
                        cap = c; break
                nb = 0
                # context at the start: living bodies and their max-hp sums per team, banked gems, enemies within 8 of the group
                alive = [0, 0]; mh = [0, 0]; en8 = 0; al8 = 0
                for i in pos:
                    p = P(i, s0)
                    if p:
                        alive[team[i]] += 1; mh[team[i]] += mhp[i][s0]
                        if gdist(gi, p) <= 8:
                            if team[i] == t:
                                al8 += 1
                            else:
                                en8 += 1
                atts.append({'g': gi, 'cls': g['cls'], 't': t, 'zone': gz(t, g), 's': s0, 'e': e0, 'n': len(who),
                             'res': ('won' if cap['t'] == t else 'stolen') if cap else 'none', 'capR': cap['r'] if cap else None,
                             'gems': g['gems'], 'aliveT': alive[t], 'aliveO': alive[1 - t], 'mhT': mh[t], 'mhO': mh[1 - t],
                             'subT': sub[t][min(s0, rmax)], 'subO': sub[1 - t][min(s0, rmax)], 'al8': al8, 'en8': en8})
            for r, b in mine:
                if s0 is None or r - e0 > 30:
                    flush()
                    s0 = r; who = set()
                e0 = r
                who.add(b)
            flush()
    # walking budget per body
    budget = {}
    for b in pos:
        t = team[b]
        lab = collections.Counter()
        steps = 0
        for r in range(1, final + 1):
            p, pp = P(b, r), P(b, r - 1)
            if not p:
                lab['dead'] += 1
                continue
            if (b, r) in fight_r:
                lab['fight'] += 1
            elif (b, r) in hits_by_body_r:
                lab['farm'] += 1
            elif pp and p != pp and cheb(p[0], p[1], pp[0], pp[1]) <= 2:
                lab['walk'] += 1
                steps += cheb(p[0], p[1], pp[0], pp[1])
            elif G.on_spawn(t, p[0], p[1]):
                lab['spawn'] += 1
            else:
                gi = group_at(p) if p in tile2g else -1
                if gi >= 0:
                    lab['oncamp'] += 1
                else:
                    lab['still'] += 1
        budget[b] = dict(lab)
        budget[b]['steps'] = steps
    # per-team summary
    teams = {}
    for t in (0, 1):
        mine = [b for b in pos if team[b] == t]
        T = {'name': names.get(t), 'types': [btype[b] for b in mine], 'win': int(win == t), 'final': final}
        T['inc'] = dict(inc[t])
        T['incCP'] = {s: v for s, v in inc_cp[t].items()}
        T['spendCP'] = spend_cp[t]
        T['sub'] = [sub[t][min(cp, rmax)] for cp in CP]
        T['subFinal'] = meta['submitted'][t]
        reach = {}
        for lvl in (250, 500, 750, 1000):
            rr = next((r for r in range(rmax + 1) if sub[t][r] >= lvl), None)
            reach[lvl] = rr
        T['reach'] = reach
        T['carriedEnd'] = sum(gems[b][rmax] for b in mine)
        T['maxBag'] = {str(b): max(gems[b]) for b in mine}
        T['bagCP'] = {str(b): [gems[b][min(cp, rmax)] for cp in CP] for b in mine}
        T['goldHeldCP'] = [sum(gold[b][min(cp, rmax)] for b in mine) for cp in CP]
        T['maxHpCP'] = [sum(mhp[b][min(cp, rmax)] for b in mine) for cp in CP]
        T['incBody'] = {str(b): dict(inc_body[b]) for b in mine}
        T['bodyType'] = {str(b): btype[b] for b in mine}
        T['steals'] = sum(s[3] for s in steals if team[s[2]] == t)
        teams[t] = T
    # bags held over time per body (every 10 rounds) for carriers
    bagtl = {str(b): [gems[b][r] for r in range(0, rmax + 1, 10)] for b in pos}
    return {'file': fname, 'map': mapname, 'S': S, 'win': win, 'final': final, 'names': names, 'teams': teams,
            'groups': [{k: g[k] for k in ('i', 'cls', 'gems', 'gold', 'resp', 'f0', 'n')} | {'idle': idle[g['i']]} for g in groups],
            'caps': caps, 'cycles': cycles, 'tribs': tribs, 'deaths': deaths, 'atts': atts, 'budget': {str(b): v for b, v in budget.items()}, 'bdec': bdec,
            'btype': {str(b): btype[b] for b in pos}, 'bteam': {str(b): team[b] for b in pos}, 'bagtl': bagtl,
            'locks': [{'r': e['r'], 'who': e['who'], 't': team[e['who']], 'to': e.get('to')} for e in locks],
            'nAltars': len(G.altars)}


def main():
    geo = load_geo()
    for key in sys.argv[1:]:
        idx = load_index(key)
        out = f'{CACHE}/t2econ/games_{key}.jsonl'
        done = set()
        if os.path.exists(out):
            for l in open(out, encoding='utf-8'):
                try:
                    done.add(json.loads(l)['file'])
                except Exception:
                    pass
        files = sorted(f for f in os.listdir(f'{CACHE}/t2econ/{key}') if f.endswith('.json.gz'))
        n = 0
        with open(out, 'a', encoding='utf-8') as fo:
            for f in files:
                name = f.replace('.json.gz', '.repl26a')
                if name in done:
                    continue
                mid = f.rsplit('_', 1)[1][:8]
                row = idx.get(mid)
                if not row:
                    print('no index row', f, file=sys.stderr)
                    continue
                row['_key'] = key
                try:
                    res = analyse(f'{CACHE}/t2econ/{key}/{f}', row, geo)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    print('ERR', f, e, file=sys.stderr)
                    continue
                res['key'] = key
                res['matchId'] = row['matchId']
                fo.write(json.dumps(res) + '\n')
                n += 1
        print(key, 'games', n, file=sys.stderr)


if __name__ == '__main__':
    main()
