#!/usr/bin/env python3
"""Deterministic-misbehaviour detectors on decoded replays, ours vs theirs, one row per game -> out/det/<mid>.json
    nice -n 19 python3 v88_bugs/detect.py [L|W|all|v84cp|old]
      L / W / all : v88's games (games.json)            v84cp : the v84 games of the same paired groups (counterparts.json)
      old         : the 160 ranked games of Nov 2-3 decoded earlier (v84-v87)
Detectors (per body; 'we' / 'they'):
  rew      every group kill (all camps dead; killer team = most hits in the 3 rounds before) -> step-on delay of the first capture
           (capture event round - 6 - kill round), by which team, whole game
  passive  map_fail/passive.py runs (>= 5 camp-hit rounds with no attack by the body)
  stall    map_fail/stall.py stalls (>= 16 rounds within 3 tiles of an anchor without progress)
  dither   40-round window, >= 20 moves, spread >= 5 tiles, ends within 2 tiles of where it started, no hit given/taken, no capture,
           no bank, no held recall, alive and off spawn throughout (back and forth between two targets)
  recamp   one body, one camp group: >= 3 separate runs (gap > 6 rounds) of hits taken from that group's camps with no attack on it
           in the run, within 150 rounds
  blocked  runs of >= 3 consecutive rounds with a 'Movement blocked' event for the body
  hoard    runs of >= 100 rounds alive off spawn carrying >= 150 gold (5 shards unspent)
  noshop   bodies with no Shop event in the whole game; shards bought by r300 / r600
  bagloss  gems lost on death (bag at death)
  tribfail 'Submit gems' starts whose bag did not land (no Banked within ticks + 3 rounds) and the cause (death / still carrying)
  wasted   damage / stun spells (abilities 2, 3, 4) with no enemy champion and no camp at the target (radius 1 for area spells)
"""
import json, os, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h88  # noqa: E402
import mapgroups  # noqa: E402
import passive  # noqa: E402
import stall  # noqa: E402
import extract as X  # noqa: E402

BASE = h88.BASE


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def old_games():
    rows = [json.loads(l) for l in open(f'{BASE}/matches_me.jsonl')]
    SW = [('2026-11-02T21:15:46', 'v84'), ('2026-11-03T01:00:56', 'v85'), ('2026-11-03T01:21:19', 'v86'), ('2026-11-03T02:52', 'v87')]
    out = []
    for m in rows:
        if m['kind'] != 'ranked' or m['status'] != 'finished' or m['createdAt'] < '2026-11-02T00:00' or m['createdAt'] >= '2026-11-03T02:52':
            continue
        if not (os.path.exists(f"{BASE}/dec/{m['matchId']}.json") and os.path.exists(f"{BASE}/mj/{m['matchId']}.json")):
            continue
        us = [t for t in m['teams'] if t['teamId'] == h88.ME][0]
        th = [t for t in m['teams'] if t['teamId'] != h88.ME][0]
        ver = next((v for t, v in SW if m['createdAt'] < t), 'v87')
        out.append({'mid': m['matchId'], 'map': m['map'], 'we': 0 if us['side'] == 'a' else 1, 'res': 'W' if us['result'] == 'win' else 'L',
                    'opp': th['name'], 'created': m['createdAt'], 'ver': ver, 'kind': 'ranked'})
    return out


def cp_games():
    cp = json.load(open(f'{h88.V}/counterparts.json'))
    rows = {json.loads(l)['matchId']: json.loads(l) for l in open(f'{BASE}/matches_me.jsonl')}
    out = []
    for new, d in cp.items():
        mid = d['v84']
        m = rows.get(mid)
        if not m or m['status'] != 'finished' or not os.path.exists(f'{BASE}/dec/{mid}.json') or not os.path.exists(f'{BASE}/mj/{mid}.json'):
            continue
        us = [t for t in m['teams'] if t['teamId'] == h88.ME][0]
        th = [t for t in m['teams'] if t['teamId'] != h88.ME][0]
        out.append({'mid': mid, 'map': m['map'], 'we': 0 if us['side'] == 'a' else 1, 'res': 'W' if us['result'] == 'win' else 'L',
                    'opp': th['name'], 'created': m['createdAt'], 'ver': 'v84', 'kind': 'v84cp', 'new': new})
    return out


