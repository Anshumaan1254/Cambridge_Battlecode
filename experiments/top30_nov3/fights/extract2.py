#!/usr/bin/env python3
"""Fights / deaths / retreats / dives / chases / focus from decoded CAMBC replays, for the top-30 benchmark.

Extends experiments/ladder_nov2/agent_fights/extract.py (same hit model, fight clustering, power index) to two datasets:
  top  = experiments/top30_nov3 (top-30 vs top-30 ranked games; dec/<map>_<mid8>.json)
  our  = experiments/ladder_nov2 (our games; dec/<mid>.json; 'we' from sides.json; version v88 from v88_bugs/games.json)

Usage: nice -n 19 python3 -I extract2.py top|our [--limit N]
Writes out/<ds>_{games,deaths,fights,retreats,dives,chases,hits,parts}.jsonl (incremental: games already in out/<ds>_games.jsonl
are skipped unless --redo).

Rows carry 't' (team index 0/1); the game row carries teams[t] = {id, name, rank, rating, result}.  For 'our', game['we'] is
HouseOfCoders' team index; for 'top' it is None.

New vs extract.py:
  fights: opener approach (walk-in / received / mutual), opener hp, opener distance to its nearest ally, target in reach,
          answer latency (rounds until the other team hit back), per-team shards per body and shards per participant
  deaths: cause (champion / camp / both), hit back?, hits dealt in the last 10 r, killer distance 3 r before, last hit kinds,
          steps toward the killer in the last 4 r, rounds since respawn, kill in the last 10 r, in Marcella's range-4 pattern
  retreats: toward allies / spawn, dash / stun / recall used to escape, enemy count within 4 after 3 rounds
  hits: per champion hit, the number of allies that hit the same target within +-2 rounds (focus) and allies within 6
  parts: body-fight participations (alone / with allies at the first own hit)
"""
import json, os, sys, bisect
from collections import defaultdict, Counter, deque

sys.path.insert(0, '/home/claude/cambridge_battlecode/experiments/ladder_nov2/agent_fights')
from extract import (cheb, shards, stat_shards, dps, bfs, map_features, STR, FOC, RANGED, CAMP_STR, STUN_IMMUNE, SPELL,  # noqa: E402
                     STUN_SPELL, DASHERS, STUNNERS, HAS_RESET, GAP, RAD)

TOP = '/home/claude/cambridge_battlecode/experiments/top30_nov3'
OUR = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
HERE = os.path.dirname(os.path.abspath(__file__))
ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
POOL = '/home/claude/data/mapjson_pool'
REACH = {ct: (4 if ct in RANGED else 2) for ct in STR}
for ct in ('Marcella', 'Ryth', 'Ren'):   # range-4 spell
    REACH[ct] = 4
for ct in ('Vendetta', 'Issac', 'HeartOfRuin'):  # dash 2 + attack
    REACH[ct] = 4


def ladder():
    lad = json.load(open(f'{TOP}/ladder.json'))['teams']
    return {t['teamId']: {'rank': t['rank'], 'rating': round(t['rating']), 'name': t['name']} for t in lad}


def games_top():
    rat = ladder()
    out = []
    for line in open(f'{TOP}/selection.jsonl'):
        m = json.loads(line)
        if m.get('status') != 'finished':
            continue
        fn = f"{m['map']}_{m['matchId'][:8]}"
        mj = f'{TOP}/mj/{fn}.json'
        if not os.path.exists(mj):   # decode_loop.sh's mj copy keys id2map by the file stem and misses: read the pool directly
            mj = f"{POOL}/{m['map']}.json"
        if not (os.path.exists(f'{TOP}/dec/{fn}.json') and os.path.getsize(f'{TOP}/dec/{fn}.json') > 0 and os.path.exists(mj)):
            continue
        teams = [None, None]
        for t in m['teams']:
            r = rat.get(t['teamId'], {'rank': None, 'rating': None, 'name': t['name']})
            teams[0 if t['side'] == 'a' else 1] = {'id': t['teamId'], 'name': t['name'], 'rank': r['rank'], 'rating': r['rating'],
                                                   'result': 'W' if t['result'] == 'win' else 'L'}
        out.append({'mid': m['matchId'], 'dec': f'{TOP}/dec/{fn}.json', 'mj': mj, 'map': m['map'],
                    'kind': m['kind'], 'created': m['createdAt'], 'teams': teams, 'we': None, 'ver': 'top', 'end': m.get('endReason')})
    return out


