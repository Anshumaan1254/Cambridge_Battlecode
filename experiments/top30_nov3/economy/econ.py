#!/usr/bin/env python3
"""ECONOMY stream: per (game, team) economy rows from decoded replays, for the top-30 dataset and for our v84-v88 games.

    nice -n 19 python3 -I economy/econ.py top30   -> economy/rows_top30.jsonl   (both teams of every decoded top-30 game)
    nice -n 19 python3 -I economy/econ.py ours    -> economy/rows_ours.jsonl    (we and the opponent of our v84-v88 games)

One row per (game, team). Fields (see build_row): phase stats per PHASES (camp hits, camp damage dealt, gems / gold captured,
gold earned, body-round states, contested vs unopposed hits), first capture, captures by r150/r300, opening visits per body
(r1-150: group, value, distance from spawn, rank by distance, bodies on it, first hit, kill, capture), items at checkpoints
(shards, emblems, gold unspent), build order per body (round, family, stat, emblem), shop trips (recall / walk / respawn /
at-spawn), emblem landing rounds, map class.
Body states per round (first match wins): dead | spawn (on own spawn tile) | bank (tribute channel) | recall (held channel) |
fight (hit or was hit by a champion) | hit (hit a camp) | capture (on a reward tile) | walk (moved) | wait (still within 4 of
a group: alive / respawning) | idle.  contested = an enemy champion within 6 (Chebyshev) at the start of the round.
"""
import json, os, sys, subprocess
from collections import Counter, defaultdict, deque
from multiprocessing import Pool

ROOT = '/home/claude/cambridge_battlecode/experiments'
T30 = f'{ROOT}/top30_nov3'
OURS = f'{ROOT}/ladder_nov2'
ECO = f'{T30}/economy'
ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
PHASES = [(1, 150), (151, 400), (401, 800), (801, 2000)]
CHECKS = (150, 300, 600, 900)
HORIZON = 150
GOLD_V = 0.5
FAM = ['Monster', 'Power', 'Durability', 'Treasure', 'Jungle', 'Home', 'Bruiser', 'Tribute', 'Capture', 'Prospector', 'Hunter',
       'Skirmish', 'Greed', 'Collectors']
STATN = ['str', 'foc', 'hp']
TYPES = ['wolf', 'elk', 'gem', 'gold', 'monolith', 'golem']
TCH = {'wolf': 'W', 'elk': 'E', 'gem': 'g', 'gold': '$', 'monolith': 'M', 'golem': 'G'}
SWITCH = [('2026-11-02T00:00:00', 'pre'), ('2026-11-02T21:15:46', 'v84'), ('2026-11-03T01:00:56', 'v85'), ('2026-11-03T01:21:19', 'v86'),
          ('2026-11-03T02:52:00', 'v87'), ('2026-11-03T04:11:33', 'v88'), ('9999', 'v89')]


def version(created):
    for t, v in SWITCH:
        if created < t:
            return v
    return 'v89'


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def mirror(x, y, W, H, sym):
    if sym == 0:
        return W - 1 - x, y
    if sym == 1:
        return x, H - 1 - y
    return W - 1 - x, H - 1 - y


_HALF = None


def half_tables():
    global _HALF
    if _HALF is None:
        h = dict(json.load(open(f'{OURS}/map_fail/half_groups.json')))
        for k, v in json.load(open(f'{OURS}/v88_bugs/half_groups_ext.json')).items():
            h.setdefault(k, v)
        if os.path.exists(f'{ECO}/groups_raw.jsonl'):
            for l in open(f'{ECO}/groups_raw.jsonl'):
                o = json.loads(l)
                h.setdefault(o['mid'].rsplit('_', 1)[0], o)
        _HALF = h
    return _HALF


