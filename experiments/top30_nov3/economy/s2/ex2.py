import sys
sys.path.insert(0,'/home/claude/cambridge_battlecode/experiments/top30_nov3/objectives')
from report_stats import load, contested
import common as C
me=load('me'); n=0
for r in me:
    if r.get('ver')!='v88': continue
    we = 0 if r['sides']['0']['id']==C.ME else 1
    for c in r['cycles']:
        if c['mono'] or not contested(c): continue
        rc=c['react'][str(we)]
        if rc and rc['beh'] in ('left',) and c['by']==1-we and n<8:
            print(r['mid'][:8], r['map'], 'G%d %dg start r%d taken r%s by them'%(c['gid'],c['gems'],c['start'],c['taken']), {k:v for k,v in rc.items()})
            n+=1
# wards near spawn example
n=0
for r in me:
    if r.get('ver')!='v88': continue
    we = 0 if r['sides']['0']['id']==C.ME else 1
    w=[x for x in r['wards'] if x['t']==we]
    ns=sum(1 for x in w if x['d_spawn']<=8)
    if len(w)>200 and n<3: print('wards', r['mid'][:8], r['map'], len(w), 'near spawn', ns, 'bush', sum(1 for x in w if x['bush'])); n+=1
