import json,gzip,glob,collections,sys
S=json.load(open(sys.argv[1])); dec=sys.argv[2]
res=collections.Counter(); tot=collections.Counter()
for f in sorted(glob.glob(dec+'/*.json.gz')):
    k=f.split('/')[-1][:-8]
    if k not in S: continue
    ours=S[k]['ours']; d=json.load(gzip.open(f)); B=d['meta']['bodies']
    pos={}  # (round, who) -> (x,y)
    for R in d['rounds']:
        for c in R['ch']: pos[(R['r'],c[0])]=(c[3],c[4],c[7])
    def occ(r,xy,team):
        for b in B:
            p=pos.get((r,b['index']))
            if p and p[2] and b['team']==team and (p[0],p[1])==tuple(xy): return b['index']
        return None
    hits=[]  # (r, attacker, victim)
    for e in d['events']:
        if e['k'] in ('Attack','Cast ability') and e.get('who') is not None and e.get('to'):
            a=e['who']; ta=B[a]['team']
            v=occ(e['r'],e['to'],1-ta)
            if v is None: v=occ(e['r']-1,e['to'],1-ta)
            if v is not None: hits.append((e['r'],a,v))
    for e in d['events']:
        if e['k']!='Death': continue
        w=e['who']; t=B[w]['team']
        side='us' if t==ours else 'them'
        r=e['r']
        win=[h for h in hits if r-15<=h[0]<=r]
        fv=[h for h in win if h[1]==w]           # victim hit an enemy
        fe=[h for h in win if h[2]==w]           # an enemy hit the victim
        if not fe: res[(side,'no champ hits (camp?)')]+=1; continue
        first_e=min(h[0] for h in fe); first_v=min((h[0] for h in fv), default=9999)
        # did ANY teammate of the victim hit first in the area?
        res[(side,'victim hit first' if first_v<first_e else 'same round' if first_v==first_e else 'enemy hit first')]+=1
for k in sorted(res): print(k,res[k])
