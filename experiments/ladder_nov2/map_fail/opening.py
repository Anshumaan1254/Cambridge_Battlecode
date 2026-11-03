#!/usr/bin/env python3
"""Opening (rounds 1-HORIZON) per body, ours and theirs: what each body walks to, hits, kills, captures; where the time goes.

    nice -n 19 python3 -I map_fail/opening.py [map ...]
    -> map_fail/out/opening_bodies.txt   per game, per body: visit sequence + time split
       map_fail/out/opening_summary.txt  per map / team aggregates, rules, examples
       map_fail/out/opening.jsonl        one row per (game, body)

Definitions (per body, rounds 1..HORIZON; positions = end of round):
  visit      consecutive hits on one camp group (a hit = Attack / Cast on one of its camps, area spells within 1); arrival = first round
             within 2 tiles of the group's tiles looking back from the first hit; kill = round all its camps are dead; capture = who took it
  d_spawn    BFS steps from the body's team spawn to the nearest tile next to the group (walls / holes / altars blocked, camps passable)
  rank       1 + number of groups with value (gems + 0.5 gold) > 0 strictly nearer the team spawn than this group
  time split dead | spawn | recall (held channel) | fight (hit / was hit by a champion) | hit (camp) | capture (on a reward tile) |
             walk-to (moving; its next camp hit / capture is within 40 rounds) | walk-home (moving, reaches own spawn before any hit) |
             flee (moving, an enemy within 6 at round start and the gap to it grows) | walk-other | wait-ready (still within 4 of a group that is
             respawning / dead, no reward) | wait-alive (still within 4 of a live group it does not hit) | idle
  abandon    an approach of >= 4 tiles that ended within 5 of a group it then left (>= 4 tiles farther within 12 rounds) without hitting it
"""
import json, os, sys
from collections import Counter, defaultdict, deque
BASE = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
sys.path.insert(0, f'{BASE}/map_fail')
from mapgroups import full_groups  # noqa: E402
from analyze import select  # noqa: E402

HORIZON = 150
LOOK = 230  # outcomes of visits that start before HORIZON are followed to this round
MAPS = ['00crater', '00gemfight', '01elk_arena', '00gem_fields', '00quarry']
GOLD_V = 0.5


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


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


