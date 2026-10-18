import json,sys,glob,os
seen=set(); tot=[0,0]; n=0
print(f"{'game':32s} {'end':>4s} {'banked':>9s} {'carried@end':>11s} {'meanCarry':>9s} {'maxCarry':>8s}")
for f in sorted(glob.glob(sys.argv[1]+'/rep_*/dmg/*.json')):
    d=json.load(open(f)); R=d['rounds']; last=R[-1]
    key=(os.path.basename(f).split('_',2)[2], last['r'], tuple(last['sub']))
    if key in seen: continue
    seen.add(key); n+=1
    car=[sum(c[8] for c in last['ch'] if c[1]==t and c[7]) for t in (0,1)]
    mc=[sum(sum(c[8] for c in rr['ch'] if c[1]==t and c[7]) for rr in R)/len(R) for t in (0,1)]
    mx=[max(sum(c[8] for c in rr['ch'] if c[1]==t and c[7]) for rr in R) for t in (0,1)]
    for t in (0,1): tot[t]+=car[t]
    print(f"{os.path.basename(f)[:-5]:32s} {last['r']:4d} {last['sub'][0]:4d}-{last['sub'][1]:4d} {car[0]:5d}-{car[1]:5d} {mc[0]:4.0f}-{mc[1]:4.0f} {mx[0]:4d}-{mx[1]:4d}")
print('distinct games',n,'carried at end total',tot)
