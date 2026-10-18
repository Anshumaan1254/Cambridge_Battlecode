#!/usr/bin/env python3
"""Draft-time map plan prototype: camp groups -> farming zones -> champion assignment -> map type.

This is the offline reference for the C++ draft planner described in docs/strategy_v2/IMPLEMENTATION_SPEC.md.
It reads the ASCII map dumps made by tools/replay/mapinfo.mjs (walls #, holes o, altars A, bushes ", spawn S/s,
camps W wolf, E elk, g gem cluster, $ gold cluster, M monolith) and prints, per map:

  * every camp group with its value, respawn, health, side (home / neutral / enemy) and distance from our spawn,
  * the map type (rich home, contest, objective, long transport) with the numbers behind it,
  * zones: k-medoids clustering of the home + neutral groups on walking distance (k = number of farming units),
  * which unit (Varg, Stellar, the Cassi & Issac pair, ...) farms which zone, chosen by brute force over all
    assignments to maximise value x fit, and a nearest-neighbour circuit through each zone,
  * the size of that plan in draft-memory bytes.

usage: python3 map_plan.py MAPDUMP.txt [--draft Varg,Stellar,CassiIssac,Ryth,Ren] [--json]
"""
import argparse
import itertools
import json
import math
import sys
from collections import deque

CAMP = {  # gems, gold, respawn, health, strength (handbook table)
    'W': ('wolf', 22, 90, 40, 1350, 20), 'E': ('elk', 36, 160, 60, 2400, 60), 'g': ('gem', 24, 0, 50, 500, 0),
    '$': ('gold', 0, 35, 50, 500, 0), 'M': ('monolith', 200, 300, 150, 20000, 200),
}
GOLD_VALUE = 0.22  # gem value of one gold early in the game (same as legend's gold_value)

# Damage per round of each farming unit on one camp, at base stats, and how well it copes with camps that hit
# back (health / damage taken). Splash (Varg) and area spells (Stellar, Ryth) multiply by the camps they hit.
UNITS = {
    'Varg': dict(dps=56, splash=True, area=False, hp=1000, ranged=False),
    'Stellar': dict(dps=35 + 25, splash=False, area=True, hp=750, ranged=True),
    'CassiIssac': dict(dps=47 + 45, splash=False, area=False, hp=1600, ranged=False),
    'Ryth': dict(dps=56, splash=False, area=True, hp=1200, ranged=False),
    'Ren': dict(dps=60, splash=False, area=False, hp=900, ranged=False, retaliate=True),
    'Tavi': dict(dps=39 + 27, splash=False, area=False, hp=750, ranged=True),
    'Vendetta': dict(dps=79, splash=False, area=False, hp=800, ranged=False),
    'Prism': dict(dps=35 + 25, splash=False, area=True, hp=700, ranged=True),
}


def load(path):
    lines = open(path).read().splitlines()
    head = lines[0]
    grid = [l[4:] for l in lines[1:] if len(l) > 4]
    h = len(grid)
    w = max(len(r) for r in grid)
    grid = [list(r.ljust(w, '.')) for r in grid]
    return head, grid, w, h


def bfs(grid, w, h, sources, blocked):
    INF = 10 ** 9
    dist = [[INF] * w for _ in range(h)]
    dq = deque()
    for (x, y) in sources:
        dist[y][x] = 0
        dq.append((x, y))
    while dq:
        x, y = dq.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if (dx or dy) and 0 <= nx < w and 0 <= ny < h and dist[ny][nx] == INF and grid[ny][nx] not in blocked:
                    dist[ny][nx] = dist[y][x] + 1
                    dq.append((nx, ny))
    return dist


def groups_of(grid, w, h):
    seen = set()
    out = []
    for y in range(h):
        for x in range(w):
            if grid[y][x] in CAMP and (x, y) not in seen:
                st = [(x, y)]
                seen.add((x, y))
                tiles = []
                while st:
                    cx, cy = st.pop()
                    tiles.append((cx, cy, grid[cy][cx]))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and grid[ny][nx] in CAMP:
                            seen.add((nx, ny))
                            st.append((nx, ny))
                out.append(tiles)
    return out


