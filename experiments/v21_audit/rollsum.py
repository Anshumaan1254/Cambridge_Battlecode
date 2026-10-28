import re,sys,os,json,glob
S=sys.argv[1]
for v in sys.argv[2:]:
    us=ul=th=tl=0; n=0; fa=0; worst=[]
    for line in open(f"{S}/roll{v}.txt"):
        m=re.search(r'([^/\s]+)_([AB])\.repl26a.*?A=(\d+) \(rounds 1-3: (\d+)\) B=(\d+) \(rounds 1-3: (\d+)\)', line)
        if not m: continue
        mp,side=m.group(1),m.group(2); a,a0,b,b0=map(int,m.groups()[2:])
        mine,mine0,opp,opp0=(a,a0,b,b0) if side=="A" else (b,b0,a,a0)
        us+=mine-mine0; ul+=mine0; th+=opp-opp0; tl+=opp0; n+=1
        if mine-mine0>0: worst.append((mine-mine0,mp+"_"+side))
    for j in glob.glob(f"{S}/keep{v}/god{v}_vs_gpta75/*.json"):
        d=json.load(open(j)); diag=d.get('diagnostics',{})
        fa+= sum(int(x) for x in (diag.get('botFaults') or {}).values()) if isinstance(diag.get('botFaults'),dict) else 0
    worst.sort(reverse=True)
    print(f"v{v}: games {n}; our lost turns after r3 {us} (r1-3 {ul}); v18 opponent {th} (r1-3 {tl}); bot faults (both teams) {fa}; worst {worst[:6]}")
