#!/usr/bin/env python3
"""Camp damage solo vs with an ally (same team body hitting a camp within Chebyshev 3 of the same camp, +-3 rounds),
per team label and champion; and spell share of camp damage. usage: cofarm.py DMG_DIR=GROUP:L0:L1[,..] [--until R] [--skip contest]"""
import json, sys, glob, os, collections
args = sys.argv[1:]
until = 99999; skip = []
if '--until' in args: i = args.index('--until'); until = int(args[i+1]); del args[i:i+2]
if '--skip' in args: i = args.index('--skip'); skip = args[i+1].split(','); del args[i:i+2]
A = collections.defaultdict(lambda: collections.defaultdict(float))
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
        camps = D['meta']['camps']
        cpos = {c['index']: (c['x'], c['y']) for c in camps}
        bodies = D['meta']['bodies']
        btype = {b['index']: b['type'] for b in bodies}; bteam = {b['index']: b['team'] for b in bodies}
        hits = []  # (r, body, camp, dmg, spell)
        for row in D['dmg']:
            r, kind, ak, ai, slot, tk, ti, dh = row[:8]
            if ak != 'c' or tk != 'm' or dh >= 0 or r > until: continue
            hits.append((r, ai, ti, -dh, slot not in (-1, 4294967295)))
        byr = collections.defaultdict(list)
        for h in hits: byr[h[0]].append(h)
        for (r, b, c, dmg, spell) in hits:
            t = bteam[b]; lab = labels[key][t]
            p = cpos.get(c, (0, 0))
            partner = False
            for rr in range(r - 3, r + 4):
                for (_, b2, c2, _, _) in byr.get(rr, ()):
                    if b2 != b and bteam[b2] == t and {btype[b], btype[b2]} != {'Cassi', 'Issac'} or (b2 != b and bteam[b2] == t and {btype[b], btype[b2]} == {'Cassi', 'Issac'} and False):
                        q = cpos.get(c2, (0, 0))
                        if max(abs(p[0]-q[0]), abs(p[1]-q[1])) <= 3: partner = True; break
                if partner: break
            k = btype[b]
            A[(lab, k)]['dmg'] += dmg
            A[(lab, k)]['solo'] += 0 if partner else dmg
            A[(lab, k)]['spell'] += dmg if spell else 0
            A[(lab, '*')]['dmg'] += dmg; A[(lab, '*')]['solo'] += 0 if partner else dmg; A[(lab, '*')]['spell'] += dmg if spell else 0
print(f"{'team':5s} {'champ':8s} {'camp dmg':>9s} {'solo %':>7s} {'spell %':>8s}")
for (lab, k), v in sorted(A.items()):
    print(f"{lab:5s} {k:8s} {v['dmg']:9.0f} {100*v['solo']/max(1,v['dmg']):6.1f}% {100*v['spell']/max(1,v['dmg']):7.1f}%")
