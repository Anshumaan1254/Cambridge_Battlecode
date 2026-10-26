"""Captured gems by round for team 0 (local games): python3 -I capsum.py index.json set..."""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icx
for s in sys.argv[2:]:
    for g in icx.games(sys.argv[1], {s}):
        cap = collections.Counter(); bank = collections.Counter(); deaths = collections.Counter()
        for e in g.ev:
            if 'who' not in e:
                continue
            t = g.team[e['who']]
            for lim in (150, 250, 400, 600, 2000):
                if e['r'] < lim:
                    if e['k'] == 'CaptureGems': cap[(t, lim)] += e['gems']
                    if e['k'] == 'Banked': bank[(t, lim)] += e['gems']
                    if e['k'] == 'Death': deaths[(t, lim)] += 1
        for t in (0, 1):
            print(f"{s:22s} team{t} cap " + ' '.join(f"{cap[(t, l)]:5d}" for l in (150, 250, 400, 600, 2000)) +
                  "  bank " + ' '.join(f"{bank[(t, l)]:5d}" for l in (150, 250, 400, 600, 2000)) + "  deaths " + ' '.join(f"{deaths[(t, l)]:2d}" for l in (150, 400, 2000)) + f"  final {g.final}")
