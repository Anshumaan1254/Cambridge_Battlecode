#!/usr/bin/env python3
"""Which champions farm together: for each camp hit, the same-team partner champions hitting a camp within Chebyshev 3 (+-3 rounds).
usage: pairs.py DMG_DIR=GROUP:L0:L1[,..] --team L [--until R] [--skip contest]"""
import json, sys, glob, os, collections
args = sys.argv[1:]
until = 99999; skip = []; team = None
if '--until' in args: i = args.index('--until'); until = int(args[i+1]); del args[i:i+2]
if '--skip' in args: i = args.index('--skip'); skip = args[i+1].split(','); del args[i:i+2]
if '--team' in args: i = args.index('--team'); team = args[i+1]; del args[i:i+2]
P = collections.defaultdict(float); T = collections.defaultdict(float)
for a in args:
    d, spec = a.split('=', 1)
    labels = {}
    for s in spec.split(','):
        g, l0, l1 = s.split(':'); labels[g] = (l0, l1)
    for f in sorted(glob.glob(os.path.join(d, '*.json'))):
        name = os.path.basename(f)[:-5]
        if any(s in name for s in skip): continue
        g = name[:8]; key = g if g in labels else ('*' if '*' in labels else None)
        if not key: continue
        D = json.load(open(f))
        cpos = {c['index']: (c['x'], c['y']) for c in D['meta']['camps']}
        btype = {b['index']: b['type'] for b in D['meta']['bodies']}; bteam = {b['index']: b['team'] for b in D['meta']['bodies']}
        hits = [(row[0], row[3], row[6], -row[7]) for row in D['dmg'] if row[2] == 'c' and row[5] == 'm' and row[7] < 0 and row[0] <= until]
        byr = collections.defaultdict(list)
        for h in hits: byr[h[0]].append(h)
        for (r, b, c, dmg) in hits:
            t = bteam[b]
            if labels[key][t] != team: continue
            p = cpos.get(c, (0, 0)); parts = set()
            for rr in range(r - 3, r + 4):
                for (_, b2, c2, _) in byr.get(rr, ()):
                    if b2 != b and bteam[b2] == t:
                        q = cpos.get(c2, (0, 0))
                        if max(abs(p[0]-q[0]), abs(p[1]-q[1])) <= 3: parts.add(btype[b2])
            T[btype[b]] += dmg
            if not parts: P[(btype[b], '-solo-')] += dmg
            for x in parts: P[(btype[b], x)] += dmg / len(parts)
for ch in sorted(T):
    row = sorted(((k[1], v) for k, v in P.items() if k[0] == ch), key=lambda kv: -kv[1])
    print(f"{ch:8s} " + '  '.join(f"{n} {100*v/T[ch]:.0f}%" for n, v in row[:6]))
