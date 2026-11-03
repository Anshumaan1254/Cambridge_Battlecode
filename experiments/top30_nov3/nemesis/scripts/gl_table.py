import json
P='/home/claude/cambridge_battlecode/experiments/top30_nov3/nemesis/out/goldlocks.jsonl'
EASY={'OneTap','eclipsed Sunlight','SilverSamurai'}
rows=[json.loads(l) for l in open(P)]
cells=[('NEM','L'),('EASY','L'),('NEM','W'),('EASY','W')]
C={c:[r for r in rows if (('EASY' if r['opp'] in EASY else 'NEM'),r['res'])==c] for c in cells}
keys=['gold300','gold600','gold','shop','shop300','tp','locks','lock_cancel','lock_cancel_gems','sub','sub_fail','sub_fail_gems','banked_n']
print(f"{'metric':24s}"+''.join(f'{a+"-"+b:>12s}' for a,b in cells))
for k in keys:
    for s in ('we','they'):
        print(f'{k+"_"+s:24s}'+''.join(f'{sum(r[k+"_"+s] for r in C[c])/max(1,len(C[c])):12.2f}' for c in cells))
print('n',[len(C[c]) for c in cells])
import collections
by=collections.defaultdict(list)
for r in rows: by[r['opp']].append(r)
print('\nper team: gold600 they/we, locks they, lock_cancel they (our tributes cancelled by their lock), gems, our sub_fail, tp they')
for o,rs in by.items():
    n=len(rs); f=lambda k: sum(r[k] for r in rs)/n
    print(f"{o[:18]:18s} n{n:3d} gold600 {f('gold600_they'):6.0f}/{f('gold600_we'):6.0f} locks {f('locks_they'):4.1f} lockcancel {f('lock_cancel_they'):4.2f} ({f('lock_cancel_gems_they'):5.1f}g) our subfail {f('sub_fail_we'):4.1f} ({f('sub_fail_gems_we'):5.1f}g) of {f('sub_we'):4.1f}; tp {f('tp_they'):4.1f}")
