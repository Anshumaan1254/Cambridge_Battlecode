"""Fit the ladder's per-game K from the rating snapshots in loop_log.md: dR = K * sum(S - E) over ranked games finished between."""
import json
B='/home/claude/cambridge_battlecode/experiments'
ME='5a103c90-b00b-4d46-8ace-6a3bb058dc72'
snap=[('2026-11-02T17:30',1946),('2026-11-02T23:17',1992),('2026-11-02T23:42',1994),('2026-11-03T01:01',1990),('2026-11-03T01:12',1991),('2026-11-03T01:21',2000),('2026-11-03T02:07',1994),('2026-11-03T02:52',2000),('2026-11-03T03:09',1996),('2026-11-03T03:29',1989),('2026-11-03T04:11',1999),('2026-11-03T04:52',2005),('2026-11-03T05:51',1985)]
rat={t['teamId']:t['rating'] for t in json.load(open(f'{B}/top30_nov3/ladder.json'))['teams']}
G=[]
for l in open(f'{B}/ladder_nov2/matches_me.jsonl'):
    m=json.loads(l)
    if m['kind']!='ranked' or m.get('status')!='finished': continue
    us=[t for t in m['teams'] if t['teamId']==ME][0]; th=[t for t in m['teams'] if t['teamId']!=ME][0]
    G.append((m.get('finishedAt') or m['createdAt'],us['result']=='win',rat.get(th['teamId'])))
xs=[];ys=[]
for (ta,ra),(tb,rb) in zip(snap,snap[1:]):
    gs=[g for g in G if ta<=g[0][:16]<tb]
    x=sum(g[1]-1/(1+10**((g[2]-ra)/400)) for g in gs if g[2]); nn=sum(1 for g in gs if g[2]); nu=len(gs)-nn
    xs.append(x); ys.append(rb-ra); print(ta,tb,len(gs),'unk',nu,f'S-E {x:+.2f} dR {rb-ra:+d}')
K=sum(x*y for x,y in zip(xs,ys))/sum(x*x for x in xs)
print(f'K (through origin) = {K:.1f} rating points per unit of (S-E) per game')
