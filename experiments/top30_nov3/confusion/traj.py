#!/usr/bin/env python3
"""Second pass on the episodes of flips.py: for ENEMY6 / ENEMY12 loops, the enemy-relative shape of the loop.
   nice -n 19 python3 -I confusion/traj.py [v88|top] > out/traj_<x>.jsonl
Per episode: the nearest enemy at the start (its id), our distance to it at the turn-away round and at the turn-back round, whether the first
move went away from it (FLEE_RETURN) or toward it (APPROACH_ABORT), the enemy's own motion (closing / opening / still), enemies within 9,
allies within 5, enemy on its spawn, our hp and bag."""
import json, os, sys, glob
sys.path.insert(0, '/home/claude/cambridge_battlecode/experiments/top30_nov3/execution')
import h30  # noqa: E402

OUT = '/home/claude/cambridge_battlecode/experiments/top30_nov3/confusion/out'


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def main():
    which = sys.argv[1]
    gs = h30.our_games('v88') if which == 'v88' else [g for g in h30.top_games() if os.path.exists(f"{OUT}/fl/{g['key']}.json")]
    for g in gs:
        f = f"{OUT}/fl/{g['key']}.json"
        if not os.path.exists(f):
            continue
        fl = json.load(open(f))
        eps = [e for e in fl['ex'] if e['cl'] in ('ENEMY6', 'ENEMY12', 'BAG', 'OPEN', 'LIVEGRP')]
        if not eps:
            continue
        d, mj = h30.load(g)
        team = {b['index']: b['team'] for b in d['meta']['bodies']}
        S = {rr['r']: {c[0]: c for c in rr['ch']} for rr in d['rounds'][1:]}
        spawn = {0: [tuple(p) for p in mj['spawnA']], 1: [tuple(p) for p in mj['spawnB']]}
        for e in eps:
            b, t, r0, r1 = e['b'], e['t'], e['r0'], e['r1']
            s0 = S.get(r0 - 1)
            if not s0 or b not in s0:
                continue
            P = {x: (S[x][b][3], S[x][b][4]) for x in range(r0 - 1, r1 + 2) if x in S and S[x][b][7]}
            en = [(cheb(P[r0 - 1], (q[3], q[4])), i) for i, q in s0.items() if q[7] and team[i] != t]
            rec = {'g': g['key'], 'mid': g['mid'], 'map': g['map'], 'tag': g['tag'], 'b': b, 'ty': e['ty'], 'cl': e['cl'], 'r0': r0, 'r1': r1, 'n': e['n'],
                   'hp': e['hp'], 'bag': e['bag'], 'al5': e['al5'], 'gs': e['gs'], 'gcl': e['gcl'], 'dsp': e['dsp'], 'dal': e['dal'],
                   'top_side': (None if g['we'] is not None else ('W' if t == fl['winner'] else 'L'))}
            # farthest point of the loop from its start
            xs = [x for x in range(r0, r1 + 1) if x in P]
            far = max(xs, key=lambda x: cheb(P[x], P[r0 - 1])) if xs else r0
            rec['exc'] = cheb(P[far], P[r0 - 1])
            rec['spawn_d0'] = min(cheb(P[r0 - 1], s) for s in spawn[t])
            rec['spawn_dfar'] = min(cheb(P[far], s) for s in spawn[t])
            if en:
                en.sort()
                d0, j = en[0]
                rec['en_n9'] = sum(1 for dd, _ in en if dd <= 9)
                qj = lambda x: (S[x][j][3], S[x][j][4]) if x in S and S[x][j][7] else None  # noqa: E731
                ej0, ejf, ej1 = qj(r0 - 1), qj(far), qj(r1)
                rec['d0'] = d0
                rec['d_far'] = cheb(P[far], ejf) if ejf else None
                rec['d_end'] = cheb(P[r1], ej1) if (ej1 and r1 in P) else None
                d1 = cheb(P[r0], qj(r0)) if (qj(r0) and r0 in P) else None
                rec['first'] = None if d1 is None else ('away' if d1 > d0 else ('toward' if d1 < d0 else 'side'))
                # our distance to the enemy's start position: did we walk away from where it was?
                rec['far_vs_en0'] = cheb(P[far], ej0) - d0 if ej0 else None
                rec['en_move'] = (cheb(ejf, P[r0 - 1]) - d0) if ejf else None   # < 0: the enemy closed on our start tile
                rec['en_spawn'] = ej0 is not None and min(cheb(ej0, s) for s in spawn[1 - t]) <= 3
                rec['en_ty'] = next(bb['type'] for bb in d['meta']['bodies'] if bb['index'] == j)
            print(json.dumps(rec))


if __name__ == '__main__':
    main()