def run(g):
    mid, we = g['mid'], g['we']
    d = json.load(open(f'{BASE}/dec/{mid}.json'))
    mj = json.load(open(f'{BASE}/mj/{mid}.json'))
    meta = d['meta']
    W, H = meta['width'], meta['height']
    team = {b['index']: b['team'] for b in meta['bodies']}
    types = {b['index']: b['type'] for b in meta['bodies']}
    side = {b: ('we' if t == we else 'they') for b, t in team.items()}
    camps = {c['index']: c for c in meta['camps']}
    camp_at = {(c['x'], c['y']): c['index'] for c in meta['camps']}
    G = mapgroups.full_groups(g['map'], meta, mj['sym'])
    tile_group = {t: gg['id'] for gg in G for t in gg['tiles']}
    camp_group = {ci: gg['id'] for gg in G for ci in gg['idx']}
    S = {rr['r']: {c[0]: c for c in rr['ch']} for rr in d['rounds'][1:]}
    R = {rr['r']: rr for rr in d['rounds'][1:]}
    final = meta['finalRound']
    spawn = {0: {tuple(p) for p in mj['spawnA']}, 1: {tuple(p) for p in mj['spawnB']}}
    altars = [(x, y) for y in range(H) for x in range(W) if mj['rows'][y][x] == 'A']
    ev = defaultdict(list)
    for e in d['events']:
        if e['k'] != 'Draft champion':
            ev[e['r']].append(e)

    # ---- per round walk of events with in-round positions
    moved = defaultdict(set)
    hit_given = defaultdict(set)      # champion hit given
    hit_taken = defaultdict(set)
    camp_given = defaultdict(lambda: defaultdict(set))  # b -> r -> {gid}
    camp_taken = defaultdict(lambda: defaultdict(set))  # b -> r -> {gid}
    blocked = defaultdict(set)
    shops = defaultdict(list)
    submits = defaultdict(list)
    banked = defaultdict(list)
    deaths = []
    recall_r = defaultdict(set)
    act_r = defaultdict(set)
    wasted = Counter()
    casts = Counter()
    wasted_ex = []
    caps = defaultdict(list)          # gid -> [(r, team, who, gems, gold)]
    group_hits = defaultdict(list)    # gid -> [(r, team, who)]
    for r in range(1, final + 1):
        prev = S.get(r - 1) or S.get(r)
        if prev is None:
            continue
        pos = {i: ((c[3], c[4]) if c[7] else None) for i, c in prev.items()}
        for e in ev.get(r, []):
            k, who = e['k'], e.get('who')
            if k == 'Attack' and who is None and e.get('camp') is not None:
                P = tuple(e['to'])
                for j, pj in pos.items():
                    if pj == P:
                        camp_taken[j][r].add(camp_group.get(e['camp']))
                continue
            if who is None:
                continue
            if k == 'Move':
                moved[who].add(r)
                pos[who] = tuple(e['to'])
            elif k == 'Movement blocked':
                blocked[who].add(r)
            elif k == 'Cast ability':
                ab = e.get('ability')
                if ab == 6 and 'to' in e:
                    moved[who].add(r)
                    pos[who] = tuple(e['to'])
                    continue
                act_r[who].add(r)
                if 'to' not in e:
                    continue
                P = tuple(e['to'])
                rad = 1 if ab == 3 else 0
                tg = [j for j, pj in pos.items() if pj is not None and team[j] != team[who] and cheb(pj, P) <= rad]
                prevR = R.get(r - 1)
                cg = {tile_group[q] for q in camp_at if q in tile_group and cheb(q, P) <= rad and (prevR is None or prevR['campHp'][camp_at[q]] > 0)}
                if tg:
                    hit_given[who].add(r)
                    for j in tg:
                        hit_taken[j].add(r)
                for gid in cg:
                    camp_given[who][r].add(gid)
                    group_hits[gid].append((r, team[who], who))
                if ab in (2, 3, 4):
                    casts[side[who]] += 1
                    if not tg and not cg:
                        wasted[side[who]] += 1
                        if side[who] == 'we' and len(wasted_ex) < 30:
                            wasted_ex.append((r, who, types[who], ab, P))
            elif k == 'Attack':
                act_r[who].add(r)
                P = tuple(e['to'])
                tg = [j for j, pj in pos.items() if pj == P and team[j] != team[who]]
                if tg:
                    hit_given[who].add(r)
                    hit_taken[tg[0]].add(r)
                elif P in camp_at and P in tile_group:
                    camp_given[who][r].add(tile_group[P])
                    group_hits[tile_group[P]].append((r, team[who], who))
            elif k == 'Shop':
                shops[who].append(r)
            elif k == 'Submit gems':
                submits[who].append(r)
                act_r[who].add(r)
            elif k == 'Banked':
                banked[who].append((r, e['gems']))
            elif k == 'Death':
                deaths.append(e)
                pos[who] = None
            elif k == 'Recall':
                recall_r[who].add(r)
            elif k in ('CaptureGems', 'CaptureGold'):
                caps[tile_group.get(tuple(e['at']))].append((r, team[who], who, e['gems'], e['gold']))
            elif k == 'Respawn':
                pos[who] = tuple(e['to']) if 'to' in e else None
    # held recall rounds (a Recall with no own action next round)
    held = defaultdict(set)
    for b in team:
        for x in recall_r[b]:
            if (x + 1) not in act_r[b] and (x + 1) not in moved[b] and (x + 1) not in recall_r[b]:
                for y in range(x, x + 6):
                    held[b].add(y)
    bankr = defaultdict(set)
    for b in team:
        for s0 in submits[b]:
            end = next((x for x, _ in banked[b] if x >= s0), None)
            if end is None or end - s0 > 40:
                end = s0
            for x in range(s0, end + 1):
                bankr[b].add(x)

    def alive_at(b, r):
        c = S.get(r, {}).get(b)
        return c if c is not None and c[7] else None

    out = {'mid': mid, 'map': g['map'], 'res': g['res'], 'ver': g['ver'], 'kind': g.get('kind'), 'final': final,
           'sub_we': meta['submitted'][we], 'sub_they': meta['submitted'][1 - we], 'draft_we': meta['drafts'][we], 'draft_they': meta['drafts'][1 - we]}

    # ---- rew: kills -> step-on delay
    rew = []
    for gg in G:
        prev_dead = True  # groups start alive; a first dead round after alive is a kill
        first = True
        for r in range(1, final + 1):
            rr = R.get(r)
            if rr is None:
                continue
            dead = all(rr['campHp'][i] == 0 for i in gg['idx'])
            if first:
                prev_dead = dead
                first = False
                continue
            if dead and not prev_dead:
                hs = [h for h in group_hits[gg['id']] if r - 3 <= h[0] <= r]
                if hs:
                    kt = Counter(h[1] for h in hs).most_common(1)[0][0]
                    killers = sorted({h[2] for h in hs if h[1] == kt})
                    cs = [c for c in caps[gg['id']] if c[0] >= r]
                    c0 = cs[0] if cs else None
                    delay = (c0[0] - 6 - r) if c0 else None
                    s3 = S.get(r + 3, {})
                    near = sorted(i for i, c in s3.items() if c[7] and team[i] == kt and min(cheb((c[3], c[4]), t) for t in gg['tiles']) <= 5)
                    en = min((min(cheb((c[3], c[4]), t) for t in gg['tiles']) for i, c in (S.get(r) or {}).items() if c[7] and team[i] != kt), default=99)
                    rew.append({'g': gg['id'], 'gems': gg['gems'], 'gold': gg['gold'], 'r': r, 'side': 'we' if kt == we else 'they',
                                'killers': killers, 'delay': delay, 'by': None if c0 is None else ('same' if c0[1] == kt else 'other'),
                                'cap_r': c0[0] if c0 else None, 'near3': near, 'enemy_d': en, 'final': final})
            prev_dead = dead
    out['rew'] = rew

    # ---- passive / stall (map_fail)
    out['passive'] = passive.run(g)
    out['stall'] = stall.run(g)

    # ---- dither
    dith = []
    for b in team:
        t = team[b]
        r = 1
        while r <= final - 40:
            win = range(r, r + 40)
            cs = [alive_at(b, x) for x in win]
            if all(c is not None and (c[3], c[4]) not in spawn[t] for c in cs):
                nm = sum(1 for x in win if x in moved[b])
                ps = [(c[3], c[4]) for c in cs]
                spread = max(cheb(ps[0], p) for p in ps)
                busy = any(x in hit_given[b] or x in hit_taken[b] or camp_given[b].get(x) or camp_taken[b].get(x) or x in bankr[b] or x in held[b]
                           for x in win)
                oncap = sum(1 for p, x in zip(ps, win) if p in tile_group and R.get(x) and R[x]['gr'][tile_group[p]])
                if nm >= 20 and spread >= 5 and cheb(ps[0], ps[-1]) <= 2 and not busy and oncap < 3:
                    en = min((cheb(ps[0], (q[3], q[4])) for i, q in S[r].items() if q[7] and team[i] != t), default=99)
                    far = max(ps, key=lambda p: cheb(ps[0], p))
                    dith.append({'side': side[b], 'b': b, 'champ': types[b], 'r': r, 'from': ps[0], 'far': far, 'spread': spread, 'moves': nm,
                                 'enemy_d': en, 'hp': round(cs[0][5] / max(1, cs[0][6]), 2), 'gems': cs[0][8], 'gold': cs[0][9]})
                    r += 40
                    continue
            r += 1
    out['dither'] = dith

    # ---- recamp: repeated passive entries into the same group's reach
    rec = []
    for b in team:
        runs = defaultdict(list)  # gid -> list of [r0, r1, attacked]
        for r in sorted(camp_taken[b]):
            for gid in camp_taken[b][r]:
                if gid is None:
                    continue
                L = runs[gid]
                if L and r - L[-1][1] <= 6:
                    L[-1][1] = r
                else:
                    L.append([r, r, False])
        for gid, L in runs.items():
            for run_ in L:
                run_[2] = any(gid in camp_given[b].get(x, ()) for x in range(run_[0] - 1, run_[1] + 2))
            pas = [x for x in L if not x[2]]
            for i in range(len(pas)):
                grp = [x for x in pas[i:] if x[0] - pas[i][0] <= 150]
                if len(grp) >= 3 and (i == 0 or pas[i][0] - pas[i - 1][0] > 150):
                    rec.append({'side': side[b], 'b': b, 'champ': types[b], 'g': gid, 'gtypes': ''.join(t[0] for t in G[gid]['types']),
                                'runs': [(x[0], x[1]) for x in grp], 'n': len(grp)})
    out['recamp'] = rec

    # ---- blocked moves
    blk = []
    for b in team:
        rs = sorted(blocked[b])
        cur = []
        for r in rs + [10 ** 9]:
            if cur and r == cur[-1] + 1:
                cur.append(r)
                continue
            if len(cur) >= 3:
                c = S.get(cur[0] - 1, {}).get(b)
                blk.append({'side': side[b], 'b': b, 'champ': types[b], 'r': cur[0], 'len': len(cur), 'at': (c[3], c[4]) if c else None})
            cur = [r]
    out['blocked'] = blk
    out['blocked_n'] = {s: sum(len(blocked[b]) for b in team if side[b] == s) for s in ('we', 'they')}

    # ---- gold hoarding / shopping
    hoard = []
    shards_at = {}
    for b in team:
        t = team[b]
        run0 = None
        for r in range(1, final + 2):
            c = alive_at(b, r)
            h = c is not None and c[9] >= 150 and (c[3], c[4]) not in spawn[t]
            if h and run0 is None:
                run0 = r
            if not h and run0 is not None:
                if r - run0 >= 100:
                    c0 = S[run0][b]
                    hoard.append({'side': side[b], 'b': b, 'champ': types[b], 'r': run0, 'len': r - run0, 'gold0': c0[9],
                                  'gold_max': max((S.get(x, {}).get(b) or [0] * 12)[9] for x in range(run0, r))})
                run0 = None
        for rr in (300, 600):
            c = S.get(min(rr, final), {}).get(b)
            shards_at[(b, rr)] = X.shards(c[11]) if c else 0
    out['hoard'] = hoard
    out['shops'] = {s: [len(shops[b]) for b in sorted(team) if side[b] == s] for s in ('we', 'they')}
    out['noshop'] = [{'side': side[b], 'b': b, 'champ': types[b]} for b in team if not shops[b]]
    out['shards300'] = {s: sum(shards_at[(b, 300)] for b in team if side[b] == s) for s in ('we', 'they')}
    out['shards600'] = {s: sum(shards_at[(b, 600)] for b in team if side[b] == s) for s in ('we', 'they')}
    # gold carried (mean over alive body-rounds)
    gsum = Counter()
    gn = Counter()
    for r in range(1, final + 1, 5):
        for b, c in (S.get(r) or {}).items():
            if c[7]:
                gsum[side[b]] += c[9]
                gn[side[b]] += 1
    out['gold_mean'] = {s: round(gsum[s] / max(1, gn[s]), 1) for s in ('we', 'they')}

    # ---- bag loss / tribute failures
    out['bagloss'] = [{'side': side[e['who']], 'b': e['who'], 'champ': types[e['who']], 'r': e['r'], 'bag': e.get('bag', 0), 'at': e.get('at')}
                      for e in deaths if e.get('bag', 0) > 0]
    out['deaths'] = {s: sum(1 for e in deaths if side[e['who']] == s) for s in ('we', 'they')}
    tf = []
    for b in team:
        for s0 in submits[b]:
            c = S.get(s0 - 1, {}).get(b) or S.get(s0, {}).get(b)
            if c is None or c[8] <= 0:
                continue
            ticks = max(1, (c[8] + 9) // 10)
            ok = any(s0 <= x <= s0 + ticks + 3 for x, _ in banked[b])
            if ok:
                continue
            # a later Submit within the window (a resubmit) is the same attempt
            if any(s0 < x <= s0 + ticks + 3 for x in submits[b]):
                continue
            dd = any(e['who'] == b and s0 <= e['r'] <= s0 + ticks + 3 for e in deaths)
            tf.append({'side': side[b], 'b': b, 'champ': types[b], 'r': s0, 'bag': c[8], 'died': dd,
                       'altar_d': min((cheb((c[3], c[4]), a) for a in altars), default=None)})
    out['tribfail'] = tf
    out['submits'] = {s: sum(len(submits[b]) for b in team if side[b] == s) for s in ('we', 'they')}
    out['banks'] = {s: sum(len(banked[b]) for b in team if side[b] == s) for s in ('we', 'they')}
    out['wasted'] = dict(wasted)
    out['casts'] = dict(casts)
    out['wasted_ex'] = wasted_ex
    out['types'] = {str(b): types[b] for b in team}
    out['side_of'] = {str(b): side[b] for b in team}
    return out


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else 'L'
    if which == 'old':
        gs = old_games()
    elif which == 'v84cp':
        gs = cp_games()
    else:
        gs = h88.games(None if which == 'all' else which)
    h88.ensure_groups(gs)
    os.makedirs(f'{h88.V}/out/det', exist_ok=True)
    for g in gs:
        f = f"{h88.V}/out/det/{g['mid']}.json"
        if os.path.exists(f):
            continue
        try:
            row = run(g)
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            print('FAIL', g['mid'], g['map'], repr(e)[:200], flush=True)
            continue
        json.dump(row, open(f, 'w'))
        print(which, g['map'], g['mid'][:8], g['res'], flush=True)


if __name__ == '__main__':
    main()
