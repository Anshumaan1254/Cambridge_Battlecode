import json, sys
from collections import defaultdict
BASE='/home/claude/cambridge_battlecode/experiments/ladder_nov2'
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def story(mid, body, r_death, back=12, rad=9):
    d=json.load(open(f'{BASE}/dec/{mid}.json'))
    types={b['index']:b['type'] for b in d['meta']['bodies']}; team={b['index']:b['team'] for b in d['meta']['bodies']}
    S={rr['r']:{c[0]:c for c in rr['ch']} for rr in d['rounds'][1:]}
    camps={c['index']:c for c in d['meta']['camps']}
    ev=defaultdict(list)
    for e in d['events']:
        if r_death-back<=e['r']<=r_death: ev[e['r']].append(e)
    t=team[body]
    print(f'== {mid[:8]} body {body} {types[body]} team {t} death r{r_death}')
    for r in range(r_death-back, r_death+1):
        s=S.get(r-1,{}); me=s.get(body)
        if not me or not me[7]: continue
        p=(me[3],me[4])
        near=[]
        for i,c in sorted(s.items()):
            if i!=body and c[7] and cheb((c[3],c[4]),p)<=rad:
                near.append(f"{'A' if team[i]==t else 'E'}{i}:{types[i][:4]}@{c[3]},{c[4]} hp{c[5]} d{cheb((c[3],c[4]),p)}")
        acts=[]
        for e in ev[r]:
            w=e.get('who')
            if w is None:
                if e['k']=='Attack' and 'camp' in e and tuple(e['to'])==p: acts.append(f"camp{e['camp']}({camps[e['camp']]['type']})->me")
                continue
            if w==body or (team[w]!=t and e['k'] in ('Attack','Cast ability','Death')) or (e['k']=='Death'):
                if e['k'] in ('Set priority','Recall','Cancel channel'): continue
                acts.append(f"{w}:{e['k'][:6]}{tuple(e['to']) if 'to' in e else ''}{'/ab'+str(e['ability']) if 'ability' in e else ''}")
        print(f" r{r} me@{p} hp{me[5]}/{me[6]} gems{me[8]} | "+'; '.join(near))
        print('      ', ' | '.join(acts))
if __name__=='__main__':
    story(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv)>4 else 12)
