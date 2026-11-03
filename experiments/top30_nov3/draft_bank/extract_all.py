#!/usr/bin/env python3
"""Banking, champion use and endgame extraction from decoded replays: top-30 games (top30_nov3/dec) and our games (ladder_nov2/dec).

Usage: nice -n 19 python3 -I extract_all.py [top30|ours|both]
Writes out/teams.jsonl   one row per (game, team): banking stats, gems lost, locks, endgame behaviour
       out/tributes.jsonl one row per Submit gems event (bag, altar class, carried rounds, outcome, enemies near)
       out/locks.jsonl    one row per altar lock placed
       out/bodies.jsonl   one row per (game, body): champion use (camp / champion hits, casts per ability, dash use, stun outcomes...)
Groups ('grp' field): top30 (team rank <= 30 in a top-30 game), t30opp (other team in those games, rank > 30),
       ours_v88 / ours_v84 (= v84..v87) / ours_old (our team), opp (the other team in our games).
"""
import json, os, sys
from collections import defaultdict, Counter
from bisect import bisect_left

BASE = '/home/claude/cambridge_battlecode/experiments'
sys.path.insert(0, f'{BASE}/top30_nov3/draft_bank')
import mapfeat  # noqa: E402

ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
OUT = f'{BASE}/top30_nov3/draft_bank/out'
STUN_SPELL = {('Ren', 4), ('Tavi', 4), ('Prism', 4), ('Cassi', 4), ('Ryth', 3), ('HeartOfRuin', 6)}
DMG_SPELL = {('Marcella', 2), ('Cassi', 2), ('Stellar', 2), ('Stellar', 3), ('Prism', 3), ('Prism', 4), ('Ren', 4), ('Tavi', 4), ('Ryth', 3)}
SWITCH = [('2026-11-02T21:15:46', 'v84'), ('2026-11-03T01:00:56', 'v85'), ('2026-11-03T01:21:19', 'v86'), ('2026-11-03T02:52:00', 'v87'),
          ('2026-11-03T04:11:33', 'v88'), ('2026-11-03T04:30:53', 'v89'), ('2026-11-03T04:52:07', 'v88'), ('9999', 'v90')]
V84_START = '2026-11-02T13:00'  # v84 live from ~Nov 2 13:00Z (ladder_nov2 study); earlier games = older versions


def version(created):
    if created < V84_START:
        return 'old'
    for t, v in SWITCH:
        if created < t:
            return v
    return 'v90'


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


_altar_fields = {}