def games_our():
    rat = ladder()
    v88 = {g['mid'] for g in json.load(open(f'{OUR}/v88_bugs/games.json'))}
    out = []
    seen = set()
    for line in open(f'{OUR}/matches_me.jsonl'):
        m = json.loads(line)
        mid = m['matchId']
        if m.get('status') != 'finished' or mid in seen:
            continue
        seen.add(mid)
        we_side = [t['side'] for t in m['teams'] if t['teamId'] == ME]
        if not we_side:
            continue
        we = 0 if we_side[0] == 'a' else 1
        if not (os.path.exists(f'{OUR}/dec/{mid}.json') and os.path.exists(f'{OUR}/mj/{mid}.json')):
            continue
        teams = [None, None]
        for t in m['teams']:
            r = rat.get(t['teamId'], {'rank': None, 'rating': None, 'name': t['name']})
            teams[0 if t['side'] == 'a' else 1] = {'id': t['teamId'], 'name': t['name'], 'rank': r['rank'], 'rating': r['rating'],
                                                   'result': 'W' if t['result'] == 'win' else 'L'}
        ver = 'v88' if mid in v88 else ('v84' if m['createdAt'] >= '2026-11-02T00:00' else 'old')
        out.append({'mid': mid, 'dec': f'{OUR}/dec/{mid}.json', 'mj': f'{OUR}/mj/{mid}.json', 'map': m['map'], 'kind': m['kind'],
                    'created': m['createdAt'], 'teams': teams, 'we': we, 'ver': ver, 'end': m.get('endReason')})
    return out


