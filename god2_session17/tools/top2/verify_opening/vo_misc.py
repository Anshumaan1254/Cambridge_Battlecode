# Rule-level facts for the verification: (a) HP share at home arrivals (recall or crystal) in r<=300 per team;
# (b) what the bodies outside the main squad hit first, and whether they join the main group by r100.
# Usage: python tools/top2/verify_opening/vo_misc.py OUT.json
import gzip, json, glob, os, sys, statistics as st
from collections import defaultdict, Counter, deque
from multiprocessing import Pool

CACHE = 'C:/battlecode/cache'
KEYS = ('pbg', 'ifish', 'pantheon', 'coo', 'cm', 'nyx')
STUDY = {'pbg': '38e6d8c4', 'ifish': '1890540d', 'pantheon': '547efb5b', 'coo': '1570a113', 'cm': 'ad5474c2', 'nyx': '6f7fd199'}
RANK = {'monolith': 6, 'golem': 5, 'elk': 4, 'wolf': 3, 'gem': 2, 'gold': 1}
GEO = {}


def init():
    for l in open(CACHE + '/an_strategy/mapgeo2.jsonl', encoding='utf-8'):
        g = json.loads(l)
        GEO[g['map']] = g


def run(args):
    key, p, row = args
    if not GEO:
        init()
    d = json.load(gzip.open(p))
    meta, R = d['meta'], d['R']
    team = {b['index']: b['team'] for b in meta['bodies']}
    ids = [None, None]
    for t in row['teams']:
        ids[0 if t['side'] == 'a' else 1] = t['teamId']
    s = 0 if ids[0].startswith(STUDY[key]) else 1
    geo = GEO[row['map']]
    sp = [set(map(tuple, geo['spawnA'])), set(map(tuple, geo['spawnB']))]
    out = {'key': key, 'file': os.path.basename(p), 'study': s, 'home': [[], []], 'side': [[], []]}
    # (a) home arrivals
    for r in range(2, min(300, len(R) - 1) + 1):
        prev = {x[0]: x for x in R[r - 1][3]}
        for x in R[r][3]:
            i = x[0]; t = team[i]; o = prev[i]
            if not (x[5] and o[5]):
                continue
            if (x[1], x[2]) in sp[t] and min(max(abs(o[1] - a), abs(o[2] - b)) for a, b in sp[t]) > 2:
                hp6 = R[max(0, r - 6)][3]
                h6 = next(y for y in hp6 if y[0] == i)
                out['home'][t].append([r, o[3] / max(1, o[4]), h6[3] / max(1, h6[4]) if h6[5] else None])
    # (b) side bodies
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
    gcls = [max((ctype[m] for m in mem), key=lambda z: RANK.get(z, 0)) for mem in groups]
    seq = defaultdict(list)
    for q, r, a, ci, amt in d['cdmg']:
        if a in team and ci in gid and r <= 300:
            g = gid[ci]
            if not seq[a] or seq[a][-1][1] != g:
                seq[a].append((r, g))
    for t in (0, 1):
        mine = [i for i in team if team[i] == t]
        firsts = Counter(seq[i][0][1] for i in mine if seq[i])
        if not firsts:
            continue
        main = firsts.most_common(1)[0][0]
        for i in mine:
            if not seq[i] or seq[i][0][1] == main:
                continue
            joined = next((r for r, g in seq[i] if g == main), None)
            out['side'][t].append([gcls[seq[i][0][1]], seq[i][0][0], joined, len(groups[seq[i][0][1]])])
    return json.dumps(out)


def jobs():
    J = []
    for key in KEYS:
        rows = {}
        for l in open(f'{CACHE}/t2/{key}/index.jsonl', encoding='utf-8'):
            r = json.loads(l)
            rows[f"{r['map']}_{r['matchId'][:8]}.json.gz"] = r
        for p in sorted(glob.glob(f'{CACHE}/t2dump/{key}/*.json.gz')):
            J.append((key, p, rows[os.path.basename(p)]))
    return J


if __name__ == '__main__':
    with Pool(3, initializer=init) as pool, open(sys.argv[1], 'w') as fo:
        for s in pool.imap(run, jobs(), chunksize=4):
            fo.write(s + '\n')
    rows = [json.loads(l) for l in open(sys.argv[1])]
    for key in KEYS:
        own = [h for x in rows if x['key'] == key for h in x['home'][x['study']]]
        opp = [h for x in rows if x['key'] == key for h in x['home'][1 - x['study']]]
        print(f"{key:9s} home arrivals r<=300: n {len(own)} HP share before arrival median {st.median([h[1] for h in own]):.2f} "
              f"(6 rounds earlier {st.median([h[2] for h in own if h[2] is not None]):.2f}); below 0.5: {sum(h[1] < 0.5 for h in own) / len(own):.2f} | "
              f"opponents median {st.median([h[1] for h in opp]):.2f}")
        side = [s_ for x in rows if x['key'] == key for s_ in x['side'][x['study']]]
        ng = sum(1 for x in rows if x['key'] == key)
        c = Counter(s_[0] for s_ in side)
        print(f"          side bodies per game {len(side) / ng:.2f}; first target class {dict(c)}; joined main group by r100 {sum(1 for s_ in side if s_[2] and s_[2] <= 100) / max(1, len(side)):.2f}")
