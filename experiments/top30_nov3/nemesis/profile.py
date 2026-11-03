#!/usr/bin/env python3
"""Per-game style profile of the opponent (and of us) in our games vs the nemesis / easy teams.

Usage: nice -n 19 python3 -I profile.py [selection.json] [out.jsonl]
Reads  ladder_nov2/dec + mj (decoded by download.sh), the selection list (mid, opp, res, map, created).
Writes nemesis/out/profiles.jsonl: one row per game with, for each side ('we' / 'they'):
  draft, opening (first targets, stacking, first capture, gems by r150), aggression (body-rounds on the enemy half per
  100-round window, invasion episodes), fights (first hits, exchange wins, range-4 spell hits, dives, chases, lures),
  banking (banks, bag at bank, banker types, carry rounds), denial (steals of groups the other side killed, locks, wards,
  wards on bush), pace (captured / banked gems at r200/400/600/800), deaths (killer, context, band, bag, round)
plus the gap timeline and the round the loser fell 150 behind for good (analyze.py).
"""
import json, os, sys
from collections import defaultdict, Counter

BASE = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, f'{BASE}/agent_fights')
sys.path.insert(0, f'{BASE}/map_fail')
sys.path.insert(0, f'{BASE}/v88_bugs')
import h88  # noqa: E402  (loads the extended half-group tables)
import extract as X  # noqa: E402
import analyze as A  # noqa: E402
from mapgroups import full_groups  # noqa: E402

ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
WIN = (200, 400, 600, 800, 1000)
RANGED4 = {('Marcella', 2), ('Cassi', 2), ('Stellar', 2), ('Stellar', 3), ('Tavi', 4), ('Ren', 4), ('Prism', 4), ('Cassi', 4),
           ('Ryth', 3), ('Prism', 3), ('Willow', 5)}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def profile(g):
    """g: {mid, map, we, res, opp, created, ver}"""
    mid, we = g['mid'], g['we']
    row, dl = A.analyse(g)
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
    camp_group = {ci: gg['id'] for gg in G for ci in gg['idx']}
    camp_at = {(c['x'], c['y']): c['index'] for c in meta['camps']}
    spawn = {0: {tuple(p) for p in mj['spawnA']}, 1: {tuple(p) for p in mj['spawnB']}}
    mf, dA, dB = X.map_features(mj)
    bush = {(x, y) for y in range(H) for x in range(W) if mj['rows'][y][x] == '"'}
    altars = [(x, y) for y in range(H) for x in range(W) if mj['rows'][y][x] == 'A']

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

    # group distance rank from each spawn (walking distance of the group centre)
    gdist = {}
    for gg in G:
        c = (round(gg['cx']), round(gg['cy']))
        for t in (0, 1):
            dd = [dhome(t, tt) for tt in gg['tiles']]
            dd = [x for x in dd if x is not None]
            gdist[(t, gg['id'])] = min(dd) if dd else 999
    grank = {}
    for t in (0, 1):
        order = sorted(G, key=lambda gg: gdist[(t, gg['id'])])
        for i, gg in enumerate(order):
            grank[(t, gg['id'])] = i

    # ---------- events with in-round positions
    ev = defaultdict(list)
    for e in d['events']:
        if e['k'] != 'Draft champion':
            ev[e['r']].append(e)
    camp_hit = defaultdict(list)       # body -> [(r, camp)]
    camp_last_hitter = {}              # camp -> (r, team) of the last champion hit
    group_last_killer = {}             # gid -> team whose body hit a camp of it last before it died
    captures = []                      # (r, body, gems, gold, gid)
    banked = []                        # (r, body, gems)
    spells4 = defaultdict(Counter)     # team -> Counter of (champ, ability, 'champ'|'camp', dist)
    champ_hits = defaultdict(list)     # team -> (r, attacker, target, dist, kind)
    deaths_ev = []
    locks = defaultdict(list)
    wards = defaultdict(list)
    first_hit_r = {}
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
                pos[who] = tuple(e['to'])
            elif k == 'Cast ability' and who is not None:
                ab = e['ability']
                P = tuple(e['to'])
                if ab == 6:
                    if tuple(e['from']) != (0, 0):
                        pos[who] = tuple(e['from'])
                    me_p = pos.get(who)
                    pos[who] = P
                    if types[who] == 'HeartOfRuin':
                        tg = [j for j, pj in pos.items() if pj is not None and team[j] != team[who] and cheb(pj, P) <= 1]
                        for j in tg:
                            champ_hits[team[who]].append((r, who, j, cheb(me_p, P) if me_p else None, 'dash'))
                    continue
                me_p = pos.get(who)
                if me_p is None:
                    continue
                dist = cheb(me_p, P)
                rad = 1 if ab == 3 else 0
                tg = [j for j, pj in pos.items() if pj is not None and team[j] != team[who] and cheb(pj, P) <= rad]
                hit_camp = any(cheb(P, q) <= rad for q in camp_at)
                if ab in (2, 3, 4):
                    if tg:
                        for j in tg:
                            champ_hits[team[who]].append((r, who, j, dist, 'spell'))
                        spells4[team[who]][(types[who], ab, 'champ', dist)] += 1
                    elif hit_camp:
                        spells4[team[who]][(types[who], ab, 'camp', dist)] += 1
                        for q, ci in camp_at.items():
                            if cheb(P, q) <= rad:
                                camp_hit[who].append((r, ci))
                                camp_last_hitter[ci] = (r, team[who])
                                first_hit_r.setdefault(who, (r, camp_group.get(ci)))
            elif k == 'Attack' and who is not None:
                P = tuple(e['to'])
                me_p = pos.get(who)
                tg = [j for j, pj in pos.items() if pj == P and team[j] != team[who]]
                if tg:
                    champ_hits[team[who]].append((r, who, tg[0], cheb(me_p, P) if me_p else None, 'atk'))
                elif P in camp_at:
                    ci = camp_at[P]
                    camp_hit[who].append((r, ci))
                    camp_last_hitter[ci] = (r, team[who])
                    first_hit_r.setdefault(who, (r, camp_group.get(ci)))
            elif k == 'Teleport complete' and who is not None:
                pos[who] = tuple(e['to'])
            elif k == 'Respawn' and who is not None:
                pos[who] = tuple(e['to'])
            elif k == 'Death':
                deaths_ev.append(e)
                pos[who] = None
            elif k == 'Banked':
                banked.append((r, who, e['gems']))
            elif k in ('CaptureGems', 'CaptureGold'):
                p = tuple(e['at'])
                captures.append((r, who, e['gems'], e['gold'], tile_group.get(p)))
            elif k == 'Place altar lock' and who is not None:
                locks[team[who]].append((r, tuple(e['to'])))
            elif k == 'Place ward' and who is not None:
                wards[team[who]].append((r, tuple(e['to'])))
        # group deaths this round: record the killer team
        rr = R.get(r)
        rp = R.get(r - 1)
        if rr and rp:
            for gg in G:
                dead_now = all(rr['campHp'][i] == 0 for i in gg['idx'])
                dead_prev = all(rp['campHp'][i] == 0 for i in gg['idx'])
                if dead_now and not dead_prev:
                    last = [camp_last_hitter.get(i) for i in gg['idx']]
                    last = [x for x in last if x]
                    if last:
                        group_last_killer[(gg['id'], r)] = max(last)[1]

    # ---------- per side
    out = {}
    for side, t in (('we', we), ('they', 1 - we)):
        own = [b for b in bodies if team[b] == t]
        o = {}
        o['draft'] = [types[b] for b in own]
        # opening
        ft = {}
        for b in own:
            if b in first_hit_r:
                r0, gid = first_hit_r[b]
                ft[b] = {'r': r0, 'g': gid, 'rank': grank.get((t, gid)), 'gems': G[gid]['gems'] if gid is not None else None,
                         'band': band(t, (round(G[gid]['cx']), round(G[gid]['cy']))) if gid is not None else None}
        o['first_targets'] = ft
        o['first_target_distinct'] = len({v['g'] for v in ft.values()}) / max(1, len(ft))
        o['first_target_rank_mean'] = sum(v['rank'] for v in ft.values() if v['rank'] is not None) / max(1, len(ft))
        o['first_target_gems_mean'] = sum(v['gems'] or 0 for v in ft.values()) / max(1, len(ft))
        o['first_hit_r_mean'] = sum(v['r'] for v in ft.values()) / max(1, len(ft))
        # stacking: for each group-visit (body hitting group gid in a run), how many own bodies hit the same group within +-5 rounds
        vis = Counter()
        n_vis = 0
        for b in own:
            seen = set()
            for (r, ci) in camp_hit[b]:
                gid = camp_group.get(ci)
                key = (gid, r // 20)
                if key in seen:
                    continue
                seen.add(key)
                n_vis += 1
                others = {b2 for b2 in own if b2 != b and any(camp_group.get(c2) == gid and abs(r2 - r) <= 5 for (r2, c2) in camp_hit[b2])}
                vis[len(others) + 1] += 1
        o['stack_mean'] = sum(k * v for k, v in vis.items()) / max(1, n_vis)
        o['stack_hist'] = dict(vis)
        capt = [c for c in captures if team[c[1]] == t]
        o['first_capture_r'] = capt[0][0] if capt else None
        o['cap150'] = sum(c[2] for c in capt if c[0] <= 150)
        o['cap_by'] = {str(w): sum(c[2] for c in capt if c[0] <= w) for w in WIN}
        sub = {r: R[r]['sub'][t] for r in R}
        o['bank_by'] = {str(w): sub.get(min(w, final), 0) for w in WIN}
        o['camp_hits_by'] = {str(w): sum(1 for b in own for (r, ci) in camp_hit[b] if r <= w) for w in WIN}
        # aggression: body-rounds per band per 100-round window; invasions
        agg = defaultdict(Counter)
        inv = []
        cur = None
        for r in range(1, final + 1):
            s = S.get(r)
            if not s:
                continue
            ps = [(c[3], c[4]) for i, c in s.items() if team[i] == t and c[7]]
            bands = Counter(band(t, p) for p in ps)
            w = min(r // 100, 12)
            for bn, n in bands.items():
                agg[w][bn] += n
            inside = [p for p in ps if band(t, p) == 'their']
            if len(inside) >= 2:
                if cur is None:
                    cur = {'r': r, 'len': 0, 'max_n': 0, 'n_sum': 0}
                cur['len'] += 1
                cur['max_n'] = max(cur['max_n'], len(inside))
                cur['n_sum'] += len(inside)
            else:
                if cur and cur['len'] >= 5:
                    inv.append(cur)
                cur = None
        if cur and cur['len'] >= 5:
            inv.append(cur)
        o['their_half_frac'] = {str(w): round(agg[w]['their'] / max(1, sum(agg[w].values())), 3) for w in sorted(agg)}
        o['mid_frac'] = {str(w): round(agg[w]['mid'] / max(1, sum(agg[w].values())), 3) for w in sorted(agg)}
        o['invasions'] = inv
        o['inv_n'] = len(inv)
        o['inv_first_r'] = inv[0]['r'] if inv else None
        o['inv_rounds'] = sum(x['len'] for x in inv)
        # fights (hits by this side)
        hs = champ_hits[t]
        o['champ_hits'] = len(hs)
        o['hits_dist'] = dict(Counter(h[3] for h in hs if h[3] is not None))
        o['hits_range4'] = sum(1 for h in hs if h[3] == 4)
        o['spells4'] = {f'{k[0]}:{k[1]}:{k[2]}:{k[3]}': v for k, v in spells4[t].items()}
        o['spell_champ_hits'] = sum(v for k, v in spells4[t].items() if k[2] == 'champ')
        o['spell_champ_hits_r4'] = sum(v for k, v in spells4[t].items() if k[2] == 'champ' and k[3] >= 4)
        o['marc_spell_champ_r4'] = sum(v for k, v in spells4[t].items() if k[0] == 'Marcella' and k[2] == 'champ' and k[3] >= 4)
        o['marc_spell_champ'] = sum(v for k, v in spells4[t].items() if k[0] == 'Marcella' and k[2] == 'champ')
        # banking
        bk = [x for x in banked if team[x[1]] == t]
        o['banks'] = len(bk)
        o['bank_mean'] = sum(x[2] for x in bk) / max(1, len(bk))
        o['bank_max'] = max((x[2] for x in bk), default=0)
        o['bank_by_type'] = dict(Counter(types[x[1]] for x in bk))
        o['bank_gems_by_type'] = {}
        for x in bk:
            o['bank_gems_by_type'][types[x[1]]] = o['bank_gems_by_type'].get(types[x[1]], 0) + x[2]
        # carry rounds: for each bank, rounds since the body's bag was last 0
        carry = []
        for (r, b, gems) in bk:
            r0 = r
            while r0 > 1 and S.get(r0 - 1, {}).get(b) and S[r0 - 1][b][7] and S[r0 - 1][b][8] > 0:
                r0 -= 1
            carry.append(r - r0)
        o['carry_mean'] = sum(carry) / max(1, len(carry))
        # denial: captures of groups killed by the other side; locks; wards
        steals = 0
        steal_gems = 0
        for (r, b, gems, gold, gid) in capt:
            if gid is None:
                continue
            ks = [kt for (kg, kr), kt in group_last_killer.items() if kg == gid and kr <= r]
            if ks:
                kr = max(kr for (kg, kr) in group_last_killer if kg == gid and kr <= r)
                if group_last_killer[(gid, kr)] != t:
                    steals += 1
                    steal_gems += gems
        o['steals'] = steals
        o['steal_gems'] = steal_gems
        o['locks'] = len(locks[t])
        o['locks_r'] = [r for r, p in locks[t]]
        o['wards'] = len(wards[t])
        o['wards_bush'] = sum(1 for r, p in wards[t] if p in bush)
        o['wards_enemy_half'] = sum(1 for r, p in wards[t] if band(t, p) == 'their')
        o['wards_r_first'] = wards[t][0][0] if wards[t] else None
        # time use + deaths from analyze
        o['use'] = row['use_we'] if side == 'we' else row['use_they']
        dd = [x for x in dl if x['side'] == side]
        o['deaths'] = len(dd)
        o['deaths_list'] = [{'b': x['body'], 'champ': x['champ'], 'r': x['r'], 'killer': x['killer'], 'ctx': x['ctx'], 'band': x['band'],
                             'bag': x['bag'], 'al5': x['al5'], 'en5': x['en5'], 'hp5': x['hp5'], 'tw8': x['tw8'], 'aw8': x['aw8'],
                             'lure': x['lure'], 'started': x['started'], 'farming': x['farming'], 'group': x['group'], 'ggems': x['ggems'],
                             'camp_waker': x['camp_waker'], 'stunned3': x['stunned3'], 'shards': x['shards'], 'x': x['x'], 'y': x['y']}
                            for x in dd]
        o['gems_lost'] = sum(x['bag'] for x in dd)
        o['shards_r300'] = sum(X.shards(S[300][b][11]) for b in own if 300 in S and b in S[300]) if 300 in S else None
        o['shards_r600'] = sum(X.shards(S[600][b][11]) for b in own if 600 in S and b in S[600]) if 600 in S else None
        o['gold_r300'] = sum(S[300][b][9] for b in own if 300 in S and b in S[300]) if 300 in S else None
        out[side] = o
    # fights from extract (already computed inside analyse via X.process; recompute cheaply for fight rows)
    drows, frows, grow, retreats, recalls, dives, chases = X.process(mid, we, {'res': g['res'], 'map': g['map'], 'opp': g['opp']})
    ex = [f for f in frows if f['exchange']]
    fr = {'n_fights': len(frows), 'n_exch': len(ex),
          'first_we': sum(1 for f in ex if f['first'] == 'we'), 'win_we': sum(1 for f in ex if f['win'] == 'we'),
          'win_they': sum(1 for f in ex if f['win'] == 'they'),
          'num_we': sum(f['num']['we'] for f in ex) / max(1, len(ex)), 'num_they': sum(f['num']['they'] for f in ex) / max(1, len(ex)),
          'parts_we': sum(f['parts']['we'] for f in ex) / max(1, len(ex)), 'parts_they': sum(f['parts']['they'] for f in ex) / max(1, len(ex)),
          'dives_we': sum(1 for x in dives if x['side'] == 'we'), 'dives_they': sum(1 for x in dives if x['side'] == 'they'),
          'chases_we': sum(1 for x in chases if x['side'] == 'we'), 'chases_they': sum(1 for x in chases if x['side'] == 'they'),
          'chase_died_we': sum(1 for x in chases if x['side'] == 'we' and x['died10']),
          'lure_deaths_we': sum(1 for x in drows if x['side'] == 'we' and x['lure']),
          'lure_deaths_they': sum(1 for x in drows if x['side'] == 'they' and x['lure']),
          'retreats_we': sum(1 for x in retreats if x['side'] == 'we'), 'retreats_they': sum(1 for x in retreats if x['side'] == 'they'),
          'recalls_we': sum(1 for x in recalls if x['side'] == 'we'), 'recalls_they': sum(1 for x in recalls if x['side'] == 'they'),
          'farm_def_they_first': sum(1 for f in ex if f['first'] == 'they' and f['farm_def']),
          'farm_def_we_first': sum(1 for f in ex if f['first'] == 'we' and f['farm_def']),
          'fights': [{'start': f['start'], 'first': f['first'], 'win': f['win'], 'num': f['num'], 'parts': f['parts'], 'dead': f['dead'],
                      'd_own': f['d_own'], 'd_their': f['d_their'], 'farm_def': f['farm_def'], 'first_hit': f['first_hit'],
                      'shards': f['shards'], 'cp': f['cp']} for f in ex]}
    # where was the gap opened: banked + carried per 100 rounds
    gap = {}
    for r in range(100, final + 1, 100):
        s = S.get(r, {})
        tot = {t: R[r]['sub'][t] + sum(c[8] for i, c in s.items() if team[i] == t and c[7]) for t in (0, 1)} if r in R else None
        if tot:
            gap[str(r)] = tot[we] - tot[1 - we]
    res = dict(g, final=final, sub_we=row['sub_we'], sub_they=row['sub_they'], tl=row['tl'], last_tie=row['last_tie'],
               behind150=row['behind150'], gap=gap, groups=row['groups'], gcap=row['gcap'], teleports=row['teleports'],
               passing_camp_hits=row['passing_camp_hits'], held_recalls=row['held_recalls'], episodes=row['episodes'],
               fights=fr, we_=out['we'], they_=out['they'], mf=mf)
    return res


def select(path):
    sel = json.load(open(path))
    rows = [json.loads(l) for l in open(f'{BASE}/matches_me.jsonl')]
    info = {m['matchId']: m for m in rows}
    out = []
    for s in sel:
        m = info.get(s['mid'])
        if not m:
            continue
        if not (os.path.exists(f"{BASE}/dec/{s['mid']}.json") and os.path.exists(f"{BASE}/mj/{s['mid']}.json")):
            continue
        us = [t for t in m['teams'] if t['teamId'] == ME][0]
        out.append({'mid': s['mid'], 'map': m['map'], 'we': 0 if us['side'] == 'a' else 1, 'res': s['res'], 'opp': s['opp'],
                    'created': m['createdAt'], 'ver': A.version(m['createdAt']), 'kind': m['kind']})
    return out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else f'{HERE}/selection.json'
    outp = sys.argv[2] if len(sys.argv) > 2 else f'{HERE}/out/profiles.jsonl'
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    games = select(path)
    h88.ensure_groups(games)
    done = set()
    if os.path.exists(outp):
        for l in open(outp):
            done.add(json.loads(l)['mid'])
    print(len(games), 'games,', len(done), 'already profiled', flush=True)
    with open(outp, 'a') as f:
        for i, g in enumerate(games):
            if g['mid'] in done:
                continue
            try:
                r = profile(g)
            except Exception as e:  # noqa: BLE001
                print('FAIL', g['mid'], g['map'], repr(e), file=sys.stderr, flush=True)
                continue
            f.write(json.dumps(r) + '\n')
            f.flush()
            print(i, g['opp'], g['res'], g['map'], g['mid'][:8], f"{r['sub_we']}-{r['sub_they']}", 'deaths', r['we_']['deaths'], r['they_']['deaths'], flush=True)


if __name__ == '__main__':
    main()
