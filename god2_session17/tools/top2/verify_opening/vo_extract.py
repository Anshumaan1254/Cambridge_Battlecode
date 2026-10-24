# Independent re-measurement of the opening (r1-300) for the verification of experiments/top2/an_opening.md.
# Usage: python tools/top2/verify_opening/vo_extract.py OUT.jsonl [workers]   (reads all six study folders)
# One JSON line per dump: game meta, per-team checkpoint series, route features, captures, engagements, deaths, choice sets.
import gzip, json, os, sys, glob, math
from collections import deque, defaultdict, Counter

CACHE = 'C:/battlecode/cache'
REPO = 'C:/battlecode/Cambridge_Battlecode'
KEYS = ['pbg', 'ifish', 'pantheon', 'coo', 'cm', 'nyx']
GEMS = {'wolf': 4, 'elk': 15, 'gem': 7, 'gold': 0, 'monolith': 200, 'golem': 36}
GOLD = {'wolf': 40, 'elk': 90, 'gem': 0, 'gold': 20, 'monolith': 300, 'golem': 160}
RESP = {'wolf': 40, 'elk': 60, 'gem': 50, 'gold': 50, 'monolith': 150, 'golem': 80}
HPV = {'wolf': 1350, 'elk': 2400, 'gem': 120, 'gold': 120, 'monolith': 20000, 'golem': 5000}
RANK = {'monolith': 6, 'golem': 5, 'elk': 4, 'wolf': 3, 'gem': 2, 'gold': 1}
CHECK = [20, 50, 100, 150, 200, 300]
DRAFT = ['Ryth', 'VesperVale', 'Vendetta', 'CassiAndIssac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin']


def bfs(grid, W, H, srcs, blocked_extra):
    dist = [[-1] * W for _ in range(H)]
    dq = deque()
    for (x, y) in srcs:
        dist[y][x] = 0
        dq.append((x, y))
    while dq:
        x, y = dq.popleft()
        d = dist[y][x] + 1
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H and dist[ny][nx] < 0:
                    c = grid[ny][nx]
                    if c in '#oA' or (nx, ny) in blocked_extra:
                        continue
                    dist[ny][nx] = d
                    dq.append((nx, ny))
    return dist


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def official_gold(comp):
    """per body index -> sorted [(round, earnedGold)] from the platform compact summary"""
    if not comp:
        return None
    out = {}
    for k, v in comp.get('champ_tl', {}).items():
        cid, name = k.split(':')
        if name == 'earnedGold':
            out[int(cid)] = v
    return out


def step_at(tl, r):
    v = 0.0
    for rr, val in tl:
        if rr <= r:
            v = val
        else:
            break
    return v


