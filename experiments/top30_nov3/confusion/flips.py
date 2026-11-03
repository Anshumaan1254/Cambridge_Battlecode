#!/usr/bin/env python3
"""Confusion stream: per-body flip episodes (wasted loops) + per-champion time budget.
   nice -n 19 python3 -I confusion/flips.py <part> <nparts> [top_limit]
Writes confusion/out/fl/<key>.json (cached).

FLIP / WASTED LOOP: body at round r back within 1 tile of where it was at round r-k (k = 2..12) after an excursion of >= 1 tile, with
>= 2 move-rounds in (r-k, r] and no productive action in the loop (attack, non-dash cast, camp hit, capture, submit/bank, shop,
teleport, lock).  Every move-round inside such a loop is a wasted round; contiguous wasted rounds form one episode.  The episode is
classified by the state at its first round (priority order):
  FIGHT     champion hit given / taken within [r0-2, r1+2]         (kiting / dancing in a fight; reported, not counted as confusion)
  ENEMY6    nearest enemy champion <= 6                               (combat / safety hysteresis)
  ENEMY12   nearest enemy champion 7..12                              (safety radius / danger fields)
  CAMPAGGRO camp hits taken inside the loop, none given               (walked into a camp's reach and back)
  RECALL    a held recall / cancel inside the loop (non-bait)
  BAG       bag >= 30 gems                                            (bank / tribute indecision)
  LOWHP     hp < 45 %                                                 (home_trip / heal indecision)
  SPAWN     within 4 of own spawn                                     (shop / escort_wait / respawn)
  DEADGRP   within 4 of a group that is dead (respawning) or reward up (wait_group / capture dance)
  LIVEGRP   within 4 of a live group not hit in the loop             (approach-abort: join limits, avoid bans)
  OPEN      else (target switch in the open)
ACTIVITY per alive body-round: bank > recall > capture > fight > camp > spawn > walk_bag > walk > wait (+ dead).
"""
import json, os, sys, zlib
from collections import Counter, defaultdict
sys.path.insert(0, '/home/claude/cambridge_battlecode/experiments/top30_nov3/execution')
import h30  # noqa: E402

OUT = '/home/claude/cambridge_battlecode/experiments/top30_nov3/confusion/out/fl'
STR = {'wolf': 20, 'elk': 60, 'golem': 120, 'monolith': 200}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def gclass(gg):
    return 'small' if gg['gems'] <= 12 else ('mid' if gg['gems'] <= 40 else 'big')


