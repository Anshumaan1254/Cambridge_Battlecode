import json,gzip,glob,collections,sys
S=json.load(open('/tmp/claude-0/v15dl/sides.json'))
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
agg=collections.defaultdict(lambda: collections.defaultdict(list))
for f in sorted(glob.glob('/tmp/claude-0/v15dl/dec/*.json.gz')):
    k=f.split('/')[-1][:-8]; ours=S[k]['ours']; opp=S[k]['opp']
    d=json.load(gzip.open(f))
    for R in d['rounds']:
        r=R['r']
        if r<30: continue
        ph=0 if r<300 else 1 if r<600 else 2
        ch=[c for c in R['ch'] if c[7]]
        for c in ch:
            side='us' if c[1]==ours else 'them'
            al=sum(1 for o in ch if o is not c and o[1]==c[1] and cheb((o[3],o[4]),(c[3],c[4]))<=5)
            en=sum(1 for o in ch if o[1]!=c[1] and cheb((o[3],o[4]),(c[3],c[4]))<=7)
            agg[(opp,ph,side)]['al5'].append(al)
            agg[(opp,ph,side)]['alone'].append(1 if al==0 else 0)
            if en>0:
                agg[(opp,ph,side)]['al5_whenE'].append(al)
                agg[(opp,ph,side)]['outnum'].append(1 if en>al+1 else 0)
                agg[(opp,ph,side)]['ahead'].append(1 if al+1>en else 0)
for key in sorted(agg):
    a=agg[key]; m=lambda x: sum(x)/len(x) if x else float('nan')
    print(key, 'allies<=5 %.2f alone %.2f | enemy<=7: allies %.2f outnumbered %.2f we-outnumber %.2f (n=%d)'%(m(a['al5']),m(a['alone']),m(a['al5_whenE']),m(a['outnum']),m(a['ahead']),len(a['outnum'])))
