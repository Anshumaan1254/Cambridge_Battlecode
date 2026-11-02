#!/usr/bin/env python3
"""Extract champion hits, fights and deaths from decoded CAMBC replays.

Usage: nice -n 19 python3 -I extract.py [outdir]
Reads  BASE/dec/<mid>.json, BASE/mj/<mid>.json, BASE/sides.json, BASE/matches_me.jsonl
Writes <outdir>/deaths.jsonl, fights.jsonl, games.jsonl (outdir defaults to this script's dir).

Conventions
- "we" = team index from sides.json; game result from matches_me.jsonl (W/L).
- Positions are tracked inside a round by replaying Move/dash/teleport events in order, so an
  Attack/Cast 'to' tile is matched to the body standing there at that moment.
- A champion hit = basic attack, targeted spell, area spell / Heart-of-Ruin dash landing / Varg
  splash that reaches an enemy champion.  Damage per hit is estimated by splitting the target's hp
  loss in that round over all hits it took (camp hits included) in proportion to nominal damage.
- Fight = connected component of champion hits, linking hits <=GAP rounds apart that share a body or
  whose attacker/target tiles are within RAD (Chebyshev).  Exchange = both teams landed a hit.
"""
import json, os, sys
from collections import defaultdict, Counter, deque

BASE = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
GAP, RAD = 5, 6
STR = {'Ryth': 45, 'VesperVale': 45, 'Vendetta': 70, 'Cassi': 30, 'Issac': 45, 'Stellar': 30, 'Prism': 35,
       'Marcella': 45, 'Willow': 55, 'Ren': 35, 'Varg': 45, 'Tavi': 45, 'HeartOfRuin': 30}
FOC = {'Ryth': 100, 'VesperVale': 100, 'Vendetta': 100, 'Cassi': 100, 'Issac': 100, 'Stellar': 70, 'Prism': 80,
       'Marcella': 60, 'Willow': 140, 'Ren': 100, 'Varg': 100, 'Tavi': 110, 'HeartOfRuin': 100}
RANGED = {'VesperVale', 'Cassi', 'Stellar', 'Prism', 'Willow', 'Tavi'}
CAMP_STR = {'wolf': 20, 'elk': 60, 'golem': 120, 'gem': 0, 'gold': 0, 'monolith': 200}
STUN_IMMUNE = {'Marcella'}
# spell multiplier (x Focus) for (champ, ability id); ability ids: 1 reset 2 single dmg 3 area 4 dmg+stun/stun 5 heal 6 dash 7 shield
SPELL = {('Marcella', 2): 2.0, ('Cassi', 2): 2.0, ('Stellar', 2): 2.0, ('Ren', 4): 1.1, ('Tavi', 4): 1.6,
         ('Prism', 4): 1.5, ('Cassi', 4): 0.0, ('Ryth', 3): 1.0, ('Stellar', 3): 1.4, ('Prism', 3): 1.0,
         ('HeartOfRuin', 6): 1.5}
STUN_SPELL = {('Ren', 4), ('Tavi', 4), ('Prism', 4), ('Cassi', 4), ('Ryth', 3), ('HeartOfRuin', 6)}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def shards(items):
    """shard-equivalents of an item list [[id,count],...]; id = family*6 + stat*2 + emblem"""
    s = 0
    for it, q in items:
        fam, rest = divmod(it, 6)
        emb = rest % 2
        if not emb:
            s += q
        else:
            s += q * (6 if fam == 1 else 7 if fam == 6 else 35 if fam == 12 else 5)
    return s


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


def map_features(mp):
    w, h, rows = mp['width'], mp['height'], mp['rows']
    dA = bfs(rows, [tuple(p) for p in mp['spawnA']], w, h)
    dB = bfs(rows, [tuple(p) for p in mp['spawnB']], w, h)
    passable = [(x, y) for y in range(h) for x in range(w) if rows[y][x] not in '#oA']
    bush = sum(1 for y in range(h) for x in range(w) if rows[y][x] == '"')
    walls = sum(1 for y in range(h) for x in range(w) if rows[y][x] in '#o')
    sx, sy = mp['spawnB'][0]
    s2s = dA[sy][sx]
    # narrowness: share of passable tiles with a blocked tile (or edge) in at least 4 of 8 neighbours
    narrow = 0
    for x, y in passable:
        b = 0
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if not (0 <= nx < w and 0 <= ny < h) or rows[ny][nx] in '#o':
                    b += 1
        narrow += b >= 4
    return {'w': w, 'h': h, 'area': w * h, 'passable': len(passable), 'bush_frac': round(bush / max(1, len(passable)), 3),
            'wall_frac': round(walls / (w * h), 3), 'spawn_dist': s2s, 'narrow_frac': round(narrow / max(1, len(passable)), 3),
            'altars': sum(1 for y in range(h) for x in range(w) if rows[y][x] == 'A'), 'champs': mp.get('champs')}, dA, dB


