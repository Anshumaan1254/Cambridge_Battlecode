import json, glob, sys, os
from collections import Counter
sys.path.insert(0,'/home/claude/cambridge_battlecode/experiments/top30_nov3/execution')
import h30
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
OUT='out/fl'
gs={g['key']:g for g in h30.our_games('v88')}
res=Counter(); ex=[]
for k,g in gs.items():
    f=f'{OUT}/{k}.json'
    if not os.path.exists(f): continue
    fl=json.load(open(f))
    eps=[e for e in fl['ex'] if e['cl']=='BAG']
    if not eps: continue
    d=json.load(open(g['dec']))
    alt=set(tuple(e['to']) for e in d['events'] if e['k'] in ('Submit gems','Place altar lock') and 'to' in e)
    if not alt: continue
    for e in eps:
        p=[tuple(x) for x in e['path'] if x]
        if len(p)<3: continue
        da=[min(cheb(q,a) for a in alt) for q in p]
        far=max(range(len(p)), key=lambda i: cheb(p[i],p[0]))
        shape='to_altar_then_back' if da[far]<da[0] else ('away_from_altar_then_back' if da[far]>da[0] else 'level')
        res[shape]+=e['n']
        if e['n']>=8 and len(ex)<12: ex.append((g['mid'][:8], g['map'], e['b'], e['ty'], e['r0'], e['r1'], e['bag'], da[0], da[far], shape, e['pre'], e['post']))
tot=sum(res.values()); print({k:f'{100*v/tot:.0f}%' for k,v in res.items()}, tot)
for x in ex: print(x)