def full_groups(mapname, meta, sym):
    """as map_fail/mapgroups.full_groups, with the extra tables"""
    W, H = meta['width'], meta['height']
    tile2camp = {(c['x'], c['y']): c['index'] for c in meta['camps']}
    out = []
    for g in half_tables()[mapname]['groups']:
        gems, gold, resp = g['raw'][0], g['raw'][1], g['raw'][2]
        x0, y0 = g['camps'][0][1], g['camps'][0][2]
        orig = []
        for t, x, y in g['camps']:
            mx, my = mirror(x, y, W, H, sym)
            if max(abs(mx - x0), abs(my - y0)) < max(abs(x - x0), abs(y - y0)):
                x, y = mx, my
            orig.append((t, x, y))
        mir = [(t,) + mirror(x, y, W, H, sym) for t, x, y in orig]
        touch = any(max(abs(a[1] - b[1]), abs(a[2] - b[2])) <= 1 for a in orig for b in mir)
        if touch:
            out.append({'gems': gems, 'gold': gold, 'resp': resp, 'camps': list(dict.fromkeys(orig + mir))})
        else:
            out.append({'gems': gems, 'gold': gold, 'resp': resp, 'camps': orig})
            out.append({'gems': gems, 'gold': gold, 'resp': resp, 'camps': mir})
    for i, g in enumerate(out):
        g['id'] = i
        g['idx'] = [tile2camp[(x, y)] for t, x, y in g['camps'] if (x, y) in tile2camp]
        g['tiles'] = [(x, y) for t, x, y in g['camps']]
        g['types'] = [TYPES[t] for t, x, y in g['camps']]
        g['cx'] = sum(x for x, y in g['tiles']) / len(g['tiles'])
        g['cy'] = sum(y for x, y in g['tiles']) / len(g['tiles'])
    return out


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


def shard_eq(items):
    """shard-equivalents (emblem = 5 shards, Power 6, Greed 35) and emblem count"""
    s = e = 0
    for it, q in items:
        fam, rest = divmod(it, 6)
        if rest % 2 == 0:
            s += q
        else:
            e += q
            s += q * (6 if fam == 1 else 35 if fam == 12 else 5)
    return s, e


