# E1 detail: respawn delay vs nominal timer, wait distribution by holder category.
import sys, os
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vagg import *
G = load()
delay = Counter(); waits = defaultdict(Counter)
for g in G:
    for c in g['cyc']:
        grp = g['groups'][c['g']]
        dl = c['resp'] - c['cap_r'] - grp['resp']
        delay[min(dl, 10)] += 1
        if c['next_team'] is None or c['team'] is None or c['first_hit'] is None: continue
        t = c['team']; own, oth = c['hold'][t], c['hold'][1 - t]
        k = 'cap' if own and not oth else ('both' if own and oth else ('other' if oth else 'nobody'))
        w = c['first_hit'] - c['resp']
        waits[k][0 if w == 0 else (1 if w == 1 else (2 if w <= 5 else (6 if w <= 10 else (11 if w <= 20 else 21))))] += 1
print('respawn - capture - nominal timer:', sorted(delay.items()))
for k, v in waits.items():
    n = sum(v.values()); print(k, n, {b: f'{c/n:.0%}' for b, c in sorted(v.items())})
