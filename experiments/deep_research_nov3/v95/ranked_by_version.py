#!/usr/bin/env python3
"""Ranked record per live version (Nov 2-3) from ladder_nov2/matches_me.jsonl + this folder's fresh lists; Elo expectation with the
opponents' ratings from top30_nov3/ladder.json (snapshot Nov 3 morning; teams not in it are skipped for the expectation).
Usage: python3 -I ranked_by_version.py"""
import json, os, math
from collections import defaultdict
ROOT = '/home/claude/cambridge_battlecode'
V95 = f'{ROOT}/experiments/deep_research_nov3/v95'
ME = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
LAD = {t['teamId']: t for t in json.load(open(f'{ROOT}/experiments/top30_nov3/ladder.json'))['teams']}
US = 1979.0
# live intervals from experiments/ladder_nov2/loop_log.md (UTC)
ERAS = [('2026-11-02T00:00:00', '2026-11-02T21:15:46', 'v84'), ('2026-11-02T21:15:46', '2026-11-03T01:00:56', 'v85'),
        ('2026-11-03T01:00:56', '2026-11-03T01:21:19', 'v86'), ('2026-11-03T01:21:19', '2026-11-03T02:52:00', 'v87'),
        ('2026-11-03T02:52:00', '2026-11-03T04:11:33', 'v88'), ('2026-11-03T04:11:33', '2026-11-03T04:30:53', 'v89'),
        ('2026-11-03T04:30:53', '2026-11-03T04:52:07', 'v88'), ('2026-11-03T04:52:07', '2026-11-03T05:30:53', 'v90'),
        ('2026-11-03T05:30:53', '2026-11-03T05:51:29', 'v88'), ('2026-11-03T05:51:29', '2026-11-03T06:16:00', 'v91'),
        ('2026-11-03T06:16:00', '2026-11-03T10:26:00', 'v88'), ('2026-11-03T10:26:00', '2026-11-03T12:45:05', 'v94'),
        ('2026-11-03T12:45:05', '2026-11-03T12:50:44', 'v95'), ('2026-11-03T12:50:44', '2026-11-03T12:52:30', 'v94/v95?'),
        ('2026-11-03T12:52:30', '2099', 'v95')]


def era(t):
    for a, b, v in ERAS:
        if a <= t < b:
            return v
    return None


rows = {}
for l in open(f'{ROOT}/experiments/ladder_nov2/matches_me.jsonl'):
    try:
        m = json.loads(l)
    except ValueError:
        continue
    rows[m['matchId']] = m
for f in ('all_recent.jsonl', 'ranked_recent.jsonl'):
    for l in open(f'{V95}/{f}'):
        m = json.loads(l)
        rows[m['matchId']] = m
agg = defaultdict(lambda: {'n': 0, 'w': 0, 'exp': 0.0, 'nexp': 0, 'opp': defaultdict(lambda: [0, 0]), 'rat': []})
for m in rows.values():
    if m.get('kind') != 'ranked' or m.get('status') != 'finished' or m['createdAt'] < '2026-11-02T00:00':
        continue
    v = era(m['createdAt'])
    us = [t for t in m['teams'] if t['teamId'] == ME][0]
    th = [t for t in m['teams'] if t['teamId'] != ME][0]
    a = agg[v]
    a['n'] += 1
    w = us['result'] == 'win'
    a['w'] += w
    a['opp'][th['name']][0] += 1
    a['opp'][th['name']][1] += w
    r = LAD.get(th['teamId'], {}).get('rating')
    if r:
        a['exp'] += 1 / (1 + 10 ** ((r - US) / 400))
        a['nexp'] += 1
        a['rat'].append(r)
order = ['v84', 'v85', 'v86', 'v87', 'v88', 'v89', 'v90', 'v91', 'v94', 'v94/v95?', 'v95']
print('version   ranked W/N    win%   Elo-exp wins (of rated n)   mean opp rating   opponents (W/N)')
for v in order:
    a = agg.get(v)
    if not a:
        continue
    ex = f"{a['exp']:.1f} of {a['nexp']}" if a['nexp'] else '-'
    mr = f"{sum(a['rat']) / len(a['rat']):.0f}" if a['rat'] else '-'
    opp = ', '.join(f"{k} {x[1]}/{x[0]}" for k, x in sorted(a['opp'].items(), key=lambda kv: -kv[1][0])[:6]) if a['n'] <= 25 else f"{len(a['opp'])} teams"
    print(f"{v:9s} {a['w']:4d}/{a['n']:<5d} {100 * a['w'] / a['n']:5.1f}   {ex:>20s}   {mr:>8s}   {opp}")
