"""Item totals (shard equivalents: emblem = 5) per side at checkpoints, by family / stat, plus gold held + spent proxy.
    python3 -I items2.py INDEX [sets]"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icx
FAM = ['monster','power','durability','treasure','jungle','home','bruiser','tribute','capture','prospector','hunter','skirmish','greed','collectors']
STAT = ['str','foc','hp']
sets = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
A = collections.defaultdict(collections.Counter); n = 0
for g in icx.games(sys.argv[1], sets):
    n += 1
    for cp in (150, 300, 500, 800):
        rs = [r for r in g.rounds if r <= cp]
        if not rs: continue
        s = g.R[max(rs)]
        for c in s['ch']:
            w = icx.who_side(g, c[1])
            A[(w, cp)]['gold_held'] += c[9]
            for iid, q in c[11]:
                fam, st, em = iid // 6, (iid % 6) // 2, iid % 2
                v = q * (5 if em else 1)
                A[(w, cp)]['tot'] += v; A[(w, cp)][FAM[fam]] += v; A[(w, cp)][STAT[st]] += v
print('games', n)
for cp in (150, 300, 500, 800):
    u, t = A[('us', cp)], A[('ic', cp)]
    keys = ['tot', 'str', 'foc', 'hp', 'treasure', 'monster', 'jungle', 'bruiser', 'power', 'durability', 'gold_held']
    print(f"r{cp}: " + '  '.join(f"{k} {u[k] / n:.1f}/{t[k] / n:.1f}" for k in keys))
