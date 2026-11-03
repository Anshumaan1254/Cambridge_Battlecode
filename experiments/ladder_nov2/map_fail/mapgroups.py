"""Full camp groups of a game (half-map groups from groups.mjs mirrored the engine's way), keyed to decoded camp indices.
full group order: half groups in order; each stored camp is moved to the side of the group's first camp (nearer of itself and its
mirror); a group touching its mirror (Chebyshev <= 1) is one group, else two (first-camp side, mirror). Validated against the bot's
runtime dumps (experiments/results/mapintel/dump) and the replays' group counts."""
import json, os
BASE = '/home/claude/cambridge_battlecode/experiments/ladder_nov2'
HALF = json.load(open(f'{BASE}/map_fail/half_groups.json'))
TYPES = ['wolf', 'elk', 'gem', 'gold', 'monolith', 'golem']


def mirror(x, y, W, H, sym):
    if sym == 0:
        return W - 1 - x, y
    if sym == 1:
        return x, H - 1 - y
    return W - 1 - x, H - 1 - y


def full_groups(mapname, meta, sym):
    W, H = meta['width'], meta['height']
    tile2camp = {(c['x'], c['y']): c['index'] for c in meta['camps']}
    out = []
    for g in HALF[mapname]['groups']:
        gems, gold, resp = g['raw'][0], g['raw'][1], g['raw'][2]
        # the stored camps of a half group may sit on either side: put each on the side of the first camp
        x0, y0 = g['camps'][0][1], g['camps'][0][2]
        orig = []
        for t, x, y in g['camps']:
            mx, my = mirror(x, y, W, H, sym)
            if max(abs(mx - x0), abs(my - y0)) < max(abs(x - x0), abs(y - y0)):
                x, y = mx, my
            orig.append((t, x, y))
        mir = [(t,) + mirror(x, y, W, H, sym) for t, x, y in orig]
        touch = any(max(abs(a[1] - b[1]), abs(a[2] - b[2])) <= 1 for a in orig for b in mir)
        if touch:
            cs = list(dict.fromkeys(orig + mir))
            out.append({'gems': gems, 'gold': gold, 'resp': resp, 'camps': cs, 'merged': True})
        else:
            out.append({'gems': gems, 'gold': gold, 'resp': resp, 'camps': orig, 'merged': False})
            out.append({'gems': gems, 'gold': gold, 'resp': resp, 'camps': mir, 'merged': False})
    for i, g in enumerate(out):
        g['id'] = i
        g['idx'] = [tile2camp[(x, y)] for t, x, y in g['camps']]
        g['tiles'] = [(x, y) for t, x, y in g['camps']]
        g['types'] = [TYPES[t] for t, x, y in g['camps']]
        g['cx'] = sum(x for x, y in g['tiles']) / len(g['tiles'])
        g['cy'] = sum(y for x, y in g['tiles']) / len(g['tiles'])
    return out
