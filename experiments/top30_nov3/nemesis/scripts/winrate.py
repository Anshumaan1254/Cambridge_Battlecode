#!/usr/bin/env python3
"""Our win rate per opponent since Oct 30 (ranked), opponent ladder rating, Elo deficit and its rating-point cost.
Usage: python3 -I winrate.py > ../out/winrate.txt"""
import json, math, collections
B='/home/claude/cambridge_battlecode/experiments'
ME='5a103c90-b00b-4d46-8ace-6a3bb058dc72'
NEM=['shoutout MAPS','KKB','filter','smurphy','Funky monkeys','the ruliad','EggsAfter11AM','dromedaries','OneTap','eclipsed Sunlight','SilverSamurai']
lad=json.load(open(f'{B}/top30_nov3/ladder.json'))['teams']
rat={t['teamId']:t['rating'] for t in lad}; rank={t['teamId']:t['rank'] for t in lad}
myR=rat[ME]
def E(a,b): return 1/(1+10**((b-a)/400))
def perf(rs,w):
    lo,hi=min(rs)-800,max(rs)+800
    for _ in range(60):
        m=(lo+hi)/2
        if sum(E(m,r) for r in rs)<w: lo=m
        else: hi=m
    return (lo+hi)/2
rows=[json.loads(l) for l in open(f'{B}/ladder_nov2/matches_me.jsonl')]
G=[]
for m in rows:
    if m.get('status')!='finished' or m['createdAt']<'2026-10-30': continue
    us=[t for t in m['teams'] if t['teamId']==ME]; th=[t for t in m['teams'] if t['teamId']!=ME]
    if not us or not th: continue
    res=us[0]['result']
    if res not in('win','loss'): continue
    G.append(dict(kind=m['kind'],opp=th[0]['name'],oid=th[0]['teamId'],w=1 if res=='win' else 0,t=m['createdAt'],map=m['map']))
rk=[g for g in G if g['kind']=='ranked']
t0=min(g['t'] for g in rk); t1=max(g['t'] for g in rk)
import datetime
f=lambda s: datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
days=(f(t1)-f(t0)).total_seconds()/86400
print(f'ranked games since Oct 30: {len(rk)} ({t0[:16]} .. {t1[:16]}, {days:.2f} days); unranked {len(G)-len(rk)}; our rating now {myR:.0f}')
known=[g for g in rk if g['oid'] in rat]
rs=[rat[g['oid']] for g in known]; W=sum(g['w'] for g in known)
P=perf(rs,W)
slope=sum(E(P,r)*(1-E(P,r)) for r in rs)*math.log(10)/400   # wins per rating point at P
print(f'perf rating over {len(known)} ranked games with a known opponent rating: {P:.0f} (wins {W}, Elo-expected at {myR:.0f}: {sum(E(myR,r) for r in rs):.1f}); 1 extra win = {1/slope:.2f} perf points')
by=collections.defaultdict(list)
for g in G: by[g['oid']].append(g)
print('\nopponent                 rank rating  ranked W/N  win%  all W/N  ExpW(@perf) deficit(wins) perf-pts  pts/day')
out=[]
for oid,gs in by.items():
    r=[g for g in gs if g['kind']=='ranked']
    if len(gs)<8 and len(r)<8: continue
    nm=gs[0]['opp']; R=rat.get(oid)
    w=sum(g['w'] for g in r); n=len(r)
    exp=sum(E(P,R) for g in r) if R else float('nan')
    d=exp-w
    out.append((d/slope if R else 0,nm,rank.get(oid),R,w,n,sum(g['w'] for g in gs),len(gs),exp,d))
out.sort(reverse=True)
for x in out:
    pts,nm,rk_,R,w,n,wa,na,exp,d=x
    print(f"{nm[:24]:24s} {rk_ if rk_ else '-':>4} {R if R else 0:6.0f}  {w:3d}/{n:<3d}  {100*w/max(1,n):4.0f}  {wa:3d}/{na:<3d}   {exp:6.1f}     {d:+6.1f}     {pts:+6.1f}  {pts/days:+6.1f}  {'NEMESIS-LIST' if nm in NEM else ''}")
nem=[g for g in known if g['opp'] in NEM[:8]]; easy3=[g for g in known if g['opp'] in NEM[8:]]
rest=[g for g in known if g['opp'] not in NEM]
for lab,gs in (('8 nemesis teams',nem),('3 mid teams (OneTap, eclipsed Sunlight, SilverSamurai)',easy3),('everyone else',rest)):
    w=sum(g['w'] for g in gs); exp=sum(E(P,rat[g['oid']]) for g in gs); expm=sum(E(myR,rat[g['oid']]) for g in gs)
    print(f'{lab}: {w}/{len(gs)} ({100*w/max(1,len(gs)):.0f}%), Elo-expected at perf {P:.0f}: {exp:.1f} (at rating {myR:.0f}: {expm:.1f}); deficit {exp-w:+.1f} wins = {(exp-w)/slope:+.1f} perf pts total, {(exp-w)/slope/days:+.1f}/day; games/day {len(gs)/days:.1f}; mean opp rating {sum(rat[g["oid"]] for g in gs)/max(1,len(gs)):.0f}')
# counterfactual: nemesis games at 50% / at Elo-expected
for lab,adj in (('nemesis games at Elo-expected (vs their rating, at perf P)',lambda g:E(P,rat[g['oid']])),('nemesis games at 50%',lambda g:0.5)):
    W2=sum((adj(g) if g['opp'] in NEM[:8] else g['w']) for g in known)
    print(f'counterfactual {lab}: perf {perf(rs,W2):.0f} (+{perf(rs,W2)-P:.0f}); gap to rank 30 (2175) from perf {P:.0f} = {2175-P:.0f}')
# non-nemesis only perf
rs2=[rat[g['oid']] for g in known if g['opp'] not in NEM[:8]]; W3=sum(g['w'] for g in known if g['opp'] not in NEM[:8])
print(f'perf without the 8 nemesis teams: {perf(rs2,W3):.0f} over {len(rs2)} games')
# band table
print('\nby opponent rating band (ranked):')
bands=collections.defaultdict(lambda:[0,0,0.0])
for g in known:
    b=int(rat[g['oid']]//100*100); bands[b][0]+=g['w']; bands[b][1]+=1; bands[b][2]+=E(P,rat[g['oid']])
for b in sorted(bands): w,n,e=bands[b]; print(f'  {b}-{b+99}: {w}/{n} ({100*w/n:.0f}%) expected {e:.1f} deficit {e-w:+.1f}')