def run(g):
    mid, we = g['mid'], g['we']
    d = json.load(open(f'{BASE}/dec/{mid}.json'))
    mj = json.load(open(f'{BASE}/mj/{mid}.json'))
    meta = d['meta']
    W, H = meta['width'], meta['height']
    types = {b['index']: b['type'] for b in meta['bodies']}
    team = {b['index']: b['team'] for b in meta['bodies']}
    bodies = sorted(types)
    S = {rr['r']: {c[0]: c for c in rr['ch']} for rr in d['rounds'][1:]}
    R = {rr['r']: rr for rr in d['rounds'][1:]}
    final = meta['finalRound']
    G = full_groups(g['map'], meta, mj['sym'])
    tile_group = {t: gg['id'] for gg in G for t in gg['tiles']}
    camp_at = {(c['x'], c['y']): c['index'] for c in meta['camps']}
    spawn = {0: {tuple(p) for p in mj['spawnA']}, 1: {tuple(p) for p in mj['spawnB']}}
    dist = {0: bfs(mj['rows'], spawn[0], W, H), 1: bfs(mj['rows'], spawn[1], W, H)}

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

    # group death rounds (all camps 0) and reward/capture
    dead_r = defaultdict(list)
    for gg in G:
        prev = False
        for r in range(1, min(final, LOOK + 60) + 1):
            rr = R.get(r)
            if rr is None:
                continue
            dead = all(rr['campHp'][i] == 0 for i in gg['idx'])
            if dead and not prev:
                dead_r[gg['id']].append(r)
            prev = dead

    def gstate(gid, r):
        rr = R.get(r)
        if rr is None:
            return '?'
        if any(rr['campHp'][i] > 0 for i in G[gid]['idx']):
            return 'alive'
        return 'reward' if rr['gr'][gid] else 'resp'

    # ---- events
    hits = defaultdict(list)        # body -> [(r, gid)]
    champ_given = defaultdict(set)
    champ_taken = defaultdict(set)
    moved = defaultdict(set)
    caps = []                       # (r, body, gid, gems, gold)
    recall_r = defaultdict(set)
    cancel_r = defaultdict(set)
    own_ev = defaultdict(set)       # body -> rounds with any own action event
    shops = defaultdict(list)
    deaths = defaultdict(list)      # body -> [(r, by)]
    tele = defaultdict(list)
    for r in range(1, min(final, LOOK) + 1):
        pass
    evr = defaultdict(list)
    for e in d['events']:
        if e['r'] <= LOOK and e['k'] != 'Draft champion':
            evr[e['r']].append(e)
    for r in range(1, min(final, LOOK) + 1):
        prev = S.get(r - 1) or S.get(r)
        pos = {i: ((c[3], c[4]) if c[7] else None) for i, c in prev.items()}
        for e in evr.get(r, []):
            k, who = e['k'], e.get('who')
            if who is not None and k in ('Move', 'Attack', 'Cast ability', 'Recall', 'Cancel channel', 'Place ward', 'Submit gems'):
                own_ev[who].add(r)
            if k == 'Move' and who is not None:
                moved[who].add(r)
                pos[who] = tuple(e['to'])
            elif k == 'Cast ability' and who is not None:
                P = tuple(e['to']) if 'to' in e else None
                if e.get('ability') == 6 and P is not None:
                    moved[who].add(r)
                    pos[who] = P
                if P is None:
                    continue
                rad = 1 if e.get('ability') == 3 else 0
                tg = [j for j, pj in pos.items() if pj is not None and team[j] != team[who] and cheb(pj, P) <= rad]
                if tg and e.get('ability') != 6:
                    champ_given[who].add(r)
                    for j in tg:
                        champ_taken[j].add(r)
                else:
                    gs = {tile_group[q] for q in camp_at if cheb(q, P) <= rad and q in tile_group}
                    for gid in gs:
                        hits[who].append((r, gid))
            elif k == 'Attack' and who is not None:
                P = tuple(e['to'])
                tg = [j for j, pj in pos.items() if pj == P and team[j] != team[who]]
                if tg:
                    champ_given[who].add(r)
                    champ_taken[tg[0]].add(r)
                elif P in tile_group:
                    hits[who].append((r, tile_group[P]))
            elif k == 'Recall' and who is not None:
                recall_r[who].add(r)
            elif k == 'Cancel channel' and who is not None:
                cancel_r[who].add(r)
            elif k == 'Shop' and who is not None:
                shops[who].append(r)
            elif k == 'Death':
                deaths[who].append((r, e['by']))
                pos[who] = None
            elif k in ('CaptureGems', 'CaptureGold'):
                caps.append((r, who, tile_group.get(tuple(e['at'])), e['gems'], e['gold']))
            elif k == 'Teleport complete' and who is not None:
                tele[who].append(r)
                pos[who] = tuple(e['to'])
            elif k == 'Respawn' and who is not None:
                pos[who] = tuple(e['to'])
    held = defaultdict(set)
    for b in bodies:
        for x in recall_r[b]:
            if (x + 1) in own_ev[b] or (x + 1) in cancel_r[b]:
                continue
            nxt = S.get(x + 1, {}).get(b)
            if nxt is None or not nxt[7]:
                continue
            for k2 in range(0, 7):
                held[b].add(x + k2)
                ck = S.get(x + k2 + 1, {}).get(b)
                if ck is None or not ck[7] or (ck[3], ck[4]) in spawn[team[b]]:
                    break
    capby = defaultdict(list)  # gid -> [(r, team, body, gems, gold)]
    for (r, who, gid, gems, gold) in caps:
        capby[gid].append((r, team[who], who, gems, gold))

    rows = []
    for b in bodies:
        t = team[b]
        side = 'we' if t == we else 'they'
        hs = sorted(hits[b])
        hit_rounds = defaultdict(set)
        for r, gid in hs:
            hit_rounds[r].add(gid)
        my_caps = [c for c in caps if c[1] == b]
        # next target per round: group of the next hit or capture by this body
        nxt_events = sorted([(r, gid) for r, gid in hs] + [(c[0], c[2]) for c in my_caps if c[2] is not None])
        # visits
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
            # arrival: walk back from the first hit while within 2 of the group
            a = v['first']
            while a - 1 >= 1:
                c = S.get(a - 1, {}).get(b)
                if c is None or not c[7] or gdist((c[3], c[4]), gid) > 2:
                    break
                a -= 1
            v['arrive'] = a
            kr = [x for x in dead_r[gid] if x >= v['first']]
            v['kill'] = kr[0] if kr and kr[0] <= v['last'] + 3 else None
            cs = [c for c in capby[gid] if c[0] >= v['first'] and (v['kill'] is None or c[0] <= v['kill'] + 30)]
            if v['kill'] is not None and cs:
                c0 = cs[0][0]
                same = [c for c in cs if c[0] == c0]
                v['cap_r'] = c0
                v['cap_by'] = ','.join(sorted({('us' if c[1] == we else 'them') + str(c[2]) for c in same}))
                v['my_gems'] = sum(c[3] for c in same if c[2] == b)
                v['my_gold'] = sum(c[4] for c in same if c[2] == b)
            else:
                v['cap_r'] = v['cap_by'] = None
                v['my_gems'] = v['my_gold'] = 0
            v['gems'], v['gold'] = G[gid]['gems'], G[gid]['gold']
            v['d_spawn'] = gd[t][gid]
            v['rank'] = grank[(t, gid)]
            v['types'] = ''.join({'wolf': 'W', 'elk': 'E', 'gem': 'g', 'gold': '$', 'monolith': 'M', 'golem': 'G'}[x] for x in G[gid]['types'])
            # allies of the same team hitting it in this visit
            v['team_bodies'] = sorted({bb for bb in bodies if team[bb] == t and any(v['first'] - 5 <= r <= v['last'] + 5 and gg2 == gid for r, gg2 in hits[bb])})
            v['enemy_bodies'] = sorted({bb for bb in bodies if team[bb] != t and any(v['first'] - 5 <= r <= v['last'] + 5 and gg2 == gid for r, gg2 in hits[bb])})
        # time split
        split = Counter()
        st_by_r = {}
        for r in range(1, HORIZON + 1):
            c = S.get(r, {}).get(b)
            if c is None:
                continue
            if not c[7]:
                st = 'dead'
            else:
                p = (c[3], c[4])
                pc = S.get(r - 1, {}).get(b)
                pp = (pc[3], pc[4]) if pc is not None and pc[7] else None
                if p in spawn[t] and (pp is None or pp in spawn[t] or r not in moved[b]):
                    st = 'spawn'
                elif r in held[b]:
                    st = 'recall'
                elif r in champ_given[b] or r in champ_taken[b]:
                    st = 'fight'
                elif r in hit_rounds:
                    st = 'hit'
                elif p in tile_group and gstate(tile_group[p], r) == 'reward':
                    st = 'capture'
                elif r in moved[b]:
                    # destination
                    nx = [x for x in nxt_events if r < x[0] <= r + 40]
                    home = False
                    for r2 in range(r, min(r + 40, LOOK) + 1):
                        c2 = S.get(r2, {}).get(b)
                        if c2 is None or not c2[7]:
                            break
                        if any(x[0] <= r2 for x in nx):
                            break
                        if (c2[3], c2[4]) in spawn[t]:
                            home = True
                            break
                    prevS = S.get(r - 1, {})
                    en = [(cheb(pp, (q[3], q[4])), (q[3], q[4])) for i, q in prevS.items() if q[7] and team[i] != t] if pp else []
                    fleeing = False
                    if en and pp:
                        dmin, epos = min(en)
                        if dmin <= 6 and cheb(p, epos) > dmin:
                            fleeing = True
                    if fleeing:
                        st = 'flee'
                    elif home:
                        st = 'walk-home'
                    elif nx:
                        st = 'walk-to'
                    else:
                        st = 'walk-other'
                else:
                    near = [(gdist(p, gg['id']), gg['id']) for gg in G]
                    dn, gn = min(near)
                    if dn <= 4:
                        gs_ = gstate(gn, r)
                        st = 'wait-ready' if gs_ == 'resp' else 'wait-alive' if gs_ == 'alive' else 'capture'
                    else:
                        st = 'idle'
            split[st] += 1
            st_by_r[r] = st
        # abandoned approaches
        aband = []
        for gg in G:
            if gval[gg['id']] <= 0:
                continue
            gid = gg['id']
            dl = {}
            for r in range(1, HORIZON + 13):
                c = S.get(r, {}).get(b)
                if c is not None and c[7]:
                    dl[r] = gdist((c[3], c[4]), gid)
            r = 1
            while r <= HORIZON:
                if r not in dl:
                    r += 1
                    continue
                # find a local minimum within 5 reached after an approach of >= 4
                if dl[r] <= 5 and (r - 1 not in dl or dl[r - 1] >= dl[r]) and (r + 1 not in dl or dl[r + 1] > dl[r]):
                    back = [dl[x] for x in range(max(1, r - 15), r) if x in dl]
                    fwd = [dl[x] for x in range(r + 1, r + 13) if x in dl]
                    hit_here = any(r - 15 <= x <= r + 12 and gg2 == gid for x, gg2 in hs)
                    if back and max(back) - dl[r] >= 4 and fwd and max(fwd) - dl[r] >= 4 and not hit_here:
                        aband.append((r, gid, dl[r], gstate(gid, r)))
                r += 1
        c150 = S.get(HORIZON, {}).get(b)
        rows.append({'mid': mid, 'map': g['map'], 'res': g['res'], 'side': side, 'b': b, 'champ': types[b], 'we': we,
                     'visits': visits, 'split': dict(split),
                     'first_hit': visits[0]['first'] if visits else None,
                     'first_target': (visits[0]['g'] if visits else None),
                     'first_d': (visits[0]['d_spawn'] if visits else None),
                     'first_rank': (visits[0]['rank'] if visits else None),
                     'caps': [(c[0], c[2], c[3], c[4]) for c in my_caps if c[0] <= HORIZON],
                     'recalls': sorted(x for x in recall_r[b] if x <= HORIZON and x in held[b] and (x - 1) not in held[b]),
                     'shops': [x for x in shops[b] if x <= HORIZON], 'deaths': [x for x in deaths[b] if x[0] <= HORIZON],
                     'abandon': aband, 'tele': [x for x in tele[b] if x <= HORIZON],
                     'gold150': c150[9] if c150 else None, 'gems150': c150[8] if c150 else None,
                     'items150': c150[11] if c150 else None})
    ginfo = {'mid': mid, 'map': g['map'], 'res': g['res'], 'we': we, 'opp': g['opp'], 'ver': g['ver'],
             'groups': [{'id': gg['id'], 'gems': gg['gems'], 'gold': gg['gold'], 'types': ''.join(x[0] for x in gg['types']),
                         'd_we': gd[we][gg['id']], 'd_they': gd[1 - we][gg['id']], 'rank_we': grank[(we, gg['id'])], 'rank_they': grank[(1 - we, gg['id'])],
                         'c': (round(gg['cx']), round(gg['cy']))} for gg in G],
             'first_cap': {s: min([c[0] for c in caps if (team[c[1]] == we) == (s == 'we')] or [None]) if any((team[c[1]] == we) == (s == 'we') for c in caps) else None for s in ('we', 'they')},
             'caps150': {s: [(c[0], c[1], c[2], c[3], c[4]) for c in caps if c[0] <= HORIZON and (team[c[1]] == we) == (s == 'we')] for s in ('we', 'they')}}
    return ginfo, rows


