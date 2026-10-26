"""Per camp cluster: attackers, kill time, time to capture; us vs them. python -I grp.py SIDES.json DECFILES..."""
import gzip, json, sys, collections, statistics as st
sides = json.load(open(sys.argv[1]))
cheb = lambda a, b: max(abs(a[0]-b[0]), abs(a[1]-b[1]))
def clusters(camps, link=4):
    n = len(camps); par = list(range(n))
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for i in range(n):
        for j in range(i+1, n):
            if cheb((camps[i]['x'], camps[i]['y']), (camps[j]['x'], camps[j]['y'])) <= link: par[f(i)] = f(j)
    return [f(i) for i in range(n)]
rows = {'us': [], 'them': []}
for fn in sys.argv[2:]:
    key = fn.replace(chr(92), '/').rsplit('/', 1)[-1].replace('.json.gz', '')
    if key not in sides: continue
    o = sides[key]['ours']; d = json.load(gzip.open(fn)); camps = d['meta']['camps']; cl = clusters(camps)
    cpos = {(c['x'], c['y']): i for i, c in enumerate(camps)}
    R = d['rounds']; s0 = R[0] if R[0]['r'] <= 1 else R[1]
    pos = {0: [], 1: []}
    for c in s0['ch']: pos[c[1]].append((c[3], c[4]))
    cen = {t: (sum(p[0] for p in pos[t]) / len(pos[t]), sum(p[1] for p in pos[t]) / len(pos[t])) for t in (0, 1)}
    hits = collections.defaultdict(list)  # cluster -> (r, who, team)
    for e in d['events']:
        if 'team' not in e: continue
        if e['k'] in ('Attack', 'Cast ability') and tuple(e.get('to', (0, 0))) in cpos:
            hits[cl[cpos[tuple(e['to'])]]].append((e['r'], e['who'], e['team']))
    caps = [e for e in d['events'] if e['k'] == 'CaptureGems' and 'team' in e]
    for e in caps:
        # nearest cluster
        best = min(set(cl), key=lambda c: min(cheb(tuple(e['at']), (camps[i]['x'], camps[i]['y'])) for i in range(len(camps)) if cl[i] == c))
        dist = min(cheb(tuple(e['at']), (camps[i]['x'], camps[i]['y'])) for i in range(len(camps)) if cl[i] == best)
        if dist > 8: continue
        # hits by capturing team in the 120 rounds before capture
        hs = [h for h in hits[best] if h[2] == e['team'] and e['r'] - 120 <= h[0] <= e['r']]
        if not hs: continue
        # episode: walk back while gaps <= 10
        hs.sort(); ep = [hs[-1]]
        for h in reversed(hs[:-1]):
            if ep[0][0] - h[0] <= 12: ep.insert(0, h)
            else: break
        side = 'us' if e['team'] == o else 'them'
        a = cheb(tuple(e['at']), cen[o]); b = cheb(tuple(e['at']), cen[1 - o])
        zone = 'mid' if abs(a - b) <= 4 else ('own' if (a < b) == (side == 'us') else 'opp')
        ncamp = sum(1 for i in range(len(camps)) if cl[i] == best)
        rows[side].append({'zone': zone, 'gems': e['gems'], 'dur': ep[-1][0] - ep[0][0] + 1, 'bodies': len(set(h[1] for h in ep)), 'hits': len(ep), 'ncamp': ncamp, 'capdelay': e['r'] - ep[-1][0], 'r': e['r']})
for side in ('us', 'them'):
    L = rows[side]; print(side, 'captures with episode', len(L))
    for z in ('own', 'mid', 'opp'):
        M = [x for x in L if x['zone'] == z]
        if not M: continue
        print('  %-3s n %4d gems %5.1f camps %4.1f | hits %5.1f  dur %5.1f  bodies %4.2f  hits/round %.2f  capture delay after last hit %.1f' % (z, len(M), st.mean(x['gems'] for x in M), st.mean(x['ncamp'] for x in M), st.mean(x['hits'] for x in M), st.mean(x['dur'] for x in M), st.mean(x['bodies'] for x in M), st.mean(x['hits'] / x['dur'] for x in M), st.mean(x['capdelay'] for x in M)))
