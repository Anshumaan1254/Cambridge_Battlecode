#!/usr/bin/env python3
"""Retreats: died within 8 r, into/was-in a bush vs open ground, MH risk difference within strata hp bin x power-ratio bin x map class."""
import json
from collections import defaultdict
from bush_analyze import load, side, mc
G = load()
for grp in ('TOP', 'US', 'OPP', 'US88'):
    S = defaultdict(lambda: [0, 0, 0, 0])
    for g in G:
        for r in g['retreats']:
            s = side(g, r['t'])
            if grp == 'TOP' and s not in ('TW', 'TL'):
                continue
            if grp in ('US', 'OPP') and s != grp:
                continue
            if grp == 'US88' and not (s == 'US' and g['ver'] == 'v88'):
                continue
            hp = r['hp'] or 0
            pw = r['pw'] if r['pw'] is not None else 1
            k = S[(min(3, int(hp * 4)), 0 if pw < 0.3 else 1 if pw < 0.7 else 2 if pw < 1.3 else 3, mc(g['bush_frac']))]
            if r['kind'] in ('into', 'was_in'):
                k[0] += 1; k[1] += bool(r['died8'])
            else:
                k[2] += 1; k[3] += bool(r['died8'])
    num = den = 0
    n1 = n0 = 0
    for k in S.values():
        if k[0] and k[2]:
            w = k[0] * k[2] / (k[0] + k[2]); num += w * (k[1] / k[0] - k[3] / k[2]); den += w; n1 += k[0]; n0 += k[2]
    print(f'{grp:5s} died8 bush-retreat minus open-ground retreat: {100 * num / den:+.1f} points (n {n1} / {n0})')
