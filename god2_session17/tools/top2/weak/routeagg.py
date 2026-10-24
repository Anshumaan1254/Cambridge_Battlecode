"""Opening repeatability (an_weak) from tools/top2/weak/routes.mjs output: for every pair of games of the same study team on the same map
   and side (different opponents or times), the mean Chebyshev distance between same-type bodies at each checkpoint (0 = identical
   route), the share of bodies whose first camp hit is the same camp, the same first capture tile, and the same first ward tile.
   python tools/top2/weak/routeagg.py KEY..."""
import json, sys, itertools, collections
CPS = [5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 100, 120, 150, 200]
for key in sys.argv[1:]:
    G = [json.loads(l) for l in open(f'C:/battlecode/cache/an_weak/routes_{key}.jsonl', encoding='utf-8') if l.strip()]
    by = collections.defaultdict(list)
    for g in G: by[(g['map'], g['side'])].append(g)
    dist = collections.defaultdict(list); same_hit = [0, 0]; same_cap = [0, 0]; same_ward = [0, 0]; exact0 = collections.Counter(); pairs = 0
    odist = collections.defaultdict(list)
    for (m, s), L in by.items():
        for a, b in itertools.combinations(L, 2):
            if a['draft'] != b['draft']: continue
            if a['opp'] == b['opp']: continue
            pairs += 1
            def match(team):
                A = [(i, x) for i, x in a['bodies'].items() if x['team'] == team]; B = [(i, x) for i, x in b['bodies'].items() if x['team'] == team]
                return A, B
            A, B = match('S')
            # pair bodies by type in index order
            ta = collections.defaultdict(list); tb = collections.defaultdict(list)
            for i, x in A: ta[x['ty']].append(x)
            for i, x in B: tb[x['ty']].append(x)
            for ty in ta:
                for xa, xb in zip(ta[ty], tb.get(ty, [])):
                    for k, r in enumerate(CPS):
                        pa, pb = xa['pos'][k], xb['pos'][k]
                        if pa and pb:
                            dd = max(abs(pa[0] - pb[0]), abs(pa[1] - pb[1])); dist[r].append(dd)
                            if dd == 0: exact0[r] += 1
                    if xa['hits'] and xb['hits']:
                        same_hit[1] += 1; same_hit[0] += int(xa['hits'][0][1:3] == xb['hits'][0][1:3])
                    if xa['wards'] and xb['wards']:
                        same_ward[1] += 1; same_ward[0] += int(xa['wards'][0][1:3] == xb['wards'][0][1:3])
            if a['caps']['S'] and b['caps']['S']:
                same_cap[1] += 1; same_cap[0] += int(a['caps']['S'][0][1:3] == b['caps']['S'][0][1:3])
    print(f'### {key}: {pairs} pairs of games (same map, side, draft; different opponents)')
    print('   mean distance between same-type bodies:', ', '.join(f'r{r} {sum(dist[r])/len(dist[r]):.1f} ({100*exact0[r]/len(dist[r]):.0f}% exact)' for r in CPS if dist[r]))
    print(f'   same first camp hit {same_hit[0]}/{same_hit[1]}; same first ward tile {same_ward[0]}/{same_ward[1]}; same first capture tile {same_cap[0]}/{same_cap[1]}')
    # first capture timing spread per map
    fc = collections.defaultdict(list)
    for g in G:
        if g['caps']['S']: fc[(g['map'], g['side'])].append(g['caps']['S'][0][0])
    spread = [max(v) - min(v) for v in fc.values() if len(v) > 1]
    print(f'   first capture round spread within (map, side): median {sorted(spread)[len(spread)//2] if spread else None}, n {len(spread)}')