def run(g):
    d, mj = h30.load(g)
    meta = d['meta']
    team = {b['index']: b['team'] for b in meta['bodies']}
    types = {b['index']: b['type'] for b in meta['bodies']}
    bodies = sorted(team)
    camps = {c['index']: c for c in meta['camps']}
    camp_at = {(c['x'], c['y']): c['index'] for c in meta['camps']}
    G = h30.mapgroups.full_groups(g['map'], meta, mj['sym'])
    ngr = len(d['rounds'][1]['gr'])
    G = [gg for gg in G if gg['id'] < ngr]
    tile_group = {t: gg['id'] for gg in G for t in gg['tiles']}
    camp_group = {ci: gg['id'] for gg in G for ci in gg['idx']}
    GB = {gg['id']: gg for gg in G}
    S = {rr['r']: {c[0]: c for c in rr['ch']} for rr in d['rounds'][1:]}
    R = {rr['r']: rr for rr in d['rounds'][1:]}
    final = meta['finalRound']
    spawn = {0: [tuple(p) for p in mj['spawnA']], 1: [tuple(p) for p in mj['spawnB']]}
    spawnset = {t: set(v) for t, v in spawn.items()}
    ev = defaultdict(list)
    altars = set()
    for e in d['events']:
        if e['k'] != 'Draft champion':
            ev[e['r']].append(e)
        if e['k'] in ('Submit gems', 'Place altar lock') and 'to' in e:
            altars.add(tuple(e['to']))
    hit_given = defaultdict(set)
    hit_taken = defaultdict(set)
    camp_given = defaultdict(dict)
    camp_taken = defaultdict(set)
    prod = defaultdict(set)
    any_ev = defaultdict(set)
    recalls = defaultdict(set)
    cancels = defaultdict(set)
    submits = defaultdict(list)
    banked = defaultdict(list)
    caps = []
    deaths = []
    opens = []          # (r, attacker, target)
    last_ch = defaultdict(lambda: -999)   # body -> last round of a champion hit given/taken
    group_hits = defaultdict(list)        # gid -> [(r, team, who)]
    tele = defaultdict(set)
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
                for j, pj in pos.items():
                    if pj == P:
                        camp_taken[j].add(r)
                continue
            if who is None:
                continue
            if k != 'Set priority':
                any_ev[who].add(r)
            tg = []
            if k == 'Move':
                pos[who] = tuple(e['to'])
            elif k == 'Cast ability':
                ab = e.get('ability')
                if ab == 6 and 'to' in e:
                    pos[who] = tuple(e['to'])
                    if types[who] == 'HeartOfRuin':
                        tg = [j for j, pj in pos.items() if pj is not None and team[j] != team[who] and cheb(pj, pos[who]) <= 1]
                else:
                    prod[who].add(r)
                    if 'to' in e:
                        P = tuple(e['to'])
                        rad = 1 if ab == 3 else 0
                        tg = [j for j, pj in pos.items() if pj is not None and team[j] != team[who] and cheb(pj, P) <= rad]
                        for q in camp_at:
                            if cheb(q, P) <= rad and (prevR is None or prevR['campHp'][camp_at[q]] > 0):
                                gid = camp_group.get(camp_at[q])
                                camp_given[who].setdefault(r, set()).add(gid)
                                group_hits[gid].append((r, team[who], who))
            elif k == 'Attack':
                prod[who].add(r)
                P = tuple(e['to'])
                tg = [j for j, pj in pos.items() if pj == P and team[j] != team[who]]
                if not tg and P in camp_at:
                    gid = camp_group.get(camp_at[P])
                    camp_given[who].setdefault(r, set()).add(gid)
                    group_hits[gid].append((r, team[who], who))
            elif k in ('Teleport complete', 'Teleport channel'):
                if k == 'Teleport complete':
                    pos[who] = tuple(e['to'])
                prod[who].add(r)
                tele[who].add(r)
            elif k == 'Death':
                deaths.append(e)
                pos[who] = None
            elif k == 'Recall':
                recalls[who].add(r)
            elif k == 'Cancel channel':
                cancels[who].add(r)
            elif k == 'Submit gems':
                submits[who].append(r)
                prod[who].add(r)
            elif k == 'Banked':
                banked[who].append((r, e['gems']))
                prod[who].add(r)
            elif k in ('CaptureGems', 'CaptureGold'):
                caps.append((r, who, e.get('gems', 0), e.get('gold', 0), tile_group.get(tuple(e['at']))))
                prod[who].add(r)
            elif k in ('Shop', 'Place altar lock', 'Consumable', 'Sell item'):
                prod[who].add(r)
            if tg:
                j = tg[0]
                if r - last_ch[who] > 20 and r - last_ch[j] > 20:
                    opens.append((r, who, j))
                hit_given[who].add(r)
                last_ch[who] = r
                for j in tg:
                    hit_taken[j].add(r)
                    last_ch[j] = r
    # held recalls (survived r+1), bank channel rounds
    held_rounds = defaultdict(set)
    held_cancel = defaultdict(set)
    for b in bodies:
        for x in sorted(recalls[b]):
            if (x + 1) in any_ev[b]:
                continue     # bait (cancelled by the next turn's events)
            for k2 in range(0, 9):
                ck = S.get(x + k2, {}).get(b)
                if ck is None or not ck[7]:
                    break
                held_rounds[b].add(x + k2)
                if k2 and (x + k2) in cancels[b]:
                    held_cancel[b].add(x)
                    break
                if k2 and (ck[3], ck[4]) in spawnset[team[b]]:
                    break
    bankr = defaultdict(set)
    for b in bodies:
        for s0 in submits[b]:
            end = next((x for x, _ in banked[b] if x >= s0), None)
            if end is None or end - s0 > 40:
                end = s0
            for x in range(s0, end + 1):
                bankr[b].add(x)
    caprounds = defaultdict(set)
    for (r, who, gm, gd, gid) in caps:
        for x in range(r - 6, r + 1):
            caprounds[who].add(x)

    def gstate(gid, r):
        rr = R.get(r)
        if rr is None:
            return None
        gg = GB[gid]
        if any(rr['campHp'][i] > 0 for i in gg['idx']):
            return 'alive'
        return 'reward' if rr['gr'][gid] else 'dead'

    def near_group(p, r, rad=4):
        best = None
        for gg in G:
            dd = min(cheb(p, x) for x in gg['tiles'])
            if dd <= rad and (best is None or dd < best[0]):
                best = (dd, gg['id'])
        if best is None:
            return None, None, None
        return best[1], best[0], gstate(best[1], r)

    out = {'key': g['key'], 'mid': g['mid'], 'map': g['map'], 'tag': g['tag'], 'ver': g['ver'], 'kind': g['kind'], 'final': final,
           'we': g['we'], 'winner': g['winner'], 'champs': meta['champsPerTeam'], 'sides': {}}
    SD = {t: {'alive': 0, 'ep': Counter(), 'lost': Counter(), 'act': defaultdict(Counter), 'gh': defaultdict(Counter),
              'cap': defaultdict(Counter), 'bank': defaultdict(Counter), 'open': Counter(), 'opened': Counter(), 'deaths': Counter(),
              'held_cancel': 0, 'types': Counter()} for t in (0, 1)}
    exs = []
    for b in bodies:
        t = team[b]
        sd = SD[t]
        ty = types[b]
        sd['types'][ty] += 1
        P = {}
        for r in range(0, final + 1):
            c = S.get(r, {}).get(b)
            if c is not None and c[7]:
                P[r] = (c[3], c[4])
        mv = {r for r in P if (r - 1) in P and P[r] != P[r - 1]}
        busy = prod[b] | set(camp_given[b])
        # ---------------- wasted loops
        wasted = set()
        for r in sorted(P):
            if r not in mv:
                continue
            for k in range(2, 13):
                r0 = r - k
                if r0 not in P:
                    break
                if cheb(P[r], P[r0]) > 1:
                    continue
                span = range(r0 + 1, r + 1)
                if any(x not in P for x in span):
                    break
                if any(x in busy for x in span):
                    break
                exc = max(cheb(P[x], P[r0]) for x in span)
                nm = [x for x in span if x in mv]
                if exc >= 1 and len(nm) >= 2 and (cheb(P[r], P[r0]) == 0 or exc >= 2):
                    wasted.update(nm)
                    break
        ws = sorted(wasted)
        eps = []
        for x in ws:
            if eps and x - eps[-1][-1] <= 2:
                eps[-1].append(x)
            else:
                eps.append([x])
        # ---------------- classify episodes
        for e in eps:
            r0, r1 = e[0], e[-1]
            p0 = P.get(r0 - 1, P[r0])
            c0 = S.get(r0 - 1, {}).get(b) or S[r0][b]
            en = sorted(cheb(p0, (q[3], q[4])) for i, q in S.get(r0 - 1, S[r0]).items() if q[7] and team[i] != t)
            en_d = en[0] if en else 99
            en6 = sum(1 for x in en if x <= 6)
            al5 = sum(1 for i, q in S.get(r0 - 1, S[r0]).items() if q[7] and team[i] == t and i != b and cheb(p0, (q[3], q[4])) <= 5)
            hpf = c0[5] / max(1, c0[6])
            bag = c0[8]
            fight = any(x in hit_given[b] or x in hit_taken[b] for x in range(r0 - 2, r1 + 3))
            aggro = any(x in camp_taken[b] for x in range(r0, r1 + 1))
            rec = any(x in held_rounds[b] for x in range(r0 - 1, r1 + 1))
            dsp = min(cheb(p0, s) for s in spawn[t])
            gid, gd, gs = near_group(p0, r0 - 1)
            dal = min((cheb(p0, a) for a in altars), default=99)
            if fight:
                cl = 'FIGHT'
            elif en_d <= 6:
                cl = 'ENEMY6'
            elif en_d <= 12:
                cl = 'ENEMY12'
            elif aggro:
                cl = 'CAMPAGGRO'
            elif rec:
                cl = 'RECALL'
            elif bag >= 30:
                cl = 'BAG'
            elif hpf < 0.45:
                cl = 'LOWHP'
            elif dsp <= 4:
                cl = 'SPAWN'
            elif gs in ('dead', 'reward'):
                cl = 'DEADGRP'
            elif gs == 'alive':
                cl = 'LIVEGRP'
            else:
                cl = 'OPEN'
            sd['ep'][cl] += 1
            sd['lost'][cl] += len(e)

            def code(x):
                if x not in P:
                    return 'D'
                if x in bankr[b]:
                    return 'B'
                if x in held_rounds[b]:
                    return 'R'
                if x in caprounds[b]:
                    return 'P'
                if x in hit_given[b] or x in hit_taken[b]:
                    return 'F'
                if x in camp_given[b]:
                    return 'C'
                if x in camp_taken[b]:
                    return 'h'
                return 'M' if x in mv else '.'
            if (g['we'] is not None and t == g['we']) or (g['we'] is None and zlib.crc32(f"{g['key']}{b}{r0}".encode()) % 10 == 0):
                path = [P.get(x) for x in range(r0 - 1, r1 + 1)]
                exs.append({'t': t, 'b': b, 'ty': ty, 'r0': r0, 'r1': r1, 'n': len(e), 'cl': cl, 'en_d': en_d, 'en6': en6, 'al5': al5,
                            'hp': round(hpf, 2), 'bag': bag, 'gold': c0[9], 'gid': gid, 'gd': gd, 'gs': gs,
                            'gcl': gclass(GB[gid]) if gid is not None else None, 'dsp': dsp, 'dal': dal,
                            'pre': ''.join(code(x) for x in range(r0 - 4, r0)), 'mid': ''.join(code(x) for x in range(r0, r1 + 1)),
                            'post': ''.join(code(x) for x in range(r1 + 1, r1 + 5)), 'path': path[:16],
                            'since_resp': next((r0 - x for x in range(r0, max(0, r0 - 200), -1) if x not in P), 200)})
        # ---------------- activity per round
        act = sd['act'][ty]
        for r in range(1, final + 1):
            if r not in P:
                act['dead'] += 1
                continue
            sd['alive'] += 1
            c = S[r][b]
            if r in bankr[b]:
                a = 'bank'
            elif r in held_rounds[b] or r in tele[b]:
                a = 'recall'
            elif r in caprounds[b] or (r not in mv and tile_group.get(P[r]) is not None and gstate(tile_group[P[r]], r) == 'reward'):
                a = 'capture'
            elif r in hit_given[b] or r in hit_taken[b]:
                a = 'fight'
            elif r in camp_given[b]:
                a = 'camp'
            elif P[r] in spawnset[t]:
                a = 'spawn'
            elif r in mv:
                a = 'walk_bag' if c[8] >= 40 else 'walk'
            else:
                a = 'wait'
            act[a] += 1
        # ---------------- group classes of camp hits
        gh = sd['gh'][ty]
        for r, gids in camp_given[b].items():
            for gid in gids:
                if gid is None or gid not in GB:
                    continue
                gg = GB[gid]
                gh[gclass(gg)] += 1
                gh['all'] += 1
                if gg['gold'] > 0:
                    gh['gold'] += 1
                if any(h[1] != t and abs(h[0] - r) <= 30 for h in group_hits[gid]):
                    gh['contested'] += 1
                if not any(h[1] == t and h[2] != b and abs(h[0] - r) <= 8 for h in group_hits[gid]):
                    gh['solo'] += 1
        sd['held_cancel'] += len(held_cancel[b])
    for (r, who, gm, gd, gid) in caps:
        sd = SD[team[who]]
        sd['cap'][types[who]]['gems'] += gm
        sd['cap'][types[who]]['gold'] += gd
        sd['cap'][types[who]]['n'] += 1
        sd['cap']['_team']['gems'] += gm
        sd['cap']['_team']['n'] += 1
        if gid is not None and gid in GB:
            sd['cap'][types[who]][gclass(GB[gid])] += 1
    for b in bodies:
        for (r, gm) in banked[b]:
            sd = SD[team[b]]
            sd['bank'][types[b]]['gems'] += gm
            sd['bank'][types[b]]['n'] += 1
            sd['bank']['_team']['gems'] += gm
    for (r, a, j) in opens:
        SD[team[a]]['open'][types[a]] += 1
        SD[team[j]]['opened'][types[j]] += 1
    for e in deaths:
        SD[e['team']]['deaths'][types[e['who']]] += 1
    for t in (0, 1):
        sd = SD[t]
        out['sides'][str(t)] = {k: (dict(v) if isinstance(v, Counter) else {kk: dict(vv) for kk, vv in v.items()} if isinstance(v, defaultdict) else v)
                                for k, v in sd.items()}
    out['ex'] = exs
    return out


def main():
    part, nparts = int(sys.argv[1]), int(sys.argv[2])
    lim = int(sys.argv[3]) if len(sys.argv) > 3 else 450
    tops = sorted(h30.top_games(), key=lambda g: zlib.crc32(g['key'].encode()))[:lim]
    gs = h30.our_games('v88') + tops + h30.our_games('old')
    gs = [g for i, g in enumerate(gs) if i % nparts == part]
    os.makedirs(OUT, exist_ok=True)
    n = 0
    for g in gs:
        f = f"{OUT}/{g['key']}.json"
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
        if n % 25 == 0:
            print(part, n, g['key'], flush=True)
    print('done', part, n, flush=True)


if __name__ == '__main__':
    main()
