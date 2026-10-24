# E4 verification: fate of big bags lost to champion kills (followed through further kills), stolen / lost gems and kill gold
# W vs L, exposed carriers per team and champion type, examples.
import sys, os
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vagg import *

G = load()


def fate(g, d):
    """follow a bag from a champion kill: returns ('banked', team) / ('camp', None) / ('carried', team)"""
    T = {int(b): v[0] for b, v in g['bodies'].items()}
    holder, q = d['by'], d['q']
    deaths = sorted(g['deaths'], key=lambda x: x['q'])
    banks = sorted(g['banked'], key=lambda x: x[0])
    for _ in range(20):
        nb = next((b for b in banks if b[2] == holder and b[0] > q), None)
        nd = next((x for x in deaths if x['who'] == holder and x['q'] > q), None)
        if nb and (not nd or nb[0] < nd['q']):
            return 'banked', T[holder]
        if nd:
            if isinstance(nd['by'], int):
                holder, q = nd['by'], nd['q']
                continue
            return 'camp', None
        return 'carried', T[holder]
    return 'carried', T[holder]


print('== fate of bags >= 50 lost to a champion kill, by victim team (study team S as victim) ==')
for k in KEYS:
    so = so_games(G, k)
    if not so:
        continue
    vic = Counter()
    kil = Counter()
    nv = nk = 0
    for g, s in so:
        for d in g['deaths']:
            if d['bag'] < 50 or not isinstance(d['by'], int):
                continue
            f, t = fate(g, d)
            if d['team'] == s:
                nv += 1
                vic['killer team banked' if (f == 'banked' and t != s) else ('S recovered+banked' if f == 'banked' else f)] += 1
            else:
                nk += 1
                kil['S banked' if (f == 'banked' and t == s) else ('O re-took+banked' if f == 'banked' else f)] += 1
    print(f"{k:9s} S big-bag deaths {nv:3d} ({nv/len(so):.2f}/game): " + ', '.join(f'{a} {b/max(1,nv):.0%}' for a, b in vic.most_common()) +
          f" | S kills O carriers {nk:3d} ({nk/len(so):.2f}/game): " + ', '.join(f'{a} {b/max(1,nk):.0%}' for a, b in kil.most_common()))

print('\n== W vs L ==')
wl_table(G, lambda g, t: sum(d.get('kgems', 0) for d in g['deaths'] if isinstance(d['by'], int) and g['bodies'][str(d['by'])][0] == t), 'gems stolen by kills')
wl_table(G, lambda g, t: sum(d['bag'] for d in g['deaths'] if d['team'] == t), 'gems lost on death')
wl_table(G, lambda g, t: sum(d.get('kgold', 0) for d in g['deaths'] if isinstance(d['by'], int) and g['bodies'][str(d['by'])][0] == t), 'kill gold')
wl_table(G, lambda g, t: sum(1 for d in g['deaths'] if d['team'] == t), 'deaths')
tot = defaultdict(int)
for g in G:
    for b, src in g['goldsrc'].items():
        for k, v in src.items():
            if not k.startswith('spent'):
                tot[k] += v
s = sum(tot.values())
print('gold sources (all team-games):', {k: f'{v/s:.1%}' for k, v in sorted(tot.items(), key=lambda t: -t[1])})

print('\n== exposed carriers: deaths with bag >= 100 per team and champion type (S) ==')
for k in KEYS:
    so = so_games(G, k)
    if not so:
        continue
    c = Counter()
    gl = defaultdict(int)
    killers = Counter()
    allgl = defaultdict(int)
    for g, s in so:
        for d in g['deaths']:
            if d['team'] != s:
                continue
            ty = g['bodies'][str(d['who'])][1]
            allgl[ty] += d['bag']
            if d['bag'] >= 100:
                c[ty] += 1
                gl[ty] += d['bag']
                killers[(ty, g['bodies'][str(d['by'])][1] if isinstance(d['by'], int) else d['by'])] += 1
    n = len(so)
    print(f'{k:9s} n {n}: big-bag deaths/game {sum(c.values())/n:.2f}; by type ' + ', '.join(f'{t} {v} ({v/n:.2f}/g, {gl[t]} gems)' for t, v in c.most_common(4)))
    print(f'          gems lost on death per game by type: ' + ', '.join(f'{t} {v/n:.0f}' for t, v in sorted(allgl.items(), key=lambda t: -t[1])[:4]))
    print(f'          killers of big-bag carriers: ' + ', '.join(f'{a[0]}<-{a[1]} {b}' for a, b in killers.most_common(6)))

print('\n== examples ==')
for g in G:
    for pre in ('00gemfight_a59c04f3', '00swirl_5cd065e4', '00gem_fields_3fc2330b'):
        if g['base'].startswith(pre):
            for d in g['deaths']:
                if d['bag'] >= 300:
                    f = fate(g, d)
                    print(pre, 'r', d['r'], 'victim', g['bodies'][str(d['who'])], 'bag', d['bag'], 'by', g['bodies'].get(str(d['by'])) if isinstance(d['by'], int) else d['by'], 'fate', f, 'winner', g['win'])
