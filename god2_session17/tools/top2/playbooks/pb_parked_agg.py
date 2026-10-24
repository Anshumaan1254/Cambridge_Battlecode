# Aggregate pb_parked.mjs / pb_holds.mjs output per study team (S) and its opponents (O), deterministic rematches removed.
#   python tools/top2/playbooks/pb_parked_agg.py [parked|holds]
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from pbcommon import KEYS, ORDER

BASE = 'C:/battlecode/cache/top2_playbooks'
what = sys.argv[1] if len(sys.argv) > 1 else 'parked'
for k in ORDER:
    idx = {}
    for l in open(f'C:/battlecode/cache/t2/{k}/index.jsonl', encoding='utf-8'):
        r = json.loads(l)
        idx[f"{r['map']}_{r['matchId'][:8]}"] = r
    p = f'{BASE}/{what}_{k}.jsonl'
    if not os.path.exists(p):
        continue
    rows = []
    for l in open(p, encoding='utf-8'):
        g = json.loads(l)
        if 'err' in g or g['file'] not in idx:
            continue
        r = idx[g['file']]
        me = [t for t in r['teams'] if t['teamId'].startswith(KEYS[k])][0]
        s = 0 if me['side'] == 'a' else 1
        rows.append((me['result'] == 'win', g['t'][s], g['t'][1 - s], g['file']))
    if what == 'parked':
        for lab, j in [('S', 1), ('O', 2)]:
            runs = [x[j]['runs'] for x in rows]
            rds = [x[j]['rounds'] for x in rows]
            longs = [x[j]['long'] for x in rows if x[j]['long']]
            g100 = np.mean([1 if (x[j]['long'] and x[j]['long'][1] >= 150) else 0 for x in rows])
            top = sorted(longs, key=lambda v: -v[1])[:3]
            print(f"{k} [{lab}] parked runs/game {np.mean(runs):.2f} rounds/game {np.mean(rds):.0f}; games with a >=150-round park {g100:.0%}; longest: {top}")
        w = [x for x in rows if x[0]]
        l = [x for x in rows if not x[0]]
        print(f"     S parked rounds/game in wins {np.mean([x[1]['rounds'] for x in w]):.0f}, losses {np.mean([x[1]['rounds'] for x in l]):.0f}")
    else:
        for lab, j in [('S', 1), ('O', 2)]:
            tot = {kk: sum(x[j][kk] for x in rows) for kk in ['runs', 'rounds', 'camp', 'altar', 'mid', 'their', 'respawnCap']}
            n = len(rows)
            R = max(1, tot['rounds'])
            print(f"{k} [{lab}] hold runs/game {tot['runs']/n:.1f} rounds/game {tot['rounds']/n:.0f}; next to a camp {tot['camp']/R:.0%} (then captured it {tot['respawnCap']/R:.0%}), next to an altar {tot['altar']/R:.0%}, mid zone {tot['mid']/R:.0%}, enemy zone {tot['their']/R:.0%}")
