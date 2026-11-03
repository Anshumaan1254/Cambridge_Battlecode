#!/usr/bin/env python3
"""Who woke the camp that hits a passing body?  python3 v88_bugs/wake.py [v88L|old_L|old_all]
Every camp hit on a body that did not attack that group in rounds r-2..r ('passive hit') is charged to the last champion damage on
the group before r: by the victim's own team ('own wake') or the other team ('their wake'); own wakes are split by the waker's
last action on the group: a spell from >= 4 tiles that was not followed by a basic attack of the same body within 3 rounds ('chip',
e.g. cast_en_route), or other. Also lists the groups our chips woke that hit us most."""
import json, os, sys, glob
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h88  # noqa: E402
import mapgroups  # noqa: E402
import detect  # noqa: E402

STR = {'wolf': 20, 'elk': 60, 'golem': 120, 'monolith': 200, 5: 120}
BASE = h88.BASE


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
    camp_at = {(c['x'], c['y']): c['index'] for c in meta['camps']}
    G = mapgroups.full_groups(g['map'], meta, mj['sym'])
    camp_group = {ci: gg['id'] for gg in G for ci in gg['idx']}
    S = {rr['r']: {c[0]: c for c in rr['ch']} for rr in d['rounds'][1:]}
    final = meta['finalRound']
    dmg_ev = defaultdict(list)    # gid -> [(r, team, who, kind, dist)]
    hits_on = []                  # (r, body, camp)
    atk_g = defaultdict(set)      # (body, gid) -> rounds
    pos_round = {}
    for e in d['events']:
        r = e['r']
        if r not in pos_round:
            prev = S.get(r - 1) or S.get(r) or {}
            pos_round = {r: {i: (c[3], c[4]) for i, c in prev.items() if c[7]}}
        pos = pos_round[r]
        w = e.get('who')
        if e['k'] == 'Attack' and w is None and e.get('camp') is not None:
            P = tuple(e['to'])
            for j, pj in pos.items():
                if pj == P:
                    hits_on.append((r, j, e['camp']))
            continue
        if w is None:
            continue
        if e['k'] == 'Move' or (e['k'] == 'Cast ability' and e.get('ability') == 6):
            if 'to' in e:
                pos[w] = tuple(e['to'])
            continue
        if e['k'] in ('Attack', 'Cast ability') and 'to' in e:
            P = tuple(e['to'])
            rad = 1 if (e['k'] == 'Cast ability' and e.get('ability') == 3) else 0
            gs = {camp_group[camp_at[q]] for q in camp_at if cheb(q, P) <= rad and camp_at[q] in camp_group}
            for gid in gs:
                dist = cheb(pos.get(w, P), P)
                dmg_ev[gid].append((r, team[w], w, 'spell' if e['k'] == 'Cast ability' else 'atk', dist))
                atk_g[(w, gid)].add(r)
    out = []
    for (r, b, ci) in hits_on:
        gid = camp_group.get(ci)
        if gid is None:
            continue
        if any(x in atk_g[(b, gid)] for x in (r - 2, r - 1, r)):
            continue  # farming it
        prev = [x for x in dmg_ev[gid] if x[0] < r]
        if not prev:
            continue
        lr, lt, lw, lk, ld = prev[-1]
        own = lt == team[b]
        chip = lk == 'spell' and ld >= 4 and not any(x[2] == lw and x[3] == 'atk' and lr <= x[0] <= lr + 3 for x in dmg_ev[gid])
        out.append({'side': 'we' if team[b] == we else 'they', 'r': r, 'b': b, 'champ': types[b], 'g': gid,
                    'ctype': camps[ci]['type'], 'dmg': STR.get(camps[ci]['type'], 20), 'own': own, 'chip': chip and own,
                    'waker': lw, 'waker_champ': types[lw], 'wake_r': lr, 'age': r - lr})
    return out


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else 'v88L'
    if which == 'v88L':
        gs = h88.games('L')
    elif which.startswith('old'):
        gs = detect.old_games()
        if which == 'old_L':
            gs = [x for x in gs if x['res'] == 'L']
    else:
        gs = detect.cp_games()
    h88.ensure_groups(gs)
    rows = []
    for g in gs:
        for x in run(g):
            x['mid'] = g['mid']
            x['map'] = g['map']
            rows.append(x)
    n = max(1, len(gs))
    print(f'{which}: {len(gs)} games; passive camp hits charged to the last waker (damage/game)')
    for side in ('we', 'they'):
        xs = [x for x in rows if x['side'] == side]
        own = [x for x in xs if x['own']]
        chip = [x for x in xs if x['chip']]
        oth = [x for x in xs if not x['own']]
        old = [x for x in own if x['age'] > 30]
        print(f"  {side:4} passive hits {len(xs) / n:5.1f}/g dmg {sum(x['dmg'] for x in xs) / n:5.0f}/g | woken by own team {sum(x['dmg'] for x in own) / n:5.0f}"
              f" (of it by a chip spell from 4+ {sum(x['dmg'] for x in chip) / n:4.0f}; wake older than 30 rounds {sum(x['dmg'] for x in old) / n:4.0f})"
              f" | woken by the other team {sum(x['dmg'] for x in oth) / n:5.0f}")
    # top groups our own chips woke
    agg = defaultdict(lambda: [0, 0, set()])
    for x in rows:
        if x['side'] == 'we' and x['chip']:
            k = (x['mid'][:8], x['map'], x['g'], x['waker_champ'])
            agg[k][0] += 1
            agg[k][1] += x['dmg']
            agg[k][2].add(x['wake_r'])
    print('  our chip wakes that hit us most (mid, map, group, waker): hits, dmg, wake rounds')
    for k, v in sorted(agg.items(), key=lambda kv: -kv[1][1])[:12]:
        print('    ', k, v[0], v[1], sorted(v[2])[:8])
    json.dump(rows, open(f'{h88.V}/out/wake_{which}.json', 'w'))


if __name__ == '__main__':
    main()
