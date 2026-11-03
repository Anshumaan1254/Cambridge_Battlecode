#!/usr/bin/env python3
"""Markdown fingerprint table (30 teams + us + reference groups) from fp_team.json, fp_sides.jsonl, draft_team.json -> table.md"""
import json
from collections import Counter, defaultdict
M = '/home/claude/cambridge_battlecode/experiments/deep_research_nov3/macro'
lad = json.load(open('/home/claude/cambridge_battlecode/experiments/top30_nov3/ladder.json'))['teams']
F = json.load(open(f'{M}/fp_team.json'))
tm = F['tm']
D = {d['name']: d for d in json.load(open(f'{M}/draft_team.json'))}
S = [json.loads(l) for l in open(f'{M}/fp_sides.jsonl')]
ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
nE = Counter(s['tid'] for s in S if s['src'] == 'e' and s['grp'] == 'top')
firstemb = defaultdict(Counter)
COLS = [('g300±', 'g300_r', '{:+.0f}'), ('p2±', 'pace2_r', '{:+.1f}'), ('walk%', 'st_walk', 'pct'), ('fight%c', 'c_fight', 'pct'),
        ('recall%c', 'c_recall', 'pct'), ('heldRec', 'held_recalls', '{:.0f}'), ('bigArrN', 'big_arr_n', '{:.2f}'),
        ('trib/g', 'b_n_sub', '{:.1f}'), ('bag', 'b_bag_mean', '{:.0f}'), ('Ma cap%', 'capby_Ma', 'pct'), ('CI cap%', 'capby_CI', 'pct'),
        ('mid%', 'mid_share', 'pct'), ('raids', 'raids', '{:.1f}'), ('locks', 'b_locks', '{:.1f}'), ('deaths', 'deaths', '{:.1f}'),
        ('gold@600', 'goldbank600', '{:.0f}'), ('emb1 r', 'first_emblem_r', '{:.0f}')]


def fmt(v, f):
    if v is None:
        return '-'
    return f'{100 * v:.0f}' if f == 'pct' else f.format(v)


def core(d):
    b = d['by_champs'].get('5') or max(d['by_champs'].values(), key=lambda x: x[0])
    n, top = b[0], b[1]
    return f"{top[0][0]} ({top[0][1]}/{n})" if top else '-'


hdr = ['rk', 'team', 'rating', 'n', 'core roster, 5-champ maps (games)', '1st pick', 'det', 'CI%'] + [c for c, _, _ in COLS]
out = ['| ' + ' | '.join(hdr) + ' |', '|' + '---|' * len(hdr)]
for t in lad[:30]:
    d = D[t['name']]
    v = tm.get(t['teamId'], {})
    fp = d['first'][0]
    row = [str(t['rank']), t['name'], f"{t['rating']:.0f}", str(nE[t['teamId']]), core(d), f"{fp[0]} {100 * fp[1] / d['n']:.0f}%",
           f"{d['det_full']:.2f}", f"{100 * d['pickrate'].get('CI', 0):.0f}"] + [fmt(v.get(k), f) for _, k, f in COLS]
    out.append('| ' + ' | '.join(row) + ' |')


def grp(cond):
    vals = {}
    for _, k, f in COLS:
        xs = [s['f'].get(k) for s in S if cond(s) and s['f'].get(k) is not None]
        vals[k] = sum(xs) / len(xs) if xs else None
    return vals


d = D['HouseOfCoders']
fp = d['first'][0]
for lab, cond, dr in (('**HouseOfCoders v84-v88 (all our decoded games, 80% losses)**', lambda s: s['grp'] == 'ME', True),
                      ('OPP (our opponents, same games)', lambda s: s['grp'] == 'OPP', False),
                      ('TOP-30 losing sides (pooled)', lambda s: s['grp'] == 'top' and s['res'] == 'L', False),
                      ('TOP-30 winning sides (pooled)', lambda s: s['grp'] == 'top' and s['res'] == 'W', False)):
    v = grp(cond)
    n = sum(1 for s in S if cond(s) and s['src'] == 'e')
    row = ['-', lab, '1979' if dr else '-', str(n), core(d) if dr else '-', f"{fp[0]} {100 * fp[1] / d['n']:.0f}%" if dr else '-',
           f"{d['det_full']:.2f}" if dr else '-', f"{100 * d['pickrate'].get('CI', 0):.0f}" if dr else '-'] + [fmt(v.get(k), f) for _, k, f in COLS]
    out.append('| ' + ' | '.join(row) + ' |')
open(f'{M}/table.md', 'w').write('\n'.join(out) + '\n')
print('\n'.join(out[:4]))
print(out[-4])
