#!/usr/bin/env python3
"""Captures in the opening per team label: who captures, when, which side, gems/gold.
usage: opening.py OUT_DIR=GROUP:L0:L1[,..] [--until R] [--team L] [--skip contest]"""
import csv, sys, collections
args = sys.argv[1:]
until = 200; only = None; skip = []
if '--until' in args: i = args.index('--until'); until = int(args[i+1]); del args[i:i+2]
if '--team' in args: i = args.index('--team'); only = args[i+1].split(','); del args[i:i+2]
if '--skip' in args: i = args.index('--skip'); skip = args[i+1].split(','); del args[i:i+2]
by = collections.defaultdict(lambda: collections.defaultdict(list))
games = collections.Counter()
for a in args:
    d, spec = a.split('=', 1)
    labels = {}
    for s in spec.split(','):
        g, l0, l1 = s.split(':'); labels[g] = (l0, l1)
    seen = set()
    for r in csv.DictReader(open(d + '/captures.csv')):
        if any(s in r['match'] for s in skip): continue
        g = r['match'][:8]; key = g if g in labels else ('*' if '*' in labels else None)
        if not key: continue
        lab = labels[key][int(r['team'])]
        if only and lab not in only: continue
        if (r['match'], lab) not in seen: seen.add((r['match'], lab)); games[lab] += 1
        if int(r['r']) <= until:
            by[lab][r['champ']].append((int(r['r']), int(r['gems']), int(r['gold']), r['side']))
    for r in csv.DictReader(open(d + '/team.csv')):
        pass
for lab in sorted(by):
    print(f"== {lab}: captures up to r{until}, per game (games with any capture: {games[lab]})")
    tot = sum(len(v) for v in by[lab].values())
    for ch, v in sorted(by[lab].items(), key=lambda kv: -len(kv[1])):
        n = games[lab]
        side = collections.Counter(x[3] for x in v)
        print(f"   {ch:8s} caps {len(v)/n:4.2f}/game gems {sum(x[1] for x in v)/n:6.1f} gold {sum(x[2] for x in v)/n:6.1f} first r{min(x[0] for x in v)} sides {dict(side)}")
    print(f"   total caps {tot/games[lab]:.2f}/game gems {sum(x[1] for v in by[lab].values() for x in v)/games[lab]:.1f} gold {sum(x[2] for v in by[lab].values() for x in v)/games[lab]:.1f}")
