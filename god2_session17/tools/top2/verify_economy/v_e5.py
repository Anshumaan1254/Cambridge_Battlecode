# E5 verification: golem / monolith attempts by number of hitters (pooled), won vs failed context, per-team captures on maps
# with the camp, incidental pokes, hitters vs duration (endogeneity), examples.
import sys, os
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vagg import *

G = load()
HP = {'golem': 5000, 'monolith': 20000, 'elk': 4800}

for cls in ('golem', 'monolith', 'elk'):
    A = [a for g in G for a in g['att'] if a['cls'] == cls]
    print(f'\n== {cls}: attempts {len(A)} ==')
    by = defaultdict(list)
    for a in A:
        by[min(a['hitters'], 5)].append(a)
    print('  success by hitters: ' + ' | '.join(f"{h}{'+' if h == 5 else ''}: {mean([1 if a['res'] == 'won' else 0 for a in v]):.0%} (n {len(v)})" for h, v in sorted(by.items())))
    # damage share of single-hitter attempts (incidental pokes?)
    if cls != 'elk':
        one = by[1]
        hp = HP[cls]
        sm = [a for a in one if a['dmg'] < 0.1 * hp]
        print(f'  1-hitter attempts dealing < 10% of one camp HP: {len(sm)}/{len(one)} ({len(sm)/max(1,len(one)):.0%}); success among the rest {mean([1 if a["res"] == "won" else 0 for a in one if a["dmg"] >= 0.1*hp]):.0%} (n {len([a for a in one if a["dmg"] >= 0.1*hp])})')
        # duration vs hitters (endogeneity)
        for h in (1, 2, 3, 4, 5):
            v = by[h]
            print(f'    hitters {h}: median duration {med([a["r2"] - a["r1"] for a in v])} rounds, median dmg {med([a["dmg"] for a in v])}, start r {med([a["r1"] for a in v])}')
        for res in ('won', 'none', 'stolen'):
            v = [a for a in A if a['res'] == res]
            if not v:
                continue
            ratio = [a['hp'][0] / a['hp'][1] if a['hp'][1] else None for a in v]
            print(f'  {res:6s} n {len(v):4d} hitters {mean([a["hitters"] for a in v]):.2f} alive diff {mean([a["al"][0]-a["al"][1] for a in v]):+.2f} maxHP ratio median {med(ratio):.2f} enemy within 8 {mean([1 if a["en8"] else 0 for a in v]):.0%} start r median {med([a["r1"] for a in v])}')
        # success with >= 3 hitters split by enemy-within-8 and by max-HP ratio
        v3 = [a for a in A if a['hitters'] >= 3]
        for lab, sel in (('>=3 hitters, no enemy within 8', [a for a in v3 if not a['en8']]), ('>=3 hitters, enemy within 8', [a for a in v3 if a['en8']]),
                         ('>=3 hitters, maxHP ratio >= 1.4', [a for a in v3 if a['hp'][1] and a['hp'][0] / a['hp'][1] >= 1.4]),
                         ('>=3 hitters, maxHP ratio < 1.0', [a for a in v3 if a['hp'][1] and a['hp'][0] / a['hp'][1] < 1.0]),
                         ('>=3 hitters, start r < 400', [a for a in v3 if a['r1'] < 400]), ('>=3 hitters, start r >= 700', [a for a in v3 if a['r1'] >= 700]),
                         ('2 hitters, start r >= 700', [a for a in A if a['hitters'] == 2 and a['r1'] >= 700]),
                         ('1 hitter dmg>=10%, start r >= 700', [a for a in A if a['hitters'] == 1 and a['r1'] >= 700 and a['dmg'] >= 0.1 * HP[cls]])):
            print(f'    {lab:38s}: {mean([1 if a["res"] == "won" else 0 for a in sel]):.0%} (n {len(sel)})')
        # committed at the start: distinct hitters within the first 10 rounds of the attempt (removes the duration effect)
        if A and 'h10' in A[0]:
            b10 = defaultdict(list)
            for a in A:
                b10[min(a['h10'], 5)].append(a)
            print('  success by hitters in the first 10 rounds: ' + ' | '.join(f"{h}{'+' if h == 5 else ''}: {mean([1 if a['res'] == 'won' else 0 for a in v]):.0%} (n {len(v)})" for h, v in sorted(b10.items())))
            real = [a for a in A if a['dmg'] >= 0.1 * HP[cls]]
            b10 = defaultdict(list)
            for a in real:
                b10[min(a['h10'], 5)].append(a)
            print('  same, attempts dealing >= 10% of one camp HP: ' + ' | '.join(f"{h}{'+' if h == 5 else ''}: {mean([1 if a['res'] == 'won' else 0 for a in v]):.0%} (n {len(v)})" for h, v in sorted(b10.items())))
        # carriers hitting
        cv = [a for a in A if a['carry'] >= 100]
        print(f'  attempts with a hitter carrying >= 100: {len(cv)}, won {mean([1 if a["res"] == "won" else 0 for a in cv]):.0%}')

print('\n== per study team on maps with the camp class (captures per game, first capture, games with one) ==')
for cls in ('golem', 'monolith'):
    for k in KEYS:
        so = [(g, s) for g, s in so_games(G, k) if any(gr['cls'] == cls for gr in g['groups'])]
        if not so:
            continue
        S = [[c for c in g['caps'] if c['team'] == s and c['cls'] == cls] for g, s in so]
        O = [[c for c in g['caps'] if c['team'] == 1 - s and c['cls'] == cls] for g, s in so]
        fs = [min(c['r'] for c in x) for x in S if x]
        fo = [min(c['r'] for c in x) for x in O if x]
        ws = [a for g, s in so for a in g['att'] if a['cls'] == cls and a['team'] == s and a['res'] == 'won']
        print(f'{cls:8s} {k:9s} games {len(so):3d}: S {mean([len(x) for x in S]):.2f}/game first r {med(fs)} games with {mean([1 if x else 0 for x in S]):.0%} | O {mean([len(x) for x in O]):.2f}/game first r {med(fo)} games with {mean([1 if x else 0 for x in O]):.0%} | S won attempts: hitters median {med([a["hitters"] for a in ws])}, duration {med([a["r2"]-a["r1"] for a in ws])}')

print('\n== examples ==')
for g in G:
    for pre, cls in (('00split_c5346c81', 'golem'), ('00quadrants_46848e89', 'golem'), ('00contest_16309139', 'monolith')):
        if g['base'].startswith(pre):
            for a in g['att']:
                if a['cls'] == cls and a['res'] == 'won':
                    print(pre, cls, 'team', a['team'], 'r', a['r1'], '->', a['r2'], 'hitters', a['hitters'], 'res', a['res'])
            print(pre, 'captures', [(c['r'], c['team'], c['gems'], c['gold'], list(c['gains'].keys())) for c in g['caps'] if c['cls'] == cls])