def load_meta():
    sides = json.load(open(f'{BASE}/sides.json'))
    info = {}
    for line in open(f'{BASE}/matches_me.jsonl'):
        m = json.loads(line)
        if m['matchId'] in sides and m.get('status') == 'finished':
            us = [t for t in m['teams'] if t['name'] == 'HouseOfCoders'][0]
            th = [t for t in m['teams'] if t['name'] != 'HouseOfCoders'][0]
            info[m['matchId']] = {'map': m['map'], 'res': 'W' if us['result'] == 'win' else 'L', 'opp': th['name'],
                                  'created': m['createdAt']}
    return sides, info


def process(mid, we, ginfo):
    d = json.load(open(f'{BASE}/dec/{mid}.json'))
    mp = json.load(open(f'{BASE}/mj/{mid}.json'))
    mf, dA, dB = map_features(mp)
    meta = d['meta']
    W, H = meta['width'], meta['height']
    types = {b['index']: b['type'] for b in meta['bodies']}
    team = {b['index']: b['team'] for b in meta['bodies']}
    bodies = sorted(types)
    camps = {c['index']: c for c in meta['camps']}
    camp_at = {(c['x'], c['y']): c['index'] for c in meta['camps']}
    S = {}
    campHp = {}
    for rr in d['rounds'][1:]:  # rounds[0] is the draft snapshot
        S[rr['r']] = {c[0]: c for c in rr['ch']}
        campHp[rr['r']] = rr['campHp']
    final = meta['finalRound']
    evr = defaultdict(list)
    for i, e in enumerate(d['events']):
        if e['k'] != 'Draft champion':
            evr[e['r']].append(e)

    def dist_home(t, p):
        dm = dA if t == 0 else dB
        x, y = p
        if 0 <= x < W and 0 <= y < H and dm[y][x] >= 0:
            return dm[y][x]
        return None

    hits = []        # champion -> enemy champion
    camp_hits = []   # camp -> champion
    champ_camp = defaultdict(set)   # body -> rounds it hit a camp
    moves = defaultdict(list)  # body -> (r, from, to, {enemy: (d0,d1)})
    recalls = defaultdict(list)  # body -> rounds a Recall was started
    cancels = defaultdict(list)
    deaths = []
    stun_on = defaultdict(list)  # body -> rounds stunned (by champion)
    heals = []
    acted = defaultdict(set)  # body -> rounds with a Move/Attack/Cast
    for e in d['events']:
        if e.get('who') is not None and e['k'] in ('Move', 'Attack', 'Cast ability', 'Recall'):
            acted[e['who']].add(e['r'])
    seq = 0
    for r in range(1, final + 1):
        prev = S.get(r - 1) or S.get(r)
        if prev is None:
            continue
        pos = {i: ((c[3], c[4]) if c[7] else None) for i, c in prev.items()}
        enh = {}
        for e in evr.get(r, []):
            seq += 1
            k = e['k']
            who = e.get('who')
            if who is not None and k in ('Attack', 'Move', 'Movement blocked') and tuple(e['from']) != (0, 0):
                pos[who] = tuple(e['from'])
            if k == 'Move' or (k == 'Cast ability' and e['ability'] == 6):
                fr, to = tuple(e['from']), tuple(e['to'])
                if k == 'Cast ability' and fr == (0, 0):
                    fr = pos.get(who) or to
                rel = {}
                for j, pj in pos.items():
                    if pj is not None and team[j] != team[who]:
                        d0 = cheb(fr, pj)
                        if d0 <= 10:
                            rel[j] = (d0, cheb(to, pj))
                moves[who].append((r, fr, to, rel))
                pos[who] = to
                if k == 'Cast ability' and types[who] == 'HeartOfRuin':
                    tg = [j for j, pj in pos.items() if pj is not None and team[j] != team[who] and cheb(pj, to) <= 1]
                    for j in tg:
                        st = types[j] not in STUN_IMMUNE
                        hits.append({'r': r, 'seq': seq, 'a': who, 't': j, 'ap': to, 'tp': pos[j], 'kind': 'dash',
                                     'w': SPELL[('HeartOfRuin', 6)] * FOC['HeartOfRuin'], 'stun': st})
                        if st:
                            stun_on[j].append(r)
                continue
            if k == 'Teleport complete' or (k == 'Respawn' and who is not None):
                pos[who] = tuple(e['to'])
                continue
            if k == 'Death':
                deaths.append({'r': r, 'seq': seq, 'who': who, 'by': e['by'], 'bag': e['bag'], 'at': tuple(e['at']),
                               'step': e.get('step')})
                pos[who] = None
                continue
            if k == 'Recall':
                recalls[who].append(r)
                continue
            if k == 'Cancel channel':
                cancels[who].append(r)
                continue
            if k == 'Attack' and 'camp' in e:
                P = tuple(e['to'])
                tg = [j for j, pj in pos.items() if pj == P]
                if tg:
                    ct = camps[e['camp']]['type'] if e['camp'] in camps else 'wolf'
                    camp_hits.append({'r': r, 'seq': seq, 'camp': e['camp'], 't': tg[0], 'w': CAMP_STR.get(ct, 20)})
                continue
            if k == 'Attack' and who is not None:
                P = tuple(e['to'])
                tg = [j for j, pj in pos.items() if pj == P and team[j] != team[who]]
                if tg:
                    j = tg[0]
                    st = bool(enh.get(who)) and types[j] not in STUN_IMMUNE
                    hits.append({'r': r, 'seq': seq, 'a': who, 't': j, 'ap': pos.get(who) or tuple(e['from']), 'tp': P,
                                 'kind': 'atk', 'w': STR[types[who]], 'stun': st})
                    if st:
                        stun_on[j].append(r)
                    if types[who] == 'Varg':
                        for j2, p2 in pos.items():
                            if p2 is not None and j2 != j and team[j2] != team[who] and cheb(p2, P) <= 1:
                                hits.append({'r': r, 'seq': seq, 'a': who, 't': j2, 'ap': pos.get(who), 'tp': p2,
                                             'kind': 'splash', 'w': STR['Varg'], 'stun': False})
                elif P in camp_at:
                    champ_camp[who].add(r)
                enh[who] = False
                continue
            if k == 'Cast ability' and who is not None:
                ab = e['ability']
                ct = types[who]
                P = tuple(e['to'])
                if ab == 1 and ct == 'Marcella':
                    enh[who] = True
                elif ab in (2, 4):
                    tg = [j for j, pj in pos.items() if pj == P and team[j] != team[who]]
                    if tg:
                        j = tg[0]
                        st = (ct, ab) in STUN_SPELL and types[j] not in STUN_IMMUNE
                        hits.append({'r': r, 'seq': seq, 'a': who, 't': j, 'ap': pos.get(who), 'tp': P, 'kind': 'spell',
                                     'w': SPELL.get((ct, ab), 1.0) * FOC[ct], 'stun': st})
                        if st:
                            stun_on[j].append(r)
                    elif P in camp_at:
                        champ_camp[who].add(r)
                elif ab == 3:
                    tg = [j for j, pj in pos.items() if pj is not None and cheb(pj, P) <= 1 and team[j] != team[who]]
                    for j in tg:
                        st = (ct, ab) in STUN_SPELL and types[j] not in STUN_IMMUNE
                        hits.append({'r': r, 'seq': seq, 'a': who, 't': j, 'ap': pos.get(who), 'tp': pos[j], 'kind': 'area',
                                     'w': SPELL.get((ct, ab), 1.0) * FOC[ct], 'stun': st})
                        if st:
                            stun_on[j].append(r)
                    if not tg and any(cheb(P, q) <= 1 for q in camp_at):
                        champ_camp[who].add(r)
                elif ab == 5:
                    heals.append((r, who))
                continue
    # ---- damage attribution per (round, target)
    byrt = defaultdict(list)
    for h in hits:
        byrt[(h['r'], h['t'])].append(h)
    for h in camp_hits:
        byrt[(h['r'], h['t'])].append(h)
    for (r, t), hs in byrt.items():
        p, c = S.get(r - 1, {}).get(t), S.get(r, {}).get(t)
        if not p or not c or not p[7]:
            D = 0
        else:
            D = max(0, p[5] - (c[5] if c[7] else 0))
        tw = sum(h['w'] for h in hs) or 1
        for h in hs:
            h['dmg'] = D * h['w'] / tw
    hits.sort(key=lambda h: (h['r'], h['seq']))
    camp_hits.sort(key=lambda h: (h['r'], h['seq']))
    hit_rounds = defaultdict(set)
    for h in hits:
        hit_rounds[h['t']].add(h['r'])
    # real recalls: the channel was held into the next turn (no own action next round) or was broken by a champion hit
    real_recalls = defaultdict(list)
    for b, rs in recalls.items():
        for x in rs:
            if (x + 1) not in acted[b] or x in hit_rounds[b] or (x + 1) in hit_rounds[b]:
                real_recalls[b].append(x)
    camp_by_r = defaultdict(list)
    for h in camp_hits:
        camp_by_r[h['r']].append(h)

    # ---- fights: union-find over hits
    n = len(hits)
    par = list(range(n))

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    lo = 0
    for j in range(n):
        hj = hits[j]
        while hits[lo]['r'] < hj['r'] - GAP:
            lo += 1
        pj = [p for p in (hj['ap'], hj['tp']) if p]
        for i in range(lo, j):
            hi = hits[i]
            if {hi['a'], hi['t']} & {hj['a'], hj['t']} or any(cheb(p, q) <= RAD for p in (hi['ap'], hi['tp']) if p for q in pj):
                a, b = find(i), find(j)
                if a != b:
                    par[a] = b
    comps = defaultdict(list)
    for i in range(n):
        comps[find(i)].append(i)
    fights = sorted(comps.values(), key=lambda c: c[0])
    hit_fight = {}
    for fi, c in enumerate(fights):
        for i in c:
            hit_fight[i] = fi

    def nearby(r, p, t, rad=6, excl=None):
        s = S.get(r, {})
        return [i for i, c in s.items() if c[7] and team[i] == t and i != excl and cheb((c[3], c[4]), p) <= rad]

    death_by_who = defaultdict(list)
    for dd in deaths:
        death_by_who[dd['who']].append(dd)

    def move_class(b, r0, r1):
        """own moves of b in rounds [r0,r1]: (toward, away, side) w.r.t. the nearest enemy within 10 at that moment"""
        tw = aw = sd = 0
        for (r, fr, to, rel) in moves[b]:
            if r0 <= r <= r1 and rel:
                j = min(rel, key=lambda q: rel[q][0])
                d0, d1 = rel[j]
                if d1 < d0:
                    tw += 1
                elif d1 > d0:
                    aw += 1
                else:
                    sd += 1
        return tw, aw, sd

    # ---- fight rows
    frows = []
    for fi, c in enumerate(fights):
        HH = [hits[i] for i in c]
        start, end = HH[0]['r'], HH[-1]['r']
        parts = {0: set(), 1: set()}
        join = {}
        for h in HH:
            for b in (h['a'], h['t']):
                parts[team[b]].add(b)
                join.setdefault(b, h['r'])
        nh = {0: 0, 1: 0}
        dmg = {0: 0.0, 1: 0.0}
        stuns = {0: 0, 1: 0}
        prim = {0: Counter(), 1: Counter()}
        for h in HH:
            ta = team[h['a']]
            nh[ta] += 1
            dmg[ta] += h.get('dmg', 0)
            stuns[ta] += h['stun']
            if h['kind'] in ('atk', 'spell'):
                prim[ta][h['t']] += 1
        allp = parts[0] | parts[1]
        fdeaths = [dd for dd in deaths if dd['who'] in allp and start <= dd['r'] <= end + 2 and
                   (dd['by'] != 'camp' or any(h['t'] == dd['who'] and h['r'] >= dd['r'] - 5 for h in HH))]
        dead = {0: 0, 1: 0}
        for dd in fdeaths:
            dead[team[dd['who']]] += 1
        h0 = HH[0]
        first = team[h0['a']]
        cp = h0['tp']
        num = {t: len(nearby(start - 1, cp, t)) for t in (0, 1)}
        num8 = {t: len(nearby(start - 1, cp, t, 8)) for t in (0, 1)}
        hp0 = {t: sum(S[start - 1][b][5] for b in parts[t] if b in S.get(start - 1, {}) and S[start - 1][b][7]) for t in (0, 1)}
        sh0 = {t: sum(shards(S[start - 1][b][11]) for b in parts[t] if b in S.get(start - 1, {})) for t in (0, 1)}
        # winner: more kills, else damage ratio >= 1.3
        if dead[0] != dead[1]:
            win = 0 if dead[1] > dead[0] else 1
        elif dmg[0] >= 1.3 * max(1, dmg[1]) and dmg[0] >= 150:
            win = 0
        elif dmg[1] >= 1.3 * max(1, dmg[0]) and dmg[1] >= 150:
            win = 1
        else:
            win = None
        # stun conversions: stunned body that died within 3 rounds
        conv = {0: 0, 1: 0}
        for h in HH:
            if h['stun'] and any(dd['who'] == h['t'] and h['r'] <= dd['r'] <= h['r'] + 3 for dd in fdeaths):
                conv[team[h['a']]] += 1
        # leave attempts by dead bodies
        leave = {0: [0, 0], 1: [0, 0]}  # [dead bodies that tried to leave, dead bodies]
        for dd in fdeaths:
            b = dd['who']
            tw, aw, sd = move_class(b, dd['r'] - 4, dd['r'])
            rec = any(dd['r'] - 5 <= x <= dd['r'] for x in real_recalls[b])
            leave[team[b]][1] += 1
            leave[team[b]][0] += (aw >= 2 or rec)
        # survivors of each team that disengaged (moved away >=2 in the 4 rounds after their last hit taken)
        zone_own = dist_home(we, cp)
        zone_their = dist_home(1 - we, cp)
        # farming by the team that was hit first, in the 3 rounds before the first hit
        defender = 1 - first
        farm_def = any(any(start - 3 <= x <= start for x in champ_camp[b]) for b in parts[defender])
        farm_att = any(any(start - 3 <= x <= start for x in champ_camp[b]) for b in parts[first])
        spread = {t: (max(join[b] for b in parts[t]) - min(join[b] for b in parts[t])) if len(parts[t]) >= 2 else 0 for t in (0, 1)}
        late = {t: sum(1 for b in parts[t] if join[b] - min(join[x] for x in parts[t]) >= 3) if parts[t] else 0 for t in (0, 1)}
        foc = {}
        for t in (0, 1):
            tot = sum(prim[t].values())
            foc[t] = (max(prim[t].values()) / tot) if tot >= 3 else None
        # camp damage taken by participants during the fight
        cdmg = {0: 0.0, 1: 0.0}
        for rr in range(start, end + 1):
            for h in camp_by_r.get(rr, ()):
                if h['t'] in allp:
                    cdmg[team[h['t']]] += h.get('dmg', 0)
        rel = lambda x: {'we': x[we], 'they': x[1 - we]}
        joins = {t: sorted(join[b] - start for b in parts[t]) for t in (0, 1)}
        # numbers around the first death (bodies within 6 of the victim one round before)
        fd = min(fdeaths, key=lambda x: x['r']) if fdeaths else None
        fd_num = None
        if fd:
            vt = team[fd['who']]
            cvb = S.get(fd['r'] - 1, {}).get(fd['who'])
            if cvb and cvb[7]:
                pv = (cvb[3], cvb[4])
                fd_num = {'side': 'we' if vt == we else 'they', 'own': 1 + len(nearby(fd['r'] - 1, pv, vt, 6, excl=fd['who'])),
                          'enemy': len(nearby(fd['r'] - 1, pv, 1 - vt, 6)), 'dt': fd['r'] - start}
        dlist = [(dd['r'], dd['who'], types[dd['who']], 'we' if team[dd['who']] == we else 'they') for dd in fdeaths]
        frows.append({'mid': mid, 'res': ginfo['res'], 'map': ginfo['map'], 'fid': fi, 'start': start, 'end': end,
                      'joins': rel(joins), 'first_death': fd_num, 'deaths': dlist,
                      'first_hit': [h0['r'], h0['a'], types[h0['a']], h0['t'], types[h0['t']], h0['kind']],
                      'exchange': nh[0] > 0 and nh[1] > 0, 'first': 'we' if first == we else 'they',
                      'win': None if win is None else ('we' if win == we else 'they'),
                      'parts': rel({t: len(parts[t]) for t in (0, 1)}), 'num': rel(num), 'num8': rel(num8),
                      'hits': rel(nh), 'dmg': rel({t: round(dmg[t]) for t in (0, 1)}), 'dead': rel(dead), 'stuns': rel(stuns),
                      'conv': rel(conv), 'spread': rel(spread), 'late': rel(late), 'focus': rel(foc),
                      'targets_avail': rel({t: len(parts[1 - t]) for t in (0, 1)}),
                      'leave': rel(leave), 'hp0': rel(hp0), 'shards': rel(sh0), 'campdmg': rel({t: round(cdmg[t]) for t in (0, 1)}),
                      'cp': cp, 'd_own': zone_own, 'd_their': zone_their, 'farm_def': farm_def, 'farm_att': farm_att,
                      'part_we': sorted(f'{b}:{types[b]}' for b in parts[we]), 'part_they': sorted(f'{b}:{types[b]}' for b in parts[1 - we])})

    # ---- death rows
    drows = []
    for dd in deaths:
        b, r = dd['who'], dd['r']
        t = team[b]
        # fight containing the killing blow / last hits on b
        fid = None
        for i in range(len(hits) - 1, -1, -1):
            h = hits[i]
            if h['r'] > r:
                continue
            if h['r'] < r - 8:
                break
            if h['t'] == b or h['a'] == b:
                fid = hit_fight[i]
                break
        started = None
        if fid is not None:
            started = 'own' if team[hits[fights[fid][0]]['a']] == t else 'enemy'
        # local numbers over the 5 rounds before
        al, en, al8, en8 = [], [], [], []
        for k in range(1, 6):
            s = S.get(r - k, {})
            c = s.get(b)
            if not c or not c[7]:
                continue
            p = (c[3], c[4])
            al.append(len(nearby(r - k, p, t, 6, excl=b)))
            en.append(len(nearby(r - k, p, 1 - t, 6)))
            al8.append(len(nearby(r - k, p, t, 8, excl=b)))
            en8.append(len(nearby(r - k, p, 1 - t, 8)))
        c5 = S.get(r - 5, {}).get(b)
        hp5 = (c5[5] / max(1, c5[6])) if c5 and c5[7] else None
        c10 = S.get(r - 10, {}).get(b)
        hp10 = (c10[5] / max(1, c10[6])) if c10 and c10[7] else None
        tw8, aw8, sd8 = move_class(b, r - 8, r)
        tw4, aw4, sd4 = move_class(b, r - 4, r)
        ch5 = [h for rr in range(r - 5, r + 1) for h in camp_by_r.get(rr, ()) if h['t'] == b]
        champ_dmg5 = sum(h.get('dmg', 0) for h in hits if h['t'] == b and r - 5 <= h['r'] <= r)
        camp_dmg5 = sum(h.get('dmg', 0) for h in ch5)
        # lure: steps toward one enemy E in the last 12 rounds while E kept its distance
        cnt = Counter()
        first_toward = {}
        for (rr, fr, to, rel) in moves[b]:
            if r - 12 <= rr < r:
                for j, (d0, d1) in rel.items():
                    if d1 < d0 and d0 <= 8:
                        cnt[j] += 1
                        first_toward.setdefault(j, (rr, d0))
        lure = False
        lure_t = None
        lure_info = None
        if cnt:
            j, nt = cnt.most_common(1)[0]
            rr0, d0 = first_toward[j]
            cj = S.get(r - 1, {}).get(j)
            cb = S.get(r - 1, {}).get(b)
            if cj and cj[7] and cb and cb[7]:
                dend = cheb((cb[3], cb[4]), (cj[3], cj[4]))
                j_away = sum(1 for (rr, fr, to, rel) in moves[j] if rr0 <= rr < r and b in rel and rel[b][1] > rel[b][0])
                rng = 3 if types[b] in RANGED else 1
                if nt >= 3 and dend >= d0 and j_away >= 2 and dend > rng:
                    lure = True
                lure_t = types[j]
                e_start = len(nearby(rr0 - 1, (cb[3], cb[4]), 1 - t, 6)) if S.get(rr0 - 1, {}).get(b) else None
                lure_info = {'steps': nt, 'd0': d0, 'dend': dend, 'j_away': j_away, 'target': f'{j}:{types[j]}',
                             'killer_is_target': dd['by'] == j}
        cpos = dd['at']
        dho, dhe = dist_home(t, cpos), dist_home(1 - t, cpos)
        rec = [x for x in real_recalls[b] if r - 6 <= x <= r]
        stunned = any(r - 3 <= x <= r for x in stun_on[b])
        # first champion hit on b in the last 15 rounds and farming just before it
        fh = [h for h in hits if h['t'] == b and r - 15 <= h['r'] <= r]
        first_hit_r = fh[0]['r'] if fh else None
        farming = bool(first_hit_r) and any(first_hit_r - 4 <= x <= first_hit_r for x in champ_camp[b])
        # did b approach before its first hit taken
        tw_pre = move_class(b, first_hit_r - 5, first_hit_r)[0] if first_hit_r else None
        dealt10 = sum(h.get('dmg', 0) for h in hits if h['a'] == b and r - 10 <= h['r'] <= r)
        killer = dd['by']
        cb1 = S.get(r - 1, {}).get(b)
        rowsh = shards(cb1[11]) if cb1 else 0
        drows.append({'mid': mid, 'res': ginfo['res'], 'map': ginfo['map'], 'side': 'we' if t == we else 'they', 'body': b,
                      'champ': types[b], 'r': r, 'killer': 'camp' if killer == 'camp' else types.get(killer, '?'),
                      'killer_body': killer, 'step': dd['step'], 'bag': dd['bag'], 'fid': fid, 'started': started,
                      'al5': sum(al) / len(al) if al else None, 'en5': sum(en) / len(en) if en else None,
                      'al8_5': sum(al8) / len(al8) if al8 else None, 'en8_5': sum(en8) / len(en8) if en8 else None,
                      'al_last': al[0] if al else None, 'en_last': en[0] if en else None,
                      'hp5': hp5, 'hp10': hp10, 'tw8': tw8, 'aw8': aw8, 'sd8': sd8, 'tw4': tw4, 'aw4': aw4,
                      'camp_hits5': len(ch5), 'camp_dmg5': round(camp_dmg5), 'champ_dmg5': round(champ_dmg5),
                      'lure': lure, 'lure_t': lure_t, 'lure_info': lure_info, 'enemy_half': (dho is not None and dhe is not None and dho > dhe),
                      'd_own': dho, 'd_enemy': dhe, 'recall6': len(rec), 'stunned3': stunned, 'farming': farming,
                      'tw_pre_hit': tw_pre, 'dealt10': round(dealt10), 'shards': rowsh, 'x': cpos[0], 'y': cpos[1]})
    # ---- game row
    g = {'mid': mid, 'res': ginfo['res'], 'map': ginfo['map'], 'opp': ginfo['opp'], 'we': we, 'final': final,
         'sub': {'we': meta['submitted'][we], 'they': meta['submitted'][1 - we]}, 'champs': meta['champsPerTeam'],
         'draft_we': meta['drafts'][we], 'draft_they': meta['drafts'][1 - we], 'mf': mf,
         'deaths': {'we': sum(1 for x in drows if x['side'] == 'we'), 'they': sum(1 for x in drows if x['side'] == 'they')},
         'gems_lost': {'we': sum(x['bag'] for x in drows if x['side'] == 'we'), 'they': sum(x['bag'] for x in drows if x['side'] == 'they')},
         'n_fights': len(frows), 'n_exch': sum(1 for f in frows if f['exchange'])}
    return drows, frows, g


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    sides, info = load_meta()
    D, F, G = [], [], []
    mids = sorted(f[:-5] for f in os.listdir(f'{BASE}/dec') if f.endswith('.json'))
    for i, mid in enumerate(mids):
        dr, fr, g = process(mid, int(sides[mid]), info[mid])
        D += dr
        F += fr
        G.append(g)
        if i % 16 == 0:
            print(i, mid, len(dr), len(fr), flush=True)
    for name, rows in (('deaths', D), ('fights', F), ('games', G)):
        with open(os.path.join(out, name + '.jsonl'), 'w') as f:
            for r in rows:
                f.write(json.dumps(r) + '\n')
    print('deaths', len(D), 'fights', len(F), 'games', len(G))


if __name__ == '__main__':
    main()
