import json, collections
P='/home/claude/cambridge_battlecode/experiments/top30_nov3/nemesis/out/profiles.jsonl'
EASY={'OneTap','eclipsed Sunlight','SilverSamurai'}
rows=[json.loads(l) for l in open(P)]
cells=[('NEM','L'),('EASY','L'),('NEM','W'),('EASY','W')]
C={c:[r for r in rows if (('EASY' if r['opp'] in EASY else 'NEM'),r['res'])==c] for c in cells}
def mean(x): x=[v for v in x if v is not None]; return sum(x)/len(x) if x else float('nan')
for c in cells:
    R=[r for r in C[c] if 'Marcella' in r['they_']['draft']]; n=len(R)
    Rw=[r for r in C[c] if 'Marcella' in r['we_']['draft']]
    print(c,'games with their Marcella',n,f"their marc spell champ hits {mean([r['they_']['marc_spell_champ'] for r in R]):.1f} (r4 {mean([r['they_']['marc_spell_champ_r4'] for r in R]):.1f}); ours (games with our Marcella {len(Rw)}) {mean([r['we_']['marc_spell_champ'] for r in Rw]):.1f} (r4 {mean([r['we_']['marc_spell_champ_r4'] for r in Rw]):.1f})")
    D=[d for r in R for d in r['we_']['deaths_list'] if d['killer']=='Marcella']
    print('   our deaths to Marcella /game',round(len(D)/n,2),'ctx',dict(collections.Counter(d['ctx'] for d in D)),'started',dict(collections.Counter(d['started'] for d in D)),'band',dict(collections.Counter(d['band'] for d in D)))
    print('   at death: hp5 %.2f al5 %.2f en5 %.2f bag %.1f stunned3 %.2f lure %.2f' % tuple(mean([d[k] for d in D]) for k in ('hp5','al5','en5','bag','stunned3','lure')))
    kd=[r['they_']['deaths'] for r in R]
    # their deaths to our Marcella
    E=[d for r in Rw for d in r['they_']['deaths_list'] if d['killer']=='Marcella']
    print('   their deaths to our Marcella /game', round(len(E)/max(1,len(Rw)),2))
    # by our dead champ
    print('   our dead champ (killer Marcella)', dict(collections.Counter(d['champ'] for d in D).most_common()))
    # round
    print('   rounds', dict(sorted(collections.Counter(min(d['r']//200,5)*200 for d in D).items())))
# example deaths to their Marcella in NEM-L
ex=[(r['mid'],r['opp'],r['map'],d['r'],d['b'],d['champ'],d['ctx'],d['en5'],d['al5'],round(d['hp5'],2) if d['hp5'] is not None else None,d['bag']) for r in C[('NEM','L')] for d in r['we_']['deaths_list'] if d['killer']=='Marcella' and r['ver'] in('v88',)]
print('v88 examples', len(ex)); [print('  ',e) for e in ex[:12]]
print(collections.Counter(r['ver'] for r in rows))
