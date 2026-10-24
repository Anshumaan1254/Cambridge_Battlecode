# pbg vs ifish games by team id (any folder)
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vlib import *
idx = load_index()
n = pw = 0
for b, e in sorted(idx.items()):
    ks = [k for k in KEYS if team_of_key(e['row'], k) is not None]
    if 'pbg' in ks and 'ifish' in ks:
        n += 1; p = team_of_key(e['row'], 'pbg'); w = winner_index(e['row']); pw += (w == p)
        print(b, e['keys'], 'pbg won' if w == p else 'ifish won')
print(n, 'pbg wins', pw)
