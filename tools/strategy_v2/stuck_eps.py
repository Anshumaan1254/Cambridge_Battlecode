#!/usr/bin/env python3
"""stuck_eps.py DMG_DIR [team] : stall episodes (alive body inside a 3x3 box for >= 20 rounds with no attack/cast/capture/channel)."""
import json,sys,glob,os,collections
team=int(sys.argv[2]) if len(sys.argv)>2 else 0
MIN=20
for f in sorted(glob.glob(sys.argv[1]+'/*.json')):
    if 'unknown' not in f: continue
    d=json.load(open(f)); name=os.path.basename(f)[:11]
    bt={b['index']:(b['team'],b['type']) for b in d['meta']['bodies']}
    acts=collections.defaultdict(set)
    for e in d['events']:
        if 'who' in e and e['k'] in ('Attack','Cast ability','Capture','CaptureGems','Submit gems','Recall','Shop','Teleport channel'):
            acts[(e['r'],e['who'])].add(e['k'])
    pos={}
    for rr in d['rounds']:
        for c in rr['ch']:
            pos[(rr['r'],c[0])]=c
    out=[]
    for b,(t,ty) in bt.items():
        if t!=team: continue
        start=None; anchor=None; last=None
        rs=sorted(r for (r,i) in pos if i==b)
        def flush(end):
            if start is not None and end-start>=MIN:
                c=pos[(start,b)]
                out.append((start,end,ty,anchor,c[5],c[6],c[8],c[9]))
        for r in rs:
            c=pos[(r,b)]
            alive=c[7]; p=(c[3],c[4])
            busy=bool(acts.get((r,b)))
            if not alive or busy or anchor is None or max(abs(p[0]-anchor[0]),abs(p[1]-anchor[1]))>1:
                flush(r); start=r if alive and not busy else None; anchor=p if alive else None
            last=r
        flush(last)
    tot=sum(e-s for s,e,*_ in out)
    print(f"== {name} stalled rounds total {tot}")
    for s,e,ty,a,hp,mhp,g,gold in sorted(out)[:14]:
        print(f"   r{s}-{e} ({e-s:3d}) {ty:8s} at {a} hp {hp:.0f}/{mhp:.0f} gems {g} gold {gold}")
