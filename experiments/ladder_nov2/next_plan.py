#!/usr/bin/env python3
"""Make the paired plan for the next candidate: the replayed results of the current one become a column.

    python3 experiments/ladder_nov2/next_plan.py OUT.json COLUMN PLAN [PLAN ...]

For every group of the input plans: if it was replayed (new_group), the replay's results (paired by map and side, as
ladder_loop.py pairs them) are stored under COLUMN (e.g. "v86"; a game without a result is null); then new_group and the
queue fields are cleared. Groups are written in the order given (replayed ones first, so the next paired-run repeats them
first and the comparison with COLUMN fills up before the never-run groups).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ladder_loop as L  # noqa: E402


def main():
    out, col, plans = sys.argv[1], sys.argv[2], sys.argv[3:]
    index = {}
    for m in L.load_local_matches().values():
        index.setdefault(m.get('groupId'), []).append(m)
    budget = [60]
    done, rest = [], []
    for p in plans:
        for g in json.load(open(p)):
            g = dict(g)
            gid = g.get('new_group')
            if gid and not str(gid).startswith('?'):
                games = L.group_games(gid, index, budget)
                pairs = L.pair_group(g, games)
                g[col] = [new for (_, _, _, new) in pairs]
                g[col + '_group'] = gid
                done.append(g)
            else:
                rest.append(g)
            for k in ('new_group', 'new_queued_at', 'new_version'):
                g.pop(k, None)
            g['new_group'] = None
    json.dump(done + rest, open(out, 'w'), indent=1)
    print(f'{out}: {len(done)} groups with {col} results first, then {len(rest)} never replayed')


if __name__ == '__main__':
    main()
