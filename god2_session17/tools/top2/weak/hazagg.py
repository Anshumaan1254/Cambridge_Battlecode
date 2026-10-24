"""Aggregate tools/top2/weak/tribhaz.mjs output (an_weak): per study team, the per-round hazard that a big tribute channel (bag >= 100)
   ends by self-cancel, by the nearest enemy distance and by champion damage that round; completion of long channels (need >= 20)
   with / without an enemy within 8; the same for their opponents.
   python tools/top2/weak/hazagg.py KEY..."""
import json, sys, collections
def bucket(d):
    return '<=3' if d <= 3 else '4-5' if d <= 5 else '6-8' if d <= 8 else '9-12' if d <= 12 else '>12'
B = ['<=3', '4-5', '6-8', '9-12', '>12']
for key in sys.argv[1:]:
    G = [json.loads(l) for l in open(f'C:/battlecode/cache/an_weak/tribhaz_{key}.jsonl', encoding='utf-8') if l.strip()]
    for side, lab in [(0, 'study'), (1, 'opponents')]:
        n = collections.Counter(); c = collections.Counter(); dm = collections.Counter(); dmc = collections.Counter()
        longs = []
        for g in G:
            for ch in g['ch']:
                if (ch['team'] == g['S']) != (side == 0): continue
                near8 = False
                for i, (dist, cd, kd, sn, end) in enumerate(ch['rows']):
                    if i == 0: continue  # the start round
                    b = bucket(dist); n[b] += 1
                    if end in ('self',): c[b] += 1
                    k = 'champ dmg' if cd > 0 else 'camp dmg' if kd > 0 else 'no dmg'
                    dm[k] += 1
                    if end == 'self': dmc[k] += 1
                    if dist <= 8: near8 = True
                if ch['need'] >= 20:
                    end = next((r[4] for r in reversed(ch['rows']) if r[4]), 'open')
                    longs.append((near8, end, ch['ty']))
        print(f'{key} {lab}: per-round self-cancel hazard by nearest enemy: ' + ', '.join(f'{b} {100*c[b]/n[b]:.1f}% (n {n[b]})' for b in B if n[b]))
        print(f'      by damage: ' + ', '.join(f'{k} {100*dmc[k]/dm[k]:.1f}% (n {dm[k]})' for k in dm))
        for nb in [True, False]:
            L = [x for x in longs if x[0] == nb]
            if L: print(f'      long channels (need >= 20) {"with" if nb else "without"} an enemy within 8: {len(L)}, ends {dict(collections.Counter(x[1] for x in L))}')