def kill_rounds(unit, g):
    """Rounds for one unit to clear group g alone at base stats (splash / area hit every camp of a packed group)."""
    u = UNITS[unit]
    hp = g['hp']
    n = g['n']
    dps = u['dps']
    if u['splash'] and n >= 2:
        dps *= min(n, 3) * 0.85  # splash hits the neighbours of the target; packs are 2-4 camps in a line or square
    elif u['area'] and n >= 2:
        dps *= 1.0 + 0.4 * min(n - 1, 2)
    if u.get('retaliate'):
        dps += 20 * max(1, g['attackers'])  # Ren reflects 0.2 x focus per camp hit
    return hp / max(1.0, dps)


def fit(unit, g):
    """How well a unit farms group g: value per round of its clear, with a survival penalty."""
    u = UNITS[unit]
    t = kill_rounds(unit, g)
    taken = g['str'] * t * (0.25 if u['ranged'] else 1.0)
    trips = max(0.0, taken - 0.6 * u['hp']) / (0.6 * u['hp'])
    rounds = t + 6 + trips * 25
    return g['value'] / rounds


def kmedoids(D, items, k, weight, iters=50):
    """Weighted k-medoids (PAM-style swaps) on a precomputed walking-distance matrix."""
    if len(items) <= k:
        return {i: [i] for i in items}
    # init: farthest-first from the most valuable item
    med = [max(items, key=lambda i: weight[i])]
    while len(med) < k:
        med.append(max((i for i in items if i not in med), key=lambda i: min(D[i][m] for m in med)))

    def cost(meds):
        return sum(weight[i] * min(D[i][m] for m in meds) for i in items)
    best = cost(med)
    for _ in range(iters):
        improved = False
        for mi in range(k):
            for cand in items:
                if cand in med:
                    continue
                trial = med[:mi] + [cand] + med[mi + 1:]
                c = cost(trial)
                if c < best - 1e-9:
                    best, med, improved = c, trial, True
        if not improved:
            break
    zones = {m: [] for m in med}
    for i in items:
        zones[min(med, key=lambda m: D[i][m])].append(i)
    return zones


def dbscan(D, items, eps, min_pts):
    """Plain DBSCAN on a precomputed distance matrix. Returns (clusters, noise)."""
    label = {}
    cid = 0
    for i in items:
        if i in label:
            continue
        nb = [j for j in items if D[i][j] <= eps]
        if len(nb) < min_pts:
            label[i] = -1
            continue
        label[i] = cid
        queue = [j for j in nb if j != i]
        while queue:
            j = queue.pop()
            if label.get(j) == -1:
                label[j] = cid
            if j in label:
                continue
            label[j] = cid
            nb2 = [k for k in items if D[j][k] <= eps]
            if len(nb2) >= min_pts:
                queue.extend(k for k in nb2 if k not in label or label[k] == -1)
        cid += 1
    clusters = [[i for i in items if label[i] == c] for c in range(cid)]
    noise = [i for i in items if label[i] == -1]
    return clusters, noise


