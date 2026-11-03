#!/usr/bin/env python3
"""Per-game extraction for the objectives / map-control / vision stream: one JSON row per game with per-side numbers.
   nice -n 19 python3 extract_obj.py [top|me|all] [--jobs N]   ->  out/games_<ds>.jsonl
Per side t (0/1): captures by band, raids into the enemy half, gold vs gem value, wards (where, when, coverage), held recalls
(from where, why, cancelled), monolith kills; and per big group (>= 30 gems) the contest cycles: who arrived first at the respawn,
with how many bodies, how long before it, at what health, what each team did when the other was there, who took the reward."""
import json, os, sys
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

BIGGEM = 30
OUT = f'{C.OBJ}/out'
WARD_R = 6


def analyse(g):
    d, mj = C.load(g)
    meta = d['meta']
    W, H = meta['width'], meta['height']
    rows = mj['rows']
    types = {b['index']: b['type'] for b in meta['bodies']}
    team = {b['index']: b['team'] for b in meta['bodies']}
    bodies = sorted(types)
    final = meta['finalRound']
    R = {rr['r']: rr for rr in d['rounds'][1:]}
    S = {r: {c[0]: c for c in rr['ch']} for r, rr in R.items()}
    G = C.full_groups(g['map'], meta, mj['sym'])
    spawn = {0: [tuple(p) for p in mj['spawnA']], 1: [tuple(p) for p in mj['spawnB']]}
    spawn_set = {t: set(spawn[t]) for t in (0, 1)}
    dist = {0: C.bfs(rows, spawn[0], W, H), 1: C.bfs(rows, spawn[1], W, H)}
    passable = [(x, y) for y in range(H) for x in range(W) if rows[y][x] not in '#oA']
    n_pass = len(passable)
    altars = [(x, y) for y in range(H) for x in range(W) if rows[y][x] == 'A']
    camp_at = {(c['x'], c['y']): c['index'] for c in meta['camps']}
    camp_type = {c['index']: c['type'] for c in meta['camps']}

    def dh(t, p):
        x, y = p
        if 0 <= x < W and 0 <= y < H and dist[t][y][x] >= 0:
            return dist[t][y][x]
        return None

    def band(t, p):
        a, b = dh(t, p), dh(1 - t, p)
        if a is None or b is None or a + b == 0:
            return '?'
        f = a / (a + b)
        return 'own' if f < 0.42 else 'mid' if f <= 0.58 else 'their'

    # group distances from each spawn (min over tiles); band of the group for each team
    for gg in G:
        ds = []
        for t in (0, 1):
            dd = [dh(t, p) for p in gg['tiles']]
            dd = [x for x in dd if x is not None]
            ds.append(min(dd) if dd else None)
        gg['d'] = ds
        gg['band'] = {}
        for t in (0, 1):
            a, b = ds[t], ds[1 - t]
            if a is None or b is None or a + b == 0:
                gg['band'][t] = '?'
            else:
                f = a / (a + b)
                gg['band'][t] = 'own' if f < 0.42 else 'mid' if f <= 0.58 else 'their'
        gg['island'] = ds[0] is None and ds[1] is None
        gg['mono'] = 'monolith' in gg['types']
        gg['lone_mono'] = gg['mono'] and len(gg['tiles']) == 1
        gg['gold_only'] = gg['gems'] == 0 and gg['gold'] > 0
    tile_group = {t: gg['id'] for gg in G for t in gg['tiles']}
    # tile -> {gid: dist} for dist <= 6 (dilated group tiles)
    near_g = defaultdict(dict)
    for gg in G:
        for (x, y) in gg['tiles']:
            for dx in range(-6, 7):
                for dy in range(-6, 7):
                    p = (x + dx, y + dy)
                    dd = max(abs(dx), abs(dy))
                    if dd < near_g[p].get(gg['id'], 99):
                        near_g[p][gg['id']] = dd

    def gdist(p, gid):
        return near_g.get(p, {}).get(gid, 99)

    # ---------- events
    ev = defaultdict(list)
    for e in d['events']:
        if e['k'] != 'Draft champion':
            ev[e['r']].append(e)
    act = defaultdict(lambda: defaultdict(set))
    camp_hits = defaultdict(list)   # camp idx -> [(r, team, who)]
    champ_hit_given = defaultdict(set)
    champ_hit_taken = defaultdict(set)
    camp_hit_given = defaultdict(set)
    camp_hit_taken = defaultdict(set)
    captures = []
    deaths = []
    recalls = defaultdict(list)
    cancels = defaultdict(set)
    wards = []
    banked = []
    shops = defaultdict(list)
    for r in range(1, final + 1):
        prev = S.get(r - 1) or S.get(r)
        if prev is None:
            continue
        pos = {i: ((c[3], c[4]) if c[7] else None) for i, c in prev.items()}
        for e in ev.get(r, []):
            k, who = e['k'], e.get('who')
            if k == 'Move' and who is not None:
                pos[who] = tuple(e['to'])
                act[who][r].add('move')
            elif k == 'Cast ability' and who is not None:
                act[who][r].add('cast')
                if e.get('ability') == 6 and 'to' in e:
                    pos[who] = tuple(e['to'])
                P = tuple(e['to']) if 'to' in e else None
                if P is not None:
                    tg = [j for j, pj in pos.items() if pj is not None and team[j] != team[who] and C.cheb(pj, P) <= (1 if e.get('ability') == 3 else 0)]
                    if tg:
                        champ_hit_given[who].add(r)
                        for j in tg:
                            champ_hit_taken[j].add(r)
                    else:
                        for q, ci in camp_at.items():
                            if C.cheb(P, q) <= (1 if e.get('ability') == 3 else 0):
                                camp_hits[ci].append((r, team[who], who))
                                camp_hit_given[who].add(r)
            elif k == 'Attack' and who is None and 'camp' in e:
                P = tuple(e['to'])
                for j, pj in pos.items():
                    if pj == P:
                        camp_hit_taken[j].add(r)
            elif k == 'Attack' and who is not None:
                act[who][r].add('attack')
                P = tuple(e['to'])
                tg = [j for j, pj in pos.items() if pj == P and team[j] != team[who]]
                if tg:
                    champ_hit_given[who].add(r)
                    champ_hit_taken[tg[0]].add(r)
                elif P in camp_at:
                    camp_hits[camp_at[P]].append((r, team[who], who))
                    camp_hit_given[who].add(r)
            elif k == 'Teleport complete' and who is not None:
                pos[who] = tuple(e['to'])
                act[who][r].add('tele')
            elif k == 'Respawn' and who is not None:
                pos[who] = tuple(e['to'])
            elif k == 'Death':
                deaths.append(e)
                pos[who] = None
            elif k == 'Recall' and who is not None:
                recalls[who].append(r)
                act[who][r].add('recall')
            elif k == 'Cancel channel' and who is not None:
                cancels[who].add(r)
            elif k == 'Submit gems' and who is not None:
                act[who][r].add('submit')
            elif k == 'Banked':
                banked.append((r, who, e['gems']))
            elif k in ('CaptureGems', 'CaptureGold'):
                p = tuple(e['at'])
                captures.append({'r': r, 't': e['team'], 'who': who, 'gems': e['gems'], 'gold': e['gold'], 'gid': tile_group.get(p)})
            elif k == 'Place ward' and who is not None and 'to' in e:
                p = tuple(e['to'])
                wards.append({'r': r, 't': team[who], 'who': who, 'at': p})
                act[who][r].add('ward')
            elif k == 'Shop' and who is not None:
                shops[who].append(r)
    death_by_body = defaultdict(list)
    for e in deaths:
        death_by_body[e['who']].append(e['r'])
    kills_by = defaultdict(list)
    for e in deaths:
        if isinstance(e.get('by'), int):
            kills_by[e['by']].append(e['r'])

    # ---------- held recalls (analyze.py rule: the channel survives the next round)
    rec_rows = []
    for b, rs in recalls.items():
        for x in rs:
            nxt = S.get(x + 1, {}).get(b)
            if nxt is None or not nxt[7]:
                continue
            if act[b].get(x + 1) or (x + 1) in cancels[b]:
                continue
            c0 = S.get(x, {}).get(b) or nxt
            p = (c0[3], c0[4])
            done = None
            for k2 in range(1, 8):
                ck = S.get(x + k2, {}).get(b)
                if ck and ck[7] and (ck[3], ck[4]) in spawn_set[team[b]]:
                    done = k2
                    break
            hit = any((x + k2) in champ_hit_taken[b] or (x + k2) in camp_hit_taken[b] for k2 in range(0, 6))
            hpf = c0[5] / max(1, c0[6])
            # the capture-recall: a reward landed on this body within 6 rounds after the recall start (recall while capturing)
            cap_soon = any(c['who'] == b and x <= c['r'] <= x + 6 for c in captures)
            cap_before = any(c['who'] == b and x - 8 <= c['r'] < x for c in captures)
            why = ('heal' if hpf < 0.5 else 'bank' if c0[8] >= 20 else 'shop' if c0[9] >= 90 else 'reposition')
            rec_rows.append({'t': team[b], 'b': b, 'champ': types[b], 'r': x, 'd_spawn': dh(team[b], p), 'band': band(team[b], p),
                             'hp': round(hpf, 2), 'bag': c0[8], 'gold': c0[9], 'done': done, 'hit': hit, 'why': why,
                             'cap_recall': cap_soon or cap_before})
    fake_recalls = {t: 0 for t in (0, 1)}
    for b, rs in recalls.items():
        fake_recalls[team[b]] += len(rs)
    for rr in rec_rows:
        fake_recalls[rr['t']] -= 1

    # ---------- captures by band (from the capturing team's perspective)
    for c in captures:
        gg = G[c['gid']] if c['gid'] is not None else None
        c['band'] = gg['band'][c['t']] if gg else '?'
        c['gold_only'] = bool(gg and gg['gold_only'])
        c['ggems'] = gg['gems'] if gg else 0

    # ---------- body-rounds by band, raids into the enemy half
    use_band = {t: Counter() for t in (0, 1)}
    raids = []
    for b in bodies:
        t = team[b]
        cur = None
        gap = 0
        for r in range(1, final + 2):
            c = S.get(r, {}).get(b)
            inside = False
            if c is not None and c[7]:
                p = (c[3], c[4])
                bd = band(t, p)
                use_band[t][bd] += 1
                inside = bd == 'their'
            if inside:
                if cur is None:
                    cur = {'t': t, 'b': b, 'champ': types[b], 'r0': r, 'rounds': [], 'hits_camp': 0, 'hits_champ': 0}
                cur['rounds'].append(r)
                cur['hits_camp'] += r in camp_hit_given[b]
                cur['hits_champ'] += r in champ_hit_given[b]
                gap = 0
            elif cur is not None:
                gap += 1
                if gap > 2 or c is None or not c[7]:
                    r1 = cur['rounds'][-1]
                    cur['r1'] = r1
                    cur['len'] = len(cur['rounds'])
                    rs = set(cur['rounds'])
                    cur['caps'] = sum(x['gems'] for x in captures if x['who'] == b and x['r'] in rs)
                    cur['gold'] = sum(x['gold'] for x in captures if x['who'] == b and x['r'] in rs)
                    cur['died'] = any(r1 <= dr <= r1 + 2 for dr in death_by_body[b])
                    cur['kills'] = sum(1 for kr in kills_by[b] if cur['r0'] <= kr <= r1 + 1)
                    # allies also in the enemy half during the raid (max simultaneous)
                    mx = 0
                    for rr in cur['rounds'][::3]:
                        n = 0
                        for j, cj in S.get(rr, {}).items():
                            if team[j] == t and cj[7] and band(t, (cj[3], cj[4])) == 'their':
                                n += 1
                        mx = max(mx, n)
                    cur['bodies'] = mx
                    del cur['rounds']
                    if cur['len'] >= 5:
                        raids.append(cur)
                    cur = None
                    gap = 0

    # ---------- wards
    bush = {(x, y) for y in range(H) for x in range(W) if rows[y][x] == '"'}
    for w in wards:
        p = w['at']
        w['bush'] = p in bush
        w['d_spawn'] = dh(w['t'], p)
        w['band'] = band(w['t'], p)
        ng = [gid for gid, dd in near_g.get(p, {}).items() if dd <= 6 and G[gid]['gems'] >= BIGGEM]
        w['near_big'] = bool(ng)
        w['near_altar'] = min((C.cheb(p, a) for a in altars), default=99) <= 4
        w['near_camp'] = min((C.cheb(p, q) for q in camp_at), default=99) <= 3
    ward_rounds = {}
    for t in (0, 1):
        ward_rounds[t] = sorted(w['r'] for w in wards if w['t'] == t)

    def coverage(t, r):
        last = {}
        for w in wards:
            if w['t'] == t and w['r'] <= r:
                last[w['who']] = w['at']
        seen = set()
        for p in last.values():
            for dx in range(-WARD_R, WARD_R + 1):
                for dy in range(-WARD_R, WARD_R + 1):
                    seen.add((p[0] + dx, p[1] + dy))
        return round(sum(1 for p in passable if p in seen) / max(1, n_pass), 3), len(last)
    reward = {t: 0 for t in (0, 1)}
    first_w = {t: defaultdict(list) for t in (0, 1)}
    for w in wards:
        first_w[w['t']][w['who']].append(w['r'])
    for t in (0, 1):
        reward[t] = sum(max(0, len(v) - 1) for v in first_w[t].values())

    # ---------- group cycles (big groups)
    cycles = []
    for gg in G:
        if gg['gems'] < BIGGEM and not gg['mono']:
            continue
        gid = gg['id']
        tiles = set(gg['tiles'])
        alive_prev = False
        cur = None
        for r in range(1, final + 1):
            rr = R.get(r)
            if rr is None:
                continue
            alive = any(rr['campHp'][i] > 0 for i in gg['idx'])
            gr = rr['gr'][gid]
            if alive and not alive_prev:
                if cur:
                    cycles.append(cur)
                cur = {'gid': gid, 'gems': gg['gems'], 'gold': gg['gold'], 'mono': gg['mono'], 'start': r, 'd': gg['d'],
                       'band': dict(gg['band']), 'died': None, 'taken': None, 'by': None, 'on': {0: 0, 1: 0}}
                near0 = {0: [], 1: []}
                for c in rr['ch']:
                    if c[7] and gdist((c[3], c[4]), gid) <= 4:
                        near0[c[1]].append(c[5] / max(1, c[6]))
                cur['n0'] = {t: len(near0[t]) for t in (0, 1)}
                cur['hp0'] = {t: round(sum(near0[t]) / len(near0[t]), 2) if near0[t] else None for t in (0, 1)}
            if cur is not None:
                if not alive and alive_prev:
                    cur['died'] = r
                if gr:
                    for c in rr['ch']:
                        if c[7] and (c[3], c[4]) in tiles:
                            cur['on'][c[1]] += 1
            alive_prev = alive
        if cur:
            cycles.append(cur)
    for cy in cycles:
        gg = G[cy['gid']]
        tiles = set(gg['tiles'])
        r0 = cy['start']
        nxt = [x['start'] for x in cycles if x['gid'] == cy['gid'] and x['start'] > r0]
        end = min(nxt) if nxt else final + 1
        cy['end'] = end
        hs = sorted((r, t, who) for i in gg['idx'] for (r, t, who) in camp_hits[i] if r0 <= r < end)
        cy['first_hit'] = hs[0][1] if hs else None
        cy['first_hit_r'] = hs[0][0] if hs else None
        cy['hits'] = {t: sum(1 for x in hs if x[1] == t) for t in (0, 1)}
        cy['hitters'] = {t: len({x[2] for x in hs if x[1] == t}) for t in (0, 1)}
        cs = [c for c in captures if r0 <= c['r'] < end and c['gid'] == cy['gid']]
        if cs:
            cy['taken'] = cs[0]['r']
            ts = Counter(c['t'] for c in cs)
            cy['by'] = 0 if ts.get(0) and not ts.get(1) else 1 if ts.get(1) and not ts.get(0) else 'split'
            cy['cap'] = {t: sum(c['gems'] for c in cs if c['t'] == t) for t in (0, 1)}
        cy['deaths'] = {t: 0 for t in (0, 1)}
        for e in deaths:
            if r0 <= e['r'] < end and gdist(tuple(e['at']), cy['gid']) <= 5:
                cy['deaths'][e['team']] += 1
        # presence per team per round within 4 (from r0-40 to end)
        pres = {t: {} for t in (0, 1)}
        for r in range(max(1, r0 - 40), min(end, final) + 1):
            s = S.get(r)
            if not s:
                continue
            for t in (0, 1):
                nb = [c for c in s.values() if c[7] and c[1] == t and gdist((c[3], c[4]), cy['gid']) <= 4]
                pres[t][r] = nb
        arr = {}
        for t in (0, 1):
            # waiting: the earliest round from which the team is continuously present within 4 until r0
            w0 = None
            if pres[t].get(r0):
                w0 = r0
                while w0 - 1 in pres[t] and pres[t][w0 - 1]:
                    w0 -= 1
                arr[t] = {'at': w0, 'wait': r0 - w0, 'n': len(pres[t][r0]), 'hp': round(sum(c[5] / max(1, c[6]) for c in pres[t][r0]) / len(pres[t][r0]), 2)}
            else:
                later = [r for r in range(r0 + 1, min(end, final) + 1) if pres[t].get(r)]
                if later:
                    r1 = later[0]
                    arr[t] = {'at': r1, 'wait': -(r1 - r0), 'n': len(pres[t][r1]), 'hp': round(sum(c[5] / max(1, c[6]) for c in pres[t][r1]) / len(pres[t][r1]), 2)}
                else:
                    arr[t] = None
        cy['arr'] = arr
        if arr[0] and arr[1]:
            cy['first_arr'] = 0 if arr[0]['at'] < arr[1]['at'] else 1 if arr[1]['at'] < arr[0]['at'] else 'same'
        elif arr[0] or arr[1]:
            cy['first_arr'] = 0 if arr[0] else 1
        else:
            cy['first_arr'] = None
        # reaction of each team when the other holds the group: the first round rc in [r0, r0+30] where the OTHER team has >= 1 body
        # within 4 and this team has a body within 6: in the next 12 rounds, does this team hit the camps / the enemy, leave, return?
        react = {}
        for t in (0, 1):
            o = 1 - t
            rc = None
            for r in range(r0, min(end, final, r0 + 40) + 1):
                s = S.get(r)
                if not s:
                    continue
                if pres[o].get(r) and any(c[7] and c[1] == t and gdist((c[3], c[4]), cy['gid']) <= 6 for c in s.values()):
                    rc = r
                    break
            if rc is None:
                react[t] = None
                continue
            s = S[rc]
            mine = [c[0] for c in s.values() if c[7] and c[1] == t and gdist((c[3], c[4]), cy['gid']) <= 6]
            n_en = len(pres[o][rc])
            ch = cg = 0
            died = 0
            for b in mine:
                for r in range(rc, rc + 13):
                    ch += r in camp_hit_given[b]
                    cg += r in champ_hit_given[b]
                died += any(rc <= dr <= rc + 12 for dr in death_by_body[b])
            # distance after 12 rounds
            s12 = S.get(min(rc + 12, final), {})
            still = sum(1 for b in mine if b in s12 and s12[b][7] and gdist((s12[b][3], s12[b][4]), cy['gid']) <= 5)
            # came back later in the cycle (within 4) after having left
            back = False
            if still == 0:
                back = any(pres[t].get(r) for r in range(rc + 13, min(end, final) + 1))
            beh = ('died' if died else 'farmed' if ch >= 3 else 'fought' if cg >= 2 else 'left' if still == 0 else 'stayed')
            hp_m = round(sum(s[b][5] / max(1, s[b][6]) for b in mine) / len(mine), 2)
            react[t] = {'r': rc, 'n': len(mine), 'n_en': n_en, 'beh': beh, 'camp_hits': ch, 'champ_hits': cg, 'died': died, 'back': back, 'hp': hp_m,
                        'enemy_hits_before': sum(1 for x in hs if x[1] == o and x[0] < rc)}
        cy['react'] = react
        # on-tile denial: rounds with the reward up and both teams on the tiles
        cy['contested_reward'] = cy['on'][0] > 0 and cy['on'][1] > 0

    # ---------- monoliths
    mono_kills = {t: [] for t in (0, 1)}
    for gg in G:
        if not gg['mono']:
            continue
        for i in gg['idx']:
            if camp_type[i] != 'monolith':
                continue
            prev = None
            for r in range(1, final + 1):
                rr = R.get(r)
                if rr is None:
                    continue
                hp = rr['campHp'][i]
                if prev is not None and prev > 0 and hp == 0:
                    # the team with the last hit
                    hh = [x for x in camp_hits[i] if x[0] <= r]
                    if hh:
                        t = hh[-1][1]
                        nb = sum(1 for c in rr['ch'] if c[7] and c[1] == t and C.cheb((c[3], c[4]), (meta['camps'][i]['x'], meta['camps'][i]['y'])) <= 5)
                        mono_kills[t].append({'r': r, 'gid': gg['id'], 'bodies': nb})
                prev = hp

    # ---------- per-side summary
    side = {}
    for t in (0, 1):
        caps_t = [c for c in captures if c['t'] == t]
        rec_t = [x for x in rec_rows if x['t'] == t]
        w_t = [w for w in wards if w['t'] == t]
        cov300, nw300 = coverage(t, 300)
        cov600, nw600 = coverage(t, 600)
        raids_t = [x for x in raids if x['t'] == t]
        side[t] = {
            'bank': meta['submitted'][t], 'win': g['winner'] == t,
            'deaths': sum(1 for e in deaths if e['team'] == t),
            'caps': {b: sum(1 for c in caps_t if c['band'] == b) for b in ('own', 'mid', 'their', '?')},
            'cap_gems': {b: sum(c['gems'] for c in caps_t if c['band'] == b) for b in ('own', 'mid', 'their', '?')},
            'cap_gold': sum(c['gold'] for c in caps_t), 'cap_gems_all': sum(c['gems'] for c in caps_t),
            'open_gems': sum(c['gems'] for c in caps_t if c['r'] <= 300), 'open_gold': sum(c['gold'] for c in caps_t if c['r'] <= 300),
            'open_gold_only_caps': sum(1 for c in caps_t if c['r'] <= 300 and c['gold_only']),
            'open_caps': sum(1 for c in caps_t if c['r'] <= 300),
            'gold_only_caps': sum(1 for c in caps_t if c['gold_only']),
            'open_gold_hits': sum(1 for i, hs in camp_hits.items() if camp_type[i] == 'gold' for x in hs if x[1] == t and x[0] <= 300),
            'open_hits': sum(1 for i, hs in camp_hits.items() for x in hs if x[1] == t and x[0] <= 300),
            'use_band': dict(use_band[t]),
            'raids': len(raids_t), 'raid_rounds': sum(x['len'] for x in raids_t), 'raid_deaths': sum(x['died'] for x in raids_t),
            'raid_caps': sum(x['caps'] for x in raids_t), 'raid_gold': sum(x['gold'] for x in raids_t),
            'raid_multi': sum(1 for x in raids_t if x['bodies'] >= 2), 'raid_kills': sum(x['kills'] for x in raids_t),
            'raid_first_r': min((x['r0'] for x in raids_t), default=None),
            'wards': len(w_t), 'wards_bush': sum(w['bush'] for w in w_t), 'wards_near_big': sum(w['near_big'] for w in w_t),
            'wards_near_spawn': sum(1 for w in w_t if w['d_spawn'] is not None and w['d_spawn'] <= 8),
            'wards_band': dict(Counter(w['band'] for w in w_t)), 'wards_near_altar': sum(w['near_altar'] for w in w_t),
            'wards_near_camp': sum(w['near_camp'] for w in w_t),
            'ward_first_r': min((w['r'] for w in w_t), default=None), 'rewards': reward[t],
            'ward_bodies': len(first_w[t]),
            'wards_by300': sum(1 for w in w_t if w['r'] <= 300), 'wards_by600': sum(1 for w in w_t if w['r'] <= 600),
            'cov300': cov300, 'cov600': cov600, 'nw300': nw300, 'nw600': nw600,
            'live_wards300': sum(1 for x in R.get(min(300, final), {}).get('wards', []) if x == t),
            'live_wards600': sum(1 for x in R.get(min(600, final), {}).get('wards', []) if x == t),
            'recalls': len(rec_t), 'recalls_done': sum(1 for x in rec_t if x['done'] is not None),
            'recalls_hit': sum(1 for x in rec_t if x['hit']),
            'recall_why': dict(Counter(x['why'] for x in rec_t)), 'recall_cap': sum(1 for x in rec_t if x['cap_recall']),
            'recall_d': [x['d_spawn'] for x in rec_t if x['d_spawn'] is not None],
            'recall_band': dict(Counter(x['band'] for x in rec_t)),
            'fake_recalls': fake_recalls[t],
            'mono_kills': mono_kills[t],
            'shops': sum(len(v) for b, v in shops.items() if team[b] == t),
            'camp_hits': sum(1 for i, hs in camp_hits.items() for x in hs if x[1] == t),
            'their_half_hits': sum(1 for i, hs in camp_hits.items() for x in hs if x[1] == t and G[tile_group[(meta['camps'][i]['x'], meta['camps'][i]['y'])]]['band'][t] == 'their'),
        }
    mapcls = {'W': W, 'H': H, 'altars': len(altars), 'lone_mono': sum(1 for gg in G if gg['lone_mono']), 'mono_groups': sum(1 for gg in G if gg['mono']),
              'islands': sum(1 for gg in G if gg['island']), 'groups': len(G), 'big_groups': sum(1 for gg in G if gg['gems'] >= BIGGEM),
              'mid_big': sum(1 for gg in G if gg['gems'] >= BIGGEM and gg['band'][0] == 'mid'),
              'gems_total': sum(gg['gems'] for gg in G), 'gold_total': sum(gg['gold'] for gg in G),
              'bush_frac': round(len(bush) / max(1, n_pass), 3), 'champs': meta['champsPerTeam'],
              's2s': dh(0, spawn[1][0])}
    row = {'mid': g['mid'], 'ds': g['ds'], 'map': g['map'], 'sides': g['sides'], 'winner': g['winner'], 'final': final, 'ver': g.get('ver'),
           'kind': g.get('kind'), 'mapcls': mapcls, 'side': side, 'cycles': cycles, 'raids': raids, 'wards': wards, 'recalls': rec_rows,
           'groups': [{'id': gg['id'], 'gems': gg['gems'], 'gold': gg['gold'], 'resp': gg['resp'], 'types': ''.join(x[0] for x in gg['types']),
                       'd': gg['d'], 'band': gg['band'], 'mono': gg['mono'], 'island': gg['island']} for gg in G]}
    return row


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    jobs = 1
    if '--jobs' in sys.argv:
        jobs = int(sys.argv[sys.argv.index('--jobs') + 1])
    os.makedirs(OUT, exist_ok=True)
    sets = []
    if which in ('top', 'all'):
        sets.append(('top', C.top_games()))
    if which in ('me', 'all'):
        sets.append(('me', C.our_games()))
    for name, games in sets:
        outf = f'{OUT}/games_{name}.jsonl'
        done = set()
        if os.path.exists(outf):
            for l in open(outf):
                try:
                    done.add(json.loads(l)['mid'])
                except Exception:
                    pass
        todo = [g for g in games if g['mid'] not in done]
        if '--reverse' in sys.argv:
            todo = todo[::-1]
        if '--half' in sys.argv:
            todo = todo[len(todo) // 2:]
        print(name, len(games), 'games,', len(todo), 'to do', flush=True)
        with open(outf, 'a') as f:
            if jobs > 1:
                from multiprocessing import Pool
                with Pool(jobs) as pool:
                    for i, row in enumerate(pool.imap_unordered(analyse, todo)):
                        f.write(json.dumps(row) + '\n')
                        f.flush()
                        if i % 20 == 0:
                            print(name, i, row['map'], flush=True)
            else:
                for i, g in enumerate(todo):
                    row = analyse(g)
                    f.write(json.dumps(row) + '\n')
                    f.flush()
                    if i % 20 == 0:
                        print(name, i, row['map'], flush=True)


if __name__ == '__main__':
    main()