def process(args):
    key, path, row, geo, comp = args
    d = json.load(gzip.open(path))
    meta, R, ev = d['meta'], d['R'], d['ev']
    W, H = meta['width'], meta['height']
    bodies = meta['bodies']
    nb = len(bodies)
    team = {b['index']: b['team'] for b in bodies}
    btype = {b['index']: b['type'] for b in bodies}
    final = meta['finalRound']
    outcome = meta['outcome']
    winner = 0 if outcome == 1 else (1 if outcome == 2 else -1)
    names = [row['teams'][0]['name'], row['teams'][1]['name']]
    sides = [row['teams'][0]['side'], row['teams'][1]['side']]
    # team index 0 = side a
    tnames = [None, None]
    tres = [None, None]
    tpicks = [None, None]
    tids = [None, None]
    for t in row['teams']:
        ti = 0 if t['side'] == 'a' else 1
        tnames[ti] = t['name']; tres[ti] = t['result']; tpicks[ti] = t['draftPicks']; tids[ti] = t['teamId']
    STUDY_IDS = {'pbg': '38e6d8c4', 'ifish': '1890540d', 'pantheon': '547efb5b', 'coo': '1570a113', 'cm': 'ad5474c2', 'nyx': '6f7fd199'}
    study = 0 if tids[0].startswith(STUDY_IDS[key]) else (1 if tids[1].startswith(STUDY_IDS[key]) else -1)
    # draft check: dump bodies of team 0 vs side-a picks
    def dtypes(t):
        c = Counter()
        for b in bodies:
            if b['team'] == t:
                ty = b['type']
                c['CassiAndIssac' if ty in ('Cassi', 'Issac') else ty] += 1
        return c
    draftok = True
    for t in (0, 1):
        want = Counter(DRAFT[p] for p in tpicks[t])
        got = dtypes(t)
        if 'CassiAndIssac' in got:
            got['CassiAndIssac'] = 1
        if want != got:
            draftok = False
    resok = (winner == 0 and tres[0] == 'win') or (winner == 1 and tres[1] == 'win')

    # spawns from geometry, assigned by initial positions
    grid = geo['grid']
    A = set(map(tuple, geo['spawnA'])); B = set(map(tuple, geo['spawnB']))
    init = {b[0]: (b[1], b[2]) for b in R[0][3]}
    sp = [None, None]
    for t in (0, 1):
        pos = [init[i] for i in init if team[i] == t]
        if all(p in A for p in pos):
            sp[t] = A
        elif all(p in B for p in pos):
            sp[t] = B
    spawnok = sp[0] is not None and sp[1] is not None and sp[0] != sp[1]
    if not spawnok:
        sp = [A, B]
    dist = [bfs(grid, W, H, sp[0], sp[1]), bfs(grid, W, H, sp[1], sp[0])]

    def ftile(t, x, y):
        a = dist[t][y][x]; b = dist[1 - t][y][x]
        if a < 0 and b < 0:
            return None
        if a < 0:
            return 1.0
        if b < 0:
            return 0.0
        return a / (a + b) if a + b > 0 else 0.5

    # camp groups by cardinal connectivity
    camps = meta['camps']
    ctype = {}
    cpos = {}
    for c in camps:
        ty = c['type']
        if ty == 5:
            ty = 'golem'
        ctype[c['index']] = ty
        cpos[c['index']] = (c['x'], c['y'])
    tile2camp = {cpos[i]: i for i in cpos}
    gid = {}
    groups = []
    for i in cpos:
        if i in gid:
            continue
        comp_ = [i]; gid[i] = len(groups); dq = deque([i])
        while dq:
            j = dq.popleft(); x, y = cpos[j]
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                k = tile2camp.get((nx, ny))
                if k is not None and k not in gid:
                    gid[k] = len(groups); comp_.append(k); dq.append(k)
        groups.append(comp_)
    G = []
    for gi, mem in enumerate(groups):
        types = [ctype[m] for m in mem]
        cls = max(types, key=lambda t: RANK.get(t, 0))
        dd = []
        for t in (0, 1):
            ds = [dist[t][cpos[m][1]][cpos[m][0]] for m in mem if dist[t][cpos[m][1]][cpos[m][0]] >= 0]
            dd.append(min(ds) if ds else -1)
        fz = []
        for t in (0, 1):
            a, b = dd[t], dd[1 - t]
            if a < 0:
                fz.append(None)
            elif b < 0:
                fz.append(0.0)
            else:
                fz.append(a / (a + b) if a + b > 0 else 0.5)
        G.append({'i': gi, 'mem': mem, 'cls': cls, 'gems': sum(GEMS.get(t, 0) for t in types), 'gold': sum(GOLD.get(t, 0) for t in types),
                  'hp': sum(HPV.get(t, 0) for t in types), 'resp': max(RESP.get(t, 0) for t in types), 'n': len(mem),
                  'nelk': types.count('elk'), 'nwolf': types.count('wolf'), 'd': dd, 'f': fz,
                  'tiles': [cpos[m] for m in mem]})

    def zone(t, gi):
        f = G[gi]['f'][t]
        if f is None:
            return 'x'
        return 'own' if f < 0.4 else ('mid' if f <= 0.6 else 'enemy')

    # my own midShare: share of the gem rate (gems / respawn) in groups whose f (team 0 view) is in [0.4, 0.6]
    rate_all = sum(g['gems'] / g['resp'] for g in G if g['resp'] > 0)
    rate_mid = sum(g['gems'] / g['resp'] for g in G if g['resp'] > 0 and g['f'][0] is not None and 0.4 <= g['f'][0] <= 0.6)
    midshare = rate_mid / rate_all if rate_all else 0

    # ---------------- per-round state ----------------
    nR = len(R)
    def st(r):
        return R[min(r, nR - 1)]
    # events by round/body
    shop_rounds = defaultdict(set)
    for e in ev:
        if e['k'] in ('Shop', 'Sell item') and 'who' in e:
            shop_rounds[e['who']].add(e['r'])
    capg = defaultdict(lambda: defaultdict(int))  # body -> round -> capture gold
    caps_ev = [e for e in ev if e['k'] == 'CaptureGems']
    capture_steps = {e['q'] for e in ev if e['k'] == 'Capture'}
    for e in caps_ev:
        capg[e['who']][e['r']] += e['gold']
    deaths = [e for e in ev if e['k'] == 'Death']
    killg = defaultdict(lambda: defaultdict(int))
    ci_seen = set()
    for e in deaths:
        by = e['by']
        if isinstance(by, int) and by in team and team[by] != e['team']:
            if btype[e['who']] in ('Cassi', 'Issac'):
                if (e['r'], by) in ci_seen:
                    continue
                ci_seen.add((e['r'], by))
            killg[by][e['r']] += 133 if btype[by] == 'VesperVale' else 100
    # gold-only group captures produce a 'Capture' step without CaptureGems: attribute them to the bodies standing on
    # a gold-only group's tiles at the end of the previous round (capture resolves at round start)
    gq = {e['q'] for e in caps_ev}
    goldonly = {}
    for g in G:
        if g['gems'] == 0 and g['gold'] > 0:
            for tl in g['tiles']:
                goldonly[tl] = g['i']
    goldcap = []  # (round, team, group, [bodies])
    for e in ev:
        if e['k'] == 'Capture' and e['q'] not in gq:
            r = e['r']
            prevs = st(r - 1)[3] if r - 1 < len(R) else R[-1][3]
            on = defaultdict(list)
            for x in prevs:
                if x[5] and (x[1], x[2]) in goldonly:
                    on[goldonly[(x[1], x[2])]].append(x[0])
            for gi_, bs in on.items():
                tms = {team[b] for b in bs}
                if len(tms) == 1:
                    goldcap.append((r, tms.pop(), gi_, bs))
    for (r, t, gi_, bs) in goldcap:
        share = G[gi_]['gold'] / len(bs)
        for b in bs:
            capg[b][r] += share * (1.33 if btype[b] == 'VesperVale' else 1.0)
    bankg = defaultdict(lambda: defaultdict(int))
    for e in ev:
        if e['k'] == 'Banked' and btype[e['who']] == 'Marcella':
            bankg[e['who']][e['r']] += 2 * e['gems']
    # gold earned estimators per body cumulated per round up to 300 (and final)
    lastr = min(final, nR - 1)
    gold_est = {i: [0.0] * (lastr + 1) for i in team}
    gold_dpos = {i: [0.0] * (lastr + 1) for i in team}
    prevg = {b[0]: b[7] for b in R[0][3]}
    for r in range(1, lastr + 1):
        cur = {b[0]: b for b in R[r][3]}
        for i in team:
            g = cur[i][7]
            dlt = g - prevg[i]
            evinc = capg[i].get(r, 0) + killg[i].get(r, 0) + bankg[i].get(r, 0)
            if r in shop_rounds[i]:
                inc = max(dlt, evinc, 0)
            else:
                inc = max(dlt, 0)
            gold_est[i][r] = gold_est[i][r - 1] + inc
            gold_dpos[i][r] = gold_dpos[i][r - 1] + max(dlt, 0)
            prevg[i] = g
    offg = official_gold(comp)

    # captures (one record per capture step): group from the capturer's tile
    capsteps = defaultdict(list)
    for e in caps_ev:
        capsteps[e['q']].append(e)
    tile2group = {}
    for g in G:
        for tl in g['tiles']:
            tile2group[tl] = g['i']
    cdmg = d['cdmg']  # [q, r, attacker body, camp index, amount]
    hits_by_group = defaultdict(list)
    for h in cdmg:
        q, r, a, ci, amt = h
        if ci in gid and a in team:
            hits_by_group[gid[ci]].append((q, r, a, amt))
    captures = []
    last_cap_r = defaultdict(lambda: 0)
    capmatch = [0, 0]
    for q in sorted(capsteps):
        es = capsteps[q]
        t = es[0]['team']
        r = es[0]['r']
        gis = Counter(tile2group.get(tuple(e['at'])) for e in es)
        gi = gis.most_common(1)[0][0]
        tot_g = sum(e['gems'] for e in es)
        tot_gold = sum(e['gold'] for e in es)
        if gi is not None:
            capmatch[0] += 1
            if tot_g == G[gi]['gems']:
                capmatch[1] += 1
        rec = {'r': r, 'q': q, 't': t, 'g': gi, 'gems': tot_g, 'gold': tot_gold, 'ncap': len(es),
               'who': [e['who'] for e in es], 'whot': [btype[e['who']] for e in es], 'whogems': [e['gems'] for e in es]}
        if gi is not None:
            g = G[gi]
            rec.update({'cls': g['cls'], 'zone': zone(t, gi), 'ggems': g['gems'], 'ghp': g['hp'], 'gn': g['n'], 'gnelk': g['nelk']})
            lo = last_cap_r[gi]
            hs = [h for h in hits_by_group[gi] if lo < h[1] <= r and h[0] < q]
            own = [h for h in hs if team[h[2]] == t]
            opp = [h for h in hs if team[h[2]] != t]
            rec['first_own'] = min((h[1] for h in own), default=None)
            rec['hitters'] = len({h[2] for h in own})
            rec['hitter_types'] = sorted({btype[h[2]] for h in own})
            rec['own_dmg'] = sum(h[3] for h in own)
            rec['opp_dmg'] = sum(h[3] for h in opp)
            rec['opp_hits'] = len(opp)
            rec['prev_cap'] = lo
            last_cap_r[gi] = r
        captures.append(rec)

    # deaths
    D = []
    for e in deaths:
        by = e['by']
        kt = team[by] if isinstance(by, int) and by in team else None
        D.append({'r': e['r'], 'q': e['q'], 'who': e['who'], 't': e['team'], 'type': btype[e['who']], 'by': by if isinstance(by, int) else 'camp',
                  'kt': kt, 'champ': kt is not None and kt != e['team'], 'bag': e.get('bag', 0)})

    # ---------------- per team series ----------------
    base_hp = [sum(b[4] for b in R[0][3] if team[b[0]] == t) for t in (0, 1)]
    ts = [{}, {}]
    for t in (0, 1):
        for c in CHECK + ['final']:
            r = lastr if c == 'final' else min(c, lastr)
            s = st(r)
            mine = [b for b in s[3] if team[b[0]] == t]
            row_ = {}
            row_['gold_est'] = sum(gold_est[i][r] for i in team if team[i] == t)
            row_['gold_dpos'] = sum(gold_dpos[i][r] for i in team if team[i] == t)
            if offg:
                row_['gold_off'] = sum(step_at(offg[i], r) for i in offg if i in team and team[i] == t)
            cps = [cp for cp in captures if cp['t'] == t and cp['r'] <= r]
            row_['capgems'] = sum(cp['gems'] for cp in cps)
            row_['capgold'] = sum(cp['gold'] for cp in cps)
            row_['ncap'] = len(cps)
            for z in ('own', 'mid', 'enemy', 'x'):
                row_['gems_' + z] = sum(cp['gems'] for cp in cps if cp.get('zone') == z)
                row_['ncap_' + z] = sum(1 for cp in cps if cp.get('zone') == z)
            row_['ncap_elkgrp'] = sum(1 for cp in cps if cp.get('cls') == 'elk')
            row_['ncap_wolfgrp'] = sum(1 for cp in cps if cp.get('cls') == 'wolf')
            row_['ncap_gemgrp'] = sum(1 for cp in cps if cp.get('cls') == 'gem')
            row_['killgold'] = sum(killg[i][rr] for i in team if team[i] == t for rr in killg[i] if rr <= r)
            dd_ = [x for x in D if x['r'] <= r]
            row_['deaths'] = sum(1 for x in dd_ if x['t'] == t)
            row_['deaths_champ'] = sum(1 for x in dd_ if x['t'] == t and x['champ'])
            row_['deaths_camp'] = sum(1 for x in dd_ if x['t'] == t and x['by'] == 'camp')
            # kill events: enemy deaths by our champions, C&I pair counted once (same round, same killer)
            ke = {(x['r'], x['by']) if x['type'] in ('Cassi', 'Issac') else (x['r'], x['who'], x['q']) for x in dd_ if x['kt'] == t and x['t'] != t}
            row_['kills'] = len(ke)
            de = {(x['r'], x['by']) if x['type'] in ('Cassi', 'Issac') else (x['r'], x['who'], x['q']) for x in dd_ if x['t'] == t}
            row_['death_events'] = len(de)
            row_['banked'] = s[1 + t]
            row_['alive'] = sum(1 for b in mine if b[5])
            row_['carried'] = sum(b[6] for b in mine)
            row_['hpbought'] = sum(b[4] for b in mine) - base_hp[t]
            row_['midbodies'] = sum(1 for b in mine if b[5] and (lambda f: f is not None and 0.4 <= f <= 0.6)(ftile(t, b[1], b[2])))
            ts[t][str(c)] = row_

    # window means: bodies in mid band, cohesion (largest Chebyshev-5 cluster share)
    def cluster_share(pts):
        n = len(pts)
        if n == 0:
            return None
        par = list(range(n))
        def fd(a):
            while par[a] != a:
                par[a] = par[par[a]]; a = par[a]
            return a
        for a in range(n):
            for b in range(a + 1, n):
                if cheb(pts[a], pts[b]) <= 5:
                    par[fd(a)] = fd(b)
        c = Counter(fd(a) for a in range(n))
        return max(c.values()) / n
    WIN = [(1, 50), (51, 100), (101, 150), (151, 200), (201, 300)]
    win = [{}, {}]
    mid_first = [[None, None, None], [None, None, None]]
    for t in (0, 1):
        for (a, b) in WIN:
            ms, cs = [], []
            for r in range(a, min(b, lastr) + 1):
                mine = [x for x in R[r][3] if team[x[0]] == t and x[5]]
                ms.append(sum(1 for x in mine if (lambda f: f is not None and 0.4 <= f <= 0.6)(ftile(t, x[1], x[2]))))
                cs_ = cluster_share([(x[1], x[2]) for x in mine])
                if cs_ is not None:
                    cs.append(cs_)
            win[t]['mid_%d_%d' % (a, b)] = sum(ms) / len(ms) if ms else None
            win[t]['coh_%d_%d' % (a, b)] = sum(cs) / len(cs) if cs else None
        for r in range(1, min(300, lastr) + 1):
            mine = [x for x in R[r][3] if team[x[0]] == t and x[5]]
            k = sum(1 for x in mine if (lambda f: f is not None and 0.4 <= f <= 0.6)(ftile(t, x[1], x[2])))
            for j in range(3):
                if mid_first[t][j] is None and k >= j + 1:
                    mid_first[t][j] = r

    # ---------------- route features ----------------
    route = [{}, {}]
    first_hit = {}
    for h in cdmg:
        q, r, a, ci, amt = h
        if a in team and a not in first_hit and ci in gid:
            first_hit[a] = (r, gid[ci], ci)
    first_move = {}
    for r in range(1, min(300, lastr) + 1):
        for x in R[r][3]:
            i = x[0]
            if i not in first_move and (x[1], x[2]) != init[i]:
                first_move[i] = r
    choice = [None, None]
    for t in (0, 1):
        mineb = [i for i in team if team[i] == t]
        n = len(mineb)
        fm = sorted(first_move.get(i, 999) for i in mineb)
        route[t]['n'] = n
        route[t]['moved_r1'] = sum(1 for i in mineb if first_move.get(i, 999) <= 1) / n
        route[t]['first_move_med'] = fm[(n - 1) // 2] if n % 2 else (fm[n // 2 - 1] + fm[n // 2]) / 2
        route[t]['first_move_team'] = fm[0]
        fh = sorted(first_hit[i][0] for i in mineb if i in first_hit and first_hit[i][0] <= 300)
        route[t]['first_hit_team'] = fh[0] if fh else None
        fhall = sorted(first_hit.get(i, (301,))[0] for i in mineb)
        route[t]['first_hit_med'] = fhall[(n - 1) // 2] if n % 2 else (fhall[n // 2 - 1] + fhall[n // 2]) / 2
        fg = Counter(first_hit[i][1] for i in mineb if i in first_hit and first_hit[i][0] <= 300)
        route[t]['squads'] = len(fg)
        if fg:
            top = max(fg.values())
            cands = [g for g in fg if fg[g] == top]
            # tie: earliest first hit
            mg = min(cands, key=lambda g: min(first_hit[i][0] for i in mineb if i in first_hit and first_hit[i][1] == g))
            route[t]['main_g'] = mg
            route[t]['squad_share'] = top / n
            route[t]['main_cls'] = G[mg]['cls']
            route[t]['main_zone'] = zone(t, mg)
            route[t]['main_walk'] = G[mg]['d'][t]
            reach = [g for g in G if g['d'][t] >= 0 and g['cls'] != 'monolith']
            dmin = min(g['d'][t] for g in reach)
            route[t]['main_nearest'] = 1 if G[mg]['d'][t] == dmin else 0
            route[t]['main_rank'] = 1 + sum(1 for g in reach if g['d'][t] < G[mg]['d'][t])
            route[t]['main_elk'] = 1 if G[mg]['cls'] == 'elk' else 0
            route[t]['share_nearest'] = sum(1 for i in mineb if i in first_hit and G[first_hit[i][1]]['d'][t] == dmin) / n
            route[t]['share_elk'] = sum(1 for i in mineb if i in first_hit and G[first_hit[i][1]]['cls'] == 'elk') / n
            route[t]['walk_med_body'] = sorted(G[first_hit[i][1]]['d'][t] for i in mineb if i in first_hit)[(len([i for i in mineb if i in first_hit]) - 1) // 2]
            choice[t] = {'chosen': mg, 'set': [{'g': g['i'], 'walk': g['d'][t], 'gems': g['gems'], 'gold': g['gold'], 'cls': g['cls'],
                                                'zone': zone(t, g['i']), 'hp': g['hp']} for g in reach]}
        caps_t = [cp for cp in captures if cp['t'] == t]
        route[t]['first_cap'] = caps_t[0]['r'] if caps_t else None
        route[t]['first_cap_gems'] = caps_t[0]['gems'] if caps_t else None
        mc = [cp for cp in caps_t if cp.get('zone') == 'mid']
        route[t]['first_midcap'] = mc[0]['r'] if mc else None
        route[t]['mid_first'] = mid_first[t]
    # ---------------- engagements (champion vs champion damage) ----------------
    pos_at = lambda r, i: next(((x[1], x[2], x[3], x[5]) for x in st(r)[3] if x[0] == i), None)
    hits = [h for h in d['dmg'] if h[2] >= 0 and h[2] in team and h[3] in team and team[h[2]] != team[h[3]] and h[2] != h[3]]
    hits.sort(key=lambda h: h[0])
    engs = []
    open_ = []
    for h in hits:
        q, r, a, v, amt, kind, slot = h
        pv = pos_at(r, v)
        if pv is None or not pv[3]:
            pv = pos_at(r - 1, v)
        p = (pv[0], pv[1])
        best = None
        for E in open_:
            if r - E['last_r'] <= 6 and cheb(p, E['last_p']) <= 10:
                if best is None or E['last_q'] > best['last_q']:
                    best = E
        if best is None:
            best = {'start_r': r, 'start_q': q, 'striker': team[a], 'first_att': a, 'first_vic': v, 'last_r': r, 'last_q': q, 'last_p': p,
                    'victims': set(), 'attackers': set(), 'nhits': 0, 'dmg': [0, 0]}
            engs.append(best)
            open_.append(best)
        best['last_r'] = r; best['last_q'] = q; best['last_p'] = p
        best['victims'].add(v); best['attackers'].add(a); best['nhits'] += 1
        best['dmg'][team[a]] += amt
        open_ = [E for E in open_ if r - E['last_r'] <= 6]
    E_out = []
    for E in engs:
        r0 = E['start_r']
        pv = pos_at(r0 - 1, E['first_vic'])
        vp = (pv[0], pv[1])
        loc = {0: [0, 0, 0, 0], 1: [0, 0, 0, 0]}  # n cheb8, hp cheb8, n eucl8, hp eucl8
        for x in st(r0 - 1)[3]:
            if not x[5]:
                continue
            tt = team[x[0]]
            if cheb((x[1], x[2]), vp) <= 8:
                loc[tt][0] += 1; loc[tt][1] += x[3]
            if (x[1] - vp[0]) ** 2 + (x[2] - vp[1]) ** 2 <= 64:
                loc[tt][2] += 1; loc[tt][3] += x[3]
        s = E['striker']
        # deaths inside: bodies that were victims of this engagement, killed by an enemy champion, within [start, last+1]
        dl = [0, 0]; dk = [0, 0]; seen = set()
        for x in D:
            if not x['champ'] or not (E['start_r'] <= x['r'] <= E['last_r'] + 1):
                continue
            inv = x['who'] in E['victims']
            if not inv and x['type'] in ('Cassi', 'Issac'):
                inv = any(btype[vv] in ('Cassi', 'Issac') and team[vv] == x['t'] for vv in E['victims'])
            if inv:
                dl[x['t']] += 1
                kk = (x['r'], x['by'], x['t']) if x['type'] in ('Cassi', 'Issac') else (x['q'], x['who'])
                if kk not in seen:
                    seen.add(kk); dk[x['t']] += 1
        E_out.append({'r': r0, 'end': E['last_r'], 's': s, 'fa': btype[E['first_att']], 'fv': btype[E['first_vic']],
                      'ln_s': loc[s][0], 'ln_v': loc[1 - s][0], 'lh_s': loc[s][1], 'lh_v': loc[1 - s][1],
                      'le_s': loc[s][2], 'le_v': loc[1 - s][2],
                      'dead_s': dl[s], 'dead_v': dl[1 - s], 'kev_s': dk[s], 'kev_v': dk[1 - s], 'nhits': E['nhits'],
                      'dmg_s': E['dmg'][s], 'dmg_v': E['dmg'][1 - s],
                      'f_s': ftile(s, vp[0], vp[1])})

    sz = W * H
    size = 'S' if sz <= 1400 else ('M' if sz <= 2600 else 'L')
    out = {'file': os.path.basename(path), 'key': key, 'map': row['map'], 'mid': row['matchId'], 'W': W, 'H': H, 'size': size,
           'final': final, 'winner': winner, 'study': study, 'names': tnames, 'picks': [len(tpicks[0]), len(tpicks[1])],
           'nb': [sum(1 for i in team if team[i] == t) for t in (0, 1)], 'draftok': draftok, 'resok': resok, 'spawnok': spawnok,
           'capmatch': capmatch, 'midshare': midshare, 'has_off': bool(offg), 'base_hp': base_hp,
           'types': [[btype[i] for i in sorted(team) if team[i] == t] for t in (0, 1)],
           'ts': ts, 'win': win, 'route': route, 'caps': captures, 'deaths': D, 'engs': E_out, 'choice': choice,
           'groups': [{k: g[k] for k in ('i', 'cls', 'gems', 'gold', 'hp', 'n', 'nelk', 'd', 'f')} for g in G]}
    return json.dumps(out)


def jobs():
    geo = {}
    for l in open(CACHE + '/an_strategy/mapgeo2.jsonl', encoding='utf-8'):
        g = json.loads(l)
        geo[g['map']] = g
    compdir = REPO + '/experiments/live/compact'
    have = set(f[:-5] for f in os.listdir(compdir))
    out = []
    for key in KEYS:
        rows = {}
        for l in open(f'{CACHE}/t2/{key}/index.jsonl', encoding='utf-8'):
            r = json.loads(l)
            rows[f"{r['map']}_{r['matchId'][:8]}.json.gz"] = r
        for p in sorted(glob.glob(f'{CACHE}/t2dump/{key}/*.json.gz')):
            b = os.path.basename(p)
            r = rows[b]
            comp = None
            if r['matchId'] in have:
                comp = json.load(open(f"{compdir}/{r['matchId']}.json", encoding='utf-8'))
            out.append((key, p, r, geo[r['map']], comp))
    return out


if __name__ == '__main__':
    outp = sys.argv[1]
    nw = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    J = jobs()
    if len(sys.argv) > 3:
        J = J[:int(sys.argv[3])]
    from multiprocessing import Pool
    with Pool(nw) as pool, open(outp, 'w', encoding='utf-8') as fo:
        for s in pool.imap(process, J, chunksize=2):
            fo.write(s + '\n')
    print('done', len(J))