def plan(path, draft):
    head, grid, w, h = load(path)
    spawn = [[(x, y) for y in range(h) for x in range(w) if grid[y][x] == s] for s in 'Ss']
    blocked = '#oA' + ''.join(CAMP)
    walk = [bfs(grid, w, h, spawn[0], blocked + 's'), bfs(grid, w, h, spawn[1], blocked + 'S')]
    altars = [(x, y) for y in range(h) for x in range(w) if grid[y][x] == 'A']
    raw = groups_of(grid, w, h)
    G = []
    for tiles in raw:
        kinds = [CAMP[c] for (_, _, c) in tiles]
        gems = sum(k[1] for k in kinds)
        gold = sum(k[2] for k in kinds)
        resp = max(k[3] for k in kinds)
        hp = sum(k[4] for k in kinds)
        st = sum(k[5] for k in kinds)
        adj = set()
        for (x, y, _) in tiles:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] not in blocked + 'Ss':
                        adj.add((nx, ny))
        d = [min((walk[t][y][x] for (x, y) in adj), default=10 ** 9) for t in (0, 1)]
        side = 'home' if d[0] < d[1] - 3 else 'enemy' if d[1] < d[0] - 3 else 'neutral'
        alt = min((max(abs(ax - x), abs(ay - y)) for (ax, ay) in altars for (x, y, _) in tiles), default=99)
        name = '+'.join(f"{sum(1 for k in kinds if k[0] == n)}{n}" for n in ('wolf', 'elk', 'gem', 'gold', 'monolith') if any(k[0] == n for k in kinds))
        value = gems + GOLD_VALUE * gold
        G.append(dict(id=len(G), name=name, tiles=[(x, y) for (x, y, _) in tiles], adj=sorted(adj), n=len(tiles), gems=gems, gold=gold,
                      resp=resp, hp=hp, str=st, attackers=sum(1 for k in kinds if k[5] > 0), d_home=d[0], d_enemy=d[1], side=side,
                      altar_cheb=alt, value=value, rate=value / (resp + 5 + hp / 150.0)))
    home = [g for g in G if g['side'] == 'home']
    neutral = [g for g in G if g['side'] == 'neutral']
    tot_gems = sum(g['gems'] for g in G)
    home_rate = sum(g['gems'] / (g['resp'] + 5 + g['hp'] / 150.0) for g in home)
    neut_rate = sum(g['gems'] / (g['resp'] + 5 + g['hp'] / 150.0) for g in neutral)
    heavy = [g for g in G if g['hp'] >= 6000 and g['gems'] > 0]
    heavy_share = sum(g['gems'] for g in heavy) / max(1, tot_gems)
    reach_home = [g for g in home if g['d_home'] < 10 ** 8]
    mean_bank = sum(g['altar_cheb'] for g in reach_home) / max(1, len(reach_home))
    mean_home_d = sum(g['d_home'] for g in reach_home) / max(1, len(reach_home))
    types = []
    if heavy_share >= 0.4:
        types.append('OBJECTIVE')
    if home_rate * 450 >= 1000:
        types.append('RICH_HOME')
    else:
        types.append('CONTEST')
    if mean_home_d >= 30:
        types.append('FIELD (farm out, bank at mid altars)')
    # zoning on home + neutral groups with walking distance between groups (from the group's adjacent tiles)
    near_d = sorted(g['d_home'] for g in home + neutral if g['d_home'] < 10 ** 8)
    med = near_d[len(near_d) // 2] if near_d else 0
    far_cut = max(60, 2.5 * med)
    far = [g for g in home + neutral if g['d_home'] >= far_cut]
    pool = [g for g in home + neutral if g['d_home'] < far_cut and not (g['hp'] >= 6000 and 'monolith' in g['name'])]
    ids = [g['id'] for g in pool]
    D = {}
    for g in pool:
        dg = bfs(grid, w, h, g['adj'], blocked + 's')
        D[g['id']] = {o['id']: min((dg[y][x] for (x, y) in o['adj']), default=10 ** 6) for o in pool}
    hubs, lone = dbscan(D, ids, eps=10, min_pts=2) if ids else ([], [])
    units = draft
    k = min(len(units), max(1, len(ids)))
    zones = kmedoids(D, ids, k, {g['id']: g['rate'] for g in pool})
    zlist = list(zones.values())
    byid = {g['id']: g for g in G}
    # assignment: brute force over permutations of units to zones (k <= 5 -> at most 120)
    best = None
    for perm in itertools.permutations(units, len(zlist)):
        s = sum(sum(fit(u, byid[i]) for i in z) for u, z in zip(perm, zlist))
        if best is None or s > best[0]:
            best = (s, perm)
    assign = list(zip(best[1], zlist)) if best else []
    circuits = []
    for u, z in assign:
        # nearest-neighbour tour from the spawn
        left = set(z)
        cur = None
        order = []
        while left:
            if cur is None:
                nxt = min(left, key=lambda i: byid[i]['d_home'])
            else:
                nxt = min(left, key=lambda i: D[cur][i])
            order.append(nxt)
            left.discard(nxt)
            cur = nxt
        work = sum(kill_rounds(u, byid[i]) + 6 for i in order) + sum(D[a][b] for a, b in zip(order, order[1:])) + byid[order[0]]['d_home']
        min_resp = min(byid[i]['resp'] for i in order)
        rate = sum(byid[i]['gems'] for i in order) / max(work, min_resp + 5)
        alt = min(range(len(altars)), key=lambda a: min(max(abs(altars[a][0] - x), abs(altars[a][1] - y)) for i in order for (x, y) in byid[i]['tiles'])) if altars else -1
        circuits.append(dict(unit=u, groups=order, est_cycle=round(work), est_gems_per_round=round(rate, 2), altar=altars[alt] if alt >= 0 else None))
    mem_bytes = 4 + len(G) // 2 + 1 + sum(1 + len(c['groups']) for c in circuits) + 8
    return dict(map=path.split('/')[-1], size=f'{w}x{h}', groups=len(G), home=len(home), neutral=len(neutral),
                home_gem_rate=round(home_rate, 2), neutral_gem_rate=round(neut_rate, 2), heavy_share=round(heavy_share, 2),
                mean_home_dist=round(mean_home_d, 1), mean_altar_cheb=round(mean_bank, 1), types=types,
                circuits=circuits, draft_memory_bytes=mem_bytes, group_table=G, hubs=hubs, lone=lone, far=[g['id'] for g in far])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('maps', nargs='+')
    ap.add_argument('--draft', default='Varg,Stellar,CassiIssac,Ryth,Ren')
    ap.add_argument('--size', type=int, default=0, help='team size (picks); default from the map header')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    out = []
    for m in a.maps:
        head = open(m).readline()
        size = a.size or int(head.split('champs ')[1].split()[0])
        draft = a.draft.split(',')[:size]
        if 'CassiIssac' in draft:
            pass  # one pick, two bodies, farmed as one unit
        p = plan(m, draft)
        out.append(p)
        if not a.json:
            print(f"== {p['map']} {p['size']} picks {size}  groups {p['groups']} (home {p['home']}, neutral {p['neutral']})  types {', '.join(p['types'])}")
            print(f"   home gem rate {p['home_gem_rate']}/round (1000 gems in {1000 / max(0.01, p['home_gem_rate']):.0f} rounds)  neutral {p['neutral_gem_rate']}/round  heavy-group gem share {p['heavy_share']}  mean home-group distance {p['mean_home_dist']}  altar distance {p['mean_altar_cheb']}")
            for c in p['circuits']:
                names = ' -> '.join(f"{byname(p, i)}" for i in c['groups'])
                print(f"   {c['unit']:10} cycle ~{c['est_cycle']:4} rounds, ~{c['est_gems_per_round']} gems/round, bank at altar {c['altar']}: {names}")
            print(f"   DBSCAN (walking eps 10, min 2): {len(p['hubs'])} hubs of sizes {[len(h) for h in p['hubs']]}; lone groups (contest points): "
                  + (', '.join(byname(p, i) for i in p['lone']) or 'none'))
            if p['far']:
                print('   far groups left out of the zones (crystal or late targets): ' + ', '.join(byname(p, i) for i in p['far']))
            print(f"   draft-memory plan: ~{p['draft_memory_bytes']} bytes of 1024")
    if a.json:
        json.dump(out, sys.stdout, default=str)


def byname(p, i):
    g = p['group_table'][i]
    return f"{g['name']}@{g['tiles'][0][0]},{g['tiles'][0][1]}(d{g['d_home']})"


if __name__ == '__main__':
    main()
