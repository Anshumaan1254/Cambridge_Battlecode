#!/usr/bin/env python3
"""Stalls as the bot's own v27_watch defines them, measured in replays: >= MIN rounds alive, off spawn, within Chebyshev 3 of an anchor
tile, with no attack, no non-dash cast, no gems / gold change, no healing, no tribute, no held recall. Waiting next to a group whose
respawn is due within 3 rounds is not a stall (the bot's legit_wait). Each stall says whether the body cast a DASH inside it (which the
bot counts as progress: progress_watch(... || cast_done ...) resets its clock), whether it took camp hits, and what group is near.

    nice -n 19 python3 -I map_fail/stall.py [all|map ...] > map_fail/out/stall.txt   (also out/stall.jsonl)
"""
import json, os, sys
from collections import Counter, defaultdict
BASE = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
sys.path.insert(0, f'{BASE}/map_fail')
from mapgroups import full_groups, HALF  # noqa: E402
from analyze import select, MAPS, ME, SINCE, version  # noqa: E402
MIN = 16


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def run(g):
    mid, we = g['mid'], g['we']
    d = json.load(open(f'{BASE}/dec/{mid}.json'))
    mj = json.load(open(f'{BASE}/mj/{mid}.json'))
    meta = d['meta']
    team = {b['index']: b['team'] for b in meta['bodies']}
    types = {b['index']: b['type'] for b in meta['bodies']}
    S = {rr['r']: {c[0]: c for c in rr['ch']} for rr in d['rounds'][1:]}
    final = meta['finalRound']
    spawn = {0: {tuple(p) for p in mj['spawnA']}, 1: {tuple(p) for p in mj['spawnB']}}
    camp_xy = [(c['x'], c['y']) for c in meta['camps']]
    act = defaultdict(set)    # rounds with an attack or a non-dash cast or submit
    dash = defaultdict(set)
    chan = defaultdict(set)   # held recall / tribute rounds (rough)
    camp_hit = defaultdict(set)
    recall_r = defaultdict(set)
    ev_by_r = defaultdict(list)
    for e in d['events']:
        w = e.get('who')
        if w is not None:
            if e['k'] == 'Attack' or e['k'] == 'Submit gems' or e['k'] == 'Teleport channel' or e['k'] == 'Place altar lock':
                act[w].add(e['r'])
            elif e['k'] == 'Cast ability':
                (dash if e.get('ability') == 6 else act)[w].add(e['r'])
            elif e['k'] == 'Recall':
                recall_r[w].add(e['r'])
            elif e['k'] in ('Gems submitted',):
                for x in range(e['r'] - 12, e['r'] + 1):
                    chan[w].add(x)
        elif e['k'] == 'Attack' and e.get('camp') is not None:
            ev_by_r[e['r']].append(tuple(e['to']))
    for r, tos in ev_by_r.items():
        for b, c in (S.get(r - 1) or {}).items():
            if c[7] and (c[3], c[4]) in tos:
                camp_hit[b].add(r)
    # held recalls: a Recall with no own event next round
    for b in team:
        for x in recall_r[b]:
            if (x + 1) not in act[b] and (x + 1) not in dash[b] and (x + 1) not in recall_r[b]:
                for y in range(x, x + 6):
                    chan[b].add(y)
    rows = []
    for b in team:
        t = team[b]
        anchor, since, prev = None, None, None
        hits = dashes = 0
        for r in range(1, final + 2):
            c = S.get(r, {}).get(b)
            ok = c is not None and c[7] and (c[3], c[4]) not in spawn[t]
            p = (c[3], c[4]) if ok else None
            progress = (not ok or r in act[b] or r in chan[b] or prev is None or not prev[7] or c[8] != prev[8] or c[9] != prev[9]
                        or c[5] > prev[5] + 0.02 * c[6] or anchor is None or cheb(p, anchor) > 3)
            if not progress:
                hits += r in camp_hit[b]
                dashes += r in dash[b]
            if progress:
                if since is not None and r - since >= MIN:
                    c0 = S[since][b]
                    en = [cheb(anchor, (q[3], q[4])) for i, q in S[since].items() if q[7] and team[i] != t]
                    nc = min((cheb(anchor, q) for q in camp_xy), default=99)
                    rows.append({'mid': mid, 'map': g['map'], 'res': g['res'], 'side': 'we' if t == we else 'they', 'b': b,
                                 'champ': types[b], 'r': since, 'len': r - since, 'at': anchor, 'hp': round(c0[5] / max(1, c0[6]), 2),
                                 'gems': c0[8], 'dashes': dashes, 'camp_hits': hits, 'enemy_d': min(en) if en else None,
                                 'camp_d': nc, 'ver': g['ver']})
                anchor, since, hits, dashes = p, r, 0, 0
            prev = c
    return rows


def main():
    args = sys.argv[1:] or MAPS
    if args == ['all']:
        rows = [json.loads(l) for l in open(f'{BASE}/matches_me.jsonl')]
        games = []
        for m in rows:
            if m['kind'] != 'ranked' or m['status'] != 'finished' or not os.path.exists(f"{BASE}/dec/{m['matchId']}.json"):
                continue
            if not os.path.exists(f"{BASE}/mj/{m['matchId']}.json"):
                continue
            us = [t for t in m['teams'] if t['teamId'] == ME][0]
            games.append({'mid': m['matchId'], 'map': m['map'], 'we': 0 if us['side'] == 'a' else 1,
                          'res': 'W' if us['result'] == 'win' else 'L', 'ver': version(m['createdAt'])})
    else:
        games = select(args)
    out = []
    for g in games:
        out += run(g)
    tag = 'all' if args == ['all'] else 'maps'
    with open(f'{BASE}/map_fail/out/stall_{tag}.jsonl', 'w') as f:
        for r in out:
            f.write(json.dumps(r) + '\n')
    maps = sorted(set(g['map'] for g in games))
    tot = Counter()
    for m in maps:
        n = sum(1 for g in games if g['map'] == m)
        line = []
        for side in ('we', 'they'):
            x = [r for r in out if r['map'] == m and r['side'] == side]
            tot[(side, 'n')] += len(x)
            tot[(side, 'len')] += sum(r['len'] for r in x)
            tot[(side, 'dash')] += sum(1 for r in x if r['dashes'])
            tot[(side, 'hit')] += sum(1 for r in x if r['camp_hits'] >= 3)
            line.append(f"{side} {len(x):3} stalls {sum(r['len'] for r in x) / n:5.0f} rnd/game (dash inside {sum(1 for r in x if r['dashes'])}, camp-hit {sum(1 for r in x if r['camp_hits'] >= 3)})")
        if args != ['all'] or n >= 3:
            print(f'{m:22} games {n:3}  ' + ' | '.join(line))
    print('TOTAL', dict(tot), 'games', len(games))


if __name__ == '__main__':
    main()
