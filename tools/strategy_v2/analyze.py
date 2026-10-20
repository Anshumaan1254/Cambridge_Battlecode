#!/usr/bin/env python3
"""Deep analysis of decoded CAMBC replays (decode_dmg.mjs output).

usage: python3 -I analyze.py DMG_DIR MAPGEO_JSON OUT_DIR

Writes CSV tables (team, body, engagements, deaths, camp kills, recalls, banks, items) and a JSON
with everything, so the strategy docs can cite exact numbers. Team 0 = side A = our bot.
"""
import collections
import csv
import glob
import json
import math
import os
import statistics
import sys
from collections import deque

BASE = {  # health, growth, strength, growth, focus, growth  (handbook, patch 3.0 of Oct 20 2026)
    'Cassi': (600, 65, 30, 3, 70, 13), 'Issac': (900, 80, 40, 3, 100, 10),
    'Ryth': (1200, 100, 45, 5, 100, 10), 'VesperVale': (900, 100, 50, 5, 100, 10),
    'Prism': (700, 60, 35, 2.5, 80, 8), 'Stellar': (750, 75, 30, 3.5, 85, 9),
    'Vendetta': (800, 100, 70, 6, 100, 10), 'Marcella': (1200, 100, 45, 5, 60, 15),
    'Tavi': (750, 75, 45, 5, 100, 10), 'Willow': (700, 50, 55, 3, 120, 5),
    'Ren': (900, 100, 35, 5, 100, 9), 'Varg': (1000, 100, 40, 5, 100, 10),
    'HeartOfRuin': (1000, 100, 40, 5, 100, 15),
}
CH = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin']
FAM = 'MPDTJHB'
FAMNAME = {'M': 'Monster', 'P': 'Power', 'D': 'Durability', 'T': 'Treasure', 'J': 'Jungle', 'H': 'Home', 'B': 'Bruiser'}
ST = 'sfh'
RANGED = {'Cassi', 'Stellar', 'Prism', 'Tavi', 'Willow', 'VesperVale'}


def item_name(k, q):
    return f"{FAM[k // 6]}{ST[(k // 2) % 3]}{'E' if k % 2 else ''}{q if (q > 1 or k % 2 == 0) else ''}"