def analyse(job):
    dec_path, mj_path, mapname, teams_info = job
    d = json.load(open(dec_path))
    mj = json.load(open(mj_path))
    meta = d['meta']
    W, H = meta['width'], meta['height']
    types = {b['index']: b['type'] for b in meta['bodies']}
    team = {b['index']: b['team'] for b in meta['bodies']}
    bodies = sorted(types)
    final = meta['finalRound']
    S = {rr['r']: {c[0]: c for c in rr['ch']} for rr in d['rounds'][1:]}
    R = {rr['r']: rr for rr in d['rounds'][1:]}
    G = full_groups(mapname, meta, mj['sym'])
    tile_group = {t: gg['id'] for gg in G for t in gg['tiles']}
    camp_at = {(c['x'], c['y']): c['index'] for c in meta['camps']}
    camp_group = {c['index']: tile_group.get((c['x'], c['y'])) for c in meta['camps']}
    spawn = {0: {tuple(p) for p in mj['spawnA']}, 1: {tuple(p) for p in mj['spawnB']}}
    dist = {0: bfs(mj['rows'], spawn[0], W, H), 1: bfs(mj['rows'], spawn[1], W, H)}
    altars = sum(1 for y in range(H) for x in range(W) if mj['rows'][y][x] == 'A')

    def dgroup(t, gg):
        best = 10 ** 6
        for (x, y) in gg['tiles']:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H and dist[t][ny][nx] >= 0 and (nx, ny) not in tile_group:
                        best = min(best, dist[t][ny][nx])
        return best if best < 10 ** 6 else None

    gval = {gg['id']: gg['gems'] + GOLD_V * gg['gold'] for gg in G}
    gd = {t: {gg['id']: dgroup(t, gg) for gg in G} for t in (0, 1)}
    grank = {}
    for t in (0, 1):
        for gg in G:
            dd = gd[t][gg['id']]
            grank[(t, gg['id'])] = 1 + sum(1 for o in G if gval[o['id']] > 0 and gd[t][o['id']] is not None and dd is not None and gd[t][o['id']] < dd)

    def gdist(p, gid):
        return min(cheb(p, q) for q in G[gid]['tiles'])

    # group state per round
    def gstate(gid, r):
        rr = R.get(r)
        if rr is None:
            return '?'
        if any(rr['campHp'][i] > 0 for i in G[gid]['idx']):
            return 'alive'
        return 'reward' if rr['gr'][gid] else 'resp'

    dead_r = defaultdict(list)
    for gg in G:
        prev = False
        for r in range(1, final + 1):
            rr = R.get(r)
            if rr is None:
                continue
            dead = all(rr['campHp'][i] == 0 for i in gg['idx'])
            if dead and not prev:
                dead_r[gg['id']].append(r)
            prev = dead

    # ---- events
    evr = defaultdict(list)
    for e in d['events']:
        if e['k'] != 'Draft champion':
            evr[e['r']].append(e)
    hits = defaultdict(list)          # body -> [(r, gid, camp index)]
    camp_hits_r = defaultdict(lambda: defaultdict(set))  # r -> camp index -> set(team)
    champ_given = defaultdict(set)
    champ_taken = defaultdict(set)
    moved = defaultdict(set)
    caps = []                         # (r, body, gid, gems, gold)
    recall_r = defaultdict(set)
    cancel_r = defaultdict(set)
    own_ev = defaultdict(set)
    shops = defaultdict(list)
    deaths = defaultdict(list)
    respawn_r = defaultdict(list)
    submit_r = defaultdict(list)
    banked = []
    for r in range(1, final + 1):
        prev = S.get(r - 1) or S.get(r)
        if prev is None:
            continue
        pos = {i: ((c[3], c[4]) if c[7] else None) for i, c in prev.items()}
        for e in evr.get(r, []):
            k, who = e['k'], e.get('who')
            if who is not None and k in ('Move', 'Attack', 'Cast ability', 'Recall', 'Cancel channel', 'Place ward', 'Submit gems', 'Shop'):
                own_ev[who].add(r)
            if k == 'Move' and who is not None:
                moved[who].add(r)
                pos[who] = tuple(e['to'])
            elif k == 'Cast ability' and who is not None:
                P = tuple(e['to']) if 'to' in e else None
                if e.get('ability') == 6 and P is not None:
                    moved[who].add(r)
                    pos[who] = P
                if P is None or e.get('ability') in (1, 5, 6, 7):
                    continue
                rad = 1 if e.get('ability') == 3 else 0
                tg = [j for j, pj in pos.items() if pj is not None and team[j] != team[who] and cheb(pj, P) <= rad]
                if tg:
                    champ_given[who].add(r)
                    for j in tg:
                        champ_taken[j].add(r)
                else:
                    for q, ci in camp_at.items():
                        if cheb(q, P) <= rad and q in tile_group:
                            hits[who].append((r, tile_group[q], ci))
                            camp_hits_r[r][ci].add(team[who])
            elif k == 'Attack' and who is not None:
                P = tuple(e['to'])
                tg = [j for j, pj in pos.items() if pj == P and team[j] != team[who]]
                if tg:
                    champ_given[who].add(r)
                    champ_taken[tg[0]].add(r)
                elif P in camp_at:
                    hits[who].append((r, tile_group.get(P), camp_at[P]))
                    camp_hits_r[r][camp_at[P]].add(team[who])
            elif k == 'Recall' and who is not None:
                recall_r[who].add(r)
            elif k == 'Cancel channel' and who is not None:
                cancel_r[who].add(r)
            elif k == 'Shop' and who is not None:
                shops[who].append(r)
            elif k == 'Submit gems' and who is not None:
                submit_r[who].append(r)
            elif k == 'Banked':
                banked.append((r, e['who'], e['gems']))
            elif k == 'Death':
                deaths[who].append(r)
                pos[who] = None
            elif k in ('CaptureGems', 'CaptureGold'):
                caps.append((r, who, tile_group.get(tuple(e['at'])), e['gems'], e['gold']))
            elif k == 'Teleport complete' and who is not None:
                pos[who] = tuple(e['to'])
            elif k == 'Respawn' and who is not None:
                respawn_r[who].append(r)
                pos[who] = tuple(e['to'])
    # respawns from state (Respawn events have no who in some decodes)
    for b in bodies:
        for r in range(2, final + 1):
            c0, c1 = S.get(r - 1, {}).get(b), S.get(r, {}).get(b)
            if c0 and c1 and not c0[7] and c1[7]:
                respawn_r[b].append(r)
    # held recalls
    held = defaultdict(set)
    held_start = defaultdict(list)
    for b in bodies:
        for x in sorted(recall_r[b]):
            if (x + 1) in own_ev[b] or (x + 1) in cancel_r[b]:
                continue
            nxt = S.get(x + 1, {}).get(b)
            if nxt is None or not nxt[7]:
                continue
            held_start[b].append(x)
            for k2 in range(0, 7):
                held[b].add(x + k2)
                ck = S.get(x + k2 + 1, {}).get(b)
                if ck is None or not ck[7] or (ck[3], ck[4]) in spawn[team[b]]:
                    break
    # tribute channel rounds
    bank_rounds = defaultdict(set)
    bk_by = defaultdict(list)
    for (r, who, gems) in banked:
        bk_by[who].append(r)
    for b in bodies:
        for s0 in submit_r[b]:
            end = next((x for x in bk_by[b] if x >= s0), None)
            if end is None or end - s0 > 40:
                end = s0
            for x in range(s0, end + 1):
                bank_rounds[b].add(x)
    # camp damage per round attributed to teams
    camp_dmg = {0: defaultdict(float), 1: defaultdict(float)}  # team -> r -> dmg
    for r in range(2, final + 1):
        r0, r1 = R.get(r - 1), R.get(r)
        if r0 is None or r1 is None:
            continue
        for ci, tms in camp_hits_r.get(r, {}).items():
            dd = r0['campHp'][ci] - r1['campHp'][ci]
            if dd > 0 and tms:
                for t in tms:
                    camp_dmg[t][r] += dd / len(tms)
    hit_rounds = {b: defaultdict(set) for b in bodies}
    for b in bodies:
        for r, gid, ci in hits[b]:
            hit_rounds[b][r].add(gid)

    # ---- body states and contested flags
    states = {b: {} for b in bodies}
    contested = {b: {} for b in bodies}   # enemy within 6 at round start
    for b in bodies:
        t = team[b]
        for r in range(1, final + 1):
            c = S.get(r, {}).get(b)
            if c is None:
                continue
            if not c[7]:
                states[b][r] = 'dead'
                continue
            p = (c[3], c[4])
            pc = S.get(r - 1, {}).get(b)
            pp = (pc[3], pc[4]) if pc is not None and pc[7] else None
            prevS = S.get(r - 1, {})
            en = min([cheb(pp, (q[3], q[4])) for i, q in prevS.items() if q[7] and team[i] != t] or [99]) if pp else 99
            contested[b][r] = en <= 6
            if p in spawn[t] and (pp is None or pp in spawn[t] or r not in moved[b]):
                st = 'spawn'
            elif r in bank_rounds[b]:
                st = 'bank'
            elif r in held[b]:
                st = 'recall'
            elif r in champ_given[b] or r in champ_taken[b]:
                st = 'fight'
            elif r in hit_rounds[b]:
                st = 'hit'
            elif p in tile_group and gstate(tile_group[p], r) == 'reward':
                st = 'capture'
            elif r in moved[b]:
                st = 'walk'
            else:
                near = min((gdist(p, gg['id']) for gg in G), default=99)
                st = 'wait' if near <= 4 else 'idle'
            states[b][r] = st

    rows = []
    for t in (0, 1):
        tb = [b for b in bodies if team[b] == t]
        info = teams_info[t]
        row = {'mid': os.path.basename(dec_path)[:-5], 'map': mapname, 'team': t, 'name': info.get('name'), 'teamId': info.get('teamId'),
               'rating': info.get('rating'), 'res': info.get('res'), 'ver': info.get('ver'), 'kind': info.get('kind'),
               'opp_rating': teams_info[1 - t].get('rating'), 'opp_name': teams_info[1 - t].get('name'),
               'final': final, 'nbody': len(tb), 'sub': meta['submitted'][t], 'sub_opp': meta['submitted'][1 - t],
               'draft': meta['drafts'][t],
               'mapclass': {'area': W * H, 'ngroups': len(G), 'altars': altars, 'gems_total': sum(gg['gems'] for gg in G),
                            'gold_total': sum(gg['gold'] for gg in G), 'mono': any('monolith' in gg['types'] for gg in G),
                            'nbig': sum(1 for gg in G if gg['gems'] >= 30), 'spawn_dist': dist[0][mj['spawnB'][0][1]][mj['spawnB'][0][0]]}}
        # phases
        ph = []
        for (a, z) in PHASES:
            z = min(z, final)
            if a > z:
                ph.append(None)
                continue
            st = Counter()
            st_c = Counter()
            hits_n = hits_c = 0
            for b in tb:
                for r in range(a, z + 1):
                    s = states[b].get(r)
                    if s is None:
                        continue
                    st[s] += 1
                    if contested[b].get(r):
                        st_c[s] += 1
                for r, gid, ci in hits[b]:
                    if a <= r <= z:
                        hits_n += 1
                        hits_c += 1 if contested[b].get(r) else 0
            dmg = sum(v for r, v in camp_dmg[t].items() if a <= r <= z)
            gems = sum(c[3] for c in caps if a <= c[0] <= z and team[c[1]] == t)
            gold = sum(c[4] for c in caps if a <= c[0] <= z and team[c[1]] == t)
            ncap = sum(1 for c in caps if a <= c[0] <= z and team[c[1]] == t and c[3] > 0)
            # gold-only groups (gems 0) vs gem groups: hits and captures
            hits_goldg = sum(1 for b in tb for (r, gid, ci) in hits[b] if a <= r <= z and gid is not None and G[gid]['gems'] == 0)
            ncap_goldg = sum(1 for c in caps if a <= c[0] <= z and team[c[1]] == t and c[2] is not None and G[c[2]]['gems'] == 0)
            gold_goldg = sum(c[4] for c in caps if a <= c[0] <= z and team[c[1]] == t and c[2] is not None and G[c[2]]['gems'] == 0)
            cap_big = sum(c[3] for c in caps if a <= c[0] <= z and team[c[1]] == t and c[2] is not None and G[c[2]]['gems'] >= 30)
            cap_enemy_side = sum(c[3] for c in caps if a <= c[0] <= z and team[c[1]] == t and c[2] is not None and gd[t][c[2]] is not None and gd[1 - t][c[2]] is not None and gd[t][c[2]] > gd[1 - t][c[2]])
            hits_enemy_side = sum(1 for b in tb for (r, gid, ci) in hits[b] if a <= r <= z and gid is not None and gd[t][gid] is not None and gd[1 - t][gid] is not None and gd[t][gid] > gd[1 - t][gid])
            # gold earned: positive deltas of c[9]
            ge = 0
            for b in tb:
                for r in range(a, z + 1):
                    c0, c1 = S.get(r - 1, {}).get(b), S.get(r, {}).get(b)
                    if c0 and c1 and c1[9] > c0[9]:
                        ge += c1[9] - c0[9]
            # gold income = gold spent on shards (30 x shard-equivalents gained) + change of unspent gold (consumables ignored):
            # the capture-recall-shop pattern lands a reward and spends it in the same round, so c[9] deltas miss it
            gi = 0
            for b in tb:
                c0 = S.get(a - 1, {}).get(b) or S.get(a, {}).get(b)
                c1 = S.get(z, {}).get(b)
                if c0 and c1:
                    gi += 30 * (shard_eq(c1[11])[0] - shard_eq(c0[11])[0]) + (c1[9] - c0[9])
            bank = sum(g for (r, who, g) in banked if a <= r <= z and team[who] == t)
            lost = 0
            for b in tb:
                for r in deaths[b]:
                    if a <= r <= z:
                        c0 = S.get(r - 1, {}).get(b)
                        lost += c0[8] if c0 else 0
            rounds = z - a + 1
            ph.append({'a': a, 'z': z, 'rounds': rounds, 'brounds': sum(st.values()), 'hits': hits_n, 'hits_c': hits_c, 'dmg': round(dmg),
                       'gems': gems, 'gold_cap': gold, 'ncap': ncap, 'gold_earned': ge, 'gold_income': gi, 'banked': bank, 'lost': lost,
                       'hits_goldg': hits_goldg, 'ncap_goldg': ncap_goldg, 'gold_goldg': gold_goldg, 'cap_big': cap_big,
                       'cap_enemy_side': cap_enemy_side, 'hits_enemy_side': hits_enemy_side,
                       'st': dict(st), 'st_c': dict(st_c), 'deaths': sum(1 for b in tb for r in deaths[b] if a <= r <= z)})
        row['phases'] = ph
        mycaps = sorted(c for c in caps if team[c[1]] == t)
        row['first_cap'] = next((c[0] for c in mycaps if c[3] > 0), None)
        row['first_cap_any'] = mycaps[0][0] if mycaps else None
        row['gems150'] = sum(c[3] for c in mycaps if c[0] <= 150)
        row['gems300'] = sum(c[3] for c in mycaps if c[0] <= 300)
        row['ncap150'] = sum(1 for c in mycaps if c[0] <= 150 and c[3] > 0)
        row['ncap300'] = sum(1 for c in mycaps if c[0] <= 300 and c[3] > 0)
        # ---- items at checkpoints, builds, emblems, shops
        chk = {}
        for cr in CHECKS:
            if cr > final:
                chk[cr] = None
                continue
            s = S.get(cr, {})
            sh = em = gold_un = 0
            per = []
            for b in tb:
                c = s.get(b)
                if not c:
                    continue
                a_, e_ = shard_eq(c[11])
                sh += a_
                em += e_
                gold_un += c[9]
                per.append(a_)
            chk[cr] = {'shards': sh, 'emblems': em, 'gold': gold_un, 'per_body': per}
        row['checks'] = chk
        builds = {}
        emblem_rounds = []
        for b in tb:
            seq = []
            prev = {}
            for r in range(1, final + 1):
                c = S.get(r, {}).get(b)
                if not c:
                    continue
                cur = dict((it, q) for it, q in c[11])
                for it, q in cur.items():
                    dq = q - prev.get(it, 0)
                    if dq > 0:
                        fam, rest = divmod(it, 6)
                        seq.append((r, fam, rest // 2, rest % 2, dq))
                        if rest % 2 == 1:
                            emblem_rounds.append((r, b, fam, rest // 2))
                prev = cur
            builds[b] = {'champ': types[b], 'seq': seq}
        row['builds'] = {str(b): v for b, v in builds.items()}
        emblem_rounds.sort()
        row['emblem_rounds'] = emblem_rounds[:6]
        row['emblems_total'] = len(emblem_rounds)
        # shops: classify
        sh_cls = Counter()
        shop_list = []
        for b in tb:
            last = -99
            for r in sorted(set(shops[b])):
                if r - last <= 2:
                    last = r
                    continue  # same trip
                last = r
                if any(r - 12 <= x <= r for x in respawn_r[b]):
                    cls = 'respawn'
                elif any(r - 9 <= x <= r for x in held_start[b]):
                    cls = 'recall'
                else:
                    # was the body on spawn for the last 12 rounds?
                    on = all(((S.get(x, {}).get(b) or [0] * 8)[3], (S.get(x, {}).get(b) or [0] * 8)[4]) in spawn[t] for x in range(max(1, r - 12), r))
                    cls = 'at-spawn' if on and r > 15 else 'walk' if r > 15 else 'start'
                sh_cls[cls] += 1
                c = S.get(r, {}).get(b)
                shop_list.append((r, b, cls, c[9] if c else None))
        row['shops'] = dict(sh_cls)
        row['shop_list'] = shop_list[:80]
        row['held_recalls'] = sum(len(held_start[b]) for b in tb)
        row['deaths'] = sum(len(deaths[b]) for b in tb)
        # ---- opening visits per body (r1-150)
        ob = {}
        for b in tb:
            hs = sorted((r, gid) for r, gid, ci in hits[b] if gid is not None)
            visits = []
            cur = None
            for r, gid in hs:
                if cur and cur['g'] == gid and r - cur['last'] <= 8:
                    cur['last'] = r
                    cur['n'] += 1
                    continue
                if cur:
                    visits.append(cur)
                if r > HORIZON:
                    cur = None
                    break
                cur = {'g': gid, 'first': r, 'last': r, 'n': 1}
            if cur:
                visits.append(cur)
            for v in visits:
                gid = v['g']
                kr = [x for x in dead_r[gid] if x >= v['first']]
                v['kill'] = kr[0] if kr and kr[0] <= v['last'] + 3 else None
                cs = [c for c in caps if c[2] == gid and c[0] >= v['first'] and (v['kill'] is None or c[0] <= v['kill'] + 30)]
                if v['kill'] is not None and cs:
                    c0 = cs[0]
                    v['cap_r'] = c0[0]
                    v['cap_team'] = 'own' if team[c0[1]] == t else 'enemy'
                else:
                    v['cap_r'] = v['cap_team'] = None
                v['gems'], v['gold'], v['val'] = G[gid]['gems'], G[gid]['gold'], gval[gid]
                v['d'] = gd[t][gid]
                v['d_enemy'] = gd[1 - t][gid]
                v['rank'] = grank[(t, gid)]
                v['types'] = ''.join(TCH[x] for x in G[gid]['types'])
                v['mates'] = sorted({bb for bb in tb if bb != b and any(v['first'] - 5 <= r <= v['last'] + 5 and gg2 == gid for r, gg2, ci in hits[bb])})
                v['enemies'] = sorted({bb for bb in bodies if team[bb] != t and any(v['first'] - 5 <= r <= v['last'] + 5 and gg2 == gid for r, gg2, ci in hits[bb])})
            ob[str(b)] = {'champ': types[b], 'visits': visits, 'first_hit': visits[0]['first'] if visits else None,
                          'deaths150': [r for r in deaths[b] if r <= HORIZON]}
        row['opening'] = ob
        row['groups'] = [{'id': gg['id'], 'gems': gg['gems'], 'gold': gg['gold'], 'val': gval[gg['id']], 'd': gd[t][gg['id']],
                          'd_enemy': gd[1 - t][gg['id']], 'rank': grank[(t, gg['id'])], 'types': ''.join(TCH[x] for x in gg['types'])} for gg in G]
        rows.append(row)
    return rows


def jobs_top30():
    sel = {s['matchId']: s for s in (json.loads(l) for l in open(f'{T30}/selection.jsonl'))}
    lad = {t['teamId']: t for t in json.load(open(f'{T30}/ladder.json'))['teams']}
    by8 = {}
    for mid, s in sel.items():
        by8[s['map'] + '_' + mid[:8]] = s
    out = []
    for f in sorted(os.listdir(f'{T30}/dec')):
        if not f.endswith('.json'):
            continue
        key = f[:-5]
        s = by8.get(key)
        mjp = f'/home/claude/data/mapjson_pool/{s["map"]}.json' if s else None
        if s is None or not os.path.exists(mjp) or os.path.getsize(f'{T30}/dec/{f}') == 0:
            continue
        ti = {}
        for tm in s['teams']:
            t = 0 if tm['side'] == 'a' else 1
            ti[t] = {'name': tm['name'], 'teamId': tm['teamId'], 'rating': lad.get(tm['teamId'], {}).get('rating'),
                     'res': 'W' if tm['result'] == 'win' else 'L', 'ver': None, 'kind': s['kind']}
        if 0 in ti and 1 in ti:
            out.append((f'{T30}/dec/{f}', mjp, s['map'], ti))
    return out


def jobs_ours():
    lad = {t['teamId']: t for t in json.load(open(f'{T30}/ladder.json'))['teams']}
    rows = [json.loads(l) for l in open(f'{OURS}/matches_me.jsonl')]
    out = []
    seen = set()
    for m in rows:
        mid = m['matchId']
        if mid in seen or m.get('status') != 'finished':
            continue
        seen.add(mid)
        if not (os.path.exists(f'{OURS}/dec/{mid}.json') and os.path.exists(f'{OURS}/mj/{mid}.json')):
            continue
        if os.path.getsize(f'{OURS}/dec/{mid}.json') == 0:
            continue
        v = version(m['createdAt'])
        if v == 'pre':
            continue
        ti = {}
        for tm in m['teams']:
            t = 0 if tm['side'] == 'a' else 1
            ti[t] = {'name': tm['name'], 'teamId': tm['teamId'], 'rating': lad.get(tm['teamId'], {}).get('rating'),
                     'res': 'W' if tm['result'] == 'win' else 'L', 'ver': v, 'kind': m['kind'], 'me': tm['teamId'] == ME}
        out.append((f'{OURS}/dec/{mid}.json', f'{OURS}/mj/{mid}.json', m['map'], ti))
    return out


def work(job):
    try:
        rows = analyse(job)
        for r, (t, ti) in zip(rows, sorted(job[3].items())):
            r['me'] = ti.get('me', False)
        return rows
    except Exception as ex:  # noqa
        import traceback
        return [{'error': f'{job[0]}: {ex}', 'tb': traceback.format_exc()[-800:]}]


def main():
    which = sys.argv[1]
    jobs = jobs_top30() if which == 'top30' else jobs_ours()
    out = f'{ECO}/rows_{which}.jsonl'
    done = set()
    if os.path.exists(out) and '--fresh' not in sys.argv:
        done = {json.loads(l)['mid'] for l in open(out) if '"error"' not in l[:40]}
        jobs = [j for j in jobs if os.path.basename(j[0])[:-5] not in done]
    print(len(jobs), 'games', '(incremental, %d done)' % len(done), flush=True)
    n = 0
    with Pool(3) as pool, open(out, 'a' if done else 'w') as f:
        for rows in pool.imap_unordered(work, jobs, chunksize=2):
            for r in rows:
                f.write(json.dumps(r) + '\n')
            n += 1
            if n % 25 == 0:
                print(n, flush=True)
    print('done', n)


if __name__ == '__main__':
    main()
