#!/usr/bin/env python3
"""Per-map failure analysis: our RANKED games since 2026-11-02T00:00Z on the worst maps.

Usage:  nice -n 19 python3 -I map_fail/analyze.py [map ...]
Writes map_fail/out/games.jsonl (one row per game: timeline, deaths, time use, flagged episodes) and
       map_fail/out/deaths.jsonl (our and their deaths with context; extract.py's death rows + location / group / activity).

Body states per round (ours and theirs), first match wins:
  dead | spawn (on own spawn tile) | bank (tribute channel) | recall (held recall channel) | fight (hit or was hit by an enemy
  champion this round) | farm (hit a camp) | capture (standing on a tile of a dead group whose reward is up) | walk (moved) |
  block (standing still on a tile of a dead, captured group: holds its respawn when due) | idle (alive, still, none of these)
Episodes flagged:
  idle10   >= 10 consecutive rounds still on one tile, away from spawn, no action at all (no attack, cast, submit, recall, ward)
  osc      a 20-round window with >= 10 moves over <= 4 distinct tiles, no camp/champion hit given or taken
  block    rounds a group's respawn was overdue (capture + respawn time passed) while one of our bodies stood on its tiles
  bag      >= 150 consecutive rounds carrying >= 20 gems (no tribute)
  rloop    >= 3 held recalls by one body within 40 rounds that never reached spawn
"""
import json, os, sys
from collections import defaultdict, Counter

BASE = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
sys.path.insert(0, f'{BASE}/agent_fights')
sys.path.insert(0, f'{BASE}/map_fail')
import extract as X  # noqa: E402
from mapgroups import full_groups  # noqa: E402

ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
MAPS = ['00crater', '00gem_fields', '00gemfight', '01elk_arena', '01islands', '00quarry', '00oasis', '01corridors']
SINCE = '2026-11-02T00:00'
SWITCH = [('2026-11-02T21:15:46', 'v84'), ('2026-11-03T01:00:56', 'v85'), ('2026-11-03T01:21:19', 'v86'), ('9999', 'v87')]
CHECK = (200, 400, 600, 800, 1000)
OUT = f'{BASE}/map_fail/out'


def version(created):
    for t, v in SWITCH:
        if created < t:
            return v
    return 'v87'


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def select(maps):
    rows = [json.loads(l) for l in open(f'{BASE}/matches_me.jsonl')]
    out = []
    for m in rows:
        if m['kind'] != 'ranked' or m['status'] != 'finished' or m['createdAt'] < SINCE or m['map'] not in maps:
            continue
        us = [t for t in m['teams'] if t['teamId'] == ME][0]
        th = [t for t in m['teams'] if t['teamId'] != ME][0]
        if not os.path.exists(f"{BASE}/dec/{m['matchId']}.json"):
            print('not decoded', m['matchId'], file=sys.stderr)
            continue
        out.append({'mid': m['matchId'], 'map': m['map'], 'we': 0 if us['side'] == 'a' else 1, 'res': 'W' if us['result'] == 'win' else 'L',
                    'opp': th['name'], 'created': m['createdAt'], 'ver': version(m['createdAt'])})
    return sorted(out, key=lambda g: (g['map'], g['created']))