def stat_points(items):
    pts = {'s': 0, 'f': 0, 'h': 0}
    passives = set()
    spent = 0
    for k, q in items:
        fam, st, emb = FAM[k // 6], ST[(k // 2) % 3], k % 2
        if not emb:
            pts[st] += q
            spent += 30 * q
            continue
        spent += 150 * q
        if fam == 'P':
            pts[st] += 6 * q
        elif fam == 'B':
            pts[st] += 5 * q
            for o in 'sfh':
                if o != st:
                    pts[o] += q
        else:
            pts[st] += 5 * q
            passives.add(fam)
    return pts, passives, spent


def stats_of(champ, items):
    h0, hg, s0, sg, f0, fg = BASE[champ]
    pts, passives, spent = stat_points(items)
    hp = h0 + hg * pts['h']
    st = s0 + sg * pts['s']
    if champ == 'Ryth':
        st += 0.01 * (hp - h0)
    fo = f0 + fg * pts['f']
    return hp, st, fo, passives, spent, pts


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def bfs(grid, w, h, sources):
    INF = 10 ** 9
    dist = [[INF] * w for _ in range(h)]
    dq = deque()
    for (x, y) in sources:
        dist[y][x] = 0
        dq.append((x, y))
    while dq:
        x, y = dq.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if not dx and not dy:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and dist[ny][nx] == INF and grid[ny][nx] not in '#oA':
                    dist[ny][nx] = dist[y][x] + 1
                    dq.append((nx, ny))
    return dist


def mirror(sym, w, h, x, y):
    if sym.startswith('H'):
        return w - 1 - x, y
    if sym.startswith('V'):
        return x, h - 1 - y
    return w - 1 - x, h - 1 - y


def analyze(path, geo):
    name = os.path.basename(path)[:-5]
    d = json.load(open(path))
    meta, R, ev, dmg = d['meta'], d['rounds'], d['events'], d['dmg']
    g = geo[name]
    w, h, sym = g['w'], g['h'], g['sym']
    grid = [list(row.ljust(w, '.')) for row in g['grid']]
    x0, y0, x1, y1 = g['spawnA']
    spawn = [set(), set()]
    for y in range(y0, y1):
        for x in range(x0, x1):
            spawn[0].add((x, y))
            spawn[1].add(mirror(sym, w, h, x, y))
    for t in (0, 1):
        for (x, y) in spawn[t]:
            if grid[y][x] in 'Ss':
                grid[y][x] = '.'
    dist = [bfs(grid, w, h, spawn[0]), bfs(grid, w, h, spawn[1])]

    def side_of(team, pos):
        x, y = pos
        if not (0 <= x < w and 0 <= y < h):
            return 'own'
        do, de = dist[team][y][x], dist[1 - team][y][x]
        if do >= 10 ** 9 or de >= 10 ** 9:
            return 'neutral'
        if do < de - 3:
            return 'own'
        if de < do - 3:
            return 'enemy'
        return 'neutral'

    bodies = meta['bodies']
    nb = len(bodies)
    btype = {b['index']: b['type'] for b in bodies}
    bteam = {b['index']: b['team'] for b in bodies}
    last = R[-1]['r']
    outcome = meta['outcome']
    winner = 0 if outcome == 1 else 1 if outcome == 2 else -1
    camps = meta['camps']
    ncamp = len(camps)
    camp_pos = {c['index']: (c['x'], c['y']) for c in camps}
    camp_type = {c['index']: c['type'] for c in camps}
    camp_max = {c['index']: c['hp'] for c in camps}
    # camp groups: cardinal components
    pos2camp = {(c['x'], c['y']): c['index'] for c in camps}
    comp = {}
    gid = 0
    for c in camps:
        if c['index'] in comp:
            continue
        stack = [c['index']]
        comp[c['index']] = gid
        while stack:
            ci = stack.pop()
            x, y = camp_pos[ci]
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                o = pos2camp.get((x + dx, y + dy))
                if o is not None and o not in comp:
                    comp[o] = gid
                    stack.append(o)
        gid += 1
    groups = collections.defaultdict(list)
    for ci, gi in comp.items():
        groups[gi].append(ci)
    camp_index_order = [c['index'] for c in camps]

    # per round state per body
    st = {}  # (r, body) -> tuple
    for rr in R:
        for c in rr['ch']:
            st[(rr['r'], c[0])] = c
    rounds = [rr['r'] for rr in R]
    rset = set(rounds)

    def state(r, b):
        while r >= 0 and (r, b) not in st:
            r -= 1
        return st.get((r, b))

    # ---- per-round damage aggregation ----
    dealt_c = collections.defaultdict(float)   # (r, body) dmg dealt to enemy champions
    taken_c = collections.defaultdict(float)   # (r, body) dmg taken from champions
    dealt_m = collections.defaultdict(float)   # (r, body) dmg dealt to camps
    taken_m = collections.defaultdict(float)   # (r, body) dmg taken from camps
    camp_dmg_by_team = collections.defaultdict(lambda: [0.0, 0.0])  # (camp, r) -> team dmg
    champ_hits = []  # (r, actor, target, dmg, x, y)
    for rec in dmg:
        r, kind, akind, ai, slot, tkind, ti, dh, alive, tx, ty, ohp, omax = rec
        if dh >= 0:
            continue
        dd = -dh
        if akind == 'c' and tkind == 'c':
            if ai in bteam and ti in bteam and bteam[ai] != bteam[ti]:
                dealt_c[(r, ai)] += dd
                taken_c[(r, ti)] += dd
                champ_hits.append((r, ai, ti, dd, tx, ty))
        elif akind == 'c' and tkind == 'm':
            if ai in bteam:
                dealt_m[(r, ai)] += dd
                camp_dmg_by_team[(ti, r)][bteam[ai]] += dd
        elif akind == 'm' and tkind == 'c':
            taken_m[(r, ti)] += dd
        elif akind == 'm' and tkind == 'm':
            pass  # Ren retaliation: attribute to nearest enemy Ren? skip (small)

    # ---- events ----
    by_kind = collections.defaultdict(list)
    for e in ev:
        by_kind[e['k']].append(e)

    deaths = by_kind['Death']
    caps = by_kind['CaptureGems']
    recalls = by_kind['Recall']
    submits = by_kind['Submit gems']
    banked = by_kind['Banked']

    kills = collections.Counter()
    for e in deaths:
        if isinstance(e.get('by'), int) and e['by'] in bteam and bteam[e['by']] != e['team']:
            kills[e['by']] += 1
    # Cassi&Issac double death = one kill credit; count credited kills from snapshot instead
    credited = {b: (R[-1]['ch'][i][10] if i < len(R[-1]['ch']) else 0) for i, b in enumerate(btype)}
    credited = {c[0]: c[10] for c in R[-1]['ch']}

    # ---- activity labelling ----
    recall_active = set()
    for e in recalls:
        b = e['who']
        for k in range(0, 6):
            rr = e['r'] + k
            s = state(rr, b)
            if s is None:
                break
            if k > 0 and (s[3], s[4]) in spawn[bteam[b]]:
                break
            recall_active.add((rr, b))
    tribute_active = set()
    bank_by_body = collections.defaultdict(list)
    for e in banked:
        bank_by_body[e['who']].append(e['r'])
    for e in submits:
        b = e['who']
        ends = [r for r in bank_by_body[b] if r >= e['r']]
        end = min(ends) if ends else e['r']
        if end - e['r'] > 30:
            end = e['r']
        for rr in range(e['r'], end + 1):
            tribute_active.add((rr, b))
    dead_camp_tiles = {}
    camp_hp_round = {}
    for rr in R:
        hp = rr['campHp']
        camp_hp_round[rr['r']] = hp
    act = collections.defaultdict(collections.Counter)  # body -> label counts
    territory = collections.defaultdict(collections.Counter)
    near_ally = collections.defaultdict(list)
    moved = collections.defaultdict(int)
    prevpos = {}
    for rr in R:
        r = rr['r']
        hp = rr['campHp']
        dead_tiles = set()
        for idx, cpos in enumerate(camp_index_order):
            if idx < len(hp) and hp[idx] <= 0:
                dead_tiles.add(camp_pos[cpos])
        alive_pos = {c[0]: (c[3], c[4]) for c in rr['ch'] if c[7]}
        for c in rr['ch']:
            b = c[0]
            pos = (c[3], c[4])
            t = bteam[b]
            if not c[7]:
                lab = 'dead'
            elif (r, b) in recall_active:
                lab = 'recall'
            elif (r, b) in tribute_active:
                lab = 'tribute'
            elif dealt_c[(r, b)] > 0 or taken_c[(r, b)] > 0:
                lab = 'fight'
            elif dealt_m[(r, b)] > 0 or taken_m[(r, b)] > 0:
                lab = 'camp'
            elif pos in dead_tiles:
                lab = 'capture'
            elif pos in spawn[t]:
                lab = 'spawn'
            elif prevpos.get(b) is not None and prevpos[b] != pos:
                lab = 'walk'
            else:
                lab = 'idle'
            act[b][lab] += 1
            if c[7]:
                territory[b][side_of(t, pos)] += 1
                ds = [cheb(pos, p) for o, p in alive_pos.items() if o != b and bteam[o] == t and not ({btype[o], btype[b]} == {'Cassi', 'Issac'})]
                if ds:
                    near_ally[b].append(min(ds))
            prevpos[b] = pos if c[7] else None

    # ---- items timeline ----
    emblem_rounds = collections.defaultdict(list)  # body -> [(r, name)]
    prev_items = {}
    for rr in R:
        for c in rr['ch']:
            b = c[0]
            cur = {k: q for k, q in c[11]}
            pv = prev_items.get(b, {})
            for k, q in cur.items():
                if k % 2 == 1 and q > pv.get(k, 0):
                    for _ in range(q - pv.get(k, 0)):
                        emblem_rounds[b].append((rr['r'], item_name(k, 1).rstrip('1')))
            prev_items[b] = cur

    # gold earned per body: gold diff + spending diff
    earned = collections.Counter()
    spent_tot = collections.Counter()
    prev_gold = {}
    prev_spent = {}
    gold_curve = collections.defaultdict(dict)
    for rr in R:
        for c in rr['ch']:
            b = c[0]
            _, _, spent = stat_points(c[11])
            g0 = prev_gold.get(b, 0)
            s0 = prev_spent.get(b, 0)
            inc = (c[9] - g0) + (spent - s0)
            if inc > 0:
                earned[b] += inc
            prev_gold[b] = c[9]
            prev_spent[b] = spent
            spent_tot[b] = spent
            gold_curve[b][rr['r']] = earned[b]

    # ---- camp group kills ----
    hp_series = {}
    for rr in R:
        hp_series[rr['r']] = rr['campHp']
    idx_of = {ci: i for i, ci in enumerate(camp_index_order)}
    group_kills = []
    for gi, members in groups.items():
        ms = [idx_of[c] for c in members]
        maxhp = sum(camp_max[c] for c in members)
        alive_prev = True
        start = None
        for r in rounds:
            hp = hp_series[r]
            tot = sum(max(0, hp[i]) for i in ms if i < len(hp))
            alive = tot > 0
            if alive and start is None and tot < maxhp - 0.5:
                start = r
            if alive_prev and not alive:
                tdmg = [0.0, 0.0]
                for rr2 in range(start if start is not None else r, r + 1):
                    for c in members:
                        v = camp_dmg_by_team.get((c, rr2))
                        if v:
                            tdmg[0] += v[0]
                            tdmg[1] += v[1]
                killer = 0 if tdmg[0] > tdmg[1] else 1
                types = collections.Counter(camp_type[c] for c in members)
                cpos = camp_pos[members[0]]
                group_kills.append(dict(match=name, group=gi, r=r, start=start if start is not None else r,
                                        dur=r - (start if start is not None else r) + 1, killer=killer,
                                        dmg0=round(tdmg[0]), dmg1=round(tdmg[1]), maxhp=maxhp,
                                        types='+'.join(f'{v}{k}' for k, v in sorted(types.items())),
                                        n=len(members), side_for_killer=side_of(killer, cpos), x=cpos[0], y=cpos[1]))
                start = None
            if not alive_prev and alive:
                start = None
            alive_prev = alive

    # ---- engagements (union-find over champion hits) ----
    hits = sorted(champ_hits)
    parent = list(range(len(hits)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    j0 = 0
    for i in range(len(hits)):
        while hits[j0][0] < hits[i][0] - 3:
            j0 += 1
        for j in range(j0, i):
            if cheb((hits[i][4], hits[i][5]), (hits[j][4], hits[j][5])) <= 8:
                ra, rb = find(i), find(j)
                if ra != rb:
                    parent[ra] = rb
    clusters = collections.defaultdict(list)
    for i in range(len(hits)):
        clusters[find(i)].append(hits[i])
    engagements = []
    for cl in clusters.values():
        r0 = min(x[0] for x in cl)
        r1 = max(x[0] for x in cl)
        cx = statistics.median(x[4] for x in cl)
        cy = statistics.median(x[5] for x in cl)
        part = [set(), set()]
        dmgside = [0.0, 0.0]
        for (r, a, t, dd, x, y) in cl:
            part[bteam[a]].add(a)
            part[bteam[t]].add(t)
            dmgside[bteam[a]] += dd
        involved = part[0] | part[1]
        dth = [0, 0]
        dth_c = [0, 0]
        for e in deaths:
            if r0 <= e['r'] <= r1 + 2 and (e['who'] in involved or cheb(tuple(e['at']), (cx, cy)) <= 8):
                dth[e['team']] += 1
                if isinstance(e.get('by'), int):
                    dth_c[e['team']] += 1
        # numbers around the first hit at the start (alive bodies within 8 of first hit location)
        first = min(cl)
        fx, fy = first[4], first[5]
        near = [0, 0]
        for b in btype:
            s = state(r0 - 1, b)
            if s and s[7] and cheb((s[3], s[4]), (fx, fy)) <= 8:
                near[bteam[b]] += 1
        first_attacker_team = bteam[first[1]]
        engagements.append(dict(match=name, r0=r0, r1=r1, x=cx, y=cy, side_for_us=side_of(0, (int(cx), int(cy))),
                                n0=len(part[0]), n1=len(part[1]), near0=near[0], near1=near[1],
                                dmg0=round(dmgside[0]), dmg1=round(dmgside[1]), deaths0=dth[0], deaths1=dth[1],
                                first=first_attacker_team, hits=len(cl)))

    # ---- deaths detail ----
    death_rows = []
    for e in deaths:
        b = e['who']
        t = e['team']
        s = state(e['r'] - 1, b)
        pos = tuple(e['at'])
        allies = enemies = 0
        ally_hp = enemy_hp = 0
        for o in btype:
            so = state(e['r'] - 1, o)
            if not so or not so[7] or o == b:
                continue
            if {btype[o], btype[b]} == {'Cassi', 'Issac'} and bteam[o] == t:
                continue
            if cheb((so[3], so[4]), pos) <= 6:
                if bteam[o] == t:
                    allies += 1
                    ally_hp += so[5]
                else:
                    enemies += 1
                    enemy_hp += so[5]
        hp_prev = s[5] if s else 0
        maxhp = s[6] if s else 1
        by = e.get('by')
        death_rows.append(dict(match=name, r=e['r'], team=t, champ=btype[b], by=('camp' if by == 'camp' else btype.get(by, by)),
                               side=side_of(t, pos), bag=e.get('bag', 0), hp_prev_frac=round(hp_prev / maxhp, 2) if maxhp else 0,
                               allies6=allies, enemies6=enemies, ally_hp=round(ally_hp), enemy_hp=round(enemy_hp)))

    # ---- recall detail ----
    recall_rows = []
    cap_by_body = collections.defaultdict(list)
    for e in caps:
        cap_by_body[e['who']].append(e['r'])
    for e in recalls:
        b = e['who']
        s = state(e['r'] - 1, b)
        if not s:
            continue
        arrived = False
        for k in range(4, 8):
            s2 = state(e['r'] + k, b)
            if s2 and (s2[3], s2[4]) in spawn[bteam[b]]:
                arrived = True
                break
        cap_after = any(e['r'] <= c <= e['r'] + 6 for c in cap_by_body[b])
        cap_before = any(e['r'] - 3 <= c < e['r'] for c in cap_by_body[b])
        recall_rows.append(dict(match=name, r=e['r'], team=bteam[b], champ=btype[b], hp_frac=round(s[5] / s[6], 2) if s[6] else 0,
                                gold=s[9], bag=s[8], arrived=arrived, cap_overlap=cap_after, cap_just_before=cap_before,
                                dist_home=min(dist[bteam[b]][s[4]][s[3]], 999) if 0 <= s[3] < w and 0 <= s[4] < h else 0))

    # ---- bank detail ----
    bank_rows = []
    for e in banked:
        b = e['who']
        s = state(e['r'], b)
        at = tuple(e['at'])
        bank_rows.append(dict(match=name, r=e['r'], team=bteam[b], champ=btype[b], gems=e['gems'],
                              side=side_of(bteam[b], at), dist_home=dist[bteam[b]][at[1]][at[0]] if 0 <= at[0] < w and 0 <= at[1] < h else -1))

    # ---- capture detail ----
    cap_rows = []
    for e in caps:
        at = tuple(e['at'])
        cap_rows.append(dict(match=name, r=e['r'], team=e['team'], champ=btype[e['who']], gems=e['gems'], gold=e['gold'],
                             side=side_of(e['team'], at), dist_home=dist[e['team']][at[1]][at[0]] if 0 <= at[0] < w and 0 <= at[1] < h else -1))

    # ---- casts ----
    casts = collections.Counter(e['who'] for e in by_kind['Cast ability'] if 'who' in e)
    prio = collections.Counter(bteam[e['who']] for e in by_kind['Set priority'] if 'who' in e)
    wards = collections.Counter(bteam[e['who']] for e in by_kind['Place ward'] if 'who' in e)
    locks = collections.Counter(bteam[e['who']] for e in by_kind['Place altar lock'] if 'who' in e)
    crystals = collections.Counter(bteam[e['who']] for e in by_kind['Teleport channel'] if 'who' in e)
    blocked = collections.Counter(bteam[e['who']] for e in by_kind['Movement blocked'] if 'who' in e)
    cancels = collections.Counter(bteam[e['who']] for e in by_kind['Cancel channel'] if 'who' in e)

    # ---- per body rows ----
    body_rows = []
    for b in sorted(btype):
        t = bteam[b]
        fin = R[-1]['ch'][[c[0] for c in R[-1]['ch']].index(b)]
        hp, stv, fo, passives, spent, pts = stats_of(btype[b], fin[11])

        def stat_at(r):
            s = state(r, b)
            if not s:
                return (0, 0, 0)
            hp_, st_, fo_, _, _, _ = stats_of(btype[b], s[11])
            return (round(hp_), round(st_, 1), round(fo_, 1))
        my_caps = [e for e in caps if e['who'] == b]
        my_deaths = [e for e in deaths if e['who'] == b]
        alive_rounds = sum(1 for r in rounds if (state(r, b) or [0] * 8)[7])
        body_rows.append(dict(
            match=name, team=t, body=b, champ=btype[b], caps=len(my_caps), cap_gems=sum(e['gems'] for e in my_caps),
            gold_earned=round(earned[b]), gold_spent=spent, deaths=len(my_deaths), kills_credited=credited.get(b, 0),
            casts=casts[b], casts_per100=round(100 * casts[b] / max(1, alive_rounds), 1),
            dmg_champ=round(sum(v for (r, bb), v in dealt_c.items() if bb == b)),
            dmg_camp=round(sum(v for (r, bb), v in dealt_m.items() if bb == b)),
            taken_champ=round(sum(v for (r, bb), v in taken_c.items() if bb == b)),
            taken_camp=round(sum(v for (r, bb), v in taken_m.items() if bb == b)),
            final_items='+'.join(item_name(k, q) for k, q in fin[11]),
            final_hp=round(hp), final_str=round(stv, 1), final_focus=round(fo, 1),
            stat150=stat_at(150), stat300=stat_at(300),
            first_emblem=(emblem_rounds[b][0][0] if emblem_rounds[b] else None),
            emblems=[f'{r}:{n}' for r, n in emblem_rounds[b]],
            act=dict(act[b]), terr=dict(territory[b]),
            med_ally_dist=(statistics.median(near_ally[b]) if near_ally[b] else None),
            first_cap=(my_caps[0]['r'] if my_caps else None),
            gold150=gold_curve[b].get(150, gold_curve[b].get(max(k for k in gold_curve[b] if k <= 150), 0)) if gold_curve[b] else 0,
        ))

    team_rows = []
    for t in (0, 1):
        tb = [r for r in body_rows if r['team'] == t]
        tot_act = collections.Counter()
        tot_terr = collections.Counter()
        for r in tb:
            tot_act.update(r['act'])
            tot_terr.update(r['terr'])
        n_act = sum(tot_act.values()) or 1
        n_terr = sum(tot_terr.values()) or 1
        golds = sorted([r['gold_earned'] for r in tb], reverse=True)
        team_rows.append(dict(
            match=name, team=t, draft=','.join(meta['drafts'][t]), won=int(winner == t), rounds=last,
            banked=meta['submitted'][t], camp_gems=sum(r['cap_gems'] for r in tb), captures=sum(r['caps'] for r in tb),
            gold=sum(golds), gold_top1_share=round(golds[0] / max(1, sum(golds)), 2), gold_top2_share=round(sum(golds[:2]) / max(1, sum(golds)), 2),
            deaths=sum(r['deaths'] for r in tb), kills=sum(r['kills_credited'] for r in tb),
            casts=sum(r['casts'] for r in tb), recalls=sum(1 for x in recall_rows if x['team'] == t),
            banks=sum(1 for x in bank_rows if x['team'] == t),
            avg_bank=round(statistics.mean([x['gems'] for x in bank_rows if x['team'] == t]), 1) if any(x['team'] == t for x in bank_rows) else 0,
            prio=prio[t], wards=wards[t], locks=locks[t], crystals=crystals[t], blocked=blocked[t], cancels=cancels[t],
            act={k: round(v / n_act, 3) for k, v in tot_act.items()}, terr={k: round(v / n_terr, 3) for k, v in tot_terr.items()},
            dmg_camp=sum(r['dmg_camp'] for r in tb), dmg_champ=sum(r['dmg_champ'] for r in tb),
            sub100=next((rr['sub'][t] for rr in R if rr['r'] >= 100), 0), sub200=next((rr['sub'][t] for rr in R if rr['r'] >= 200), 0),
            sub300=next((rr['sub'][t] for rr in R if rr['r'] >= 300), 0),
            first_emblem=min([r['first_emblem'] for r in tb if r['first_emblem']], default=None),
        ))
    return dict(name=name, team=team_rows, body=body_rows, engagements=engagements, deaths=death_rows,
                recalls=recall_rows, banks=bank_rows, captures=cap_rows, group_kills=group_kills,
                meta=dict(w=w, h=h, sym=sym, rounds=last, winner=winner, drafts=meta['drafts'], submitted=meta['submitted']))


def write_csv(path, rows):
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(path, 'w', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=keys)
        wr.writeheader()
        for r in rows:
            wr.writerow({k: (json.dumps(v) if isinstance(v, (dict, list, tuple)) else v) for k, v in r.items()})


def main():
    dmg_dir, geo_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True)
    geo = json.load(open(geo_path))
    allres = []
    for f in sorted(glob.glob(os.path.join(dmg_dir, '*.json'))):
        allres.append(analyze(f, geo))
    json.dump(allres, open(os.path.join(out, 'analysis.json'), 'w'))
    for key in ('team', 'body', 'engagements', 'deaths', 'recalls', 'banks', 'captures', 'group_kills'):
        rows = [r for res in allres for r in res[key]]
        write_csv(os.path.join(out, f'{key}.csv'), rows)
    print('wrote', out)


if __name__ == '__main__':
    main()
