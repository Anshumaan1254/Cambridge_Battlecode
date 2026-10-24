"""v_purity.py (verify_draft): per team (wr/<id8>.jsonl newest 150): slot purity given map, map+side, map+opponent's earlier
picks; set purity; cm's slot-4 reaction to opponent Marcella.  Usage: python v_purity.py [--since ISO]"""
import sys, collections, json
sys.path.insert(0, 'C:/battlecode/Cambridge_Battlecode/tools/top2/verify_draft')
from vcommon import *
args = sys.argv[1:]
since = args[args.index('--since') + 1] if '--since' in args else None
def purity(items):
    # items: list of (key, value); purity over keys seen >= 2 times
    g = collections.defaultdict(list)
    for k, v in items: g[k].append(v)
    n = sum(len(v) for v in g.values() if len(v) >= 2)
    hit = sum(collections.Counter(v).most_common(1)[0][1] for v in g.values() if len(v) >= 2)
    return hit / n if n else float('nan'), n
for key, id8 in STUDY.items():
    rows = []
    for line in open(f'{ROOT}/experiments/live/lists/wr/{id8}.jsonl', encoding='utf-8'):
        m = json.loads(line)
        if since and m['createdAt'] < since: continue
        me = [t for t in m['teams'] if t['teamId'].startswith(id8)]
        if len(me) != 1: continue
        me = me[0]; op = [t for t in m['teams'] if t is not me][0]
        rows.append((m, me, op))
    out = []
    for slot in range(5):
        it_map = [((m['map'],), picks(me)[slot]) for m, me, op in rows if len(picks(me)) > slot]
        it_side = [((m['map'], me['side']), picks(me)[slot]) for m, me, op in rows if len(picks(me)) > slot]
        it_opp = [((m['map'], tuple(picks(op)[:slot])), picks(me)[slot]) for m, me, op in rows if len(picks(me)) > slot]
        pm, nm = purity(it_map); ps, ns = purity(it_side); po, no = purity(it_opp)
        out.append(f's{slot+1} {pm:.2f}/{ps:.2f}/{po:.2f}(n{nm}/{ns}/{no})')
    sp, sn = purity([((m['map'],), tuple(sorted(picks(me)))) for m, me, op in rows])
    print(f'{key:8s} games {len(rows)} [{min(m["createdAt"] for m,_,_ in rows)[:16]} .. {max(m["createdAt"] for m,_,_ in rows)[:16]}] set-purity {sp:.3f} (n{sn})')
    print('    slot purity map/map+side/map+oppEarlier:', ' '.join(out))
    if key == 'cm':
        c = collections.Counter()
        for m, me, op in rows:
            if len(picks(me)) < 4: continue
            om = 6 in picks(op)[:3]
            c[(om, NAMES[picks(me)[3]])] += 1
        print('    cm slot-4 pick by "opponent picked Marcella in its first 3":', dict(c))
