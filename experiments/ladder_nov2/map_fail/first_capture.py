#!/usr/bin/env python3
"""First capture of each team per game: which group, bodies, first hit on it, kill, capture; the team's earlier visits that did not
end in a capture.   python3 -I map_fail/first_capture.py > map_fail/out/opening_firstcap.txt"""
import json
from collections import defaultdict
B = '/home/claude/cambridge_battlecode/experiments/ladder_nov2/map_fail/out'
rows = [json.loads(l) for l in open(f'{B}/opening.jsonl')]
games = {json.loads(l)['mid']: json.loads(l) for l in open(f'{B}/opening_games.jsonl')}
for mid, gi in sorted(games.items(), key=lambda kv: (kv[1]['map'], kv[1]['res'])):
    print(f"\n== {gi['map']} {mid[:8]} {gi['res']} we side {'AB'[gi['we']]} | first capture we r{gi['first_cap']['we']} they r{gi['first_cap']['they']}")
    for side in ('we', 'they'):
        brs = [r for r in rows if r['mid'] == mid and r['side'] == side]
        fc = gi['first_cap'][side]
        caps = [c for c in gi['caps150'][side] if c[0] == fc]
        if caps:
            gid = caps[0][2]
            vis = [(r['b'], r['champ'][:4], v) for r in brs for v in r['visits'] if v['g'] == gid and v['first'] <= fc]
            gg = [x for x in gi['groups'] if x['id'] == gid][0]
            hit0 = min(v['first'] for _, _, v in vis) if vis else None
            kill = max([v['kill'] for _, _, v in vis if v['kill']] or [None]) if vis else None
            line = (f"  {side:4} first cap r{fc} G{gid} {gg['types']} {gg['gems']}g/{gg['gold']}$ d{gg['d_we'] if side == 'we' else gg['d_they']} "
                    f"bodies {[c[1] for c in caps]} +{sum(c[3] for c in caps)}g/{sum(c[4] for c in caps)}$ | hitters {[(b, ch, v['arrive'], v['first'], v['last']) for b, ch, v in vis]} first hit r{hit0} kill r{kill}")
        else:
            line = f"  {side:4} no capture by r150"
        print(line)
        # visits before the first capture that did not capture (no kill)
        pre = [(r['b'], r['champ'][:4], v) for r in brs for v in r['visits'] if v['first'] < (fc or 151) and not v['cap_r']]
        if pre:
            print('        earlier visits w/o capture: ' + '; '.join(f"b{b}{ch} G{v['g']}({v['gems']}g/{v['gold']}$ d{v['d_spawn']}) r{v['first']}-{v['last']} n{v['n']}{' kill' if v['kill'] else ''}" for b, ch, v in sorted(pre, key=lambda x: x[2]['first'])[:10]))
