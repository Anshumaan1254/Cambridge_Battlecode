# E7 verification: captures by class S vs O (pbg, ifish), elk share of gems W vs L, elk attempts by hitters with damage /
# duration controls, bodies per elk attempt, first elk capture, time use (walk / farm / dead) W vs L, steps per captured gem,
# zone of skipped small groups.
import sys, os
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vagg import *

G = load()
CLS = ['elk', 'wolf', 'gem', 'gold', 'golem', 'monolith']

print('== captures per game by class: count / gems (S vs O) ==')
for k in KEYS:
    so = so_games(G, k)
    if not so:
        continue
    line = f'{k:9s} n {len(so):3d} '
    for side in ('S', 'O'):
        tot_n = mean([sum(1 for c in g['caps'] if c['team'] == (s if side == 'S' else 1 - s)) for g, s in so])
        tot_g = mean([sum(c['gems'] for c in g['caps'] if c['team'] == (s if side == 'S' else 1 - s)) for g, s in so])
        parts = []
        for cls in CLS:
            n = mean([sum(1 for c in g['caps'] if c['team'] == (s if side == 'S' else 1 - s) and c['cls'] == cls) for g, s in so])
            gm = mean([sum(c['gems'] for c in g['caps'] if c['team'] == (s if side == 'S' else 1 - s) and c['cls'] == cls) for g, s in so])
            parts.append(f'{cls} {n:.1f}/{gm:.0f}')
        line += f'| {side} all {tot_n:.1f}/{tot_g:.0f} ' + ' '.join(parts) + ' '
    print(line)

print('\n== small-group captures by zone (share of S / O small captures in own / mid / enemy zone) ==')
for k in ('pbg', 'ifish'):
    so = so_games(G, k)
    for side in ('S', 'O'):
        z = Counter()
        for g, s in so:
            t = s if side == 'S' else 1 - s
            for c in g['caps']:
                if c['team'] == t and c['cls'] in ('gem', 'gold', 'wolf'):
                    z[(c['cls'], c['zone'])] += 1
        n = len(so)
        print(f'{k} {side}: ' + ' | '.join(f"{cls}: own {z[(cls,'own')]/n:.1f} mid {z[(cls,'mid')]/n:.1f} en {z[(cls,'enemy')]/n:.1f}" for cls in ('gem', 'gold', 'wolf')))

print('\n== W vs L ==')
wl_table(G, lambda g, t: sum(c['gems'] for c in g['caps'] if c['team'] == t and c['cls'] == 'elk'), 'elk-group gems')
wl_table(G, lambda g, t: (sum(c['gems'] for c in g['caps'] if c['team'] == t and c['cls'] == 'elk') / max(1, sum(c['gems'] for c in g['caps'] if c['team'] == t))), 'elk share of captured gems')
wl_table(G, lambda g, t: sum(1 for c in g['caps'] if c['team'] == t and c['cls'] == 'gold'), 'gold-cluster captures')
wl_table(G, lambda g, t: sum(1 for c in g['caps'] if c['team'] == t), 'captures')
wl_table(G, lambda g, t: 100 * g['tu'][str(t)][2] / g['tu'][str(t)][0], 'walking % of body-rounds (moved)')
wl_table(G, lambda g, t: 100 * g['tu'][str(t)][3] / g['tu'][str(t)][0], 'farming % (hit a camp)')
wl_table(G, lambda g, t: 100 * g['tu'][str(t)][1] / g['tu'][str(t)][0], 'dead %')
wl_table(G, lambda g, t: 100 * g['tu'][str(t)][2] / max(1, (g['tu'][str(t)][0] - g['tu'][str(t)][1])), 'walking % of alive rounds')
wl_table(G, lambda g, t: 100 * g['tu'][str(t)][3] / max(1, (g['tu'][str(t)][0] - g['tu'][str(t)][1])), 'farming % of alive rounds')

print('\n== elk attempts (pooled) ==')
A = [a for g in G for a in g['att'] if a['cls'] == 'elk']
by = defaultdict(list)
for a in A:
    by[min(a['hitters'], 5)].append(a)
for h, v in sorted(by.items()):
    big = [a for a in v if a['dmg'] >= 1200]
    print(f"  hitters {h}: success {mean([1 if a['res'] == 'won' else 0 for a in v]):.0%} (n {len(v)}); dmg >= 1200 (half an elk): {mean([1 if a['res'] == 'won' else 0 for a in big]):.0%} (n {len(big)}); median dur {med([a['r2']-a['r1'] for a in v])}; stolen {mean([1 if a['res'] == 'stolen' else 0 for a in v]):.0%}; enemy within 8 {mean([1 if a['en8'] else 0 for a in v]):.0%}")
print('\n== bodies per elk attempt, first elk capture (S vs O) ==')
for k in KEYS:
    so = so_games(G, k)
    if not so:
        continue
    hs = [a['hitters'] for g, s in so for a in g['att'] if a['cls'] == 'elk' and a['team'] == s]
    ho = [a['hitters'] for g, s in so for a in g['att'] if a['cls'] == 'elk' and a['team'] == 1 - s]
    hsw = [a['hitters'] for g, s in so for a in g['att'] if a['cls'] == 'elk' and a['team'] == s and a['res'] == 'won']
    how = [a['hitters'] for g, s in so for a in g['att'] if a['cls'] == 'elk' and a['team'] == 1 - s and a['res'] == 'won']
    fs = [min([c['r'] for c in g['caps'] if c['team'] == s and c['cls'] == 'elk'] or [None]) for g, s in so if any(c['cls'] == 'elk' and c['team'] == s for c in g['caps'])]
    fo = [min([c['r'] for c in g['caps'] if c['team'] == 1 - s and c['cls'] == 'elk'] or [None]) for g, s in so if any(c['cls'] == 'elk' and c['team'] == 1 - s for c in g['caps'])]
    st = [g['tu'][str(s)][2] for g, s in so]
    sg = [sum(c['gems'] for c in g['caps'] if c['team'] == s) for g, s in so]
    ot = [g['tu'][str(1 - s)][2] for g, s in so]
    og = [sum(c['gems'] for c in g['caps'] if c['team'] == 1 - s) for g, s in so]
    print(f'{k:9s} hitters/attempt S {mean(hs):.2f} O {mean(ho):.2f} | per won attempt S {mean(hsw):.2f} O {mean(how):.2f} | first elk capture S r{med(fs)} O r{med(fo)} | steps per captured gem S {sum(st)/sum(sg):.2f} O {sum(ot)/sum(og):.2f}'
          f' | team size S {mean([sum(1 for b, x in g["bodies"].items() if x[0] == s) for g, s in so]):.1f} O {mean([sum(1 for b, x in g["bodies"].items() if x[0] == 1 - s) for g, s in so]):.1f}')