def fmt_body(rw):
    out = []
    for v in rw['visits']:
        if v['first'] > HORIZON:
            break
        s = (f"G{v['g']}[{v['types']} {v['gems']}g/{v['gold']}$ d{v['d_spawn']} #{v['rank']}] arr r{v['arrive']} hit r{v['first']}-{v['last']}"
             f"({v['n']})")
        if v['kill']:
            s += f" kill r{v['kill']}"
        if v['cap_r']:
            s += f" cap r{v['cap_r']} {v['cap_by']}" + (f" +{v['my_gems']}g/{v['my_gold']}$" if v['my_gems'] or v['my_gold'] else '')
        if len(v['team_bodies']) > 1:
            s += f" with{[x for x in v['team_bodies'] if x != rw['b']]}"
        if v['enemy_bodies']:
            s += f" CONTEST{v['enemy_bodies']}"
        out.append(s)
    extra = []
    if rw['recalls']:
        extra.append(f"recall {rw['recalls']}")
    if rw['shops']:
        extra.append(f"shop {sorted(set(rw['shops']))}")
    if rw['deaths']:
        extra.append(f"died {rw['deaths']}")
    if rw['abandon']:
        extra.append('abandon ' + ', '.join(f"G{a[1]}@r{a[0]}(d{a[2]},{a[3]})" for a in rw['abandon']))
    sp = rw['split']
    ks = ['walk-to', 'walk-home', 'walk-other', 'flee', 'hit', 'capture', 'fight', 'wait-ready', 'wait-alive', 'idle', 'recall', 'spawn', 'dead']
    split = ' '.join(f"{k}{sp.get(k, 0)}" for k in ks if sp.get(k, 0))
    return ' -> '.join(out) or '(no camp hit)', ' | '.join(extra), split


