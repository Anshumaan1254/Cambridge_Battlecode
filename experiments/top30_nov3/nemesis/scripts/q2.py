import json, collections
P='/home/claude/cambridge_battlecode/experiments/top30_nov3/nemesis/out/profiles.jsonl'
EASY={'OneTap','eclipsed Sunlight','SilverSamurai'}
rows=[json.loads(l) for l in open(P)]
cells=[('NEM','L'),('EASY','L'),('NEM','W'),('EASY','W')]
C={c:[r for r in rows if (('EASY' if r['opp'] in EASY else 'NEM'),r['res'])==c] for c in cells}
def mean(x): x=[v for v in x if v is not None]; return sum(x)/len(x) if x else float('nan')
for c in cells:
    R=C[c]; n=len(R)
    tb=collections.Counter(v['band'] for r in R for v in r['they_']['first_targets'].values())
    wb=collections.Counter(v['band'] for r in R for v in r['we_']['first_targets'].values())
    # overlap: their first target groups that are also one of our first targets
    ov=mean([len({v['g'] for v in r['they_']['first_targets'].values()} & {v['g'] for v in r['we_']['first_targets'].values()})>0 for r in R])
    # who took the biggest group first (gcap of the max-gem group)
    big_they=[];big_we=[]
    for r in R:
        gs=sorted(r['groups'],key=lambda g:-g['gems'])
        if not gs: continue
        g=gs[0]; v=r['gcap'].get(str(g['id']),[0,0,0,0]); big_we.append(v[0]); big_they.append(v[2])
    # bag at death
    bag=[d['bag'] for r in R for d in r['we_']['deaths_list']]
    bagt=[d['bag'] for r in R for d in r['they_']['deaths_list']]
    print(c,n,'their first-target band',dict(tb),'ours',dict(wb),f'overlap {ov:.2f}',f'biggest group captures we {mean(big_we):.2f} they {mean(big_they):.2f}',
          f'our deaths with bag>=20: {sum(b>=20 for b in bag)/n:.2f}/g, gems {sum(bag)/n:.1f}; theirs {sum(b>=20 for b in bagt)/n:.2f}/g')
    bt=collections.Counter(); bg=collections.Counter()
    for r in R:
        for k,v in r['they_']['bank_by_type'].items(): bt[k]+=v
        for k,v in r['they_']['bank_gems_by_type'].items(): bg[k]+=v
    print('   their banks by type /game', {k:round(v/n,1) for k,v in bt.most_common()}, 'gems/bank', {k:round(bg[k]/bt[k]) for k in bt})
    bt=collections.Counter(); bg=collections.Counter()
    for r in R:
        for k,v in r['we_']['bank_by_type'].items(): bt[k]+=v
    print('   our banks by type /game', {k:round(v/n,1) for k,v in bt.most_common()})
    # deaths of ours by killer champion
    kc=collections.Counter(str(d['killer']) for r in R for d in r['we_']['deaths_list'])
    print('   our killers /game', {k:round(v/n,2) for k,v in kc.most_common(8)})
    vc=collections.Counter(d['champ'] for r in R for d in r['we_']['deaths_list'])
    print('   our dead champs /game', {k:round(v/n,2) for k,v in vc.most_common(8)})
    # deaths by round window
    wd=collections.Counter(min(d['r']//200,5) for r in R for d in r['we_']['deaths_list'])
    print('   our deaths per 200-round window /game', {k*200:round(v/n,2) for k,v in sorted(wd.items())})
    # fights: who hit first and who won, by first
    ff=collections.Counter((f['first'],f['win']) for r in R for f in r['fights']['fights'])
    print('   fights (first,win)/game', {k:round(v/n,2) for k,v in sorted(ff.items(),key=str)})
    nf=collections.Counter((f['num']['we'],f['num']['they']) for r in R for f in r['fights']['fights'] if f['first']=='they')
    print('   they-first fights by (num we, num they)/game', {k:round(v/n,2) for k,v in nf.most_common(6)})
