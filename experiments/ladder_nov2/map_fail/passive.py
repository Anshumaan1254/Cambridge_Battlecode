#!/usr/bin/env python3
"""Passive camp damage: runs of rounds in which an awake camp hits one of our bodies while that body hits no camp and no champion.

    nice -n 19 python3 -I map_fail/passive.py [map ...] > map_fail/out/passive.txt   (also out/passive.jsonl)

A run: consecutive rounds (gaps <= 2) with >= 1 camp hit on the body and no camp/champion attack by it; kept when >= 5 hit rounds.
Recorded: hit rounds, estimated damage (camp strength per hit), camp types, enemy champion within 6 at the start, the body standing on
a dead group's tile (waiting / capturing), moved during the run, death within 3 rounds of the end; ours and theirs."""
import json, sys
from collections import Counter, defaultdict
BASE = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
sys.path.insert(0, f'{BASE}/map_fail')
from mapgroups import full_groups  # noqa: E402
from analyze import select, MAPS  # noqa: E402
STR = {'wolf': 20, 'elk': 60, 'golem': 120, 'monolith': 200, 5: 120}


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def run(g):
    mid, we = g['mid'], g['we']
    d = json.load(open(f'{BASE}/dec/{mid}.json'))
    mj = json.load(open(f'{BASE}/mj/{mid}.json'))
    meta = d['meta']
    team = {b['index']: b['team'] for b in meta['bodies']}
    types = {b['index']: b['type'] for b in meta['bodies']}
    camps = {c['index']: c for c in meta['camps']}
    camp_tiles = {(c['x'], c['y']) for c in meta['camps']}
    G = full_groups(g['map'], meta, mj['sym'])
    tile_group = {t: gg['id'] for gg in G for t in gg['tiles']}
    S = {rr['r']: {c[0]: c for c in rr['ch']} for rr in d['rounds'][1:]}
    R = {rr['r']: rr for rr in d['rounds'][1:]}
    final = meta['finalRound']
    hit = defaultdict(lambda: defaultdict(list))  # body -> r -> [camp idx]
    atk = defaultdict(set)
    moved = defaultdict(set)
    died = defaultdict(list)
    pos_ev = defaultdict(dict)
    for e in d['events']:
        r = e['r']
        if e['k'] == 'Attack' and e.get('camp') is not None and 'to' in e:
            P = tuple(e['to'])
            prev = S.get(r - 1, {})
            for b, c in prev.items():
                if c[7] and (c[3], c[4]) == P:
                    hit[b][r].append(e['camp'])
            # bodies that moved onto P this round
            for b, p in pos_ev[r].items():
                if p == P and not any(P == (c[3], c[4]) for bb, c in prev.items() if bb == b):
                    hit[b][r].append(e['camp'])
        elif e.get('who') is not None and e['k'] in ('Attack', 'Cast ability'):
            if e['k'] == 'Cast ability' and e.get('ability') == 6:
                moved[e['who']].add(r)
                pos_ev[r][e['who']] = tuple(e['to'])
                continue
            atk[e['who']].add(r)
        elif e.get('who') is not None and e['k'] == 'Move':
            moved[e['who']].add(r)
            pos_ev[r][e['who']] = tuple(e['to'])
        elif e['k'] == 'Death':
            died[e['who']].append(r)
    rows = []
    for b in team:
        rs = sorted(r for r in hit[b] if r not in atk[b])
        runs = []
        cur = []
        for r in rs:
            if cur and r - cur[-1] <= 3 and not any(x in atk[b] for x in range(cur[-1] + 1, r)):
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
            r0, r1 = run_[0], run_[-1]
            c0 = S.get(r0 - 1, {}).get(b) or S.get(r0, {}).get(b)
            p = (c0[3], c0[4])
            ctypes = Counter(camps[ci]['type'] for r in run_ for ci in hit[b][r])
            dmg = sum(STR.get(camps[ci]['type'], 20) for r in run_ for ci in hit[b][r])
            en = [cheb(p, (q[3], q[4])) for i, q in S.get(r0 - 1, {}).items() if q[7] and team[i] != team[b]]
            on_dead = sum(1 for r in run_ if (lambda c: c is not None and c[7] and (c[3], c[4]) in tile_group and
                                              all(R[r]['campHp'][i] == 0 for i in G[tile_group[(c[3], c[4])]]['idx']))(S.get(r, {}).get(b)))
            mv = sum(1 for r in range(r0, r1 + 1) if r in moved[b])
            cend = S.get(r1, {}).get(b)
            dd = any(r1 - 1 <= x <= r1 + 3 for x in died[b])
            rows.append({'mid': mid, 'map': g['map'], 'res': g['res'], 'side': 'we' if team[b] == we else 'they', 'b': b, 'champ': types[b],
                         'r': r0, 'r1': r1, 'hits': len(run_), 'dmg': dmg, 'types': dict(ctypes), 'enemy_d': min(en) if en else None,
                         'on_dead_tile': on_dead, 'moves': mv, 'hp0': round(c0[5] / max(1, c0[6]), 2),
                         'hp1': round(cend[5] / max(1, cend[6]), 2) if cend and cend[7] else 0, 'died': dd, 'at': p})
    return rows


def main():
    maps = sys.argv[1:] or MAPS
    games = select(maps)
    out = []
    for g in games:
        out += run(g)
    with open(f'{BASE}/map_fail/out/passive.jsonl', 'w') as f:
        for r in out:
            f.write(json.dumps(r) + '\n')
    for m in maps:
        gs = [g for g in games if g['map'] == m]
        rs = [r for r in out if r['map'] == m]
        for side in ('we', 'they'):
            x = [r for r in rs if r['side'] == side]
            print(f"{m:13} {side:4} runs {len(x):3} ({len(x) / len(gs):.1f}/game) hits {sum(r['hits'] for r in x):4} dmg {sum(r['dmg'] for r in x) / len(gs):6.0f}/game"
                  f" | enemy<=6 {sum(1 for r in x if (r['enemy_d'] or 99) <= 6):3} on-dead-tile {sum(1 for r in x if r['on_dead_tile'] >= 3):3}"
                  f" no-move {sum(1 for r in x if r['moves'] == 0):3} died {sum(1 for r in x if r['died']):3} types {dict(sum((Counter(r['types']) for r in x), Counter()))}")


if __name__ == '__main__':
    main()
