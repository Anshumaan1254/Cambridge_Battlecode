# pbg vs ifish games in the index (count, results)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vlib import *
idx = load_index()
n = 0; pw = 0
for b, e in sorted(idx.items()):
    if 'pbg' in e['keys'] and 'ifish' in e['keys']:
        n += 1; p = team_of_key(e['row'], 'pbg'); w = winner_index(e['row'])
        pw += (w == p)
        print(b, 'pbg won' if w == p else 'ifish won', e['row']['createdAt'])
print(n, 'games; pbg wins', pw)
from collections import Counter
print(Counter(tuple(sorted(e['keys'])) for e in idx.values() if len(e['keys']) > 1))
