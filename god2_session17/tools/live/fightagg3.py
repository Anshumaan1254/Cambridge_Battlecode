# Extra death breakdowns (camp kills pure/contested, phases, pattern x phase, deaths by engagement starter, approach / flee / even-fight details, bags).
# Uses tools/live/fightagg.py (exec) on C:/battlecode/cache/an_fights/an.jsonl.   python tools/live/fightagg3.py
import json, sys
sys.argv=['x','C:/battlecode/cache/an_fights/an.jsonl','none']
exec(open('C:/battlecode/Cambridge_Battlecode/tools/live/fightagg.py',encoding='utf-8').read())
from collections import Counter
print('\n--- camp kills: pure (no champion damage in the sequence) vs contested; per team-game')
for k, rows in DR.items():
    rr=[x for x in rows if mode2(x)=='camp']
    pure=[x for x in rr if x['natk']==0]; con=[x for x in rr if x['natk']>0]
    print(f'  {k:14s} pure {len(pure)/NG[k]:.2f}/g (r<=300 {sum(x["r"]<=300 for x in pure)/NG[k]:.2f})  contested {len(con)/NG[k]:.2f}/g (r<=300 {sum(x["r"]<=300 for x in con)/NG[k]:.2f})  pure hpS {mean([x["hpS"] for x in pure]):.2f} bag {mean([x["bag"] for x in pure]):.1f}')
print('\n--- deaths per team-game by phase')
for k, rows in DR.items():
    rr=[x for x in rows if mode2(x)!='linked']
    ph=[(0,150),(150,300),(300,600),(600,1000),(1000,2001)]
    print(f'  {k:14s} '+'  '.join(f'r{a}-{b}: {sum(a<x["r"]<=b for x in rr)/NG[k]:.2f}' for a,b in ph))
print('\n--- patterns x phase (us minus them-vs-us, deaths per game)')
pats=sorted(set(pattern(x) for x in DR['us'] if pattern(x)))
for p in pats:
    line=f'  {p:30s}'
    for a,b in [(0,300),(300,600),(600,2001)]:
        u=sum(1 for x in DR['us'] if pattern(x)==p and a<x['r']<=b)/NG['us']
        t=sum(1 for x in DR['them(vs us)'] if pattern(x)==p and a<x['r']<=b)/NG['them(vs us)']
        tt=sum(1 for x in DR['top-vs-top'] if pattern(x)==p and a<x['r']<=b)/NG['top-vs-top']
        line+=f' | r{a}-{b}: us {u:.2f} them {t:.2f} top {tt:.2f}'
    print(line)
print('\n--- our deaths by engagement starter (deaths linked to a champion-hit engagement)')
for k, rows in DR.items():
    rr=[x for x in rows if mode2(x) not in ('linked','camp') and x['eng']]
    own=sum(1 for x in rr if x['eng']['st']==x['team']); oth=len(rr)-own
    print(f'  {k:14s} n={len(rr)} victim side started {pct(own,len(rr))}  other side started {pct(oth,len(rr))}')
print('\n--- approach deaths (all rounds): who killed, power, round, hp, own dmg')
for k, rows in DR.items():
    rr=[x for x in rows if pattern(x)=='walking into them (approach)']
    km=Counter(x['by'] for x in rr)
    print(f'  {k:14s} n={len(rr)} r med {sorted(x["r"] for x in rr)[len(rr)//2] if rr else 0} killers '+', '.join(f'{a} {pct(b,len(rr))}' for a,b in km.most_common(5))+
          f' | mhR8 {mean([x["l8"]["mh"][0]/x["l8"]["mh"][1] for x in rr if x["l8"]["mh"][1]]):.2f} n6 {mean([x["l6"]["n"][0] for x in rr]):.2f}v{mean([x["l6"]["n"][1] for x in rr]):.2f} hpS {mean([x["hpS"] for x in rr]):.2f} own10 {mean([x["own"] for x in rr]):.0f} own0 {pct(sum(x["own"]==0 for x in rr),len(rr))} victim '+', '.join(f'{a} {b}' for a,b in Counter(x["v"] for x in rr).most_common(4)))
print('\n--- fleeing deaths (all rounds): killer melee/dash share, victim type, hp at seq start, seq length')
for k, rows in DR.items():
    for p in ('fleeing after fighting','fleeing, no fight'):
        rr=[x for x in rows if pattern(x)==p]
        print(f'  {k:14s} {p:24s} n={len(rr)} killer melee {mean([1 if x["by"] in MELEE else 0 for x in rr]):.2f} dash {mean([1 if x["by"] in DASH else 0 for x in rr]):.2f} hpS {mean([x["hpS"] for x in rr]):.2f} hp1 {mean([x["hp1"] for x in rr]):.2f} seq {mean([x["seq"] for x in rr]):.1f} natk {mean([x["natk"] for x in rr]):.2f} n6 {mean([x["l6"]["n"][0] for x in rr]):.2f}v{mean([x["l6"]["n"][1] for x in rr]):.2f} victim '+', '.join(f'{a} {b}' for a,b in Counter(x["v"] for x in rr).most_common(4)))
print('\n--- even/ahead fight deaths: the engagement exchange and idle allies')
for k, rows in DR.items():
    rr=[x for x in rows if pattern(x) in ('fight: even/ahead','fight: even numbers, weaker')]
    st=sum(1 for x in rr if x['eng'] and x['eng']['st']==x['team'])
    tr=sum(1 for x in rr if x['trade'])
    print(f'  {k:14s} n={len(rr)} victim side started {pct(st,len(rr))} trade (enemy died within 5r/10t) {pct(tr,len(rr))} idle healthy allies {mean([sum(1 for a in x["allies"] if not a["hit"] and a["hpf"]>=0.5) for x in rr]):.2f} hitting allies {mean([sum(1 for a in x["allies"] if a["hit"]) for x in rr]):.2f} mhR8 {mean([x["l8"]["mh"][0]/x["l8"]["mh"][1] for x in rr if x["l8"]["mh"][1]]):.2f} hpR8 {mean([x["l8"]["hp"][0]/x["l8"]["hp"][1] for x in rr if x["l8"]["hp"][1]]):.2f}')
print('\n--- bags: gems lost per team-game on death (all / r<=300), and deaths with bag >= 20')
for k, rows in DR.items():
    rr=[x for x in rows if mode2(x)!='linked']
    print(f'  {k:14s} {sum(x["bag"] for x in rr)/NG[k]:.0f} / {sum(x["bag"] for x in rr if x["r"]<=300)/NG[k]:.1f}   bag>=20: {sum(x["bag"]>=20 for x in rr)/NG[k]:.2f}/g, mean bag of those {mean([x["bag"] for x in rr if x["bag"]>=20]):.0f}')
