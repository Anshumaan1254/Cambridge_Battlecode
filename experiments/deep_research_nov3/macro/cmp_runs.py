#!/usr/bin/env python3
"""Key features: 854-game run (fp_corr_run854.json) vs full 1,201-game run (fp_corr_full.json) -> cmp_runs.txt"""
import json
M = '/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro'
A = {r[0]: r for r in json.load(open(f'{M}/fp_corr_run854.json'))['rows']}
B = {r[0]: r for r in json.load(open(f'{M}/fp_corr_full.json'))['rows']}
K = ['final', 'c_recall', 'c_fight', 'b_kills', 'c_capture', 'b_n_sub', 'big_arr_n', 'pace2_r', 'recall_reposition', 'held_recalls',
     'raid_kills', 'g300_r', 'recall_heal', 'shards300_r', 'raid_caps', 'capby_CI', 'g150_r', 'b_bag_mean', 'capby_Ma', 'capby_HR',
     'st_walk', 'hits_c_share', 'c_hit', 'deaths', 'open_stack', 'mid_share', 'b_locks', 'b_spawnaltar_share', 'goldbank600', 'win1000']
f = lambda v: '   -  ' if v is None else f'{v:6.3f}' if abs(v) < 1 else f'{v:6.1f}'
with open(f'{M}/cmp_runs.txt', 'w') as o:
    print(f'{"feature":20} rho854 rhoFULL |  T5full T20full |  MEfull OPPfull | n(T5l,T20l) full', file=o)
    for k in K:
        a, b = A.get(k), B.get(k)
        if not b:
            continue
        print(f'{k:20} {f(a[1] if a else None)} {f(b[1])} | {f(b[3][0])} {f(b[4][0])} | {f(b[9][0])} {f(b[12][0])} | ({b[7][1]},{b[8][1]})', file=o)
print('ok')
