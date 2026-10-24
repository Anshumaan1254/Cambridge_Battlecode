# E1 verification: mid / own / elk gems W vs L, S vs O mid share, mid-group respawn cycles by holders, timed-return test.
import sys, os
from collections import defaultdict, Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vagg import *

G = load()
print('games', len(G))


def capsum(g, t, pred):
    return sum(c['gems'] for c in g['caps'] if c['team'] == t and pred(c))


print('\n== W vs L (pooled distinct matches) ==')
wl_table(G, lambda g, t: capsum(g, t, lambda c: True), 'captured gems')
wl_table(G, lambda g, t: capsum(g, t, lambda c: c['zone'] == 'mid'), 'mid-zone gems')
wl_table(G, lambda g, t: capsum(g, t, lambda c: c['zone'] == 'own'), 'own-zone gems')
wl_table(G, lambda g, t: capsum(g, t, lambda c: c['zone'] == 'enemy'), 'enemy-zone gems')
wl_table(G, lambda g, t: capsum(g, t, lambda c: c['cls'] == 'elk'), 'elk-group gems')
# same, first 300 rounds only (before most outcomes are decided)
wl_table(G, lambda g, t: capsum(g, t, lambda c: c['zone'] == 'mid' and c['r'] <= 300), 'mid-zone gems r<=300')
wl_table(G, lambda g, t: capsum(g, t, lambda c: c['zone'] == 'own' and c['r'] <= 300), 'own-zone gems r<=300')
# per 100 rounds (game length is shared within a match, so this only rescales)
# unknown zone share
unk = sum(c['gems'] for g in G for c in g['caps'] if c['zone'] is None)
tot = sum(c['gems'] for g in G for c in g['caps'])
print('gems with unknown zone', unk, 'of', tot)

print('\n== S vs O ==')
for k in KEYS:
    so = so_games(G, k)
    S = defaultdict(list)
    for g, s in so:
        for side, t in (('S', s), ('O', 1 - s)):
            S[side + 'all'].append(capsum(g, t, lambda c: True))
            S[side + 'mid'].append(capsum(g, t, lambda c: c['zone'] == 'mid'))
            S[side + 'own'].append(capsum(g, t, lambda c: c['zone'] == 'own'))
            S[side + 'en'].append(capsum(g, t, lambda c: c['zone'] == 'enemy'))
    print(f"{k:9s} n {len(so):3d} | S all {mean(S['Sall']):6.0f} own {mean(S['Sown']):5.0f} mid {mean(S['Smid']):5.0f} en {mean(S['Sen']):4.0f} share {sum(S['Smid'])/max(1,sum(S['Sall'])):.2f}"
          f" | O all {mean(S['Oall']):6.0f} own {mean(S['Oown']):5.0f} mid {mean(S['Omid']):5.0f} en {mean(S['Oen']):4.0f} share {sum(S['Omid'])/max(1,sum(S['Oall'])):.2f}"
          f" | mid diff {mean(S['Smid'])-mean(S['Omid']):+5.0f} own diff {mean(S['Sown'])-mean(S['Oown']):+5.0f}")

print('\n== mid-group respawn cycles (consecutive captures) ==')
for hk in ('hold', 'hold2'):
    cat = defaultdict(lambda: [0, 0, []])
    byn = defaultdict(lambda: [0, 0])
    n = 0
    for g in G:
        for c in g['cyc']:
            if c['next_team'] is None or c['team'] is None:
                continue
            n += 1
            t = c['team']
            own, oth = c[hk][t], c[hk][1 - t]
            k = 'capturer only' if own and not oth else ('both' if own and oth else ('other only' if oth else 'nobody'))
            kept = c['next_team'] == t
            cat[k][0] += 1
            cat[k][1] += kept
            if c['first_hit'] is not None:
                cat[k][2].append(c['first_hit'] - c['resp'])
            byn[min(own, 3)][0] += 1
            byn[min(own, 3)][1] += kept
    print(f'-- holders measured at {"end of respawn round - 1" if hk == "hold" else "end of the respawn round"}: cycles {n}')
    for k in ('capturer only', 'both', 'other only', 'nobody'):
        v = cat[k]
        print(f'   {k:14s} cycles {v[0]:6d} kept {v[1]/max(1,v[0]):.0%} re-hit median {med(v[2]):5.1f} p25 {pct(v[2],0.25):5.1f}')
    print('   capturer holders 0/1/2/3+ kept:', ' '.join(f'{i}:{byn[i][1]/max(1,byn[i][0]):.0%}(n{byn[i][0]})' for i in range(4)))

print('\n== same, elk groups only / by class ==')
for cls in ('elk', 'wolf', 'gem', 'gold'):
    cat = defaultdict(lambda: [0, 0, []])
    for g in G:
        for c in g['cyc']:
            if c['next_team'] is None or c['team'] is None or c['cls'] != cls:
                continue
            t = c['team']
            own, oth = c['hold'][t], c['hold'][1 - t]
            k = 'cap' if own and not oth else ('both' if own and oth else ('other' if oth else 'nobody'))
            cat[k][0] += 1
            cat[k][1] += c['next_team'] == t
            if c['first_hit'] is not None:
                cat[k][2].append(c['first_hit'] - c['resp'])
    print(cls, ' | '.join(f"{k} n{v[0]} kept {v[1]/max(1,v[0]):.0%} wait {med(v[2])}" for k, v in sorted(cat.items())))

print('\n== per study team: wait before first hit on a respawned mid group (cycles ending in a capture by that team) ==')
for k in KEYS:
    so = so_games(G, k)
    ws, wo, hs, ho, ks, ko = [], [], [], [], [], []
    for g, s in so:
        for c in g['cyc']:
            if c['next_team'] is None or c['first_hit'] is None:
                continue
            w = c['first_hit'] - c['resp']
            (ws if c['next_team'] == s else wo).append(w)
            if c['team'] == s:
                hs.append(1 if c['hold'][s] else 0)
                ks.append(1 if c['next_team'] == s else 0)
            elif c['team'] == 1 - s:
                ho.append(1 if c['hold'][1 - s] else 0)
                ko.append(1 if c['next_team'] == 1 - s else 0)
    print(f'{k:9s} wait S {med(ws):5.1f} (n {len(ws)}) O {med(wo):5.1f} (n {len(wo)}) | own-holder share of own cycles S {mean(hs):.2f} O {mean(ho):.2f} | kept S {mean(ks):.2f} O {mean(ko):.2f}')

print('\n== timed-return test: capturer-team bodies within 4 of the group around its respawn (all mid cycles; S teams vs their O) ==')
offs = ['-60', '-40', '-30', '-20', '-10', '-5', '-2', '-1', '0', '5', '10']
for k in ['ALL'] + KEYS:
    rows = {'S': defaultdict(list), 'O': defaultdict(list)}
    if k == 'ALL':
        it = [(g, None) for g in G]
    else:
        it = so_games(G, k)
    for g, s in it:
        for c in g['cyc']:
            if c['team'] is None or 'prof' not in c:
                continue
            side = 'S' if (s is None or c['team'] == s) else 'O'
            for o in offs:
                rows[side][o].append(1 if c['prof'][o][c['team']] else 0)
    for side in ('S', 'O') if k != 'ALL' else ('S',):
        r = rows[side]
        print(f'{k:9s} {side} n {len(r["0"]):5d} ' + ' '.join(f'{o}:{mean(r[o]):.2f}' for o in offs))
