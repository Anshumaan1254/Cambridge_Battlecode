#!/usr/bin/env python3
"""Execution metrics per game, both sides, for the top-30 games and ours.  nice -n 19 python3 -I execution/metrics.py [top|v88|old|all]
Writes out/met/<key>.json (cached).  Per side ('0' / '1' = team index):
  alive        body-rounds alive;  offspawn: of them off the own spawn tiles
  stall12      body-rounds in stalls (stall.py rule: >= 12 rounds within 3 tiles of an anchor, no attack / non-dash cast / gems / gold /
               heal / tribute / held recall);  stall12_n: stalls;  stall_live: stalled rounds next to a live group (within 5) with no
               enemy within 6
  aba          A-B-A episodes: moved A->B at r, B->A at r+1 (merged runs); aba_pure: no champion hit given / taken within +-3 rounds
  rev          moves that reverse the previous move's direction within 2 rounds (delta == -prev delta); rev_pure: no hit within +-3
  passive      passive.py runs (>= 5 camp-hit rounds, no attack by the body): n, dmg, deaths (within 3 rounds of the run end)
  wake_leave   sleeping group (all camps full hp, no champion hit in the last 30 rounds) first hit by a body of this side which then
               leaves it alive: no hit on it by that body in 20 rounds and the body > 6 tiles away, group alive at that time; cost =
               passive camp hits (damage) that group lands on this side's bodies in the next 150 rounds
  deadtile     body-rounds standing still on a tile of a dead group with no reward up (holds its respawn); rewtile: still on a tile
               with the reward up for more than 7 rounds after the kill (capture takes 6)
  idle         body-rounds alive, off spawn, no move, no attack/cast/submit/ward/lock/shop/teleport, not banking, not in a held recall,
               not on a reward tile, not in a dead-tile block
  recall       bait = Recall cancelled by any own event at r+1; held = recall that survived r+1; held_cancel = held then cancelled
               (Cancel channel) before reaching spawn
  tribfail     Submit gems whose bag did not land (detect.py rule); died / other
  dash         ability-6 casts; dash_travel: no enemy within 8 at the cast; dash_wasted: travel dash followed by 8 rounds with no hit
               given / taken, camp hit, capture, bank and the body ends within 3 tiles of the landing tile
  noev         body-rounds alive with no event at all for the body (the bot issued nothing: fuel rollover, stun, or a deliberate
               stand); noev_far: of them with no enemy champion within 3 (not stunned by a melee)
  camp_given   camp hits given by camp type and attacker distance; camp_taken: camp hits taken by camp type; per-type hit ratio
  kills        group kills by this side: [gid, gems, gold, types, r_first_hit, r_kill, n_attackers, max_simultaneous]
  deaths, banked, collected (capture gems), bagloss
"""
import json, os, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h30  # noqa: E402

