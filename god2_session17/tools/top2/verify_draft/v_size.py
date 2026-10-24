"""v_size.py (verify_draft): a study team's results by team size since T, opponents' wins vs rating expectation (several k),
per-opponent breakdown.  Usage: python v_size.py TEAMKEY [--since ISO] [--size N]"""
import sys, collections, math
sys.path.insert(0, 'C:/battlecode/Cambridge_Battlecode/tools/top2/verify_draft')
from vcommon import *
args = sys.argv[1:]; key = args[0]
since = args[args.index('--since') + 1] if '--since' in args else '2026-10-22T18:00:00Z'
M = load_matches(since=since); R, NM, RK = ratings()
tid8 = STUDY[key]
rows = []
for m in M.values():
    me = [t for t in m['teams'] if t['teamId'].startswith(tid8)]
    if len(me) != 1: continue
    me = me[0]; op = [t for t in m['teams'] if t is not me][0]
    rows.append(dict(m=m, me=me, op=op, size=len(picks(me)), oppwin=1 if op['result'] == 'win' else 0,
                     ro=R.get(op['teamId']), rm=R.get(me['teamId']), oname=op['name'], opicks=tuple(picks(op))))
print(f'{key}: games since {since}: {len(rows)}; opp unrated: {sum(r["ro"] is None for r in rows)}')
def exp(rs, k):
    return sum(1 / (1 + math.exp(-k * (r['ro'] - r['rm']) / 100)) for r in rs if r['ro'] is not None)
for s in (3, 4, 5):
    rs = [r for r in rows if r['size'] == s]; rr = [r for r in rs if r['ro'] is not None]
    print(f' size {s}: opp wins {sum(r["oppwin"] for r in rs)}/{len(rs)} (rated only {sum(r["oppwin"] for r in rr)}/{len(rr)}); expected k=0.72 {exp(rr,0.72):.1f}, k=0.44 {exp(rr,0.44):.1f}, k=0.10 {exp(rr,0.10):.1f}, k=0 {len(rr)/2:.1f}')
    if '--size' in args and int(args[args.index('--size') + 1]) == s or '--opp' in args:
        c = collections.defaultdict(lambda: [0, 0, None, collections.Counter()])
        for r in rs:
            x = c[r['oname']]; x[0] += r['oppwin']; x[1] += 1; x[2] = r['ro']; x[3]['/'.join(NAMES[p] for p in r['opicks'])] += 1
        for nm, x in sorted(c.items(), key=lambda kv: -kv[1][1]):
            print(f'    {nm:24s} rating {x[2] and round(x[2])} opp W-L {x[0]}-{x[1]-x[0]}  comps {dict(x[3])}')