def process(gm):
    mid = gm['mid']
    d = json.load(open(gm['dec']))
    mp = json.load(open(gm['mj']))
    mf, dA, dB = map_features(mp)
    meta = d['meta']
    W, H = meta['width'], meta['height']
    types = {b['index']: b['type'] for b in meta['bodies']}
    team = {b['index']: b['team'] for b in meta['bodies']}
    camps = {c['index']: c for c in meta['camps']}
    camp_at = {(c['x'], c['y']): c['index'] for c in meta['camps']}
    S = {}
    for rr in d['rounds'][1:]:
        S[rr['r']] = {c[0]: c for c in rr['ch']}
    final = meta['finalRound']
    evr = defaultdict(list)
    for e in d['events']:
        if e['k'] != 'Draft champion':
            evr[e['r']].append(e)

    def dist_home(t, p):
        dm = dA if t == 0 else dB
        x, y = p
        if 0 <= x < W and 0 <= y < H and dm[y][x] >= 0:
            return dm[y][x]
        return None

    hits, camp_hits = [], []
    champ_camp = defaultdict(set)
    moves = defaultdict(list)
    recalls, cancels = defaultdict(list), defaultdict(list)
    deaths = []
    respawns = defaultdict(list)
    stun_on = defaultdict(list)
    stun_cast = defaultdict(list)   # body -> rounds it cast a stun that hit an enemy champion
    dash_cast = defaultdict(list)   # body -> (round, from, to)
    camp_hit_by = defaultdict(list)
    acted = defaultdict(set)
    for e in d['events']:
        if e.get('who') is not None and e['k'] in ('Move', 'Attack', 'Cast ability', 'Recall', 'Cancel channel', 'Place ward', 'Submit gems'):
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
                if k == 'Cast ability':
                    dash_cast[who].append((r, fr, to))
                    if types[who] == 'HeartOfRuin':
                        tg = [j for j, pj in pos.items() if pj is not None and team[j] != team[who] and cheb(pj, to) <= 1]
                        for j in tg:
                            st = types[j] not in STUN_IMMUNE
                            hits.append({'r': r, 'seq': seq, 'a': who, 't': j, 'ap': to, 'tp': pos[j], 'kind': 'dash',
                                         'w': SPELL[('HeartOfRuin', 6)] * FOC['HeartOfRuin'], 'stun': st})
                            if st:
                                stun_on[j].append(r)
                                stun_cast[who].append(r)
                continue
            if k == 'Teleport complete' or (k == 'Respawn' and who is not None):
                pos[who] = tuple(e['to'])
                if k == 'Respawn':
                    respawns[who].append(r)
                continue
            if k == 'Death':
                deaths.append({'r': r, 'seq': seq, 'who': who, 'by': e['by'], 'bag': e['bag'], 'at': tuple(e['at']), 'step': e.get('step')})
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
                        stun_cast[who].append(r)
                    if types[who] == 'Varg':
                        for j2, p2 in pos.items():
                            if p2 is not None and j2 != j and team[j2] != team[who] and cheb(p2, P) <= 1:
                                hits.append({'r': r, 'seq': seq, 'a': who, 't': j2, 'ap': pos.get(who), 'tp': p2,
                                             'kind': 'splash', 'w': STR['Varg'], 'stun': False})
                elif P in camp_at:
                    champ_camp[who].add(r)
                    camp_hit_by[camp_at[P]].append((r, team[who]))
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
                            stun_cast[who].append(r)
                    elif P in camp_at:
                        champ_camp[who].add(r)
                        camp_hit_by[camp_at[P]].append((r, team[who]))
                elif ab == 3:
                    tg = [j for j, pj in pos.items() if pj is not None and cheb(pj, P) <= 1 and team[j] != team[who]]
                    for j in tg:
                        st = (ct, ab) in STUN_SPELL and types[j] not in STUN_IMMUNE
                        hits.append({'r': r, 'seq': seq, 'a': who, 't': j, 'ap': pos.get(who), 'tp': pos[j], 'kind': 'area',
                                     'w': SPELL.get((ct, ab), 1.0) * FOC[ct], 'stun': st})
                        if st:
                            stun_on[j].append(r)
                            stun_cast[who].append(r)
                    for q, ci in camp_at.items():
                        if cheb(P, q) <= 1:
                            camp_hit_by[ci].append((r, team[who]))
                            if not tg:
                                champ_camp[who].add(r)
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
    hits_by_a = defaultdict(list)
    hits_by_t = defaultdict(list)
    for i, h in enumerate(hits):
        hit_rounds[h['t']].add(h['r'])
        hits_by_a[h['a']].append(i)
        hits_by_t[h['t']].append(i)
    real_recalls = defaultdict(list)
    for b, rs in recalls.items():
        for x in rs:
            nxt = S.get(x + 1, {}).get(b)
            stunned = x in stun_on[b] or (x + 1) in stun_on[b]
            if (x + 1) not in acted[b] and nxt is not None and nxt[7] and not stunned:
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

    def nearest_ally_d(r, b):
        s = S.get(r, {})
        c = s.get(b)
        if not c or not c[7]:
            return None
        p = (c[3], c[4])
        ds = [cheb(p, (q[3], q[4])) for i, q in s.items() if i != b and q[7] and team[i] == team[b]]
        return min(ds) if ds else 99

    def move_class(b, r0, r1, ref=None):
        """own moves of b in rounds [r0,r1]: (toward, away, side) w.r.t. the nearest enemy within 10 (or body ref)"""
        tw = aw = sd = 0
        for (r, fr, to, rel) in moves[b]:
            if r0 <= r <= r1 and rel:
                if ref is not None:
                    if ref not in rel:
                        continue
                    j = ref
                else:
                    j = min(rel, key=lambda q: rel[q][0])
                d0, d1 = rel[j]
                if d1 < d0:
                    tw += 1
                elif d1 > d0:
                    aw += 1
                else:
                    sd += 1
        return tw, aw, sd

    last_casts = defaultdict(list)
    for e in d['events']:
        if e['k'] == 'Cast ability' and e.get('who') is not None:
            last_casts[(e['who'], e['ability'])].append(e['r'])

    def ready(b, ab, r):
        rs = last_casts.get((b, ab))
        if not rs:
            return True
        i = bisect.bisect_left(rs, r) - 1
        return i < 0 or r - rs[i] >= 8

    def power(r, p, t, rad=6, excl=None, incl_self=None):
        s = S.get(r, {})
        hp = dp = 0.0
        k = 0
        for i, c in s.items():
            if c[7] and team[i] == t and i != excl and cheb((c[3], c[4]), p) <= rad:
                hp += c[5]
                dp += dps(types[i], c[11])
                k += 1
        if incl_self is not None:
            c = s.get(incl_self)
            if c and c[7]:
                hp += c[5]
                dp += dps(types[incl_self], c[11])
                k += 1
        return hp * dp, k

    def threat(r, b):
        s = S.get(r - 1, {})
        cb = s.get(b)
        if not cb or not cb[7]:
            return None
        p = (cb[3], cb[4])
        n4 = nd = ns = 0
        for i, c in s.items():
            if not c[7] or team[i] == team[b]:
                continue
            dd = cheb((c[3], c[4]), p)
            if dd <= 4:
                n4 += 1
                if types[i] in DASHERS and ready(i, 6, r):
                    nd += 1
            if dd <= 5 and types[i] in STUNNERS and ready(i, STUNNERS[types[i]], r):
                ns += 1
        return n4, nd, ns

    def tpos(r, b):
        c = S.get(r, {}).get(b)
        return (c[3], c[4]) if c and c[7] else None

    death_r = defaultdict(list)
    for dd in deaths:
        death_r[dd['who']].append(dd['r'])
    spawn_tiles = {0: {tuple(q) for q in mp['spawnA']}, 1: {tuple(q) for q in mp['spawnB']}}

    # ---- retreat episodes
    retreats = []
    for b, mv in moves.items():
        last_start = -100
        for (r, fr, to, rel) in mv:
            if not rel:
                continue
            j = min(rel, key=lambda q: rel[q][0])
            d0, d1 = rel[j]
            if d0 > 5 or d1 <= d0:
                continue
            if not any(x in hit_rounds[b] for x in (r - 2, r - 1, r)):
                continue
            if r - last_start < 6:
                continue
            last_start = r
            c = S.get(r - 1, {}).get(b)
            if not c or not c[7]:
                continue
            p = (c[3], c[4])
            th = threat(r, b)
            pw_own, n_own = power(r - 1, p, team[b], 6, excl=b, incl_self=b)
            pw_en, n_en = power(r - 1, p, 1 - team[b], 6)
            died = any(r <= x <= r + 8 for x in death_r[b])
            own_dash = types[b] in DASHERS and ready(b, 6, r)
            # direction: toward allies (nearest ally distance shrinks or ally count within 6 grows) / toward spawn
            s0 = S.get(r - 1, {})
            allies = [(q[3], q[4]) for i, q in s0.items() if i != b and q[7] and team[i] == team[b]]
            da0 = min((cheb(fr, a) for a in allies), default=None)
            da1 = min((cheb(to, a) for a in allies), default=None)
            to_ally = (da1 is not None and da0 is not None and da1 < da0)
            dh0, dh1 = dist_home(team[b], fr), dist_home(team[b], to)
            to_spawn = (dh0 is not None and dh1 is not None and dh1 < dh0)
            used_dash = any(r <= x[0] <= r + 2 for x in dash_cast[b])
            used_stun = any(r - 1 <= x <= r + 2 for x in stun_cast[b])
            used_recall = any(r <= x <= r + 3 for x in real_recalls[b])
            c3 = S.get(r + 3, {}).get(b)
            en4_3 = len(nearby(r + 3, (c3[3], c3[4]), 1 - team[b], 4)) if c3 and c3[7] else None
            hp3 = c3[5] / max(1, c3[6]) if c3 and c3[7] else None
            # pursued: the nearest enemy stepped toward b in r..r+3
            pursued = sum(1 for (r2, f2, t2, rl) in moves[j] if r <= r2 <= r + 3 and b in rl and rl[b][1] < rl[b][0])
            retreats.append({'mid': mid, 't': team[b], 'body': b, 'champ': types[b], 'r': r, 'hp': c[5] / max(1, c[6]), 'hp_abs': c[5],
                             'n_own': n_own, 'n_en': n_en, 'pw_ratio': (pw_own / pw_en) if pw_en > 0 else None,
                             'en4': th[0] if th else None, 'dash4': th[1] if th else None, 'stun5': th[2] if th else None,
                             'own_dash': own_dash, 'died8': died, 'gems': c[8], 'to_ally': to_ally, 'to_spawn': to_spawn,
                             'da0': da0, 'dash': used_dash, 'stun': used_stun, 'recall': used_recall, 'en4_3': en4_3, 'hp3': hp3,
                             'pursued': pursued, 'd_enemy': d0, 'enemy': types[j]})

    # ---- dives / chases / step stats
    dives, chases = [], []
    step_stats = Counter()
    for b, mv in moves.items():
        tb = team[b]
        cand = []
        for (r, fr, to, rel) in mv:
            if not rel:
                continue
            j = min(rel, key=lambda q: rel[q][0])
            d0, d1 = rel[j]
            if d0 > 6:
                continue
            po, no = power(r - 1, fr, tb, 6, excl=b, incl_self=b)
            pe, ne = power(r - 1, fr, 1 - tb, 6)
            ratio = po / pe if pe > 0 else 9.0
            rb = 'weak' if ratio < 0.67 else 'par' if ratio <= 1.5 else 'strong'
            nb = 'nless' if no < ne else 'neq' if no == ne else 'nmore'
            dirn = 'toward' if d1 < d0 else 'away' if d1 > d0 else 'side'
            died = any(r <= x <= r + 6 for x in death_r[b])
            step_stats[(str(tb), rb, dirn, 'n')] += 1
            step_stats[(str(tb), rb, dirn, 'died6')] += died
            step_stats[(str(tb), rb + '+' + nb, dirn, 'n')] += 1
            step_stats[(str(tb), rb + '+' + nb, dirn, 'died6')] += died
            if dirn == 'toward' and ratio < 0.67:
                cand.append((r, j, ratio))
        last = -100
        for i, (r, j, ratio) in enumerate(cand):
            if r - last < 8:
                continue
            if any(r < r2 <= r + 3 for (r2, _, _) in cand[i + 1:i + 4]):
                last = r
                c = S.get(r - 1, {}).get(b)
                died = [dd for dd in deaths if dd['who'] == b and r <= dd['r'] <= r + 8]
                dives.append({'mid': mid, 't': tb, 'body': b, 'champ': types[b], 'r': r, 'hp': c[5] / max(1, c[6]) if c else None,
                              'ratio': round(ratio, 3), 'target': f'{j}:{types[j]}',
                              'n_own': len(nearby(r - 1, (c[3], c[4]), tb, 6, excl=b)) + 1 if c else None,
                              'n_en': len(nearby(r - 1, (c[3], c[4]), 1 - tb, 6)) if c else None,
                              'died8': bool(died), 'killer': (types.get(died[0]['by'], 'camp') if died else None), 'bag': died[0]['bag'] if died else 0})
        last = -100
        for i, (r, fr, to, rel) in enumerate(mv):
            if r - last < 8 or not rel:
                continue
            j = min(rel, key=lambda q: rel[q][0])
            d0, d1 = rel[j]
            if d0 > 6 or d1 >= d0:
                continue
            steps = [(r2, rl[j]) for (r2, f2, t2, rl) in mv[i:] if r2 <= r + 6 and j in rl and rl[j][1] < rl[j][0]]
            if len(steps) < 3:
                continue
            cj = S.get(r + 6, {}).get(j) or S.get(steps[-1][0], {}).get(j)
            cb = S.get(r + 6, {}).get(b) or S.get(steps[-1][0], {}).get(b)
            j_away = sum(1 for (r2, f2, t2, rl) in moves[j] if r <= r2 <= r + 6 and b in rl and rl[b][1] > rl[b][0])
            if not cj or not cb or not cj[7] or not cb[7]:
                dend = 0
            else:
                dend = cheb((cb[3], cb[4]), (cj[3], cj[4]))
            if j_away >= 2 and dend >= d0:
                last = r
                c = S.get(r - 1, {}).get(b)
                died = [dd for dd in deaths if dd['who'] == b and r <= dd['r'] <= r + 10]
                n_en0 = len(nearby(r - 1, fr, 1 - tb, 6))
                ce = S.get(steps[-1][0], {}).get(b)
                n_en1 = len(nearby(steps[-1][0], (ce[3], ce[4]), 1 - tb, 6)) if ce and ce[7] else None
                chases.append({'mid': mid, 't': tb, 'body': b, 'champ': types[b], 'r': r, 'target': f'{j}:{types[j]}', 'tgt_champ': types[j],
                               'steps': len(steps), 'd0': d0, 'dend': dend, 'hp': c[5] / max(1, c[6]) if c else None, 'n_en0': n_en0,
                               'n_en1': n_en1, 'died10': bool(died), 'killer_is_target': bool(died) and died[0]['by'] == j,
                               'killer': (types.get(died[0]['by'], 'camp') if died else None)})

    # ---- fight rows
    frows = []
    parts_rows = []
    for fi, c in enumerate(fights):
        HH = [hits[i] for i in c]
        start, end = HH[0]['r'], HH[-1]['r']
        parts = {0: set(), 1: set()}
        join = {}
        first_own_hit = {}
        for h in HH:
            for b in (h['a'], h['t']):
                parts[team[b]].add(b)
                join.setdefault(b, h['r'])
            first_own_hit.setdefault(h['a'], h['r'])
        nh = {0: 0, 1: 0}
        dmg = {0: 0.0, 1: 0.0}
        stuns = {0: 0, 1: 0}
        first_hit_r = {0: None, 1: None}
        for h in HH:
            ta = team[h['a']]
            nh[ta] += 1
            dmg[ta] += h.get('dmg', 0)
            stuns[ta] += h['stun']
            if first_hit_r[ta] is None:
                first_hit_r[ta] = h['r']
        allp = parts[0] | parts[1]
        fdeaths = [dd for dd in deaths if dd['who'] in allp and start <= dd['r'] <= end + 2 and
                   (dd['by'] != 'camp' or any(h['t'] == dd['who'] and h['r'] >= dd['r'] - 5 for h in HH))]
        dead = {0: 0, 1: 0}
        bag = {0: 0, 1: 0}
        for dd in fdeaths:
            dead[team[dd['who']]] += 1
            bag[team[dd['who']]] += dd['bag']
        h0 = HH[0]
        a0, t0 = h0['a'], h0['t']
        first = team[a0]
        cp = h0['tp']
        num = {t: len(nearby(start - 1, cp, t)) for t in (0, 1)}
        pw = {t: power(start - 1, cp, t, 6)[0] for t in (0, 1)}
        hp0 = {t: sum(S[start - 1][b][5] for b in parts[t] if b in S.get(start - 1, {}) and S[start - 1][b][7]) for t in (0, 1)}
        sh0 = {t: sum(shards(S[start - 1][b][11]) for b in parts[t] if b in S.get(start - 1, {})) for t in (0, 1)}
        # shards of all live bodies within 6 of the contact tile (what a scout sees), per body
        sh6 = {t: [shards(S[start - 1][i][11]) for i in nearby(start - 1, cp, t)] if S.get(start - 1) else [] for t in (0, 1)}
        if dead[0] != dead[1]:
            win = 0 if dead[1] > dead[0] else 1
        elif dmg[0] >= 1.3 * max(1, dmg[1]) and dmg[0] >= 150:
            win = 0
        elif dmg[1] >= 1.3 * max(1, dmg[0]) and dmg[1] >= 150:
            win = 1
        else:
            win = None
        # opener context
        ca = S.get(start - 1, {}).get(a0)
        ct = S.get(start - 1, {}).get(t0)
        a_hp = ca[5] / max(1, ca[6]) if ca and ca[7] else None
        t_hp = ct[5] / max(1, ct[6]) if ct and ct[7] else None
        a_ally = nearest_ally_d(start - 1, a0)
        t_ally = nearest_ally_d(start - 1, t0)
        pa6, pt6 = tpos(start - 6, a0), tpos(start - 6, t0)
        d6 = cheb(pa6, pt6) if pa6 and pt6 else None
        pa1, pt1 = tpos(start - 1, a0), tpos(start - 1, t0)
        d1 = cheb(pa1, pt1) if pa1 and pt1 else None
        a_tw = move_class(a0, start - 5, start, ref=t0)[0]
        t_tw = move_class(t0, start - 5, start - 1, ref=a0)[0]
        if d6 is None:
            approach = 'unknown'
        elif d6 <= REACH[types[a0]] + 1:
            approach = 'static'       # already in / next to reach 6 rounds before
        elif a_tw >= t_tw + 2:
            approach = 'walkin'       # the opener closed the distance
        elif t_tw >= a_tw + 2:
            approach = 'received'     # the target walked into the opener
        else:
            approach = 'mutual'
        # own-side power from the opener's perspective, at the opener's tile
        pa = power(start - 1, pa1, first, 6, excl=a0, incl_self=a0)[0] if pa1 else 0
        pe = power(start - 1, pa1, 1 - first, 6)[0] if pa1 else 0
        r_open = (pa / pe) if pe > 0 else None
        answer = None if first_hit_r[1 - first] is None else first_hit_r[1 - first] - start
        farm_def = any(any(start - 3 <= x <= start for x in champ_camp[b]) for b in parts[1 - first])
        farm_att = any(any(start - 3 <= x <= start for x in champ_camp[b]) for b in parts[first])
        # retreat of the losing side: did any dead body try to leave
        leave = {0: [0, 0], 1: [0, 0]}
        for dd in fdeaths:
            b = dd['who']
            tw, aw, sd = move_class(b, dd['r'] - 4, dd['r'])
            rec = any(dd['r'] - 5 <= x <= dd['r'] for x in real_recalls[b])
            leave[team[b]][1] += 1
            leave[team[b]][0] += (aw >= 2 or rec)
        dlist = [(dd['r'], dd['who'], types[dd['who']], team[dd['who']]) for dd in fdeaths]
        frows.append({'mid': mid, 'fid': fi, 'start': start, 'end': end, 'first': first, 'opener': a0, 'opener_champ': types[a0],
                      'target': t0, 'target_champ': types[t0], 'kind0': h0['kind'], 'exchange': nh[0] > 0 and nh[1] > 0,
                      'win': win, 'parts': {t: len(parts[t]) for t in (0, 1)}, 'num': num, 'pw': pw, 'hits': nh,
                      'dmg': {t: round(dmg[t]) for t in (0, 1)}, 'dead': dead, 'bag': bag, 'stuns': stuns, 'hp0': hp0, 'shards': sh0,
                      'sh6': sh6, 'cp': cp, 'd_home': {t: dist_home(t, cp) for t in (0, 1)}, 'farm_def': farm_def, 'farm_att': farm_att,
                      'a_hp': a_hp, 't_hp': t_hp, 'a_ally': a_ally, 't_ally': t_ally, 'd6': d6, 'd1': d1, 'a_tw': a_tw, 't_tw': t_tw,
                      'approach': approach, 'r_open': r_open, 'answer': answer, 'leave': leave, 'deaths': dlist,
                      'part_bodies': {t: sorted(f'{b}:{types[b]}' for b in parts[t]) for t in (0, 1)}})
        # participations: each body that landed a hit, state at its first own hit
        for b, r1 in first_own_hit.items():
            c1 = S.get(r1 - 1, {}).get(b)
            if not c1 or not c1[7]:
                continue
            p1 = (c1[3], c1[4])
            al = nearby(r1 - 1, p1, team[b], 6, excl=b)
            en = nearby(r1 - 1, p1, 1 - team[b], 6)
            died = any(r1 <= x <= end + 2 for x in death_r[b])
            parts_rows.append({'mid': mid, 'fid': fi, 't': team[b], 'body': b, 'champ': types[b], 'r': r1, 'al6': len(al), 'en6': len(en),
                               'al8': len(nearby(r1 - 1, p1, team[b], 8, excl=b)), 'hp': c1[5] / max(1, c1[6]), 'died': died,
                               'opener': b == a0, 'exchange': nh[0] > 0 and nh[1] > 0})

    # ---- hit rows (focus): allies that hit the same target within +-2 rounds
    by_target_r = defaultdict(list)
    for h in hits:
        by_target_r[h['t']].append((h['r'], h['a']))
    hrows = []
    for i, h in enumerate(hits):
        if h['kind'] == 'splash':
            continue
        helpers = {a for (r2, a) in by_target_r[h['t']] if a != h['a'] and abs(r2 - h['r']) <= 2}
        c = S.get(h['r'] - 1, {}).get(h['a'])
        if not c or not c[7]:
            continue
        p = (c[3], c[4])
        al6 = len(nearby(h['r'] - 1, p, team[h['a']], 6, excl=h['a']))
        en6 = len(nearby(h['r'] - 1, p, 1 - team[h['a']], 6))
        hrows.append({'mid': mid, 't': team[h['a']], 'a': h['a'], 'champ': types[h['a']], 'tgt': types[h['t']], 'r': h['r'], 'kind': h['kind'],
                      'helpers': len(helpers), 'al6': al6, 'en6': en6, 'fid': hit_fight[i]})

    # ---- death rows
    drows = []
    for dd in deaths:
        b, r = dd['who'], dd['r']
        t = team[b]
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
        al, en = [], []
        for k in range(1, 6):
            s = S.get(r - k, {})
            c = s.get(b)
            if not c or not c[7]:
                continue
            p = (c[3], c[4])
            al.append(len(nearby(r - k, p, t, 6, excl=b)))
            en.append(len(nearby(r - k, p, 1 - t, 6)))
        c5 = S.get(r - 5, {}).get(b)
        hp5 = (c5[5] / max(1, c5[6])) if c5 and c5[7] else None
        c10 = S.get(r - 10, {}).get(b)
        hp10 = (c10[5] / max(1, c10[6])) if c10 and c10[7] else None
        tw8, aw8, sd8 = move_class(b, r - 8, r)
        tw4, aw4, sd4 = move_class(b, r - 4, r)
        ch5 = [h for rr in range(r - 5, r + 1) for h in camp_by_r.get(rr, ()) if h['t'] == b]
        wakers = set()
        for h in ch5:
            prev = [tm for (rr, tm) in camp_hit_by.get(h['camp'], ()) if rr <= h['r']]
            if prev:
                wakers.add('own' if prev[-1] == t else 'enemy')
        camp_waker = None if not ch5 else ('both' if len(wakers) > 1 else (next(iter(wakers)) if wakers else 'unknown'))
        champ_dmg5 = sum(hits[i].get('dmg', 0) for i in hits_by_t[b] if r - 5 <= hits[i]['r'] <= r)
        camp_dmg5 = sum(h.get('dmg', 0) for h in ch5)
        taken10 = [hits[i] for i in hits_by_t[b] if r - 10 <= hits[i]['r'] <= r]
        dealt10 = [hits[i] for i in hits_by_a[b] if r - 10 <= hits[i]['r'] <= r]
        dealt_dmg10 = sum(h.get('dmg', 0) for h in dealt10)
        kinds3 = Counter(h['kind'] for h in taken10 if h['r'] >= r - 2)
        attackers10 = {h['a'] for h in taken10}
        killer = dd['by']
        cause = 'camp' if killer == 'camp' and champ_dmg5 == 0 else 'champion' if killer != 'camp' and not ch5 else 'both'
        kd3 = None
        tw_k = None
        if killer != 'camp':
            pk, pb = tpos(r - 3, killer), tpos(r - 3, b)
            kd3 = cheb(pk, pb) if pk and pb else None
            tw_k = move_class(b, r - 4, r, ref=killer)[0]
        # Marcella pattern: within 4 of an enemy Marcella for >=3 of the last 5 rounds and took her spell
        marc = False
        if killer != 'camp' and types.get(killer) == 'Marcella':
            cnt = 0
            for k in range(1, 6):
                pk, pb = tpos(r - k, killer), tpos(r - k, b)
                if pk and pb and cheb(pk, pb) <= 4:
                    cnt += 1
            marc = cnt >= 3 and any(h['kind'] == 'spell' and h['a'] == killer for h in taken10)
        last_resp = max((x for x in respawns[b] if x <= r), default=None)
        age = (r - last_resp) if last_resp is not None else None
        kills10 = sum(1 for d2 in deaths if d2['by'] == b and r - 10 <= d2['r'] <= r)
        cpos = dd['at']
        dho, dhe = dist_home(t, cpos), dist_home(1 - t, cpos)
        pr = []
        for k in (3, 5):
            cbk = S.get(r - k, {}).get(b)
            if cbk and cbk[7]:
                pk = (cbk[3], cbk[4])
                po = power(r - k, pk, t, 6, excl=b, incl_self=b)[0]
                pe = power(r - k, pk, 1 - t, 6)[0]
                pr.append(po / pe if pe > 0 else None)
            else:
                pr.append(None)
        th = threat(r, b)
        fin = [m for m in moves[b] if r - 10 <= m[0] <= r and m[3]]
        ret_r = ret_hp = None
        for m in reversed(fin):
            j = min(m[3], key=lambda q: m[3][q][0])
            d0, d1 = m[3][j]
            if d1 > d0:
                ret_r = m[0]
            elif d1 < d0:
                break
        if ret_r is not None:
            cr = S.get(ret_r - 1, {}).get(b)
            ret_hp = cr[5] / max(1, cr[6]) if cr and cr[7] else None
        rec = [x for x in real_recalls[b] if r - 6 <= x <= r]
        stunned = any(r - 3 <= x <= r for x in stun_on[b])
        fh = [hits[i] for i in hits_by_t[b] if r - 15 <= hits[i]['r'] <= r]
        first_hit_r = fh[0]['r'] if fh else None
        farming = bool(first_hit_r) and any(first_hit_r - 4 <= x <= first_hit_r for x in champ_camp[b])
        tw_pre = move_class(b, first_hit_r - 5, first_hit_r)[0] if first_hit_r else None
        cb1 = S.get(r - 1, {}).get(b)
        rowsh = shards(cb1[11]) if cb1 else 0
        # shards per body of the attackers in the last 10 rounds
        att_sh = [shards(S[r - 1][a][11]) for a in attackers10 if a in S.get(r - 1, {})]
        drows.append({'mid': mid, 't': t, 'body': b, 'champ': types[b], 'r': r, 'killer': 'camp' if killer == 'camp' else types.get(killer, '?'),
                      'killer_body': killer, 'step': dd['step'], 'bag': dd['bag'], 'fid': fid, 'started': started, 'cause': cause,
                      'al5': sum(al) / len(al) if al else None, 'en5': sum(en) / len(en) if en else None,
                      'al_last': al[0] if al else None, 'en_last': en[0] if en else None,
                      'hp5': hp5, 'hp10': hp10, 'tw8': tw8, 'aw8': aw8, 'tw4': tw4, 'aw4': aw4,
                      'camp_hits5': len(ch5), 'camp_dmg5': round(camp_dmg5), 'champ_dmg5': round(champ_dmg5),
                      'hit_back': len(dealt10) > 0, 'n_dealt10': len(dealt10), 'dealt10': round(dealt_dmg10), 'n_taken10': len(taken10),
                      'n_attackers10': len(attackers10), 'att_shards': att_sh, 'kinds3': dict(kinds3), 'kd3': kd3, 'tw_killer4': tw_k,
                      'marcella_pattern': marc, 'age': age, 'kills10': kills10,
                      'enemy_half': (dho is not None and dhe is not None and dho > dhe), 'd_own': dho, 'd_enemy': dhe,
                      'recall6': len(rec), 'stunned3': stunned, 'farming': farming, 'tw_pre_hit': tw_pre, 'shards': rowsh,
                      'x': cpos[0], 'y': cpos[1], 'pw3': pr[0], 'pw5': pr[1], 'threat': th, 'ret_r': ret_r, 'ret_hp': ret_hp,
                      'camp_waker': camp_waker})
    g = {'mid': mid, 'map': gm['map'], 'kind': gm['kind'], 'ver': gm['ver'], 'created': gm['created'], 'teams': gm['teams'], 'we': gm['we'],
         'final': final, 'sub': meta['submitted'], 'champs': meta['champsPerTeam'], 'drafts': meta['drafts'], 'mf': mf, 'end': gm.get('end'),
         'deaths': {t: sum(1 for x in drows if x['t'] == t) for t in (0, 1)},
         'gems_lost': {t: sum(x['bag'] for x in drows if x['t'] == t) for t in (0, 1)},
         'n_fights': len(frows), 'n_exch': sum(1 for f in frows if f['exchange']),
         'hits': {t: sum(1 for h in hits if team[h['a']] == t) for t in (0, 1)},
         'step_stats': {'|'.join(k): v for k, v in step_stats.items()}}
    return {'games': [g], 'deaths': drows, 'fights': frows, 'retreats': retreats, 'dives': dives, 'chases': chases, 'hits': hrows, 'parts': parts_rows}