def analyse(g):
    mid, we = g['mid'], g['we']
    d = json.load(open(f'{BASE}/dec/{mid}.json'))
    mj = json.load(open(f'{BASE}/mj/{mid}.json'))
    meta = d['meta']
    W, H = meta['width'], meta['height']
    types = {b['index']: b['type'] for b in meta['bodies']}
    team = {b['index']: b['team'] for b in meta['bodies']}
    bodies = sorted(types)
    final = meta['finalRound']
    S = {rr['r']: {c[0]: c for c in rr['ch']} for rr in d['rounds'][1:]}
    R = {rr['r']: rr for rr in d['rounds'][1:]}
    G = full_groups(g['map'], meta, mj['sym'])
    tile_group = {t: gg['id'] for gg in G for t in gg['tiles']}
    camp_tiles = set(tile_group)
    spawn = {0: {tuple(p) for p in mj['spawnA']}, 1: {tuple(p) for p in mj['spawnB']}}
    altars = [(x, y) for y in range(H) for x in range(W) if mj['rows'][y][x] == 'A']
    mf, dA, dB = X.map_features(mj)

    def dhome(t, p):
        dm = dA if t == 0 else dB
        x, y = p
        return dm[y][x] if 0 <= x < W and 0 <= y < H and dm[y][x] >= 0 else None

    def band(t, p):
        a, b = dhome(t, p), dhome(1 - t, p)
        if a is None or b is None or a + b == 0:
            return '?'
        f = a / (a + b)
        return 'own' if f < 0.42 else 'mid' if f <= 0.58 else 'their'

    def near_group(p, rad=5):
        best = None
        for gg in G:
            dd = min(cheb(p, t) for t in gg['tiles'])
            if dd <= rad and (best is None or dd < best[0]):
                best = (dd, gg['id'])
        return best[1] if best else None

    # ---------- group state per round: dead (all camps hp 0), reward up (gr), overdue respawn
    gstate = {}  # (gid, r) -> 'alive' | 'reward' | 'resp' (dead, reward taken) | 'over' (respawn overdue)
    gcap = defaultdict(list)  # gid -> rounds the reward was taken
    for gg in G:
        prev_gr = 0
        t_cap = None
        for r in range(1, final + 1):
            rr = R.get(r)
            if rr is None:
                continue
            dead = all(rr['campHp'][i] == 0 for i in gg['idx'])
            gr = rr['gr'][gg['id']]
            if prev_gr and not gr:
                t_cap = r
                gcap[gg['id']].append(r)
            if not dead:
                st = 'alive'
                t_cap = None
            elif gr:
                st = 'reward'
            elif t_cap is not None and r >= t_cap + gg['resp']:
                st = 'over'
            else:
                st = 'resp'
            gstate[(gg['id'], r)] = st
            prev_gr = gr

    # ---------- events per round
    ev = defaultdict(list)
    for e in d['events']:
        if e['k'] != 'Draft champion':
            ev[e['r']].append(e)
    camp_at = {(c['x'], c['y']): c['index'] for c in meta['camps']}

    act = defaultdict(lambda: defaultdict(set))  # body -> round -> set of action kinds
    moved = defaultdict(set)
    champ_hit_given = defaultdict(set)
    champ_hit_taken = defaultdict(set)
    camp_hit_taken = defaultdict(set)
    camp_hit_given = defaultdict(set)
    camp_dmg_taken = defaultdict(float)
    captures = []  # (r, body, gems, gold, gid)
    banked = []
    deaths_ev = []
    recalls = defaultdict(list)
    cancels = defaultdict(set)
    tele = Counter()
    locks = Counter()
    wards = Counter()
    shop_rounds = defaultdict(list)
    for r in range(1, final + 1):
        prev = S.get(r - 1) or S.get(r)
        if prev is None:
            continue
        pos = {i: ((c[3], c[4]) if c[7] else None) for i, c in prev.items()}
        for e in ev.get(r, []):
            k, who = e['k'], e.get('who')
            if k == 'Move' and who is not None:
                moved[who].add(r)
                pos[who] = tuple(e['to'])
                act[who][r].add('move')
            elif k == 'Cast ability' and who is not None:
                act[who][r].add('cast')
                if e.get('ability') == 6 and 'to' in e:
                    moved[who].add(r)
                    pos[who] = tuple(e['to'])
                P = tuple(e['to']) if 'to' in e else None
                if P is not None:
                    tg = [j for j, pj in pos.items() if pj is not None and team[j] != team[who] and cheb(pj, P) <= (1 if e.get('ability') == 3 else 0)]
                    if tg:
                        champ_hit_given[who].add(r)
                        for j in tg:
                            champ_hit_taken[j].add(r)
                    elif any(cheb(P, q) <= 1 for q in camp_at):
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
                    camp_hit_given[who].add(r)
            elif k in ('Teleport complete',) and who is not None:
                pos[who] = tuple(e['to'])
                tele[team[who]] += 1
                act[who][r].add('tele')
            elif k == 'Teleport channel' and who is not None:
                act[who][r].add('telechan')
            elif k == 'Respawn' and who is not None:
                pos[who] = tuple(e['to'])
            elif k == 'Death':
                deaths_ev.append(e)
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
                captures.append((r, who, e['gems'], e['gold'], tile_group.get(p)))
            elif k == 'Place altar lock' and who is not None:
                locks[team[who]] += 1
                act[who][r].add('lock')
            elif k == 'Place ward' and who is not None:
                wards[team[who]] += 1
                act[who][r].add('ward')
            elif k == 'Shop' and who is not None:
                shop_rounds[who].append(r)
    # tribute channel rounds: from Submit gems to the Banked event of that body (or death / 12 rounds)
    bank_rounds = defaultdict(set)
    bk_by = defaultdict(list)
    for (r, who, gems) in banked:
        bk_by[who].append(r)
    for b in bodies:
        subs = sorted(r for r in act[b] if 'submit' in act[b][r])
        for s0 in subs:
            end = next((x for x in bk_by[b] if x >= s0), None)
            if end is None or end - s0 > 40:
                end = s0
            for x in range(s0, end + 1):
                bank_rounds[b].add(x)
    # held recalls: the channel survived the next round (no own action next round)
    held = defaultdict(list)
    recall_rounds = defaultdict(set)
    rec_out = []
    for b, rs in recalls.items():
        for x in rs:
            nxt = S.get(x + 1, {}).get(b)
            if nxt is None or not nxt[7]:
                continue
            # fake recall: started at a turn end and cancelled at the next turn start (any own event next round: a new
            # recall, a cancel, a move, an attack...). Same rule as extract.py's real_recalls.
            if act[b].get(x + 1) or (x + 1) in cancels[b]:
                continue
            held[b].append(x)
            done = None
            for k2 in range(1, 8):
                ck = S.get(x + k2, {}).get(b)
                if ck and ck[7] and (ck[3], ck[4]) in spawn[team[b]]:
                    done = k2
                    break
            for k2 in range(0, (done or 1) + 1):
                recall_rounds[b].add(x + k2)
            hit = any((x + k2) in champ_hit_taken[b] or (x + k2) in camp_hit_taken[b] for k2 in range(0, 6))
            rec_out.append({'b': b, 'r': x, 'done': done, 'hit': hit})

    # ---------- per body state per round
    states = {b: {} for b in bodies}
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
            gid = tile_group.get(p)
            gs = gstate.get((gid, r)) if gid is not None else None
            if p in spawn[t]:
                st = 'spawn'
            elif r in bank_rounds[b]:
                st = 'bank'
            elif r in recall_rounds[b]:
                st = 'recall'
            elif r in champ_hit_given[b] or r in champ_hit_taken[b]:
                st = 'fight'
            elif r in camp_hit_given[b]:
                st = 'farm'
            elif gs == 'reward':
                st = 'capture'
            elif r in moved[b]:
                st = 'walk'
            elif gs in ('resp', 'over'):
                st = 'block'
            else:
                st = 'idle'
            states[b][r] = st

    # ---------- episodes
    eps = []
    for b in bodies:
        t = team[b]
        side = 'we' if t == we else 'they'
        # idle runs: still on one tile, away from spawn, no action of any kind, 10+ rounds
        run = []
        for r in range(1, final + 2):
            c = S.get(r, {}).get(b)
            ok = (c is not None and c[7] and (c[3], c[4]) not in spawn[t] and states[b].get(r) in ('idle', 'block')
                  and not (act[b].get(r, set()) - {'recall'}))
            if ok and run and (S[run[-1]][b][3], S[run[-1]][b][4]) == (c[3], c[4]) and r == run[-1] + 1:
                run.append(r)
                continue
            if len(run) >= 10:
                r0 = run[0]
                c0 = S[r0][b]
                p = (c0[3], c0[4])
                en = [cheb(p, (q[3], q[4])) for i, q in S[r0].items() if q[7] and team[i] != t]
                al = [cheb(p, (q[3], q[4])) for i, q in S[r0].items() if q[7] and team[i] == t and i != b]
                ng = near_group(p, 3)
                eps.append({'kind': 'idle10', 'side': side, 'b': b, 'champ': types[b], 'r': r0, 'len': len(run), 'at': p,
                            'band': band(t, p), 'hp': round(c0[5] / max(1, c0[6]), 2), 'gems': c0[8],
                            'enemy_d': min(en) if en else None, 'ally_d': min(al) if al else None,
                            'group': ng, 'gstate': gstate.get((ng, r0)) if ng is not None else None,
                            'on_group': tile_group.get(p), 'altar_d': min((cheb(p, a) for a in altars), default=None),
                            'held_recall': any(r0 - 1 <= x <= run[-1] for x in held[b])})
            run = [r] if ok else []
        # oscillation
        r = 1
        while r <= final - 20:
            win = range(r, r + 20)
            cs = [S.get(x, {}).get(b) for x in win]
            if all(c is not None and c[7] and (c[3], c[4]) not in spawn[t] for c in cs):
                nm = sum(1 for x in win if x in moved[b])
                tiles = {(c[3], c[4]) for c in cs}
                hits = any(x in champ_hit_given[b] or x in champ_hit_taken[b] or x in camp_hit_given[b] or x in camp_hit_taken[b] for x in win)
                if nm >= 10 and len(tiles) <= 4 and not hits:
                    # extend
                    r1 = r + 20
                    while r1 <= final:
                        c = S.get(r1, {}).get(b)
                        if not c or not c[7] or (c[3], c[4]) not in tiles or r1 in champ_hit_given[b] or r1 in champ_hit_taken[b] or r1 in camp_hit_given[b]:
                            break
                        r1 += 1
                    c0 = cs[0]
                    p = (c0[3], c0[4])
                    en = [cheb(p, (q[3], q[4])) for i, q in S[r].items() if q[7] and team[i] != t]
                    ng = near_group(p, 4)
                    eps.append({'kind': 'osc', 'side': side, 'b': b, 'champ': types[b], 'r': r, 'len': r1 - r, 'tiles': sorted(tiles),
                                'band': band(t, p), 'hp': round(c0[5] / max(1, c0[6]), 2), 'gems': c0[8],
                                'enemy_d': min(en) if en else None, 'group': ng,
                                'gstate': gstate.get((ng, r)) if ng is not None else None,
                                'moves': sum(1 for x in range(r, r1) if x in moved[b])})
                    r = r1
                    continue
            r += 1
        # bag carried
        run0 = None
        for r in range(1, final + 2):
            c = S.get(r, {}).get(b)
            carrying = c is not None and c[7] and c[8] >= 20 and r not in bank_rounds[b]
            if carrying and run0 is None:
                run0 = r
            if not carrying and run0 is not None:
                if r - run0 >= 150:
                    cl = S.get(r - 1, {}).get(b)
                    eps.append({'kind': 'bag', 'side': side, 'b': b, 'champ': types[b], 'r': run0, 'len': r - run0,
                                'gems_end': cl[8] if cl else None, 'ended': 'death' if (c is not None and not c[7]) else ('bank' if r in bank_rounds[b] else 'other')})
                run0 = None
        # recall loops
        fails = [o for o in rec_out if o['b'] == b and o['done'] is None]
        for i in range(len(fails)):
            grp = [o for o in fails[i:] if o['r'] - fails[i]['r'] <= 40]
            if len(grp) >= 3 and (i == 0 or fails[i]['r'] - fails[i - 1]['r'] > 40):
                eps.append({'kind': 'rloop', 'side': side, 'b': b, 'champ': types[b], 'r': fails[i]['r'], 'n': len(grp),
                            'hit': sum(o['hit'] for o in grp)})
    # respawn blocking (group respawn overdue while a body stands on its tiles)
    blocks = []
    for gg in G:
        cur = None
        for r in range(1, final + 1):
            if gstate.get((gg['id'], r)) != 'over':
                if cur:
                    blocks.append(cur)
                    cur = None
                continue
            occ = [i for i, c in S.get(r - 1, {}).items() if c[7] and (c[3], c[4]) in gg['tiles']]
            if cur is None:
                cur = {'kind': 'block', 'group': gg['id'], 'r': r, 'len': 0, 'by_we': Counter(), 'by_they': Counter(), 'gems': gg['gems']}
            cur['len'] += 1
            for i in occ:
                cur['by_we' if team[i] == we else 'by_they'][i] += 1
        if cur:
            blocks.append(cur)
    for bl in blocks:
        bl['by_we'] = dict(bl['by_we'])
        bl['by_they'] = dict(bl['by_they'])
        bl['side'] = 'we' if bl['by_we'] and not bl['by_they'] else 'they' if bl['by_they'] and not bl['by_we'] else 'both' if bl['by_we'] else 'none'
        bl['types'] = ''.join(t[0] for t in G[bl['group']]['types'])
        eps.append(bl)

    # ---------- timeline
    sub = {r: R[r]['sub'] for r in R}
    col = {0: [], 1: []}
    for (r, who, gems, gold, gid) in captures:
        col[team[who]].append((r, gems, gold, gid))
    lost = {0: [], 1: []}
    for e in deaths_ev:
        lost[e['team']].append((e['r'], e['bag']))

    def at(r):
        rr = min(r, final)
        s = sub.get(rr) or sub[max(sub)]
        return {'bank_we': s[we], 'bank_they': s[1 - we],
                'col_we': sum(x[1] for x in col[we] if x[0] <= r), 'col_they': sum(x[1] for x in col[1 - we] if x[0] <= r),
                'lost_we': sum(x[1] for x in lost[we] if x[0] <= r), 'lost_they': sum(x[1] for x in lost[1 - we] if x[0] <= r),
                'deaths_we': sum(1 for x in lost[we] if x[0] <= r), 'deaths_they': sum(1 for x in lost[1 - we] if x[0] <= r)}
    tl = {r: at(r) for r in CHECK}
    tl['final'] = at(final)
    winner = we if g['res'] == 'W' else 1 - we
    last_tie = 0
    for r in sorted(sub):
        if sub[r][1 - winner] >= sub[r][winner] and sub[r][winner] > 0:
            last_tie = r
    # the round the eventual loser fell 150+ behind for good (banked + carried)
    def total(r, t):
        s = S.get(r, {})
        return sub[r][t] + sum(c[8] for i, c in s.items() if team[i] == t and c[7])
    behind = None
    for r in sorted(sub, reverse=True):
        if total(r, winner) - total(r, 1 - winner) < 150:
            behind = r + 1
            break
    # group captures by team
    gcap_team = defaultdict(lambda: [0, 0, 0, 0])  # gid -> [we n, we gems, they n, they gems]
    for (r, who, gems, gold, gid) in captures:
        if gid is None:
            continue
        k = 0 if team[who] == we else 2
        gcap_team[gid][k] += 1
        gcap_team[gid][k + 1] += gems
    # ---------- time use
    use = {'we': Counter(), 'they': Counter()}
    for b in bodies:
        side = 'we' if team[b] == we else 'they'
        for r, st in states[b].items():
            use[side][st] += 1
    # camp damage taken while not farming ("passing" camps): camp hits on a body that hit no camp in the last 3 rounds
    passing = {'we': 0, 'they': 0}
    for b in bodies:
        side = 'we' if team[b] == we else 'they'
        for r in camp_hit_taken[b]:
            if not any(x in camp_hit_given[b] for x in range(r - 3, r + 1)):
                passing[side] += 1
    # ---------- deaths (extract.py rows + context)
    drows, frows, grow, _, _, _, _ = X.process(mid, we, {'res': g['res'], 'map': g['map'], 'opp': g['opp']})
    dl = []
    for dd in drows:
        b = dd['body']
        r = dd['r']
        p = (dd['x'], dd['y'])
        last5 = range(r - 5, r + 1)
        acts = Counter()
        for x in last5:
            st = states[b].get(x)
            if st:
                acts[st] += 1
        farm5 = any(x in camp_hit_given[b] for x in last5)
        fight5 = any(x in champ_hit_given[b] for x in last5)
        took5 = any(x in champ_hit_taken[b] for x in last5)
        # recall = a REAL recall (extract.py: channel held through the next round) in the last 6 rounds; the per-turn bait recall
        # (g17_bait: recall at turn end, cancel at the next turn start) is not one
        ctx = ('camp' if dd['killer'] == 'camp' else
               'recall' if dd['recall6'] > 0 else 'bank' if acts.get('bank') else
               'farm->jumped' if farm5 and not fight5 else 'farm+fight' if farm5 else
               'fight' if fight5 else 'caught' if took5 else 'other')
        ng = near_group(p, 5)
        dl.append(dict(dd, band=band(team[b], p), group=ng,
                       gtypes=(''.join(t[0] for t in G[ng]['types']) if ng is not None else None),
                       ggems=(G[ng]['gems'] if ng is not None else None), ctx=ctx, acts5=dict(acts),
                       version=g['ver']))
    ours = [x for x in dl if x['side'] == 'we']
    theirs = [x for x in dl if x['side'] == 'they']
    row = dict(g, final=final, sub_we=meta['submitted'][we], sub_they=meta['submitted'][1 - we],
               draft_we=meta['drafts'][we], draft_they=meta['drafts'][1 - we], champs=meta['champsPerTeam'],
               tl=tl, last_tie=last_tie, behind150=behind,
               deaths_we=len(ours), deaths_they=len(theirs),
               death_ctx_we=dict(Counter(x['ctx'] for x in ours)), death_ctx_they=dict(Counter(x['ctx'] for x in theirs)),
               death_band_we=dict(Counter(x['band'] for x in ours)),
               death_killer_we=dict(Counter(x['killer'] for x in ours)),
               use_we=dict(use['we']), use_they=dict(use['they']), passing_camp_hits=passing,
               gcap={str(k): v for k, v in gcap_team.items()},
               groups=[{'id': gg['id'], 'gems': gg['gems'], 'gold': gg['gold'], 'resp': gg['resp'], 'types': ''.join(t[0] for t in gg['types']),
                        'c': (round(gg['cx']), round(gg['cy'])), 'band_we': band(we, (round(gg['cx']), round(gg['cy'])))} for gg in G],
               teleports={'we': tele[we], 'they': tele[1 - we]}, locks={'we': locks[we], 'they': locks[1 - we]},
               wards={'we': wards[we], 'they': wards[1 - we]},
               held_recalls={'we': sum(len(held[b]) for b in bodies if team[b] == we), 'they': sum(len(held[b]) for b in bodies if team[b] != we)},
               recall_fail={'we': sum(1 for o in rec_out if team[o['b']] == we and o['done'] is None),
                            'they': sum(1 for o in rec_out if team[o['b']] != we and o['done'] is None)},
               banks={'we': sum(1 for x in banked if team[x[1]] == we), 'they': sum(1 for x in banked if team[x[1]] != we)},
               n_fights=grow['n_fights'], n_exch=grow['n_exch'],
               episodes=eps)
    return row, dl


def main():
    maps = sys.argv[1:] or MAPS
    os.makedirs(OUT, exist_ok=True)
    games = select(maps)
    print(len(games), 'games', Counter(g['map'] for g in games), flush=True)
    with open(f'{OUT}/games.jsonl', 'w') as fg, open(f'{OUT}/deaths.jsonl', 'w') as fd:
        for i, g in enumerate(games):
            row, dl = analyse(g)
            fg.write(json.dumps(row) + '\n')
            for x in dl:
                fd.write(json.dumps(x) + '\n')
            print(i, g['map'], g['mid'][:8], g['res'], f"{row['sub_we']}-{row['sub_they']}", 'deaths', row['deaths_we'], row['deaths_they'], flush=True)


if __name__ == '__main__':
    main()
