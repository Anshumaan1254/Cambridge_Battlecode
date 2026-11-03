import sys; sys.path.insert(0,'/home/claude/cambridge_battlecode/experiments/top30_nov3/economy')
from compare import *
T=load('top30'); O=load('ours')
US88=[r for r in O if r['me'] and r['ver']=='v88']
def vis(r):
    out=[]
    for b,o in r['opening'].items():
        for v in o['visits']: out.append(v)
    return out
def f_waste(r):
    V=vis(r); h=sum(v['n'] for v in V); w=sum(v['n'] for v in V if v['kill'] is None)
    return 100*w/h if h else None
def f_waste_en(r):
    V=vis(r); h=sum(v['n'] for v in V); w=sum(v['n'] for v in V if v['kill'] is None and v['enemies'])
    return 100*w/h if h else None
def f_lost(r):  # killed but captured by enemy, hits share
    V=vis(r); h=sum(v['n'] for v in V); w=sum(v['n'] for v in V if v['kill'] is not None and v.get('cap_team')=='enemy')
    return 100*w/h if h else None
def f_solo_big(r):
    V=[v for v in vis(r) if v['gems']>=30]; 
    if not V: return None
    return 100*sum(1 for v in V if not v['mates'])/len(V)
def f_big_kill(r):
    V=[v for v in vis(r) if v['gems']>=30]
    if not V: return None
    return 100*sum(1 for v in V if v['kill'] is not None)/len(V)
def f_hits_per_kill(r):
    V=vis(r); k=len({(v['g'],v['kill']) for v in V if v['kill'] is not None}); h=sum(v['n'] for v in V)
    return h/k if k else None
for lab,f in [('% opening hits in visits with no kill',f_waste),('  ... with an enemy in the visit',f_waste_en),('% hits on kills the enemy captured',f_lost),
  ('% visits to >=30g groups with no mate',f_solo_big),('% visits to >=30g groups ending in kill',f_big_kill),('hits per distinct kill r1-150',f_hits_per_kill)]:
    a=matched(T,US88,f); print(f'{lab:42} top {a[0]:6.1f} us88 {a[1]:6.1f} ({a[2]} maps)')
import collections
print(collections.Counter(v.get('cap_team') for r in US88 for v in vis(r)))
