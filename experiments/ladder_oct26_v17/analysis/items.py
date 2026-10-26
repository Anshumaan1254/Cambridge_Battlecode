"""Item build composition per team at checkpoints. python3 -I items.py SIDES.json DECFILES..."""
import gzip, json, sys, collections
FAM = ['monster','power','durability','treasure','jungle','home','bruiser','tribute','capture','prospector','hunter','skirmish','greed','collectors']
STAT = ['str','foc','hp']
sides = json.load(open(sys.argv[1]))
acc = {w: collections.defaultdict(lambda: collections.Counter()) for w in ('us','them')}
emb = {w: collections.Counter() for w in ('us','them')}
ng = 0
for f in sys.argv[2:]:
    key = f.rsplit('/',1)[-1].replace('.json.gz','')
    if key not in sides: continue
    ours = sides[key]['ours']; ng += 1
    d = json.load(gzip.open(f))
    R = {s['r']: s for s in d['rounds']}
    for cp in (200, 400, 600, 800):
        rs = [r for r in R if r <= cp]
        if not rs: continue
        s = R[max(rs)]
        for c in s['ch']:
            w = 'us' if c[1] == ours else 'them'
            for iid, q in c[11]:
                fam, st, em = iid // 6, (iid % 6) // 2, iid % 2
                acc[w][cp][STAT[st]] += q * (5 if em else 1)
                acc[w][cp]['fam_' + FAM[fam]] += q * (5 if em else 1)
                if cp == 800 and em: emb[w][FAM[fam] + '_' + STAT[st]] += q
print('games', ng)
for cp in (200, 400, 600, 800):
    print('r', cp)
    keys = sorted(set(acc['us'][cp]) | set(acc['them'][cp]))
    for k in keys:
        print(f"  {k:18s} us {acc['us'][cp][k]/ng:6.1f}  them {acc['them'][cp][k]/ng:6.1f}")
print('emblems by r800 us', emb['us'].most_common(12))
print('emblems by r800 them', emb['them'].most_common(12))
