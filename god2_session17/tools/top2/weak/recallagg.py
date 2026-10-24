"""Aggregate tools/top2/weak/recallpun.mjs (an_weak): recall starts by distance to the nearest enemy, share damaged within 5 rounds, outcome.
   python tools/top2/weak/recallagg.py KEY..."""
import json, sys, collections
for key in sys.argv[1:]:
    G = [json.loads(l) for l in open(f'C:/battlecode/cache/an_weak/recall_{key}.jsonl', encoding='utf-8') if l.strip()]
    for side in ['S', 'O']:
        R = [r for g in G for r in g['rec'] if r[0] == side]
        if not R: continue
        out = []
        for lo, hi, lab in [(0, 3, '<=3'), (4, 5, '4-5'), (6, 8, '6-8'), (9, 99, '>8')]:
            B = [r for r in R if lo <= r[2] <= hi]
            if not B: continue
            res = collections.Counter(r[5] for r in B); dm = [r for r in B if r[4]]; nd = [r for r in B if not r[4]]
            out.append(f'{lab}: n {len(B)} ({len(B)/len(G):.1f}/g) home {100*res["home"]/len(B):.0f}% dead {100*res["dead"]/len(B):.0f}% | damaged {100*len(dm)/len(B):.0f}% -> home {100*sum(1 for r in dm if r[5]=="home")/max(1,len(dm)):.0f}% dead {100*sum(1 for r in dm if r[5]=="dead")/max(1,len(dm)):.0f}%; undamaged -> home {100*sum(1 for r in nd if r[5]=="home")/max(1,len(nd)):.0f}%')
        print(f'{key} {side} recalls ({len(R)} in {len(G)} games, hp share mean {sum(r[3] for r in R)/len(R):.2f}):')
        for o in out: print('     ', o)