def main():
    maps = sys.argv[1:] or MAPS
    games = select(maps)
    allrows, ginfos = [], []
    with open(f'{BASE}/map_fail/out/opening_bodies.txt', 'w') as fo:
        fo.write(__doc__ + '\n')
        for g in games:
            gi, rows = run(g)
            ginfos.append(gi)
            allrows += rows
            fo.write(f"\n===== {g['map']} {g['mid']} {g['res']} ({g['ver']}) vs {g['opp']}  we = side {'AB'[g['we']]}  first capture we r{gi['first_cap']['we']} they r{gi['first_cap']['they']}\n")
            gl = sorted([x for x in gi['groups'] if x['gems'] + x['gold'] > 0], key=lambda x: x['d_we'] if x['d_we'] is not None else 999)
            fo.write('  groups by our distance: ' + '; '.join(f"G{x['id']} {x['types']} {x['gems']}g/{x['gold']}$ d{x['d_we']}/{x['d_they']}" for x in gl) + '\n')
            for side in ('we', 'they'):
                for rw in [x for x in rows if x['side'] == side]:
                    seq, extra, split = fmt_body(rw)
                    fo.write(f"  {side:4} b{rw['b']} {rw['champ'][:4]:4} {seq}\n")
                    fo.write(f"            time: {split}" + (f" | {extra}" if extra else '') + f" | r150 gold {rw['gold150']} gems {rw['gems150']}\n")
    with open(f'{BASE}/map_fail/out/opening.jsonl', 'w') as f:
        for r in allrows:
            f.write(json.dumps(r) + '\n')
    with open(f'{BASE}/map_fail/out/opening_games.jsonl', 'w') as f:
        for gi in ginfos:
            f.write(json.dumps(gi) + '\n')
    print(len(games), 'games', len(allrows), 'body rows')


if __name__ == '__main__':
    main()
