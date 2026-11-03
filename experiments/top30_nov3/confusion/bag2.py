import json, glob
from collections import Counter
R=Counter(); N=Counter(); G=Counter()
for f in glob.glob('out/fl/*.json'):
    o=json.load(open(f))
    if o['tag']=='old': continue
    k='v88' if o['tag']=='v88' else 'top'
    G[k]+=1
    for e in o['ex']:
        if o['tag']=='v88' and e['t']!=o['we']: continue
        if e['cl'] in ('BAG','ENEMY12','ENEMY6','OPEN','LIVEGRP'):
            b='60+' if e['bag']>=60 else ('30-59' if e['bag']>=30 else ('10-29' if e['bag']>=10 else '<10'))
            R[(k,e['cl'],b)]+=e['n']
for cl in ('BAG','ENEMY12','ENEMY6','OPEN','LIVEGRP'):
    for k in ('v88','top'):
        mult = 1 if k=='v88' else 10/2   # top: 10% sample of both sides -> per side-game x10, /2 sides
        print(cl,k,' '.join(f"{b}:{R[(k,cl,b)]*mult/G[k]:.1f}" for b in ('<10','10-29','30-59','60+')), 'rounds/side-game')
