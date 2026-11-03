#!/usr/bin/env python3
"""Three-way paired report: the candidate (new_group) against v84 ('old') and, where the plan has it, v85 ('v85').

    python3 experiments/ladder_nov2/three_way.py PLAN [PLAN ...] [--refresh N] [--show-max N]

Uses ladder_loop.py's cache and pairing (same map and side in the replayed group). Prints per-plan totals and the sign test of
the net flips for candidate vs v84 and candidate vs v85 (only games where both results exist).
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ladder_loop as L  # noqa: E402


def sign_p(a, b):
    """Two-sided sign test: a successes vs b failures."""
    n = a + b
    if n == 0:
        return 1.0
    k = min(a, b)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def main():
    args = sys.argv[1:]
    refresh, show_max, plans = 2, 40, []
    while args:
        x = args.pop(0)
        if x == '--refresh':
            refresh = int(args.pop(0))
        elif x == '--show-max':
            show_max = int(args.pop(0))
        else:
            plans.append(x)
    if refresh:
        L.refresh_local(refresh)
    index = {}
    for m in L.load_local_matches().values():
        index.setdefault(m.get('groupId'), []).append(m)
    budget = [show_max]
    tot = {}
    for p in plans:
        plan = json.load(open(p))
        c = {'groups': 0, 'n': 0, 'new_w': 0, 'old_w': 0, 'lw': 0, 'wl': 0, 'pending': 0}
        extra = {}  # column -> [n, col wins, new wins, L->W, W->L]
        for g in plan:
            gid = g.get('new_group')
            if not gid or str(gid).startswith('?'):
                continue
            games = L.group_games(gid, index, budget)
            if any(x['opp'] != g['oppId'] for x in games):
                print(f"  {g.get('opp', '?')[:24]}: opponent differs; skipped")
                continue
            pairs = L.pair_group(g, games)
            c['groups'] += 1
            cols = [k for k in g if k not in ('old', 'maps', 'sides') and isinstance(g[k], list) and len(g[k]) == len(pairs)
                    and all(x in ('win', 'loss', None) for x in g[k])]
            line = []
            for gi, (mp, sd, old, new) in enumerate(pairs):
                if new is None:
                    c['pending'] += 1
                    line.append('.')
                    continue
                c['n'] += 1
                c['new_w'] += new == 'win'
                c['old_w'] += old == 'win'
                c['lw'] += old == 'loss' and new == 'win'
                c['wl'] += old == 'win' and new == 'loss'
                for k in cols:
                    o = g[k][gi]
                    if o in ('win', 'loss'):
                        e = extra.setdefault(k, [0, 0, 0, 0, 0])
                        e[0] += 1
                        e[1] += o == 'win'
                        e[2] += new == 'win'
                        e[3] += o == 'loss' and new == 'win'
                        e[4] += o == 'win' and new == 'loss'
                line.append('W' if new == 'win' else 'L')
            ex = ''.join(f" {k} " + ''.join('W' if o == 'win' else 'L' if o == 'loss' else '.' for o in g[k]) for k in cols)
            print(f"  {g.get('opp', '?')[:22]:<22} v84 {''.join('W' if o == 'win' else 'L' for o in g['old'])}{ex} new {''.join(line)}")
        tot[p] = c
        print(f"{os.path.basename(p)}: {c['groups']} groups, {c['n']} games done ({c['pending']} pending)")
        print(f"   vs v84: new {c['new_w']}/{c['n']} old {c['old_w']}/{c['n']} | flips L->W {c['lw']} W->L {c['wl']} net {c['lw'] - c['wl']:+d}"
              f" p={sign_p(c['lw'], c['wl']):.2f}")
        for k, e in sorted(extra.items()):
            print(f"   vs {k}: new {e[2]}/{e[0]} {k} {e[1]}/{e[0]} | flips L->W {e[3]} W->L {e[4]} net {e[3] - e[4]:+d} p={sign_p(e[3], e[4]):.2f}")
            tot.setdefault('_extra', {}).setdefault(k, [0, 0, 0, 0, 0])
            tot['_extra'][k] = [a + b for a, b in zip(tot['_extra'][k], e)]
    ex_tot = tot.pop('_extra', {})
    if len(tot) > 1:
        lw = sum(c['lw'] for c in tot.values())
        wl = sum(c['wl'] for c in tot.values())
        n = sum(c['n'] for c in tot.values())
        print(f"ALL vs v84: {n} games, flips L->W {lw} W->L {wl} net {lw - wl:+d} p={sign_p(lw, wl):.2f}")
        for k, e in sorted(ex_tot.items()):
            print(f"ALL vs {k}: {e[0]} games, new {e[2]} {k} {e[1]} | flips L->W {e[3]} W->L {e[4]} net {e[3] - e[4]:+d} p={sign_p(e[3], e[4]):.2f}")


if __name__ == '__main__':
    main()
