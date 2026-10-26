"""IC study 2: how IC moves as a pack. Per round and team: living bodies, the largest cluster (bodies chained within 3 tiles), mean allies
within 4 of a body; per phase. Also how many distinct groups each team hits per 20-round window (spread vs pack farming), and camp hits
per living body-round.
    python3 -I ic_pack.py /tmp/claude-0/ic_all.json [sets]"""
import collections, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icx

sets = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
A = collections.defaultdict(list)
ng = 0
for g in icx.games(sys.argv[1], sets):
    if not g.D:
        continue
    ng += 1
    tg = g.D['tile_group']
    hits = collections.defaultdict(set)    # (window, team) -> groups hit
    nh = collections.Counter()
    for e in g.ev:
        if e['k'] in ('Attack', 'Cast ability') and 'who' in e and e.get('to') and tuple(e['to']) in tg:
            t = g.team[e['who']]
            hits[(e['r'] // 20, t)].add(tg[tuple(e['to'])])
            nh[(e['r'] // 100, t)] += 1
    for r in g.rounds:
        if r % 5:
            continue
        ph = 'p0' if r < 150 else 'p1' if r < 400 else 'p2' if r < 800 else 'p3'
        s = g.R[r]
        for t in (0, 1):
            side = icx.who_side(g, t)
            pts = [(c[3], c[4]) for c in s['ch'] if c[1] == t and c[7]]
            if not pts:
                continue
            # clusters: chain within 3
            seen = set(); best = 0
            for i in range(len(pts)):
                if i in seen:
                    continue
                stack = [i]; seen.add(i); n = 0
                while stack:
                    j = stack.pop(); n += 1
                    for k in range(len(pts)):
                        if k not in seen and icx.cheb(pts[j], pts[k]) <= 3:
                            seen.add(k); stack.append(k)
                best = max(best, n)
            A[(side, ph, 'alive')].append(len(pts))
            A[(side, ph, 'largest_pack')].append(best)
            A[(side, ph, 'pack_share')].append(best / len(pts))
            A[(side, ph, 'allies_within4')].append(st.mean(sum(1 for q in pts if q != p and icx.cheb(p, q) <= 4) for p in pts))
    for (w, t), gs in hits.items():
        ph = 'p0' if w * 20 < 150 else 'p1' if w * 20 < 400 else 'p2' if w * 20 < 800 else 'p3'
        A[(icx.who_side(g, t), ph, 'groups_hit_per_20r')].append(len(gs))
print('games', ng)
for k in ('alive', 'largest_pack', 'pack_share', 'allies_within4', 'groups_hit_per_20r'):
    for ph in ('p0', 'p1', 'p2', 'p3'):
        u = A.get(('us', ph, k)) or [0]; i = A.get(('ic', ph, k)) or [0]
        print(f"{k:20s} {ph}: us {st.mean(u):5.2f}  IC {st.mean(i):5.2f}")
