#!/usr/bin/env python3
"""Head-to-head summary that counts each distinct game once.

usage: python3 tools/strategy_v2/h2hsum.py BENCH_OUT_DIR [...]   (bench.py --out folders)

Prints, for bot A (the first name in the bench run): wins on the official maps (maps/comp), on the other maps, and on
all distinct maps, with deaths A-B. Maps whose name starts with lad_ are skipped: maps/ladder holds copies of
official maps that replay identically, so they would count the same game twice.
"""
import json, glob, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
for d in sys.argv[1:]:
    runs = glob.glob(os.path.join(d, '*', ''))
    if not runs: continue
    r = runs[0]
    res = {'comp':[0,0,0,0], 'gen':[0,0,0,0]}
    comp = set(os.path.basename(p)[:-7] for p in glob.glob(os.path.join(ROOT, 'maps', 'comp', '*.map26a')))
    for f in glob.glob(r+'*.json'):
        name=os.path.basename(f)[:-5]; mp, side = name.rsplit('_',1)
        if mp.startswith('lad_'): continue
        j=json.load(open(f))
        me = 'teamA' if side=='A' else 'teamB'
        deaths={'teamA':0,'teamB':0}
        for c in j['champions']: deaths[c['team']]+=int(c['metrics']['deaths'])
        k = 'comp' if mp in comp else 'gen'
        res[k][0] += j['match']['outcome']==me; res[k][1] += 1
        res[k][2] += deaths[me]; res[k][3] += deaths['teamB' if me=='teamA' else 'teamA']
    c, g = res['comp'], res['gen']
    tot = [c[i]+g[i] for i in range(4)]
    print(f"{os.path.basename(d.rstrip('/')):22} official {c[0]}/{c[1]} ({100*c[0]/max(1,c[1]):.0f}%) deaths {c[2]}-{c[3]} | generated {g[0]}/{g[1]} | all distinct {tot[0]}/{tot[1]} ({100*tot[0]/max(1,tot[1]):.1f}%) deaths {tot[2]}-{tot[3]}")
