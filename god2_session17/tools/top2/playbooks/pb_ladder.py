# How each study team holds its rating: its 150 newest ranked games (experiments/live/lists/wr/<teamId8>.jsonl) by opponent rating band
# (current ratings, C:/battlecode/cache/ladder_now.json), by map class (team size, map size, objective camps) and by side; the Elo-expected
# score vs the actual one; the opponents it farms and the ones it loses to.
#   python tools/top2/playbooks/pb_ladder.py
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from collections import defaultdict
from pbcommon import KEYS, ORDER, size_class

lad = json.load(open('C:/battlecode/cache/ladder_now.json', encoding='utf-8'))['teams']
rating = {t['teamId']: t['rating'] for t in lad}
rank = {t['teamId']: t['rank'] for t in lad}
geo = {}
for l in open('C:/battlecode/cache/an_strategy/mapgeo2.jsonl', encoding='utf-8'):
    g = json.loads(l)
    geo[g['map']] = g
for k in ORDER:
    tid8 = KEYS[k]
    rows = [json.loads(l) for l in open(f'experiments/live/lists/wr/{tid8}.jsonl', encoding='utf-8')]
    rows = [r for r in rows if r.get('status') == 'finished' and r.get('kind') == 'ranked']
    me_id = [t['teamId'] for t in rows[0]['teams'] if t['teamId'].startswith(tid8)][0]
    R = rating.get(me_id, 0)
    bands = defaultdict(lambda: [0, 0, 0.0])
    cls = defaultdict(lambda: [0, 0])
    opp = defaultdict(lambda: [0, 0])
    exp_tot = 0
    act = 0
    t0 = min(r['createdAt'] for r in rows)
    t1 = max(r['createdAt'] for r in rows)
    for r in rows:
        me = [t for t in r['teams'] if t['teamId'].startswith(tid8)][0]
        ot = [t for t in r['teams'] if not t['teamId'].startswith(tid8)][0]
        win = me['result'] == 'win'
        ro = rating.get(ot['teamId'])
        if ro is None:
            band = 'unrated'
            e = 0.5
        else:
            dd = ro - R
            band = 'opp >= +0' if dd >= 0 else ('opp -0..-100' if dd > -100 else ('opp -100..-200' if dd > -200 else 'opp < -200'))
            e = 1 / (1 + 10 ** ((ro - R) / 400))
        b = bands[band]
        b[0] += 1
        b[1] += win
        b[2] += e
        exp_tot += e
        act += win
        g = geo.get(r['map'])
        n = len(me['draftPicks'])
        sc = size_class(g['W'], g['H']) if g else '?'
        ob = 'obj' if g and (g['feat']['mono'] or g['feat']['golem']) else 'noobj'
        for c in [f'{n}p', sc, ob, f"side {me['side']}"]:
            cls[c][0] += 1
            cls[c][1] += win
        o = opp[ot['name']]
        o[0] += 1
        o[1] += win
    print(f"\n== {k}: rating {R:.0f} rank {rank.get(me_id)}; {len(rows)} ranked games {t0[:16]} .. {t1[:16]}; won {act} ({act/len(rows):.0%}), Elo-expected {exp_tot:.1f} ({exp_tot/len(rows):.0%})")
    for band in ['opp >= +0', 'opp -0..-100', 'opp -100..-200', 'opp < -200', 'unrated']:
        if band in bands:
            n_, w_, e_ = bands[band]
            print(f"   {band:15s} {w_}/{n_} ({w_/n_:.0%}) expected {e_/n_:.0%}")
    print('   classes: ' + ', '.join(f"{c} {v[1]}/{v[0]} ({v[1]/v[0]:.0%})" for c, v in sorted(cls.items())))
    top = sorted(opp.items(), key=lambda kv: -kv[1][0])[:10]
    print('   opponents: ' + ', '.join(f"{o} {v[1]}-{v[0]-v[1]}" for o, v in top))
