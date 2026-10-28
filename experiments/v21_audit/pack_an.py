import re,sys,glob,collections,os
d=sys.argv[1]
bands=[(0,400),(400,1000),(1000,2001)]
tot=collections.Counter(); pk=collections.Counter(); fol=collections.Counter(); lead=collections.Counter(); aldanger=collections.Counter(); epk=collections.Counter()
aba=collections.Counter(); abaN=collections.Counter(); ldr_flip=0; ldr_n=0
games=0; pkgames=0
for f in sorted(glob.glob(d+"/*.stdout")):
    games+=1; seen=set(); last={}; pos=collections.defaultdict(dict); anypk=False; prevL={}
    for line in open(f,errors="replace"):
        if line.startswith("PM "):
            m=dict(kv.split("=",1) for kv in line.split()[1:] if "=" in kv)
            if not all(k in m for k in ("r","i","pk","L","T","ep","al")): continue
            r,i=int(m["r"]),int(m["i"])
            if (r,i) in seen: continue
            seen.add((r,i))
            b=next(k for k,(lo,hi) in enumerate(bands) if lo<=r<hi)
            tot[b]+=1
            if m["pk"]=="1":
                pk[b]+=1; anypk=True
                L,T=int(m["L"]),int(m["T"])
                if L>=0 and L!=i and T>=0: fol[b]+=1
                if L==i: lead[b]+=1
                if int(m["ep"])<=30: epk[b]+=1
                elif m["al"]=="1": aldanger[b]+=1
            if i==0:
                L=int(m["L"])
                if L>=0:
                    ldr_n+=1
                    if prevL.get(0) is not None and prevL[0]>=0 and prevL[0]!=L: ldr_flip+=1
                prevL[0]=L
        elif line.startswith("PT "):
            m=dict(kv.split("=",1) for kv in line.split()[1:] if "=" in kv)
            if not all(k in m for k in ("r","i","x","y")): continue
            r,i=int(m["r"]),int(m["i"]); p=(int(m["x"]),int(m["y"]))
            pos[i][r]=p
    pkgames+=anypk
    for i,pr in pos.items():
        for r,p in pr.items():
            if r-1 in pr and r-2 in pr and pr[r-2]==p and pr[r-1]!=p:
                aba[0]+=1
            abaN[0]+= 1
print(f"{os.path.basename(d)}: games {games}, games with pack mode {pkgames}")
for b,(lo,hi) in enumerate(bands):
    t=max(1,tot[b]); print(f"  r{lo}-{hi-1}: body-turns {tot[b]}; pack mode {100*pk[b]/t:.1f}% (enemy pack seen {100*epk[b]/t:.1f}%, ally DANGER alert only {100*aldanger[b]/t:.1f}%); following the leader {100*fol[b]/t:.1f}%; leading {100*lead[b]/t:.1f}%")
print(f"  leader changes seen by body 0: {ldr_flip} per {ldr_n} pack turns; A-B-A steps per 1000 body-turns {1000*aba[0]/max(1,abaN[0]):.1f}")
