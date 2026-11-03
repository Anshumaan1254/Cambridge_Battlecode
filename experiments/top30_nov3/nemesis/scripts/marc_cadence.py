"""Marcella capture -> next bank: rounds and distance (Chebyshev from the capture tile to where she banked), per side, nemesis vs easy."""
import json, statistics as st, collections
B='/home/claude/cambridge_battlecode/experiments/ladder_nov2'
EASY={'OneTap','eclipsed Sunlight','SilverSamurai'}
acc=collections.defaultdict(lambda: collections.defaultdict(list))
for l in open('/home/claude/cambridge_battlecode/experiments/top30_nov3/nemesis/out/profiles.jsonl'):
    g=json.loads(l); we=g['we']; grp='EASY' if g['opp'] in EASY else 'NEM'
    d=json.load(open(f"{B}/dec/{g['mid']}.json"))
    for b in d['meta']['bodies']:
        if b['type']!='Marcella': continue
        s='we' if b['team']==we else 'they'; i=b['index']
        caps=[(e['r'],tuple(e['at']),e['gems']) for e in d['events'] if e['k']=='CaptureGems' and e.get('who')==i]
        banks=[(e['r'],tuple(e['at']),e['gems']) for e in d['events'] if e['k']=='Banked' and e.get('who')==i]
        deaths=[e['r'] for e in d['events'] if e['k']=='Death' and e.get('who')==i]
        k=(grp,g['res'],s)
        for (r,p,gm) in caps:
            nb=[x for x in banks if x[0]>=r]; nd=[x for x in deaths if x>=r]
            if nb and (not nd or nb[0][0]<nd[0]):
                acc[k]['lat'].append(nb[0][0]-r); acc[k]['dist'].append(max(abs(nb[0][1][0]-p[0]),abs(nb[0][1][1]-p[1])))
                acc[k]['bank20'].append(nb[0][0]-r<=20)
            elif nd and (not nb or nd[0]<=nb[0][0]):
                acc[k]['died_before_bank'].append(1)
            acc[k]['caps'].append(gm)
for k in sorted(acc):
    a=acc[k]; n=len(a['caps'])
    print(k, f"captures {n}, banked within 20 rounds {100*sum(a['bank20'])/max(1,n):.0f}%, median latency {st.median(a['lat']) if a['lat'] else 0}, median capture->bank distance {st.median(a['dist']) if a['dist'] else 0}, died before banking {len(a['died_before_bank'])}")
