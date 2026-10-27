"""IC study 1: the opening and the groups each team farms.

For every body: its first camp hit (round, group, the group's gems / gold / kind / camps / distance from both spawns, how many of its own
team's bodies hit the same group within the first 60 rounds). For every capture: group value, round, how many of the capturing team's
bodies were within 4 tiles, and whether the group lies in the middle band (|d_own - d_opp| <= 4, Chebyshev from the spawn centres).
Per group and team: share of the group's captures over the game.
    python3 -I ic_open.py /tmp/claude-0/ic_all.json [set,set]"""
import collections, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icx

sets = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
F = collections.defaultdict(list)          # (side, key) -> values
caps_by = collections.Counter()
grp_share = collections.defaultdict(lambda: collections.Counter())
ng = 0
for g in icx.games(sys.argv[1], sets):
    if not g.D:
        continue
    ng += 1
    D = g.D
    sp = {t: D['spawn'][t] for t in (0, 1)}
    tg = D['tile_group']
    gid = {gg['id']: gg for gg in D['groups']}

    def zone(team, p):
        da, db = icx.cheb(p, sp[team]), icx.cheb(p, sp[1 - team])
        return 'M' if abs(da - db) <= 4 else ('O' if da < db else 'T')
    first = {}
    hits60 = collections.defaultdict(set)   # (team, group) -> bodies hitting it before r60
    for e in g.ev:
        if e['k'] in ('Attack', 'Cast ability') and 'who' in e and e.get('to'):
            t = tuple(e['to'])
            if t in tg:
                b = e['who']
                if b not in first:
                    first[b] = (e['r'], tg[t])
                if e['r'] <= 60:
                    hits60[(g.team[b], tg[t])].add(b)
    for b, (r, gi) in first.items():
        side = icx.who_side(g, g.team[b]); G = gid[gi]
        F[(side, 'first_hit_round')].append(r)
        F[(side, 'first_group_gems')].append(G['gems'])
        F[(side, 'first_group_value')].append(G['gems'] + 0.5 * G['gold'])
        F[(side, 'first_group_mates')].append(len(hits60[(g.team[b], gi)]))
        F[(side, 'first_group_mid')].append(zone(g.team[b], G['center']) == 'M')
        F[(side, 'first_group_dist')].append(icx.cheb(G['center'], sp[g.team[b]]))
    # captures
    R = g.R
    for e in g.ev:
        if e['k'] != 'CaptureGems' or 'who' not in e:
            continue
        b = e['who']; team = g.team[b]; side = icx.who_side(g, team)
        at = tuple(e['at']); gi = tg.get(at)
        s = R.get(e['r']) or R.get(e['r'] - 1)
        near = 0
        if s:
            near = sum(1 for c in s['ch'] if c[1] == team and c[7] and icx.cheb((c[3], c[4]), at) <= 4)
        z = zone(team, at)
        ph = 'p0' if e['r'] < 200 else 'p1' if e['r'] < 500 else 'p2'
        F[(side, 'cap_near_allies')].append(near)
        F[(side, f'cap_gems_{z}')].append(e['gems'])
        caps_by[(side, z, ph)] += e['gems']
        if gi is not None:
            grp_share[(g.path, gi)][side] += 1
    caps_by[('games', '', '')] += 1


def m(side, k, f=st.mean):
    v = F.get((side, k)) or [0]
    return f([float(x) for x in v])


print('games', ng)
for k in ('first_hit_round', 'first_group_gems', 'first_group_value', 'first_group_mates', 'first_group_mid', 'first_group_dist', 'cap_near_allies'):
    print(f"{k:22s} us mean {m('us', k):7.2f} med {m('us', k, st.median):7.1f} | IC mean {m('ic', k):7.2f} med {m('ic', k, st.median):7.1f}")
for z in ('O', 'M', 'T'):
    for ph in ('p0', 'p1', 'p2'):
        print(f"captured gems/game zone {z} {ph}: us {caps_by[('us', z, ph)] / ng:6.1f}  IC {caps_by[('ic', z, ph)] / ng:6.1f}")
# groups where IC took most captures: what kind / value
kinds = collections.Counter(); tot = collections.Counter()
for (path, gi), c in grp_share.items():
    n = c['us'] + c['ic']
    if n >= 3:
        tot['groups'] += 1
        if c['ic'] >= 0.75 * n:
            tot['ic_dominated'] += 1
        if c['us'] >= 0.75 * n:
            tot['us_dominated'] += 1
print('groups with 3+ captures:', dict(tot))
