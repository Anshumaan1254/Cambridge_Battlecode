#!/usr/bin/env python3
"""Per-map tables from map_fail/out/games.jsonl + deaths.jsonl.   python3 -I map_fail/summary.py [map ...] > map_fail/out/summary.txt"""
import json, sys
from collections import Counter, defaultdict

BASE = '/home/claude/cambridge_battlecode/experiments/ladder_nov2/map_fail/out'
G = [json.loads(l) for l in open(f'{BASE}/games.jsonl')]
D = [json.loads(l) for l in open(f'{BASE}/deaths.jsonl')]
maps = sys.argv[1:] or list(dict.fromkeys(g['map'] for g in G))
STATES = ['dead', 'spawn', 'walk', 'farm', 'capture', 'fight', 'recall', 'bank', 'block', 'idle']


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float('nan')


for m in maps:
    gs = [g for g in G if g['map'] == m]
    if not gs:
        continue
    W = sum(g['res'] == 'W' for g in gs)
    print(f'\n=================== {m}: {len(gs)} games, {W}-{len(gs) - W}  (champs {gs[0]["champs"]})')
    for g in gs:
        tl = g['tl']
        line = ' '.join(f"{tl[str(r)]['bank_we']:>4}/{tl[str(r)]['bank_they']:<4}" for r in (200, 400, 600, 800))
        print(f"  {g['mid'][:8]} {g['res']} {g['ver']} vs {g['opp'][:18]:18} side {'AB'[g['we']]} r{g['final']:>4} final {g['sub_we']:>4}-{g['sub_they']:<4} "
              f"bank@200/400/600/800 {line} | col {tl['final']['col_we']}/{tl['final']['col_they']} lost {tl['final']['lost_we']}/{tl['final']['lost_they']} "
              f"deaths {g['deaths_we']}/{g['deaths_they']} last_tie r{g['last_tie']} behind150 r{g['behind150']} banks {g['banks']['we']}/{g['banks']['they']} "
              f"tele {g['teleports']['we']}/{g['teleports']['they']} draft {','.join(x[:4] for x in g['draft_we'])} vs {','.join(x[:4] for x in g['draft_they'])}")
    for res in ('L', 'W'):
        sel = [g for g in gs if g['res'] == res]
        if not sel:
            continue
        print(f'  -- {res} ({len(sel)}): mean banked we/they at r200 {mean([g["tl"]["200"]["bank_we"] for g in sel]):.0f}/{mean([g["tl"]["200"]["bank_they"] for g in sel]):.0f}'
              f' r400 {mean([g["tl"]["400"]["bank_we"] for g in sel]):.0f}/{mean([g["tl"]["400"]["bank_they"] for g in sel]):.0f}'
              f' r600 {mean([g["tl"]["600"]["bank_we"] for g in sel]):.0f}/{mean([g["tl"]["600"]["bank_they"] for g in sel]):.0f}'
              f' r800 {mean([g["tl"]["800"]["bank_we"] for g in sel]):.0f}/{mean([g["tl"]["800"]["bank_they"] for g in sel]):.0f}'
              f' | collected@400 {mean([g["tl"]["400"]["col_we"] for g in sel]):.0f}/{mean([g["tl"]["400"]["col_they"] for g in sel]):.0f}'
              f' final {mean([g["tl"]["final"]["col_we"] for g in sel]):.0f}/{mean([g["tl"]["final"]["col_they"] for g in sel]):.0f}'
              f' lost {mean([g["tl"]["final"]["lost_we"] for g in sel]):.0f}/{mean([g["tl"]["final"]["lost_they"] for g in sel]):.0f}'
              f' | deaths {mean([g["deaths_we"] for g in sel]):.1f}/{mean([g["deaths_they"] for g in sel]):.1f}'
              f' | game length {mean([g["final"] for g in sel]):.0f} behind150 r{mean([g["behind150"] for g in sel]):.0f}')
        for side in ('we', 'they'):
            tot = Counter()
            for g in sel:
                tot.update(g['use_' + side])
            n = sum(tot.values()) or 1
            print(f'     time use {side:4}: ' + ' '.join(f'{s} {100 * tot[s] / n:.0f}%' for s in STATES))
        print(f'     camp hits taken while not farming we/they per game {mean([g["passing_camp_hits"]["we"] for g in sel]):.0f}/{mean([g["passing_camp_hits"]["they"] for g in sel]):.0f};'
              f' held recalls {mean([g["held_recalls"]["we"] for g in sel]):.0f}/{mean([g["held_recalls"]["they"] for g in sel]):.0f}'
              f' (failed {mean([g["recall_fail"]["we"] for g in sel]):.1f}/{mean([g["recall_fail"]["they"] for g in sel]):.1f});'
              f' wards {mean([g["wards"]["we"] for g in sel]):.0f}/{mean([g["wards"]["they"] for g in sel]):.0f};'
              f' locks {mean([g["locks"]["we"] for g in sel]):.1f}/{mean([g["locks"]["they"] for g in sel]):.1f}')
    # deaths
    ds = [x for x in D if x['map'] == m and x['side'] == 'we']
    dt = [x for x in D if x['map'] == m and x['side'] == 'they']
    print(f'  our deaths {len(ds)} (their {len(dt)}): ctx ' + ', '.join(f'{k} {v}' for k, v in Counter(x['ctx'] for x in ds).most_common()))
    print(f'     their deaths ctx ' + ', '.join(f'{k} {v}' for k, v in Counter(x['ctx'] for x in dt).most_common()))
    print('     band (own/mid/their) ' + ', '.join(f'{k} {v}' for k, v in Counter(x['band'] for x in ds).most_common())
          + ' | theirs ' + ', '.join(f'{k} {v}' for k, v in Counter(x['band'] for x in dt).most_common()))
    print('     killer ' + ', '.join(f'{k} {v}' for k, v in Counter(x['killer'] for x in ds).most_common()))
    print('     near group ' + ', '.join(f'G{k} {v}' for k, v in Counter(x['group'] for x in ds).most_common(8))
          + ' | theirs ' + ', '.join(f'G{k} {v}' for k, v in Counter(x['group'] for x in dt).most_common(6)))
    print('     victims ' + ', '.join(f'{k} {v}' for k, v in Counter(x['champ'] for x in ds).most_common()))
    print(f"     started by enemy {sum(1 for x in ds if x['started'] == 'enemy')}, own {sum(1 for x in ds if x['started'] == 'own')};"
          f" lure {sum(1 for x in ds if x['lure'])}; camp woken by enemy {sum(1 for x in ds if x['camp_waker'] == 'enemy')};"
          f" bag lost {sum(x['bag'] for x in ds)}; outnumbered(en5>al5+1) {sum(1 for x in ds if (x['en5'] or 0) > (x['al5'] or 0) + 1)};"
          f" alone(al5<0.5) {sum(1 for x in ds if (x['al5'] or 0) < 0.5)}")
    # group captures
    caps = defaultdict(lambda: [0, 0, 0, 0])
    for g in gs:
        for k, v in g['gcap'].items():
            for i in range(4):
                caps[int(k)][i] += v[i]
    grp = {x['id']: x for x in gs[0]['groups']}
    print('  group captures over all games (we n/gems | they n/gems), groups with gems:')
    for k in sorted(caps, key=lambda k: -(caps[k][1] + caps[k][3])):
        if caps[k][1] + caps[k][3] == 0:
            continue
        gg = grp[k]
        print(f"     G{k:<2} {gg['types']:10} {gg['gems']:>3}g resp {gg['resp']} at {tuple(gg['c'])} ({gg['band_we']} for us in side A games)  we {caps[k][0]}/{caps[k][1]}  they {caps[k][2]}/{caps[k][3]}")
    # episodes
    ep = Counter()
    eplen = Counter()
    for g in gs:
        for e in g['episodes']:
            key = (e['kind'], e.get('side'))
            ep[key] += 1
            eplen[key] += e.get('len', 0)
    print('  episodes (kind side: count / rounds): ' + ', '.join(f'{k[0]}:{k[1]} {v}/{eplen[k]}' for k, v in sorted(ep.items())))