NAMES = ('games', 'deaths', 'fights', 'retreats', 'dives', 'chases', 'hits', 'parts')


def main():
    ds = sys.argv[1]
    limit = None
    redo = '--redo' in sys.argv
    if '--limit' in sys.argv:
        limit = int(sys.argv[sys.argv.index('--limit') + 1])
    out = f'{HERE}/out'
    os.makedirs(out, exist_ok=True)
    gms = games_top() if ds == 'top' else games_our()
    done = set()
    gpath = f'{out}/{ds}_games.jsonl'
    if os.path.exists(gpath) and not redo:
        done = {json.loads(l)['mid'] for l in open(gpath)}
    todo = [g for g in gms if g['mid'] not in done]
    if limit:
        todo = todo[:limit]
    print(ds, 'games', len(gms), 'done', len(done), 'todo', len(todo), flush=True)
    mode = 'w' if redo else 'a'
    fh = {n: open(f'{out}/{ds}_{n}.jsonl', mode) for n in NAMES}
    for i, gm in enumerate(todo):
        try:
            res = process(gm)
        except Exception as ex:  # keep going; report
            print('FAIL', gm['mid'], repr(ex), flush=True)
            continue
        for n in NAMES:
            for row in res[n]:
                fh[n].write(json.dumps(row) + '\n')
        if i % 20 == 0:
            print(i, gm['mid'][:8], len(res['deaths']), len(res['fights']), flush=True)
            for f in fh.values():
                f.flush()
    for f in fh.values():
        f.close()


if __name__ == '__main__':
    main()