CAMP_RANGE = {'wolf': 3, 'elk': 4, 'golem': 4, 'monolith': 5, 'gem': 0, 'gold': 0}
STR = {'wolf': 20, 'elk': 60, 'golem': 120, 'monolith': 200}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def run(g):
    d, mj = h30.load(g)
    meta = d['meta']
    W, H = meta['width'], meta['height']
    team = {b['index']: b['team'] for b in meta['bodies']}
    types = {b['index']: b['type'] for b in meta['bodies']}
    bodies = sorted(team)
    camps = {c['index']: c for c in meta['camps']}
    camp_at = {(c['x'], c['y']): c['index'] for c in meta['camps']}
    G = h30.mapgroups.full_groups(g['map'], meta, mj['sym'])
    ngr = len(d['rounds'][1]['gr'])
    tile_group = {t: gg['id'] for gg in G for t in gg['tiles']}
    camp_group = {ci: gg['id'] for gg in G for ci in gg['idx']}
    S = {rr['r']: {c[0]: c for c in rr['ch']} for rr in d['rounds'][1:]}
    R = {rr['r']: rr for rr in d['rounds'][1:]}
    final = meta['finalRound']
    spawn = {0: {tuple(p) for p in mj['spawnA']}, 1: {tuple(p) for p in mj['spawnB']}}
    ev = defaultdict(list)
    for e in d['events']:
        if e['k'] != 'Draft champion':
            ev[e['r']].append(e)

    def gid_ok(gid):
        return gid is not None and gid < ngr

    # ------------------------------------------------------------------ event walk
    moved = defaultdict(dict)            # b -> r -> (from, to)
    hit_given = defaultdict(set)
    hit_taken = defaultdict(set)
    camp_given = defaultdict(dict)       # b -> r -> [(gid, ctype, dist)]
    camp_taken = defaultdict(dict)       # b -> r -> [(gid, ctype)]
    any_ev = defaultdict(set)            # b -> rounds with any own event
    act = defaultdict(lambda: defaultdict(set))  # b -> r -> kinds
    recalls = defaultdict(set)
    cancels = defaultdict(set)
    submits = defaultdict(list)
    banked = defaultdict(list)
    deaths = []
    dashes = defaultdict(list)           # b -> [(r, from, to)]
    caps = defaultdict(list)             # gid -> [(r, team, who, gems, gold)]
    collected = Counter()
    group_hits = defaultdict(list)       # gid -> [(r, team, who, dist)]
    for r in range(1, final + 1):
        prev = S.get(r - 1) or S.get(r)
        if prev is None:
            continue
        pos = {i: ((c[3], c[4]) if c[7] else None) for i, c in prev.items()}
        prevR = R.get(r - 1)
        for e in ev.get(r, []):
            k, who = e['k'], e.get('who')
            if k == 'Attack' and who is None and e.get('camp') is not None:
                P = tuple(e['to'])
                ci = e['camp']
                for j, pj in pos.items():
                    if pj == P:
                        camp_taken[j].setdefault(r, []).append((camp_group.get(ci), camps[ci]['type']))
                continue
            if who is None:
                continue
            if k != 'Set priority':
                any_ev[who].add(r)
            if k == 'Move':
                moved[who][r] = (tuple(e['from']) if 'from' in e else pos[who], tuple(e['to']))
                pos[who] = tuple(e['to'])
                act[who][r].add('move')
            elif k == 'Cast ability':
                ab = e.get('ability')
                if ab == 6 and 'to' in e:
                    fr = pos[who]
                    dashes[who].append((r, fr, tuple(e['to'])))
                    moved[who][r] = (fr, tuple(e['to']))
                    pos[who] = tuple(e['to'])
                    act[who][r].add('dash')
                    # HoR dash lands damage: treat as a hit if an enemy is at the landing tile
                    if types[who] == 'HeartOfRuin':
                        tg = [j for j, pj in pos.items() if pj is not None and team[j] != team[who] and j != who and cheb(pj, tuple(e['to'])) <= 1]
                        if tg:
                            hit_given[who].add(r)
                            for j in tg:
                                hit_taken[j].add(r)
                    continue
                act[who][r].add('cast')
                if 'to' not in e:
                    continue
                P = tuple(e['to'])
                rad = 1 if ab == 3 else 0
                tg = [j for j, pj in pos.items() if pj is not None and team[j] != team[who] and cheb(pj, P) <= rad]
                if tg:
                    hit_given[who].add(r)
                    for j in tg:
                        hit_taken[j].add(r)
                for q in camp_at:
                    if cheb(q, P) <= rad and (prevR is None or prevR['campHp'][camp_at[q]] > 0):
                        gid = camp_group.get(camp_at[q])
                        dist = cheb(pos[who], q) if pos[who] else 0
                        camp_given[who].setdefault(r, []).append((gid, camps[camp_at[q]]['type'], dist))
                        group_hits[gid].append((r, team[who], who, dist))
            elif k == 'Attack':
                act[who][r].add('attack')
                P = tuple(e['to'])
                tg = [j for j, pj in pos.items() if pj == P and team[j] != team[who]]
                if tg:
                    hit_given[who].add(r)
                    hit_taken[tg[0]].add(r)
                elif P in camp_at:
                    gid = camp_group.get(camp_at[P])
                    dist = cheb(pos[who], P) if pos[who] else 0
                    camp_given[who].setdefault(r, []).append((gid, camps[camp_at[P]]['type'], dist))
                    group_hits[gid].append((r, team[who], who, dist))
            elif k == 'Teleport complete':
                pos[who] = tuple(e['to'])
                act[who][r].add('tele')
            elif k == 'Teleport channel':
                act[who][r].add('tele')
            elif k == 'Respawn':
                pos[who] = tuple(e['to']) if 'to' in e else pos[who]
            elif k == 'Death':
                deaths.append(e)
                pos[who] = None
            elif k == 'Recall':
                recalls[who].add(r)
                act[who][r].add('recall')
            elif k == 'Cancel channel':
                cancels[who].add(r)
                act[who][r].add('cancel')
            elif k == 'Submit gems':
                submits[who].append(r)
                act[who][r].add('submit')
            elif k == 'Banked':
                banked[who].append((r, e['gems']))
            elif k in ('CaptureGems', 'CaptureGold'):
                gid = tile_group.get(tuple(e['at']))
                caps[gid].append((r, team[who], who, e['gems'], e['gold']))
                collected[team[who]] += e['gems']
            elif k in ('Place ward', 'Place altar lock', 'Shop', 'Consumable', 'Sell item'):
                act[who][r].add('other')
    # held recalls: survived r+1 (no own event at r+1 other than nothing)
    held = defaultdict(set)      # b -> start rounds
    held_rounds = defaultdict(set)
    held_cancel = defaultdict(list)
    bait = Counter()
    for b in bodies:
        for x in sorted(recalls[b]):
            if (x + 1) in any_ev[b]:
                bait[b] += 1
                continue
            held[b].add(x)
            done = None
            for k2 in range(1, 8):
                ck = S.get(x + k2, {}).get(b)
                if ck is None or not ck[7]:
                    break
                if (x + k2) in cancels[b]:
                    held_cancel[b].append((x, k2))
                    break
                if (ck[3], ck[4]) in spawn[team[b]]:
                    done = k2
                    break
            for k2 in range(0, (done or 1) + 1):
                held_rounds[b].add(x + k2)
    bankr = defaultdict(set)
    for b in bodies:
        for s0 in submits[b]:
            end = next((x for x, _ in banked[b] if x >= s0), None)
            if end is None or end - s0 > 40:
                end = s0
            for x in range(s0, end + 1):
                bankr[b].add(x)
    # group state per round
    gstate = {}  # (gid, r) -> 'alive' | 'reward' | 'dead'
    kill_r = defaultdict(list)  # gid -> rounds it died
    for gg in G:
        if gg['id'] >= ngr:
            continue
        prev_dead = None
        for r in range(1, final + 1):
            rr = R.get(r)
            if rr is None:
                continue
            dead = all(rr['campHp'][i] == 0 for i in gg['idx'])
            gstate[(gg['id'], r)] = 'alive' if not dead else ('reward' if rr['gr'][gg['id']] else 'dead')
            if dead and prev_dead is False:
                kill_r[gg['id']].append(r)
            prev_dead = dead

    out = {'key': g['key'], 'mid': g['mid'], 'map': g['map'], 'tag': g['tag'], 'ver': g['ver'], 'kind': g['kind'], 'final': final,
           'we': g['we'], 'winner': g['winner'], 'teams': g['teams'], 'ratings': g['ratings'], 'champs': meta['champsPerTeam'],
           'drafts': meta['drafts'], 'sub': meta['submitted'], 'sides': {}}
    ex = defaultdict(list)

    # ------------------------------------------------------------------ per body
    M = {0: Counter(), 1: Counter()}
    camp_given_t = {0: Counter(), 1: Counter()}   # (ctype, dist) -> n
    camp_taken_t = {0: Counter(), 1: Counter()}
    for b in bodies:
        t = team[b]
        m = M[t]
        # alive / off spawn / idle / noev / dead tile
        prev_c = None
        for r in range(1, final + 1):
            c = S.get(r, {}).get(b)
            if c is None or not c[7]:
                prev_c = c
                continue
            m['alive'] += 1
            p = (c[3], c[4])
            on_spawn = p in spawn[t]
            if not on_spawn:
                m['offspawn'] += 1
            if r not in any_ev[b]:
                m['noev'] += 1
                en = min((cheb(p, (q[3], q[4])) for i, q in S.get(r - 1, S[r]).items() if q[7] and team[i] != t), default=99)
                if en > 3:
                    m['noev_far'] += 1
                if not on_spawn:
                    m['noev_off'] += 1
            still = r not in moved[b]
            gid = tile_group.get(p)
            gs = gstate.get((gid, r)) if gid_ok(gid) else None
            if still and not on_spawn:
                if gs == 'dead':
                    m['deadtile'] += 1
                elif gs == 'reward':
                    kr = [x for x in kill_r[gid] if x <= r]
                    if kr and r - kr[-1] > 7:
                        m['rewtile'] += 1
                busy = (r in hit_given[b] or r in hit_taken[b] or r in camp_given[b] or r in bankr[b] or r in held_rounds[b]
                        or (act[b].get(r, set()) - {'recall', 'cancel'}))
                if not busy and gs is None:
                    m['idle'] += 1
            prev_c = c
        # stalls (stall.py rule, MIN 12)
        anchor, since, prev = None, None, None
        hits = dsh = 0
        for r in range(1, final + 2):
            c = S.get(r, {}).get(b)
            ok = c is not None and c[7] and (c[3], c[4]) not in spawn[t]
            p = (c[3], c[4]) if ok else None
            acted = r in act[b] and (act[b][r] & {'attack', 'cast', 'submit', 'tele', 'other'})
            progress = (not ok or acted or r in held_rounds[b] or r in bankr[b] or prev is None or not prev[7] or c[8] != prev[8] or c[9] != prev[9]
                        or c[5] > prev[5] + 0.02 * c[6] or anchor is None or cheb(p, anchor) > 3)
            if not progress:
                hits += r in camp_taken[b]
                dsh += r in dashes_r(dashes, b)
            if progress:
                if since is not None and r - since >= 12:
                    L = r - since
                    m['stall12'] += L
                    m['stall12_n'] += 1
                    s0 = S[since]
                    en = min((cheb(anchor, (q[3], q[4])) for i, q in s0.items() if q[7] and team[i] != t), default=99)
                    # nearest group within 5 and its state
                    best = None
                    for gg in G:
                        if gg['id'] >= ngr:
                            continue
                        dd = min(cheb(anchor, x) for x in gg['tiles'])
                        if dd <= 5 and (best is None or dd < best[0]):
                            best = (dd, gg['id'])
                    gst = gstate.get((best[1], since)) if best else None
                    if gst == 'alive' and en > 6:
                        m['stall_live'] += L
                    if gst == 'dead':
                        m['stall_dead'] += L
                    if L >= 20:
                        ex['stall'].append((t, b, types[b], since, L, anchor, en, gst, hits, dsh))
                anchor, since, hits, dsh = p, r, 0, 0
            prev = c
        # A-B-A and reversals
        mv = moved[b]
        rs = sorted(mv)
        last_aba = -9
        for r in rs:
            if (r + 1) in mv and mv[r][0] == mv[r + 1][1] and mv[r][1] != mv[r][0]:
                if r > last_aba + 1:
                    m['aba'] += 1
                    nearhit = any(x in hit_given[b] or x in hit_taken[b] for x in range(r - 3, r + 5))
                    if not nearhit:
                        m['aba_pure'] += 1
                        if len(ex['aba']) < 40:
                            c0 = S.get(r - 1, {}).get(b)
                            en = min((cheb(mv[r][0], (q[3], q[4])) for i, q in S.get(r - 1, {}).items() if q[7] and team[i] != t), default=99)
                            ex['aba'].append((t, b, types[b], r, mv[r][0], mv[r][1], en))
                last_aba = r
            pr = [x for x in (r - 1, r - 2) if x in mv]
            if pr:
                d0 = (mv[r][1][0] - mv[r][0][0], mv[r][1][1] - mv[r][0][1])
                d1 = (mv[pr[0]][1][0] - mv[pr[0]][0][0], mv[pr[0]][1][1] - mv[pr[0]][0][1])
                if d0 == (-d1[0], -d1[1]) and d0 != (0, 0):
                    m['rev'] += 1
                    if not any(x in hit_given[b] or x in hit_taken[b] for x in range(r - 3, r + 4)):
                        m['rev_pure'] += 1
        # passive runs (passive.py rule)
        atk = {r for r in act[b] if act[b][r] & {'attack', 'cast'}}
        prs = sorted(r for r in camp_taken[b] if r not in atk)
        runs, cur = [], []
        for r in prs:
            if cur and r - cur[-1] <= 3 and not any(x in atk for x in range(cur[-1] + 1, r)):
                cur.append(r)
            else:
                if cur:
                    runs.append(cur)
                cur = [r]
        if cur:
            runs.append(cur)
        for run_ in runs:
            if len(run_) < 5:
                continue
            dmg = sum(STR.get(ct, 20) for r in run_ for (gid, ct) in camp_taken[b][r])
            r1 = run_[-1]
            dd = any(e['who'] == b and r1 - 1 <= e['r'] <= r1 + 3 for e in deaths)
            m['passive_n'] += 1
            m['passive_dmg'] += dmg
            m['passive_hits'] += len(run_)
            m['passive_deaths'] += dd
            ct = Counter(ct for r in run_ for (gid, ct) in camp_taken[b][r]).most_common(1)[0][0]
            m[f'passive_{ct}'] += dmg
            if len(ex['passive']) < 40:
                c0 = S.get(run_[0] - 1, {}).get(b)
                ex['passive'].append((t, b, types[b], run_[0], r1, len(run_), dmg, ct, dd, (c0[3], c0[4]) if c0 else None))
        # recalls
        m['recall_bait'] += bait[b]
        m['recall_held'] += len(held[b])
        m['recall_held_cancel'] += len(held_cancel[b])
        # tribute failures
        for s0 in submits[b]:
            c = S.get(s0 - 1, {}).get(b) or S.get(s0, {}).get(b)
            if c is None or c[8] <= 0:
                continue
            ticks = max(1, (c[8] + 9) // 10)
            if any(s0 <= x <= s0 + ticks + 3 for x, _ in banked[b]):
                continue
            if any(s0 < x <= s0 + ticks + 3 for x in submits[b]):
                continue
            dd = any(e['who'] == b and s0 <= e['r'] <= s0 + ticks + 3 for e in deaths)
            m['tribfail'] += 1
            m['tribfail_died' if dd else 'tribfail_other'] += 1
            m['tribfail_gems'] += c[8]
        m['submits'] += len(submits[b])
        # dashes
        for (r, fr, to) in dashes[b]:
            m['dash'] += 1
            if fr is None:
                continue
            en = min((cheb(fr, (q[3], q[4])) for i, q in S.get(r - 1, {}).items() if q[7] and team[i] != t), default=99)
            if en > 8:
                m['dash_travel'] += 1
                gain = any(x in hit_given[b] or x in hit_taken[b] or x in camp_given[b] or x in bankr[b] for x in range(r, r + 9))
                gain = gain or any(c[2] == b and r <= c[0] <= r + 8 for L in caps.values() for c in L)
                c8 = S.get(r + 8, {}).get(b)
                far = c8 is not None and c8[7] and cheb((c8[3], c8[4]), to) > 3
                if not gain and not far:
                    m['dash_wasted'] += 1
                    if len(ex['dash']) < 30:
                        ex['dash'].append((t, b, types[b], r, fr, to))
        # camp hits given / taken by type
        for r, L in camp_given[b].items():
            for (gid, ct, dist) in L:
                camp_given_t[t][(ct, min(dist, 6))] += 1
        for r, L in camp_taken[b].items():
            for (gid, ct) in L:
                camp_taken_t[t][ct] += 1
        # deaths / bag
    for e in deaths:
        M[e['team']]['deaths'] += 1
        M[e['team']]['bagloss'] += e.get('bag', 0)
    for t in (0, 1):
        M[t]['collected'] = collected[t]
        M[t]['banked'] = meta['submitted'][t]

    # ------------------------------------------------------------------ wake and leave
    wl = {0: [], 1: []}
    for gg in G:
        gid = gg['id']
        if gid >= ngr or not any(ct in STR for ct in gg['types']):
            continue
        hs = sorted(group_hits[gid])
        last = -999
        i = 0
        while i < len(hs):
            r, t, who, dist = hs[i]
            rr = R.get(r - 1)
            sleeping = (r - last > 30) and rr is not None and all(rr['campHp'][ci] >= camps[ci]['hp'] - 1 for ci in gg['idx'])
            if sleeping:
                # the waker's hits on this group within the next 60 rounds
                mine = [h for h in hs if h[2] == who and r <= h[0] <= r + 60]
                last_mine = max(h[0] for h in mine)
                chk = last_mine + 20
                alive = gstate.get((gid, min(chk, final))) == 'alive'
                c = S.get(min(chk, final), {}).get(who)
                away = c is None or not c[7] or min(cheb((c[3], c[4]), x) for x in gg['tiles']) > 6
                killed_before = any(r <= k <= chk for k in kill_r[gid])
                if alive and away and not killed_before:
                    # cost: passive damage this group lands on the waker's team in the next 150 rounds
                    cost = 0
                    for b2 in bodies:
                        if team[b2] != t:
                            continue
                        for x in range(r, min(final, r + 150) + 1):
                            if x in camp_taken[b2] and not any(y in camp_given[b2] and any(q[0] == gid for q in camp_given[b2][y]) for y in (x - 2, x - 1, x)):
                                cost += sum(STR.get(ct, 20) for (g2, ct) in camp_taken[b2][x] if g2 == gid)
                    teamhit = any(h[1] == t and h[2] != who and r <= h[0] <= chk for h in hs)
                    wl[t].append({'g': gid, 'types': ''.join(x[0] for x in gg['types']), 'gems': gg['gems'], 'b': who, 'champ': types[who],
                                  'r': r, 'last': last_mine, 'dist': dist, 'cost': cost, 'teamhit': teamhit})
            last = r
            i += 1
    for t in (0, 1):
        M[t]['wake_leave'] = len(wl[t])
        M[t]['wake_leave_cost'] = sum(x['cost'] for x in wl[t])
        M[t]['wake_leave_solo'] = sum(1 for x in wl[t] if not x['teamhit'])

    # ------------------------------------------------------------------ group kills: attackers, duration
    kills = {0: [], 1: []}
    for gid, krs in kill_r.items():
        gg = G[gid]
        for kr in krs:
            hs = [h for h in group_hits[gid] if h[0] <= kr]
            if not hs:
                continue
            # the kill sequence: hits going back from kr with gaps <= 15 rounds
            seq = [hs[-1]]
            for h in reversed(hs[:-1]):
                if seq[-1][0] - h[0] <= 15:
                    seq.append(h)
                else:
                    break
            kt = Counter(h[1] for h in seq).most_common(1)[0][0]
            mine = [h for h in seq if h[1] == kt]
            atk_b = sorted({h[2] for h in mine})
            r0 = min(h[0] for h in mine)
            per_r = Counter(h[0] for h in mine)
            sim = max(len({h[2] for h in mine if h[0] == x}) for x in per_r)
            both = len({h[1] for h in seq}) > 1
            cs = [c for c in caps.get(gid, []) if c[0] >= kr]
            taken_by = None if not cs else ('same' if cs[0][1] == kt else 'other')
            kills[kt].append([gid, gg['gems'], gg['gold'], ''.join(x[0] for x in gg['types']), r0, kr, len(atk_b), sim, both, taken_by,
                              cs[0][0] - kr if cs else None])
    for t in (0, 1):
        M[t]['kills'] = len(kills[t])
        M[t]['kill_gems'] = sum(k[1] for k in kills[t])
    for t in (0, 1):
        out['sides'][str(t)] = dict(M[t])
        out['sides'][str(t)]['camp_given'] = {f'{k[0]}@{k[1]}': v for k, v in camp_given_t[t].items()}
        out['sides'][str(t)]['camp_taken'] = dict(camp_taken_t[t])
        out['sides'][str(t)]['kill_list'] = kills[t]
        out['sides'][str(t)]['wake_list'] = wl[t]
    out['ex'] = {k: v for k, v in ex.items()}
    return out


def dashes_r(dashes, b):
    return {x[0] for x in dashes[b]}


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    gs = []
    if which in ('top', 'all'):
        gs += h30.top_games()
    if which in ('v88', 'old', 'all'):
        gs += h30.our_games('all' if which == 'all' else which)
    need = {}
    for g in gs:
        if g['map'] not in h30.mapgroups.HALF and g['map'] not in need:
            need[g['map']] = g['replay']
    h30.ensure_groups(need)
    os.makedirs(f'{h30.EXE}/out/met', exist_ok=True)
    n = 0
    for g in gs:
        f = f"{h30.EXE}/out/met/{g['key']}.json"
        if os.path.exists(f):
            continue
        try:
            row = run(g)
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            print('FAIL', g['key'], repr(e)[:200], flush=True)
            continue
        json.dump(row, open(f, 'w'))
        n += 1
        if n % 20 == 0:
            print(n, g['key'], flush=True)
    print('done', n)


if __name__ == '__main__':
    main()
