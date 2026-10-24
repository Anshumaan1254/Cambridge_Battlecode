# Elk / wolf group pipeline timing, split into kill phase and capture phase, by hitters and exact group composition.
# Usage: python tools/top2/verify_opening/vo_elk.py OUT.jsonl   (all six study folders; one line per capture r<=300)
# kill phase = first own hit -> last own hit before the capture; capture phase = last own hit -> capture round.
# 'early hitters' = own bodies whose first hit on the group falls within 5 rounds of the team's first hit (concurrent squad).
import gzip, json, glob, os, sys
from collections import defaultdict, deque, Counter
from multiprocessing import Pool

CACHE = 'C:/battlecode/cache'
KEYS = ('pbg', 'ifish', 'pantheon', 'coo', 'cm', 'nyx')
RANK = {'monolith': 6, 'golem': 5, 'elk': 4, 'wolf': 3, 'gem': 2, 'gold': 1}


def run(p):
    d = json.load(gzip.open(p))
    meta = d['meta']
    team = {b['index']: b['team'] for b in meta['bodies']}
    bt = {b['index']: b['type'] for b in meta['bodies']}
    cpos, ctype = {}, {}
    for c in meta['camps']:
        cpos[c['index']] = (c['x'], c['y']); ctype[c['index']] = 'golem' if c['type'] == 5 else c['type']
    t2c = {v: k for k, v in cpos.items()}
    gid, groups = {}, []
    for i in cpos:
        if i in gid:
            continue
        gid[i] = len(groups); mem = [i]; dq = deque([i])
        while dq:
            j = dq.popleft(); x, y = cpos[j]
            for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                k = t2c.get(q)
                if k is not None and k not in gid:
                    gid[k] = len(groups); mem.append(k); dq.append(k)
        groups.append(mem)
    tile2g = {cpos[m]: gi for gi, mem in enumerate(groups) for m in mem}
    hits = defaultdict(list)
    for q, r, a, ci, amt in d['cdmg']:
        if ci in gid and a in team:
            hits[gid[ci]].append((q, r, a, amt))
    steps = defaultdict(list)
    for e in d['ev']:
        if e['k'] == 'CaptureGems':
            steps[e['q']].append(e)
    last = defaultdict(int)
    out = []
    for q in sorted(steps):
        es = steps[q]
        r = es[0]['r']; t = es[0]['team']
        gi = Counter(tile2g.get(tuple(e['at'])) for e in es).most_common(1)[0][0]
        if gi is None:
            continue
        lo = last[gi]; last[gi] = r
        if r > 300:
            continue
        hs = [h for h in hits[gi] if lo < h[1] <= r and h[0] < q]
        own = [h for h in hs if team[h[2]] == t]
        opp = [h for h in hs if team[h[2]] != t]
        if not own:
            continue
        f = min(h[1] for h in own); l = max(h[1] for h in own)
        firsts = {}
        for h in sorted(own):
            firsts.setdefault(h[2], h[1])
        comp = Counter(ctype[m] for m in groups[gi])
        cls = max(comp, key=lambda k: RANK.get(k, 0))
        out.append({'file': os.path.basename(p), 'r': r, 't': t, 'cls': cls, 'comp': '+'.join(f'{comp[k]}{k}' for k in sorted(comp)),
                    'nelk': comp.get('elk', 0), 'nwolf': comp.get('wolf', 0), 'first': f, 'last': l, 'hitters': len(firsts),
                    'early': sum(1 for b in firsts if firsts[b] - f <= 5), 'contested': len(opp) > 0,
                    'dmg': sum(h[3] for h in own), 'ncap': len(es), 'capt': [bt[e['who']] for e in es]})
    return out


if __name__ == '__main__':
    files = [f for f in sorted(glob.glob(f'{CACHE}/t2dump/*/*.json.gz')) if os.path.basename(os.path.dirname(f)) in KEYS]
    with Pool(3) as pool, open(sys.argv[1], 'w') as fo:
        for rows in pool.imap(run, files, chunksize=4):
            for x in rows:
                fo.write(json.dumps(x) + '\n')
    print('done', len(files))
