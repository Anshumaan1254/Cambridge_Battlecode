#!/usr/bin/env python3
"""killers.py DMG_DIR : per team, camp-group kills by group type with the number of distinct bodies that hit the group during the kill."""
import json,sys,glob,os,collections
def groups_of(camps):
    idx={ (c['x'],c['y']):c['index'] for c in camps}
    par={c['index']:c['index'] for c in camps}
    def f(a):
        while par[a]!=a: par[a]=par[par[a]]; a=par[a]
        return a
    for c in camps:
        for dx,dy in ((1,0),(0,1)):
            j=idx.get((c['x']+dx,c['y']+dy))
            if j is not None: par[f(c['index'])]=f(j)
    g=collections.defaultdict(list)
    for c in camps: g[f(c['index'])].append(c)
    return {c['index']:gid for gid,cs in g.items() for c in cs}, g
agg={0:collections.defaultdict(lambda:[0,0,0.0,0.0]),1:collections.defaultdict(lambda:[0,0,0.0,0.0])}
for f in sorted(glob.glob(sys.argv[1]+'/*unknown.json')):
    d=json.load(open(f)); camps=d['meta']['camps']; cg,gl=groups_of(camps)
    bt={b['index']:b['team'] for b in d['meta']['bodies']}
    # per group: track live hp; a 'kill' when the last camp of the group reaches 0; attackers since the group was last full
    hp={c['index']:c['hp'] for c in camps}; maxhp=dict(hp)
    hitters=collections.defaultdict(set); first=collections.defaultdict(lambda:None)
    for row in d['dmg']:
        r,kind,sk,si,_,tk,ti,delta=row[:8]
        if tk!='m' or sk!='c': continue
        gid=cg[ti]
        if first[gid] is None: first[gid]=r
        hitters[gid].add(si)
        hp[ti]=max(0,hp[ti]+delta)
        if all(hp[c['index']]<=0 for c in gl[gid]):
            team=bt[si]
            typ='+'.join(f"{n}{t}" for t,n in sorted(collections.Counter(c['type'] for c in gl[gid]).items()))
            a=agg[team][typ]; a[0]+=1; a[1]+=len(hitters[gid]); a[2]+=r-first[gid]; a[3]+=sum(maxhp[c['index']] for c in gl[gid])
            for c in gl[gid]: hp[c['index']]=maxhp[c['index']]
            hitters[gid]=set(); first[gid]=None
for team in (0,1):
    print('== team', 'us' if team==0 else 'Nyx')
    for typ,(n,b,dur,mh) in sorted(agg[team].items(), key=lambda x:-x[1][0])[:16]:
        print(f"   {typ:24s} kills {n:4d}  bodies/kill {b/n:4.2f}  rounds/kill {dur/n:6.1f}  hp {mh/n:7.0f}")
