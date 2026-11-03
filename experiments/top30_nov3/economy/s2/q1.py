import sys; sys.path.insert(0,'/home/claude/cambridge_battlecode/experiments/top30_nov3/economy')
from compare import *
T=load('top30'); O=load('ours')
V=('v84','v85','v86','v87','v88')
US=[r for r in O if r['me'] and r['ver'] in V]; US88=[r for r in US if r['ver']=='v88']
OPP88=[r for r in O if not r['me'] and r['ver']=='v88']
TL=[r for r in T if r['res']=='L']
def ph(i,k,den=None):
    def f(r):
        p=r['phases'][i]
        if p is None or p['rounds']<30: return None
        if den: return p[k]/p[den] if p[den] else None
        return 100*p[k]/p['rounds']
    return f
def tot(k,den):
    def f(r):
        ps=[p for p in r['phases'] if p]
        a=sum(p[k] for p in ps); b=sum(p[den] for p in ps)
        return a/b if b else None
    return f
print('label: T|US88  matched ; TL|US88 matched ; OPP88 pooled, US88 pooled')
def L(lab,f):
    a=matched(T,US88,f); b=matched(TL,US88,f)
    print(f'{lab:36} {a[0]:7.2f} {a[1]:7.2f} | TL {b[0]:7.2f} {b[1]:7.2f} | opp {mean([f(r) for r in OPP88]):7.2f} us {mean([f(r) for r in US88]):7.2f}  n={a[2]}')
for i in range(4):
    print('phase',PH[i])
    L(' gold_income/100r',ph(i,'gold_income')); L(' gold_cap/100r',ph(i,'gold_cap'))
    L(' gems per capture',ph(i,'gems','ncap')); L(' gems per hit',ph(i,'gems','hits')); L(' dmg per hit',ph(i,'dmg','hits'))
    L(' captures/100r',ph(i,'ncap')); L(' cap_big gems/100r',ph(i,'cap_big')); L(' gold-group caps/100r',ph(i,'ncap_goldg'))
    L(' hits/100r',ph(i,'hits')); L(' deaths/100r',ph(i,'deaths'))
L('whole: gems per capture',tot('gems','ncap')); L('whole: gems per hit',tot('gems','hits')); L('whole: dmg per hit',tot('dmg','hits'))
L('whole: gold_income per round',tot('gold_income','rounds'))
