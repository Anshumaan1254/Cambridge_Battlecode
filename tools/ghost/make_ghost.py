#!/usr/bin/env python3
"""Build a ghost opponent from ladder replays: a test-only bot that replays one team's recorded actions (moves, attacks, casts,
priorities, wards, tributes, recalls, teleports, altar locks, purchases) for the first R rounds of a game on the same map and side,
then hands over to GOD v18's brain. Against v18 on side A it reproduces the ladder game (deterministic engine and bots); against a
candidate it shows what the candidate would have done against that team's real pressure (open loop: the ghost does not react).

    python tools/ghost/make_ghost.py SIDES.json DECDIR MATCHES.jsonl OUT_BOT [--rounds 400] [--team-side b]

SIDES.json: matchId -> {"ours": our side index, "map": ...}; the ghost replays the OTHER side (must be side b: we play side a).
Writes bots/OUT_BOT (a copy of bots/god18 + src/ghost.cpp, src/ghost_data.h, and a hook in main.cpp).
"""
import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CHAMP = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin']
OP = {'Move': 1, 'Attack': 2, 'Cast0': 3, 'Cast1': 4, 'Prio': 5, 'Ward': 6, 'Submit': 7, 'Recall': 8, 'Cancel': 9, 'Tele': 10, 'Lock': 11, 'Buy': 12, 'Crystal': 13, 'LockBuy': 14}


