#!/usr/bin/env python3
"""Draft fingerprint: for each top-10 team's 3 most used rosters, P(team | roster) over all 45 teams' team-games in matches_current.jsonl.
Usage: nice -n 19 python3 -I fingerprint.py -> out/fingerprint.txt"""
import json
from collections import Counter, defaultdict
BASE = '/home/claude/cambridge_battlecode/experiments/top30_nov3'
CH = ['Ryth', 'Vesper', 'Vendetta', 'C&I', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HoR']
lad = json.load(open(f'{BASE}/ladder.json'))['teams']
name = {t['teamId']: t['name'] for t in lad}
rank = {t['teamId']: t['rank'] for t in lad}
seen = set()
by_roster = defaultdict(Counter)
by_team = defaultdict(Counter)
for l in open(f'{BASE}/matches_current.jsonl'):
    m = json.loads(l)
    for t in m['teams']:
        k = (m['matchId'], t['teamId'])
        if k in seen:
            continue
        seen.add(k)
        r = tuple(sorted(t['draftPicks']))
        by_roster[r][t['teamId']] += 1
        by_team[t['teamId']][r] += 1
out = []
for tid in sorted(by_team, key=lambda x: rank.get(x, 99)):
    if rank.get(tid, 99) > 30:
        continue
    cells = []
    for r, n in by_team[tid].most_common(3):
        tot = sum(by_roster[r].values())
        cells.append(f"{'+'.join(CH[i] for i in r)} {n}/{sum(by_team[tid].values())} used, P(team|roster)={n}/{tot}={n / tot:.2f}")
    out.append(f"#{rank[tid]} {name[tid]}: " + ' | '.join(cells))
open('out/fingerprint.txt', 'w').write('\n'.join(out) + '\n')
print('\n'.join(out))
