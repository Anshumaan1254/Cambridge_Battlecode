import json, sys
from collections import Counter
def load(f): return [json.loads(l) for l in open(f)]
V=load('out/traj_v88.jsonl'); T=load('out/traj_top.jsonl')
for cl in ('ENEMY12','ENEMY6'):
  for name,L in (('v88',V),('topW',[x for x in T if x['top_side']=='W']),('topL',[x for x in T if x['top_side']=='L'])):
    L=[x for x in L if x['cl']==cl and 'd0' in x]
    if not L: continue
    lost=sum(x['n'] for x in L)
    sh=lambda p: f"{100*sum(x['n'] for x in L if p(x))/max(1,lost):3.0f}%"
    print(f"{cl} {name:5s} eps={len(L)} lost={lost} | first away {sh(lambda x:x['first']=='away')} toward {sh(lambda x:x['first']=='toward')} side {sh(lambda x:x['first']=='side')} | far>d0 (retreat) {sh(lambda x:(x['far_vs_en0'] or 0)>0)} | en closed>=2 {sh(lambda x:(x['en_move'] or 0)<=-2)} en opened>=2 {sh(lambda x:(x['en_move'] or 0)>=2)} | en_n9>=2 {sh(lambda x:x.get('en_n9',0)>=2)} en_spawn {sh(lambda x:x.get('en_spawn'))} | al5>=1 {sh(lambda x:x['al5']>=1)} | toward spawn {sh(lambda x:x['spawn_dfar']<x['spawn_d0'])} exc>=3 {sh(lambda x:x['exc']>=3)}")
    print('   d0 hist:', sorted(Counter(min(x['d0'],13) for x in L).items()))
    print('   d_far hist:', sorted(Counter(min(x['d_far'] or 99,13) for x in L).items()))
print()
for name,L in (('v88',V),('top',T)):
  for first in ('toward','away'):
    X=[x for x in L if x['cl'] in ('ENEMY12','ENEMY6') and x.get('first')==first]
    lost=sum(x['n'] for x in X)
    c=Counter()
    for x in X: c[min(x['d_far'] if first=='toward' else x['d0'],13) if (x['d_far'] is not None) else 99]+=x['n']
    print(name, first, 'lost', lost, ' dist (toward: closest point; away: start) share of lost:', ' '.join(f"{k}:{100*v/lost:.0f}" for k,v in sorted(c.items())))
    print('    bag>=20', f"{100*sum(x['n'] for x in X if x['bag']>=20)/lost:.0f}%", 'hp<.6', f"{100*sum(x['n'] for x in X if x['hp']<.6)/lost:.0f}%", 'en_n9>=2', f"{100*sum(x['n'] for x in X if x.get('en_n9',0)>=2)/lost:.0f}%", 'grp alive', f"{100*sum(x['n'] for x in X if x['gs']=='alive')/lost:.0f}%", 'grp dead/rew', f"{100*sum(x['n'] for x in X if x['gs'] in ('dead','reward'))/lost:.0f}%")
