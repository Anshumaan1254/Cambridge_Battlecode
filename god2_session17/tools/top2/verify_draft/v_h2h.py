"""v_h2h.py (verify_draft): opponent X vs study team Y by team size and opponent comp since T.
Usage: python v_h2h.py --since ISO"""
import sys, collections
sys.path.insert(0, 'C:/battlecode/Cambridge_Battlecode/tools/top2/verify_draft')
from vcommon import *
args = sys.argv[1:]
since = args[args.index('--since') + 1] if '--since' in args else '2026-10-22T18:00:00Z'
M = load_matches(since=since); R, NM, RK = ratings()
opps = {}
for m in M.values():
    for me in m['teams']:
        for key in ('pbg', 'ifish'):
            if not me['teamId'].startswith(STUDY[key]): continue
            op = [t for t in m['teams'] if t is not me][0]
            if op['name'] not in (':3', 'policy wonk', 'procless'): continue
            k = (op['name'], op['teamId'][:8], key, len(picks(op)), '/'.join(NAMES[p] for p in picks(op)))
            opps.setdefault(k, [0, 0]); opps[k][0] += op['result'] == 'win'; opps[k][1] += 1
for k in sorted(opps):
    w, n = opps[k]
    print(f'{k[0]:12s} {k[1]} vs {k[2]:6s} size {k[3]} {k[4]:16s} opp {w}-{n-w}')
tot = collections.defaultdict(lambda: [0, 0])
for k, (w, n) in opps.items():
    t = tot[(k[0], k[3])]; t[0] += w; t[1] += n
print('totals vs pbg+ifish by size:')
for k in sorted(tot): print('  ', k, f'{tot[k][0]}-{tot[k][1]-tot[k][0]}')
