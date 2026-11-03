import json, sys
sys.path.insert(0,'/home/claude/cambridge_battlecode/experiments/top30_nov3/objectives')
from report_stats import load, contested
import common as C
ECO='/home/claude/cambridge_battlecode/experiments/top30_nov3/economy'
O=[json.loads(l) for l in open(f'{ECO}/rows_ours.jsonl') if '"error"' not in l[:40]]
US88=[r for r in O if r['me'] and r['ver']=='v88']
print('# E1 opening: v88 bodies alone on >=30g groups (r<=150), no kill')
n=0
for r in US88:
    for b,o in r['opening'].items():
        for v in o['visits']:
            if v['gems']>=30 and not v['mates'] and v['kill'] is None and v['first']<=100 and n<6:
                print(f"  {r['mid'][:8]} {r['map']} body {b} {o['champ']} G{v['g']} {v['gems']}g types {v['types']} hits r{v['first']}-{v['last']} n={v['n']} no kill; enemies {v['enemies']}"); n+=1
print('# E2 opening split: v88 games where bodies spread over >=3 groups first')
n=0
for r in US88:
    f=[o['visits'][0]['g'] for o in r['opening'].values() if o['visits']]
    if len(set(f))>=4 and n<4:
        print(f"  {r['mid'][:8]} {r['map']} first groups per body {f} first gem cap r{r['first_cap']} gems150 {r['gems150']}"); n+=1
me=load('me')
print('# E3 contested big cycles hit first by us and taken by them (v88)')
n=0
for r in me:
    if r.get('ver')!='v88': continue
    we = 0 if r['sides']['0']['id']==C.ME else 1
    for c in r['cycles']:
        if c['mono'] or not contested(c) or c['first_hit']!=we or c['by']!=1-we: continue
        rc=c['react'][str(we)]
        if n<6:
            print(f"  {r['mid'][:8]} {r['map']} G{c['gid']} ({c['gems']}g) respawn r{c['start']} first hit r{c['first_hit_r']} us, taken r{c['taken']} by them; hitters us {c['hitters'][str(we)]} them {c['hitters'][str(1-we)]}; contact {rc['beh'] if rc else '-'}")
        n+=1
