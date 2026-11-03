#!/usr/bin/env python3
"""Timeline of one camp group in one game: python3 -I map_fail/gtrace.py <mid> <gid> [r0 r1]
Each round: group state, camp hp sum, our/their bodies on its tiles (T) or within 3 (n), captures."""
import json, sys
sys.path.insert(0, '/home/claude/cambridge_battlecode/experiments/ladder_nov2/map_fail')
from mapgroups import full_groups
BASE = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
mid, gid = sys.argv[1], int(sys.argv[2])
r0 = int(sys.argv[3]) if len(sys.argv) > 3 else 1
r1 = int(sys.argv[4]) if len(sys.argv) > 4 else 99999
m = [json.loads(l) for l in open(f'{BASE}/matches_me.jsonl') if mid in l][0]
we = 0 if [t for t in m['teams'] if t['teamId'] == ME][0]['side'] == 'a' else 1
d = json.load(open(f'{BASE}/dec/{mid}.json')); mj = json.load(open(f'{BASE}/mj/{mid}.json'))
G = full_groups(m['map'], d['meta'], mj['sym'])[gid]
types = {b['index']: b['type'] for b in d['meta']['bodies']}
team = {b['index']: b['team'] for b in d['meta']['bodies']}
caps = {}
for e in d['events']:
    if e['k'] in ('CaptureGems', 'CaptureGold') and tuple(e['at']) in G['tiles']:
        caps.setdefault(e['r'], []).append(f"{'W' if e['team'] == we else 'T'}{e['who']}+{e['gems']}g")
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
prev = None
for rr in d['rounds'][1:]:
    r = rr['r']
    if r < r0 or r > r1:
        continue
    hp = sum(rr['campHp'][i] for i in G['idx'])
    gr = rr['gr'][gid]
    on = {0: [], 1: []}
    for c in rr['ch']:
        if not c[7]:
            continue
        p = (c[3], c[4])
        dd = min(cheb(p, t) for t in G['tiles'])
        side = 0 if c[1] == we else 1
        if dd == 0:
            on[side].append(f"T{c[0]}{types[c[0]][:3]}")
        elif dd <= 3:
            on[side].append(f"n{c[0]}{types[c[0]][:3]}{c[5]}")
    line = f"hp{hp:>5} gr{gr} we[{' '.join(on[0])}] they[{' '.join(on[1])}] {' '.join(caps.get(r, []))}"
    if line != prev:
        print(f"r{r:>4} {line}")
    prev = line
