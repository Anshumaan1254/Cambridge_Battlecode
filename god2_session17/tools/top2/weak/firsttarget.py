"""First camp target of each study body (an_weak): from tools/top2/weak/routes.mjs output + mapgeo2 groups, the rank of the first-hit
   camp group by walking distance from the body's spawn (1 = nearest group), its class, its distance, and whether it lies in the
   team's own / middle / enemy zone (f = dOwn / (dOwn + dEnemy)); also how many study bodies share the first group (opening blob size).
   python tools/top2/weak/firsttarget.py KEY..."""
import json, sys, collections
GEO = {}
for l in open('C:/battlecode/cache/an_strategy/mapgeo2.jsonl', encoding='utf-8'):
    g = json.loads(l); GEO[g['map']] = g
def gcls(g):
    ts = set(c[2] for c in g['camps'])
    for k in ['monolith', 'golem', 'elk', 'wolf', 'gem']:
        if k in ts: return k
    return 'gold'
for key in sys.argv[1:]:
    G = [json.loads(l) for l in open(f'C:/battlecode/cache/an_weak/routes_{key}.jsonl', encoding='utf-8') if l.strip()]
    ranks = collections.Counter(); cls = collections.Counter(); zone = collections.Counter(); share = collections.Counter(); n = 0
    firstR = []
    for g in G:
        geo = GEO.get(g['map'])
        if not geo: continue
        tile = {}
        for gr in geo['groups']:
            for c in gr['camps']: tile[(c[0], c[1])] = gr
        S = g['S']
        # team 0 = A unless the replay spawn is swapped: compare the first body position at r5 with spawnA
        sA = geo['spawnA'][0]
        firstpos = [b['pos'][0] for b in g['bodies'].values() if b['team'] == 'S' and b['pos'][0]]
        dA = lambda gr: gr['dA']; dB = lambda gr: gr['dB']
        isA = (S == 0)
        if firstpos:
            px, py = firstpos[0]
            da = max(abs(px - sA[0]), abs(py - sA[1])); sb = geo['spawnB'][0]; db = max(abs(px - sb[0]), abs(py - sb[1]))
            isA = da < db
        own = (lambda gr: gr['dA']) if isA else (lambda gr: gr['dB'])
        oth = (lambda gr: gr['dB']) if isA else (lambda gr: gr['dA'])
        order = sorted(geo['groups'], key=lambda gr: own(gr) if own(gr) >= 0 else 9999)
        rank = {gr['i']: k + 1 for k, gr in enumerate(order)}
        firsts = []
        for b in g['bodies'].values():
            if b['team'] != 'S' or not b['hits']: continue
            h = b['hits'][0]; gr = tile.get((h[1], h[2]))
            if not gr: continue
            n += 1; ranks[min(rank[gr['i']], 6)] += 1; cls[gcls(gr)] += 1
            f = own(gr) / max(1, own(gr) + oth(gr)); zone['own' if f < 0.4 else 'enemy' if f > 0.6 else 'mid'] += 1
            firsts.append(gr['i']); firstR.append(h[0])
        if firsts:
            c = collections.Counter(firsts); share[max(c.values())] += 1
    print(f'### {key}: {n} bodies; first-group rank by walking distance from own spawn: {dict(sorted(ranks.items()))}; class {dict(cls)}; zone {dict(zone)}; '
          f'largest number of bodies sharing one first group per game: {dict(sorted(share.items()))}; first hit round median {sorted(firstR)[len(firstR)//2]}')
