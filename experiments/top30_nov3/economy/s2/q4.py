import sys
sys.path.insert(0,'/home/claude/cambridge_battlecode/experiments/top30_nov3/objectives')
from report_stats import load, contested
import common as C
from collections import Counter
for name in ('top','me'):
    G=load(name); cnt=Counter(); tot=Counter()
    for r in G:
        if name=='me' and r.get('ver')!='v88': continue
        sides=[0,1] if name=='top' else [0 if r['sides']['0']['id']==C.ME else 1]
        for we in sides:
            for c in r['cycles']:
                if c['mono'] or not contested(c): continue
                rc=c['react'][str(we)]
                if not rc: continue
                k='1v1 hp>=.8' if rc['n']==1 and rc['n_en']==1 and rc['hp']>=0.8 else ('us>=them' if rc['n']>=rc['n_en'] else 'us<them')
                tot[k]+=1; cnt[(k,rc['beh'])]+=1
    print(name, {k: f"n={tot[k]} left {100*cnt[(k,'left')]/tot[k]:.0f}% farmed {100*cnt[(k,'farmed')]/tot[k]:.0f}% fought {100*cnt[(k,'fought')]/tot[k]:.0f}% died {100*cnt[(k,'died')]/tot[k]:.0f}%" for k in tot})