def map_sig(mapname):
    f = os.path.join(ROOT, 'maps', 's3', mapname.replace('_', '-') + '.map26a')
    out = subprocess.run(['node', os.path.join(ROOT, 'tools', 'replay', 'mapinfo.mjs'), f], capture_output=True, text=True, cwd=ROOT).stdout
    m = re.search(r': (\d+)x(\d+) .* spawnA (\d+),(\d+),(\d+),(\d+)', out.splitlines()[0])
    return tuple(int(x) for x in m.groups())  # w, h, x0, y0, x1, y1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sides')
    ap.add_argument('dec')
    ap.add_argument('matches')
    ap.add_argument('out')
    ap.add_argument('--rounds', type=int, default=400)
    a = ap.parse_args()
    S = json.load(open(a.sides))
    M = {}
    for l in open(a.matches, encoding='utf-8'):
        m = json.loads(l)
        M[m['matchId']] = m
    maps = []
    acts = []
    seen = set()
    for k, v in sorted(S.items(), key=lambda kv: kv[1]['map']):
        if v['ours'] != 0 or v['map'] in seen:
            continue  # the ghost plays side b (index 1)
        seen.add(v['map'])
        d = json.load(gzip.open(os.path.join(a.dec, k + '.json.gz')))
        side = 1
        team = [t for t in M[k]['teams'] if t['side'] == 'b'][0]
        picks = team['draftPicks']
        sig = map_sig(v['map'])
        typ = {b['index']: CHAMP.index(b['type']) for b in d['meta']['bodies'] if b['team'] == side}
        R = {s['r']: {c[0]: c for c in s['ch']} for s in d['rounds']}
        start = len(acts)
        cposs = {(c['x'], c['y']) for c in d['meta']['camps']}

        def tkind(r, t):
            # 1 camp, 2 enemy champion, 0 ground / other (the attack's target kind on the ladder, for the ghost's fallback)
            t = tuple(t)
            if t in cposs:
                return 1
            for rr in (r - 1, r):
                for c in R.get(rr, {}).values():
                    if c[1] != side and c[7] and (c[3], c[4]) == t:
                        return 2
            return 0
        byr = {}
        for e in d['events']:
            if e.get('team') != side or 'who' not in e or e['r'] > a.rounds:
                continue
            byr.setdefault((e['r'], e['who']), []).append(e)
        # future consumable needs per body
        need = {}
        for (r, w), es in byr.items():
            for e in es:
                if e['k'] in ('Teleport channel', 'Place altar lock'):
                    need.setdefault(w, []).append((r, e['k']))
        for r in range(1, a.rounds + 1):
            for w in sorted(typ):
                es = byr.get((r, w), [])
                prev = R.get(r - 1, {}).get(w)
                cur = R.get(r, {}).get(w)
                buys = []
                if prev and cur:
                    pi = {i: n for i, n in prev[11]}
                    for i, n in cur[11]:
                        if n > pi.get(i, 0):
                            buys.append((i, n - pi.get(i, 0)))
                ops = []
                shopped = False
                for e in es:
                    k2 = e['k']
                    t = e.get('to', [0, 0])
                    if k2 == 'Move':
                        ops.append((OP['Move'], t[0], t[1]))
                    elif k2 == 'Attack':
                        ops.append((OP['Attack'] + 100 * tkind(r, t), t[0], t[1]))
                    elif k2 == 'Cast ability':
                        ops.append((OP['Cast0'] + (e.get('slot', 0) & 1) + 100 * tkind(r, t), t[0], t[1]))
                    elif k2 == 'Set priority':
                        p = e.get('priority', -1) & 0xffffffff
                        ops.append((OP['Prio'], p & 0xffff, p >> 16))
                    elif k2 == 'Place ward':
                        ops.append((OP['Ward'], t[0], t[1]))
                    elif k2 == 'Submit gems':
                        ops.append((OP['Submit'], t[0], t[1]))
                    elif k2 == 'Recall':
                        ops.append((OP['Recall'], 0, 0))
                    elif k2 == 'Cancel channel':
                        ops.append((OP['Cancel'], 0, 0))
                    elif k2 == 'Teleport channel':
                        ops.append((OP['Tele'], t[0], t[1]))
                    elif k2 == 'Place altar lock':
                        ops.append((OP['Lock'], t[0], t[1]))
                    elif k2 == 'Shop' and not shopped:
                        shopped = True
                        for i, n in buys:
                            ops.append((OP['Buy'], i, n))
                        buys = []
                        for (rr, kk) in need.get(w, []):
                            if r < rr <= r + 300:
                                ops.append((OP['Crystal'] if kk == 'Teleport channel' else OP['LockBuy'], 0, 0))
                                break
                for i, n in buys:  # purchases without a Shop event (dead bodies)
                    ops.append((OP['Buy'], i, n))
                for op, x, y in ops:
                    acts.append((r, typ[w], op, x, y))
        maps.append((sig, picks, start, len(acts) - start, v['map']))
    sigs = [m[0] for m in maps]
    if len(set(sigs)) != len(sigs):
        print('WARNING: duplicate map signatures', file=sys.stderr)
    dst = os.path.join(ROOT, 'bots', a.out)
    if os.path.exists(os.path.join(dst, 'src')):
        shutil.rmtree(os.path.join(dst, 'src'))
    shutil.copytree(os.path.join(ROOT, 'bots', 'god18', 'src'), os.path.join(dst, 'src'))
    with open(os.path.join(dst, 'src', 'ghost_data.h'), 'w') as f:
        f.write('// generated by tools/ghost/make_ghost.py: %d maps, %d actions, rounds <= %d\n#pragma once\n#include <cstdint>\n' % (len(maps), len(acts), a.rounds))
        f.write('struct GhostMap { int w, h, x0, y0, x1, y1, npick; signed char picks[6]; int start, count; };\n')
        f.write('static const int GHOST_ROUNDS = %d;\nstatic const GhostMap GHOST_MAPS[] = {\n' % a.rounds)
        for sig, picks, st, n, nm in maps:
            pk = list(picks) + [0] * (6 - len(picks))
            f.write('\t{ %d, %d, %d, %d, %d, %d, %d, { %s }, %d, %d }, // %s\n' % (sig[0], sig[1], sig[2], sig[3], sig[4], sig[5], len(picks), ', '.join(map(str, pk)), st, n, nm))
        f.write('};\nstatic const int GHOST_NMAPS = %d;\nstatic const std::int32_t GHOST_ACTS[] = {\n' % len(maps))
        for i in range(0, len(acts), 8):
            f.write(', '.join('%d,%d,%d,%d,%d' % t for t in acts[i:i + 8]) + ',\n')
        f.write('0 };\n')
    shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ghost.cpp'), os.path.join(dst, 'src', 'ghost.cpp'))
    shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ghost.h'), os.path.join(dst, 'src', 'ghost.h'))
    mp = os.path.join(dst, 'src', 'main.cpp')
    s = open(mp, encoding='utf-8').read()
    nl = chr(10)
    s = s.replace('#include "draft.h"', '#include "draft.h"' + nl + '#include "ghost.h"', 1)
    s = s.replace('\t\t\t\tplay_draft();', '\t\t\t\t{' + nl + '\t\t\t\t\tif (!ghost_draft())' + nl + '\t\t\t\t\t\tplay_draft();' + nl + '\t\t\t\t}', 1)
    s = s.replace('\t\t\t\tbrain().turn();', '\t\t\t\tif (!ghost_turn())' + nl + '\t\t\t\t\tbrain().turn();', 1)
    open(mp, 'w', encoding='utf-8', newline='').write(s)
    gi = os.path.join(ROOT, 'bots', 'god18', '.gitignore')
    if os.path.exists(gi):
        shutil.copy(gi, os.path.join(dst, '.gitignore'))
    print('bots/%s: %d maps, %d actions' % (a.out, len(maps), len(acts)))


if __name__ == '__main__':
    main()
