import sys; sys.path.insert(0,'/home/claude/cambridge_battlecode/experiments/top30_nov3/economy')
from compare import *
T=load('top30'); O=load('ours'); US88=[r for r in O if r['me'] and r['ver']=='v88']
def vis(r): return [v for o in r['opening'].values() for v in o['visits']]
harm=lambda v: set(v['types'])<=set('g$')
for lab,cond in [('harmless >=30g',lambda v: v['gems']>=30 and harm(v)),('attackers >=30g',lambda v: v['gems']>=30 and not harm(v)),('10-29g',lambda v: 10<=v['gems']<30)]:
    def bodies(r):
        V=[v for v in vis(r) if cond(v)]; return mean([len(v['mates'])+1 for v in V]) if V else None
    def solo(r):
        V=[v for v in vis(r) if cond(v)]; return 100*sum(1 for v in V if not v['mates'])/len(V) if V else None
    def kill(r):
        V=[v for v in vis(r) if cond(v)]; return 100*sum(1 for v in V if v['kill'] is not None)/len(V) if V else None
    def hits(r):
        V=[v for v in vis(r) if cond(v)]; return mean([v['n'] for v in V]) if V else None
    for nm,f in [('bodies/visit',bodies),('% solo',solo),('% killed',kill)]:
        a=matched(T,US88,f); print(f'{lab:16} {nm:14} top {a[0]:6.2f} us88 {a[1]:6.2f} ({a[2]} maps, w {a[3]:.0f})')
