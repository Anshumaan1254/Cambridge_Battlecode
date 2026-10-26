"""IC study 3: time budget per living body-round by phase (share of body-rounds): dead, camp hit, champion hit, walk (enemy within 8 / not),
stand, on spawn; plus camp damage per alive body-round and travel per camp hit.
    python3 -I ic_budget.py /tmp/claude-0/ic_all.json [sets]"""
import collections, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icx

sets = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
cats = ['dead', 'camp', 'champ', 'walkE', 'walk', 'standE', 'stand', 'spawn']
B = collections.defaultdict(collections.Counter)
ng = 0
for g in icx.games(sys.argv[1], sets):
    if not g.D:
        continue
    ng += 1
    tg = g.D['tile_group']
    act = {}
    for e in g.ev:
        if e['k'] in ('Attack', 'Cast ability') and 'who' in e and e.get('to'):
            k = (e['r'], e['who'])
            if tuple(e['to']) in tg:
                act.setdefault(k, 'camp')
            else:
                act[k] = 'champ'
    s1 = g.R[g.rounds[0]]
    spawn = collections.defaultdict(list)
    for c in s1['ch']:
        spawn[c[1]].append((c[3], c[4]))
    rs = g.rounds
    for i in range(1, len(rs)):
        r0, r1 = rs[i - 1], rs[i]
        if r1 != r0 + 1:
            continue
        ph = 'p0' if r1 < 150 else 'p1' if r1 < 400 else 'p2'
        P0 = {c[0]: c for c in g.R[r0]['ch']}
        for c in g.R[r1]['ch']:
            side = icx.who_side(g, c[1])
            o = P0.get(c[0])
            if not c[7]:
                cat = 'dead'
            elif act.get((r1, c[0])):
                cat = act[(r1, c[0])]
            else:
                en = any(q[1] != c[1] and q[7] and icx.cheb((q[3], q[4]), (c[3], c[4])) <= 8 for q in g.R[r1]['ch'])
                moved = o is not None and (o[3], o[4]) != (c[3], c[4])
                if moved:
                    cat = 'walkE' if en else 'walk'
                elif min(icx.cheb(p, (c[3], c[4])) for p in spawn[c[1]]) <= 2:
                    cat = 'spawn'
                else:
                    cat = 'standE' if en else 'stand'
            B[(side, ph)][cat] += 1
            B[(side, 'all')][cat] += 1
print('games', ng, '(share of body-rounds; total body-rounds per game)')
print(f"{'':8s} " + ' '.join(f'{c:>12s}' for c in cats) + '   body-rounds/game')
for ph in ('p0', 'p1', 'p2', 'all'):
    for side in ('us', 'ic'):
        b = B[(side, ph)]; n = sum(b.values()) or 1
        print(f"{side + ' ' + ph:8s} " + ' '.join(f'{100 * b[c] / n:11.1f}%' for c in cats) + f'   {n / ng:7.0f}')
