import json
V=[json.loads(l) for l in open('out/traj_v88.jsonl')]
from collections import defaultdict
for cl in ('ENEMY12','ENEMY6','OPEN','LIVEGRP'):
    by=defaultdict(int)
    for x in V:
        if x['cl']==cl: by[(x['mid'][:8],x['map'])]+=x['n']
    top=sorted(by.items(), key=lambda kv:-kv[1])[:3]
    print(cl, 'worst games (lost rounds):', top)
    for (m,mp),_ in top[:3]:
        L=sorted([x for x in V if x['cl']==cl and x['mid'][:8]==m], key=lambda x:-x['n'])[:2]
        for x in L: print('   ', m, mp, 'b',x['b'], x['ty'], f"r{x['r0']}-{x['r1']}", 'n',x['n'], 'd0',x.get('d0'), 'dfar',x.get('d_far'), 'first',x.get('first'), 'en_n9',x.get('en_n9'), 'en',x.get('en_ty'), 'hp',x['hp'],'bag',x['bag'],'gs',x['gs'],x['gcl'])