def altar_fields(mapname):
    """walking distance fields from every altar (and from both spawns)"""
    if mapname in _altar_fields:
        return _altar_fields[mapname]
    mj = mapfeat.mapjson(mapname)
    w, h, rows = mj['width'], mj['height'], mj['rows']
    altars = [(x, y) for y in range(h) for x in range(w) if rows[y][x] == 'A']
    fields = {}
    for a in altars:
        starts = [(a[0] + dx, a[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx or dy) and 0 <= a[0] + dx < w and 0 <= a[1] + dy < h and rows[a[1] + dy][a[0] + dx] not in '#oA']
        fields[a] = mapfeat.bfs(rows, starts, w, h)
    dA = mapfeat.bfs(rows, [tuple(p) for p in mj['spawnA']], w, h)
    dB = mapfeat.bfs(rows, [tuple(p) for p in mj['spawnB']], w, h)
    res = {'altars': altars, 'fields': fields, 'd': {0: dA, 1: dB}, 'spawn': {0: {tuple(p) for p in mj['spawnA']}, 1: {tuple(p) for p in mj['spawnB']}}, 'w': w, 'h': h}
    # the altar nearest each spawn
    res['spawn_altar'] = {}
    for t in (0, 1):
        best = None
        for a in altars:
            dd = min((fields[a][y][x] for (x, y) in res['spawn'][t] if fields[a][y][x] >= 0), default=None)
            if dd is not None and (best is None or dd < best[0]):
                best = (dd, a)
        res['spawn_altar'][t] = best
    _altar_fields[mapname] = res
    return res


def load_games(which):
    games = []
    if which in ('top30', 'both'):
        ladder = json.load(open(f'{BASE}/top30_nov3/ladder.json'))['teams']
        rank = {t['teamId']: t['rank'] for t in ladder}
        rating = {t['teamId']: t['rating'] for t in ladder}
        sel = {}
        for l in open(f'{BASE}/top30_nov3/selection.jsonl'):
            m = json.loads(l)
            sel[m['matchId'][:8]] = m
        for f in sorted(os.listdir(f'{BASE}/top30_nov3/dec')):
            if not f.endswith('.json'):
                continue
            mapname, id8 = f[:-5].rsplit('_', 1)
            m = sel.get(id8)
            if m is None:
                continue
            teams = []
            for t in m['teams']:
                tid = t['teamId']
                teams.append({'teamId': tid, 'name': t['name'], 'side': 0 if t['side'] == 'a' else 1, 'result': t['result'],
                              'rank': rank.get(tid, 999), 'rating': rating.get(tid), 'grp': 'top30' if rank.get(tid, 999) <= 30 else 't30opp'})
            games.append({'mid': m['matchId'], 'dec': f'{BASE}/top30_nov3/dec/{f}', 'map': mapname, 'teams': teams, 'set': 'top30',
                          'end': m['endReason'], 'created': m['createdAt'], 'kind': m['kind']})
    if which in ('ours', 'both'):
        info = {}
        for l in open(f'{BASE}/ladder_nov2/matches_me.jsonl'):
            m = json.loads(l)
            info[m['matchId']] = m
        ladder = json.load(open(f'{BASE}/top30_nov3/ladder.json'))['teams']
        rank = {t['teamId']: t['rank'] for t in ladder}
        rating = {t['teamId']: t['rating'] for t in ladder}
        for f in sorted(os.listdir(f'{BASE}/ladder_nov2/dec')):
            mid = f[:-5]
            m = info.get(mid)
            if m is None or m.get('status') != 'finished':
                continue
            ver = version(m['createdAt'])
            teams = []
            for t in m['teams']:
                tid = t['teamId']
                if tid == ME:
                    grp = 'ours_v88' if ver == 'v88' else 'ours_v84' if ver in ('v84', 'v85', 'v86', 'v87') else 'ours_old'
                else:
                    grp = 'opp'
                teams.append({'teamId': tid, 'name': t['name'], 'side': 0 if t['side'] == 'a' else 1, 'result': t['result'],
                              'rank': rank.get(tid, 999), 'rating': rating.get(tid), 'grp': grp, 'ver': ver if tid == ME else None})
            games.append({'mid': mid, 'dec': f'{BASE}/ladder_nov2/dec/{f}', 'map': m['map'], 'teams': teams, 'set': 'ours',
                          'end': m['endReason'], 'created': m['createdAt'], 'kind': m['kind']})
    return games


def analyse(g):
    d = json.load(open(g['dec']))
    meta = d['meta']
    W, H = meta['width'], meta['height']
    types = {b['index']: b['type'] for b in meta['bodies']}
    team = {b['index']: b['team'] for b in meta['bodies']}
    bodies = sorted(types)
    final = meta['finalRound']
    S = {rr['r']: {c[0]: c for c in rr['ch']} for rr in d['rounds'][1:]}
    SUB = {rr['r']: rr['sub'] for rr in d['rounds'][1:]}
    camp_at = {(c['x'], c['y']): c['index'] for c in meta['camps']}
    AF = altar_fields(g['map'])
    altars = AF['altars']
    spawn = AF['spawn']
    mf = mapfeat.features(g['map'])

    def dhome(t, p):
        dm = AF['d'][t]
        x, y = p
        return dm[y][x] if 0 <= x < W and 0 <= y < H and dm[y][x] >= 0 else None

    def altar_class(t, a):
        """own = this team's spawn altar; their = the enemy's spawn altar; else field: and the altar's half by walking distance"""
        if AF['spawn_altar'][t] and AF['spawn_altar'][t][1] == a:
            return 'spawnaltar'
        if AF['spawn_altar'][1 - t] and AF['spawn_altar'][1 - t][1] == a:
            return 'enemyspawnaltar'
        da, db = dhome(t, a), dhome(1 - t, a)
        if da is None or db is None:
            # altar tile itself is blocked: use a neighbour
            nb = [(a[0] + dx, a[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
            da = min((dhome(t, q) for q in nb if dhome(t, q) is not None), default=None)
            db = min((dhome(1 - t, q) for q in nb if dhome(1 - t, q) is not None), default=None)
        if da is None or db is None or da + db == 0:
            return 'field?'
        f = da / (da + db)
        return 'field_own' if f < 0.42 else 'field_mid' if f <= 0.58 else 'field_their'

    ev = defaultdict(list)
    for e in d['events']:
        if e['k'] != 'Draft champion':
            ev[e['r']].append(e)

    # ---------- per-round position-tracked event pass
    camp_hit = defaultdict(Counter)       # body -> Counter(kind)  kind: atk, cast<ab>
    champ_hit = defaultdict(Counter)      # body -> Counter(kind)
    casts = defaultdict(Counter)          # body -> Counter((ability, target)) target: champ / camp / none
    dash_use = defaultdict(Counter)       # body -> Counter(fight / camp / travel)
    dash_dist = defaultdict(list)
    stuns = []                            # (r, caster, target, ability)
    marc_spell = defaultdict(Counter)     # Marcella body -> Counter(dist of ability-2 target)
    spell_kills = Counter()               # body -> kills whose step is Cast ability
    kills = Counter()
    deaths = []
    submits = []                          # (r, body, altar)
    banked = defaultdict(list)            # body -> [(r, gems, at)]
    locks = []                            # (r, body, at)
    cancels = defaultdict(set)
    shops = defaultdict(list)             # body -> rounds (with pos)
    captures = defaultdict(list)          # body -> (r, gems, gold)
    recalls = defaultdict(list)
    tele = defaultdict(list)
    moved = defaultdict(set)
    attacked_lock = Counter()
    hit_given_r = defaultdict(set)
    hit_taken_r = defaultdict(set)
    camp_r = defaultdict(set)
    first_alive = {}
    for r in range(1, final + 1):
        prev = S.get(r - 1) or S.get(r)
        if prev is None:
            continue
        pos = {i: ((c[3], c[4]) if c[7] else None) for i, c in prev.items()}
        for e in ev.get(r, []):
            k, who = e['k'], e.get('who')
            if who is not None and k in ('Attack', 'Move', 'Movement blocked') and tuple(e['from']) != (0, 0):
                pos[who] = tuple(e['from'])
            if k == 'Move' and who is not None:
                moved[who].add(r)
                pos[who] = tuple(e['to'])
            elif k == 'Cast ability' and who is not None:
                ab = e['ability']
                ct = types[who]
                P = tuple(e['to'])
                if ab == 6:
                    fr = pos.get(who) or P
                    dd = cheb(fr, P)
                    pos[who] = P
                    moved[who].add(r)
                    en = [j for j, pj in pos.items() if pj is not None and team[j] != team[who] and cheb(pj, P) <= (1 if ct == 'HeartOfRuin' else 2)]
                    en_near = [j for j, pj in pos.items() if pj is not None and team[j] != team[who] and cheb(pj, P) <= 5]
                    camp_near = any(cheb(P, q) <= 1 for q in camp_at)
                    if en:
                        use = 'fight'
                        if ct == 'HeartOfRuin':
                            for j in en:
                                champ_hit[who]['dash'] += 1
                                hit_given_r[who].add(r)
                                hit_taken_r[j].add(r)
                                if types[j] != 'Marcella':
                                    stuns.append((r, who, j, 6))
                    elif camp_near:
                        use = 'camp'
                        if ct == 'HeartOfRuin':
                            camp_hit[who]['dash'] += 1
                            camp_r[who].add(r)
                    elif en_near:
                        use = 'near'   # enemy within 5 but not reached: approach / escape
                    else:
                        use = 'travel'
                    dash_use[who][use] += 1
                    dash_dist[who].append(dd)
                    casts[who][(6, use)] += 1
                    continue
                if ab in (2, 4):
                    tg = [j for j, pj in pos.items() if pj == P and team[j] != team[who]]
                    if tg:
                        j = tg[0]
                        casts[who][(ab, 'champ')] += 1
                        champ_hit[who][f'cast{ab}'] += 1
                        hit_given_r[who].add(r)
                        hit_taken_r[j].add(r)
                        if (ct, ab) in STUN_SPELL and types[j] != 'Marcella':
                            stuns.append((r, who, j, ab))
                        if ct == 'Marcella' and ab == 2 and pos.get(who):
                            marc_spell[who][cheb(pos[who], P)] += 1
                    elif P in camp_at:
                        casts[who][(ab, 'camp')] += 1
                        camp_hit[who][f'cast{ab}'] += 1
                        camp_r[who].add(r)
                    else:
                        casts[who][(ab, 'none')] += 1
                elif ab == 3:
                    tg = [j for j, pj in pos.items() if pj is not None and cheb(pj, P) <= 1 and team[j] != team[who]]
                    cn = any(cheb(P, q) <= 1 for q in camp_at)
                    if tg:
                        casts[who][(3, 'champ')] += 1
                        for j in tg:
                            champ_hit[who]['cast3'] += 1
                            hit_given_r[who].add(r)
                            hit_taken_r[j].add(r)
                            if (ct, 3) in STUN_SPELL and types[j] != 'Marcella':
                                stuns.append((r, who, j, 3))
                    elif cn:
                        casts[who][(3, 'camp')] += 1
                        camp_hit[who]['cast3'] += 1
                        camp_r[who].add(r)
                    else:
                        casts[who][(3, 'none')] += 1
                else:
                    casts[who][(ab, 'self')] += 1
            elif k == 'Attack' and who is not None:
                P = tuple(e['to'])
                tg = [j for j, pj in pos.items() if pj == P and team[j] != team[who]]
                if tg:
                    champ_hit[who]['atk'] += 1
                    hit_given_r[who].add(r)
                    hit_taken_r[tg[0]].add(r)
                elif P in camp_at:
                    camp_hit[who]['atk'] += 1
                    camp_r[who].add(r)
                elif P in altars:
                    attacked_lock[who] += 1
                else:
                    champ_hit[who]['miss'] += 1
            elif k == 'Teleport complete' and who is not None:
                pos[who] = tuple(e['to'])
                tele[who].append(r)
            elif k == 'Respawn' and who is not None:
                pos[who] = tuple(e['to'])
            elif k == 'Death':
                deaths.append(e)
                if e['by'] != 'camp' and isinstance(e['by'], int):
                    kills[e['by']] += 1
                    if e.get('step') == 'Cast ability':
                        spell_kills[e['by']] += 1
                pos[who] = None
            elif k == 'Recall' and who is not None:
                recalls[who].append(r)
            elif k == 'Cancel channel' and who is not None:
                cancels[who].add(r)
            elif k == 'Submit gems' and who is not None:
                submits.append((r, who, tuple(e['to']), pos.get(who)))
            elif k == 'Banked':
                banked[who].append((r, e['gems'], tuple(e['at'])))
            elif k in ('CaptureGems', 'CaptureGold'):
                captures[who].append((r, e['gems'], e['gold']))
            elif k == 'Place altar lock' and who is not None:
                locks.append((r, who, tuple(e['to']), pos.get(who)))
            elif k == 'Shop' and who is not None:
                shops[who].append((r, pos.get(who)))
    # ---------- tributes
    trib_rows = []
    bank_by = defaultdict(list)
    for b, lst in banked.items():
        bank_by[b] = sorted(x[0] for x in lst)
    death_r = defaultdict(list)
    for e in deaths:
        death_r[e['who']].append(e['r'])
    lock_at = defaultdict(list)  # altar -> [(r, team)]
    for (r, who, at, p) in locks:
        lock_at[at].append((r, team[who]))
    stun_on = defaultdict(list)
    for (r, a, j, ab) in stuns:
        stun_on[j].append(r)
    # bag start: the round the body's bag went from 0 to >0 (capture) since its last bank / death
    submit_rounds = defaultdict(set)
    for (r, who, at, p) in submits:
        submit_rounds[who].add(r)
    for (r, who, at, p) in submits:
        c = S.get(r - 1, {}).get(who)
        c1 = S.get(r, {}).get(who)
        bag = c[8] if c and c[7] else (c1[8] if c1 else 0)
        if c1 and c1[7] and c1[8] > bag:
            bag = c1[8]  # captured this round
        if bag <= 0:
            continue
        # consecutive submits of one tribute (an enemy lock turns submit calls into attacks): keep the first of a run
        if (r - 1) in submit_rounds[who]:
            continue
        ticks = max(1, (bag + 9) // 10)
        t = team[who]
        land = next((x for x in bank_by[who] if r <= x <= r + ticks + 1), None)
        outcome = 'banked' if land is not None else 'cancelled'
        cause = None
        if outcome == 'cancelled':
            win = range(r, r + ticks + 1)
            if any(x in win for x in death_r[who]):
                cause = 'death'
            elif any(x in win and tt != t for (x, tt) in lock_at.get(at, [])):
                cause = 'lock'
            elif any(x in win for x in stun_on[who]):
                cause = 'stun'
            elif any(x in cancels[who] for x in win):
                cause = 'self'
            else:
                cause = 'unknown'
        # bag start round
        start = None
        for (cr, cg, cgold) in captures[who]:
            if cr <= r and cg > 0:
                # is this the first capture after the last bank/death?
                last_reset = max([x for x in bank_by[who] if x < cr] + [x for x in death_r[who] if x < cr] + [0])
                prior = [cr2 for (cr2, cg2, _) in captures[who] if last_reset <= cr2 < cr and cg2 > 0]
                if not prior:
                    start = cr
        last_cap = max([cr for (cr, cg, _) in captures[who] if cr <= r and cg > 0] + [0])
        # distance walked: from the position at the last capture to the altar used (altar field)
        cs = S.get(last_cap, {}).get(who) if last_cap else None
        fld = AF['fields'].get(at)
        walk = None
        if cs and cs[7] and fld:
            walk = fld[cs[4]][cs[3]] if fld[cs[4]][cs[3]] >= 0 else None
        # recall-banked: on a spawn tile within the 8 rounds before
        via_spawn = any((S.get(r - k, {}).get(who) or [0] * 8)[7] and ((S[r - k][who][3], S[r - k][who][4]) in spawn[t]) for k in range(1, 9) if S.get(r - k))
        en6 = 0
        en10 = 0
        if p is not None:
            for i, c2 in (S.get(r - 1) or {}).items():
                if c2[7] and team[i] != t:
                    dd = cheb((c2[3], c2[4]), p)
                    en6 += dd <= 6
                    en10 += dd <= 10
        allies5 = sum(1 for i, c2 in (S.get(r - 1) or {}).items() if c2[7] and team[i] == t and i != who and p is not None and cheb((c2[3], c2[4]), p) <= 5)
        hp = c[5] / max(1, c[6]) if c and c[7] else None
        trib_rows.append({'mid': g['mid'], 'set': g['set'], 'map': g['map'], 'team': t, 'grp': g['teams'][t]['grp'], 'res': g['teams'][t]['result'],
                          'body': who, 'champ': types[who], 'r': r, 'bag': bag, 'ticks': ticks, 'altar': at, 'aclass': altar_class(t, at),
                          'outcome': outcome, 'cause': cause, 'start': start, 'carried': (r - start) if start else None,
                          'since_cap': (r - last_cap) if last_cap else None, 'walk': walk, 'via_spawn': via_spawn, 'en6': en6, 'en10': en10,
                          'allies5': allies5, 'hp': hp, 'sub_own': SUB.get(r, [0, 0])[t], 'sub_en': SUB.get(r, [0, 0])[1 - t]})
    # ---------- locks
    lock_rows = []
    for (r, who, at, p) in locks:
        t = team[who]
        # enemy tribute in progress at that altar
        victim = None
        for (sr, sw, sat, sp) in submits:
            if sat == at and team[sw] != t and sr <= r:
                c = S.get(sr - 1, {}).get(sw)
                bag = c[8] if c else 0
                ticks = max(1, (bag + 9) // 10)
                landed = next((x for x in bank_by[sw] if sr <= x <= r), None)
                if sr + ticks >= r and landed is None:
                    victim = {'body': sw, 'champ': types[sw], 'bag': bag, 'started': sr}
        en_near = sum(1 for i, c2 in (S.get(r - 1) or {}).items() if c2[7] and team[i] != t and cheb((c2[3], c2[4]), at) <= 3)
        lock_rows.append({'mid': g['mid'], 'set': g['set'], 'map': g['map'], 'team': t, 'grp': g['teams'][t]['grp'], 'res': g['teams'][t]['result'],
                          'body': who, 'champ': types[who], 'r': r, 'altar': at, 'aclass': altar_class(t, at), 'victim': victim, 'en3': en_near,
                          'sub_own': SUB.get(r, [0, 0])[t], 'sub_en': SUB.get(r, [0, 0])[1 - t]})
    # ---------- per team
    team_rows = []
    reach = {}
    for t in (0, 1):
        reach[t] = next((r for r in sorted(SUB) if SUB[r][t] >= 1000), None)
    winner = 0 if g['teams'][0]['result'] == 'win' else 1
    for t in (0, 1):
        tb = [b for b in bodies if team[b] == t]
        my_tribs = [x for x in trib_rows if x['team'] == t]
        bk = [x for x in my_tribs if x['outcome'] == 'banked']
        tot_banked = sum(x['bag'] for x in bk)
        marc = sum(x['bag'] for x in bk if x['champ'] == 'Marcella')
        lost = [e['bag'] for e in deaths if e['team'] == t]
        # gem-rounds carried (exposure) and carried at the end
        carried_rounds = 0
        for r, s in S.items():
            carried_rounds += sum(c[8] for i, c in s.items() if team[i] == t and c[7])
        send = S.get(final) or S[max(S)]
        carried_end = sum(c[8] for i, c in send.items() if team[i] == t and c[7])
        captured = sum(cg for b in tb for (cr, cg, _) in captures[b])
        gold = sum(cgold for b in tb for (cr, cg, cgold) in captures[b])
        # endgame window: last 200 rounds (or from the round the leader passed 800)
        w0 = max(1, final - 200)
        beh = Counter()
        half = Counter()
        for b in tb:
            for r in range(w0, final + 1):
                c = S.get(r, {}).get(b)
                if not c:
                    continue
                if not c[7]:
                    beh['dead'] += 1
                    continue
                p = (c[3], c[4])
                st = ('fight' if r in hit_given_r[b] or r in hit_taken_r[b] else 'farm' if r in camp_r[b] else
                      'spawn' if p in spawn[t] else 'walk' if r in moved[b] else 'still')
                beh[st] += 1
                a, bb = dhome(t, p), dhome(1 - t, p)
                if a is not None and bb is not None and a + bb > 0 and p not in spawn[t]:
                    f = a / (a + bb)
                    half['own' if f < 0.42 else 'mid' if f <= 0.58 else 'their'] += 1
        n_locks = sum(1 for x in lock_rows if x['team'] == t)
        n_locks_hit = sum(1 for x in lock_rows if x['team'] == t and x['victim'])
        team_rows.append({'mid': g['mid'], 'set': g['set'], 'map': g['map'], 'team': t, 'grp': g['teams'][t]['grp'], 'name': g['teams'][t]['name'],
                          'rank': g['teams'][t]['rank'], 'ver': g['teams'][t].get('ver'), 'res': g['teams'][t]['result'], 'end': g['end'], 'kind': g['kind'],
                          'champs': meta['champsPerTeam'], 'draft': meta['drafts'][t], 'draft_en': meta['drafts'][1 - t], 'final': final,
                          'sub': meta['submitted'][t], 'sub_en': meta['submitted'][1 - t], 'reach1000': reach[t], 'winner': winner == t,
                          'n_sub': len(my_tribs), 'n_banked': len(bk), 'n_cancel': len(my_tribs) - len(bk),
                          'cancel_cause': dict(Counter(x['cause'] for x in my_tribs if x['outcome'] == 'cancelled')),
                          'banked_sum': tot_banked, 'bag_mean': (tot_banked / len(bk)) if bk else None,
                          'bags': sorted(x['bag'] for x in bk), 'marc_share': (marc / tot_banked) if tot_banked and any(types[b] == 'Marcella' for b in tb) else None,
                          'has_marc': any(types[b] == 'Marcella' for b in tb),
                          'aclass': dict(Counter(x['aclass'] for x in bk)), 'via_spawn': sum(1 for x in bk if x['via_spawn']),
                          'carried_mean': sum(x['carried'] for x in bk if x['carried']) / max(1, sum(1 for x in bk if x['carried'])),
                          'en6_banks': sum(1 for x in bk if x['en6'] > 0), 'en6_subs': sum(1 for x in my_tribs if x['en6'] > 0),
                          'deaths': len(lost), 'gems_lost': sum(lost), 'deaths_bag20': sum(1 for x in lost if x >= 20),
                          'carried_rounds': carried_rounds, 'carried_end': carried_end, 'captured': captured, 'gold': gold,
                          'locks': n_locks, 'locks_hit': n_locks_hit, 'lock_rounds': [x['r'] for x in lock_rows if x['team'] == t],
                          'beh200': dict(beh), 'half200': dict(half), 'kills': sum(kills[b] for b in tb),
                          'size': mf['size_class'], 'altars': mf['altars'], 'groups': mf['groups'], 'mono': mf['mono'], 'map_gems': mf['gems']})
    # ---------- per body
    body_rows = []
    for b in bodies:
        t = team[b]
        alive = sum(1 for r, s in S.items() if s.get(b) and s[b][7])
        st_out = Counter()
        for (r, a, j, ab) in stuns:
            if a != b:
                continue
            died3 = any(r <= x <= r + 3 for x in death_r[j])
            # target was tributing (a submit by j within its ticks before r, not landed)
            trib = False
            for (sr, sw, sat, sp) in submits:
                if sw == j and sr <= r:
                    c = S.get(sr - 1, {}).get(sw)
                    bag = c[8] if c else 0
                    tk = max(1, (bag + 9) // 10)
                    if sr + tk >= r and next((x for x in bank_by[sw] if sr <= x <= r), None) is None:
                        trib = True
            # target was fleeing (moved away from the caster in the 2 rounds before)
            st_out['n'] += 1
            st_out['kill3'] += died3
            st_out['on_tribute'] += trib
            # stunned target carried gems
            cj = S.get(r - 1, {}).get(j)
            st_out['bag_sum'] += cj[8] if cj else 0
        body_rows.append({'mid': g['mid'], 'set': g['set'], 'map': g['map'], 'team': t, 'grp': g['teams'][t]['grp'], 'res': g['teams'][t]['result'],
                          'body': b, 'champ': types[b], 'alive': alive, 'final': final, 'champs': meta['champsPerTeam'],
                          'camp_hits': dict(camp_hit[b]), 'champ_hits': dict(champ_hit[b]),
                          'casts': {f'{k[0]}:{k[1]}': v for k, v in casts[b].items()}, 'dash': dict(dash_use[b]),
                          'dash_dist_mean': (sum(dash_dist[b]) / len(dash_dist[b])) if dash_dist[b] else None,
                          'stuns': dict(st_out), 'marc_spell_dist': {str(k): v for k, v in marc_spell[b].items()},
                          'spell_kills': spell_kills[b], 'kills': kills[b], 'deaths': len(death_r[b]),
                          'banked': sum(x[1] for x in banked[b]), 'n_banks': len(banked[b]),
                          'captured': sum(cg for (cr, cg, _) in captures[b]), 'gold_cap': sum(cgold for (cr, cg, cgold) in captures[b]),
                          'shops': len(shops[b]), 'shops_field': sum(1 for (r, p) in shops[b] if p is not None and p not in spawn[t]),
                          'recalls': len(recalls[b]), 'teleports': len(tele[b]), 'lock_attacks': attacked_lock[b],
                          'fight_rounds': len(hit_given_r[b] | hit_taken_r[b]), 'farm_rounds': len(camp_r[b]),
                          'items_end': (S.get(final) or S[max(S)]).get(b, [None] * 12)[11]})
    return team_rows, trib_rows, lock_rows, body_rows


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else 'both'
    os.makedirs(OUT, exist_ok=True)
    games = load_games(which)
    print(len(games), 'games', Counter(g['set'] for g in games), flush=True)
    suffix = '' if which == 'both' else '_' + which
    fs = {n: open(f'{OUT}/{n}{suffix}.jsonl', 'w') for n in ('teams', 'tributes', 'locks', 'bodies')}
    for i, g in enumerate(games):
        try:
            tr, tb, lk, br = analyse(g)
        except Exception as ex:  # noqa: BLE001
            print('fail', g['mid'], g['map'], repr(ex), file=sys.stderr, flush=True)
            continue
        for n, rows in (('teams', tr), ('tributes', tb), ('locks', lk), ('bodies', br)):
            for x in rows:
                fs[n].write(json.dumps(x) + '\n')
        if i % 25 == 0:
            print(i, g['set'], g['map'], g['mid'][:8], flush=True)
    for f in fs.values():
        f.close()


if __name__ == '__main__':
    main()
