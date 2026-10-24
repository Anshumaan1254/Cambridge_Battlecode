"""Blob coverage (an_weak): captures before R (default 300) by the opponent of a study team, with the distance from the capture tile to the
   nearest study body (alive) and to the study team's largest cluster centre at that round; plus the study team's own captures.
   python tools/top2/weak/blobfree.py KEY [R]"""
import json, gzip, glob, os, sys, collections
key = sys.argv[1]; RMAX = int(sys.argv[2]) if len(sys.argv) > 2 else 300
TEAMS = {'pbg': '38e6d8c4', 'ifish': '1890540d', 'cm': 'ad5474c2', 'pantheon': '547efb5b', 'coo': '1570a113', 'nyx': '6f7fd199'}
idx = {}
for l in open(f'C:/battlecode/cache/t2/{key}/index.jsonl', encoding='utf-8'):
    r = json.loads(l); idx[r['matchId'][:8]] = r
cheb = lambda a, b: max(abs(a[0] - b[0]), abs(a[1] - b[1]))
agg = {1: collections.Counter(), 0: collections.Counter()}; ng = collections.Counter()
for f in glob.glob(f'C:/battlecode/cache/t2dump/{key}/*.json.gz'):
    row = idx.get(os.path.basename(f).split('_')[-1][:8])
    if not row: continue
    me = [t for t in row['teams'] if t['teamId'].startswith(TEAMS[key])][0]; S = 0 if me['side'] == 'a' else 1; win = 1 if me['result'] == 'win' else 0
    d = json.loads(gzip.open(f).read()); team = {b['index']: b['team'] for b in d['meta']['bodies']}
    PM = {e[0]: e[3] for e in d['R']}
    ng[win] += 1
    for e in d['ev']:
        if e['k'] != 'CaptureGems' or e['r'] >= RMAX: continue
        L = [c for c in PM.get(e['r'] - 1, []) if team[c[0]] == S and c[5]]
        if not L: continue
        dmin = min(cheb((c[1], c[2]), e['at']) for c in L)
        # largest cluster (Chebyshev <= 4 connected) centre
        best = []; seen = set()
        for i in range(len(L)):
            if i in seen: continue
            comp = [i]; seen.add(i); k = 0
            while k < len(comp):
                u = comp[k]; k += 1
                for j in range(len(L)):
                    if j not in seen and cheb((L[u][1], L[u][2]), (L[j][1], L[j][2])) <= 4: seen.add(j); comp.append(j)
            if len(comp) > len(best): best = comp
        cx = sum(L[i][1] for i in best) / len(best); cy = sum(L[i][2] for i in best) / len(best)
        dblob = cheb((cx, cy), e['at'])
        who = 'S' if team[e['who']] == S else 'O'
        A = agg[win]
        A[who + ' caps'] += 1; A[who + ' gems'] += e['gems']
        if who == 'O':
            if dmin > 10: A['O free caps'] += 1; A['O free gems'] += e['gems']
            if dblob > 15: A['O far-from-blob caps'] += 1; A['O far-from-blob gems'] += e['gems']
for win in [1, 0]:
    A = agg[win]; n = ng[win]
    print(f'{key} {"wins" if win else "losses"} (n {n}) r<{RMAX}: study caps {A["S caps"]/n:.1f} ({A["S gems"]/n:.0f} g) | opp caps {A["O caps"]/n:.1f} ({A["O gems"]/n:.0f} g), '
          f'with no study body within 10: {A["O free caps"]/n:.1f} ({A["O free gems"]/n:.0f} g), >15 from the study blob centre: {A["O far-from-blob caps"]/n:.1f} ({A["O far-from-blob gems"]/n:.0f} g)')
