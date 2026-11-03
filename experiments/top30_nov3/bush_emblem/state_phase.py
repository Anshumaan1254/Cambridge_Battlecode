#!/usr/bin/env python3
"""Emblems k>=1 by phase x gem lead (+-20) at completion: FIGHT / ECON / DEF shares (does the state matter once the phase is held?)."""
import json
from collections import defaultdict, Counter
import emblem as E
T = E.load('top30'); O = E.load('ours')
by = defaultdict(dict)
for r in T + O:
    by[r['mid']][r['team']] = r
US = [r for r in O if r['me'] and r['ver'] in ('v84', 'v85', 'v86', 'v87', 'v88')]
OPP = [r for r in O if not r['me'] and r['ver'] in ('v84', 'v85', 'v86', 'v87', 'v88')]
for lab, rows in (('TOP', T), ('US', US), ('OPP', OPP)):
    S = defaultdict(Counter)
    for r in rows:
        opp = by[r['mid']].get(1 - r['team'])
        if not opp:
            continue
        for b, bd in r['builds'].items():
            k = 0
            for (rr, f, s, e, q) in bd['seq']:
                if not e:
                    continue
                for _ in range(q):
                    if k >= 1:
                        lead = E.cum_gems(r, rr) - E.cum_gems(opp, rr)
                        st = 'ahead' if lead >= 20 else 'behind' if lead <= -20 else 'even'
                        key = (E.ph(rr), st)
                        S[key]['n'] += 1
                        S[key][E.GRP[E.FAM[f]]] += 1
                    k += 1
    for P in ('p2<=400', 'p3<=700', 'p4>700'):
        print(f'{lab:3s} {P}: ' + ' | '.join(f"{st} n={S[(P, st)]['n']}: F{E.pct(S[(P, st)]['FIGHT'], S[(P, st)]['n'])} E{E.pct(S[(P, st)]['ECON'], S[(P, st)]['n'])} D{E.pct(S[(P, st)]['DEF'], S[(P, st)]['n'])}" for st in ('ahead', 'even', 'behind')))
