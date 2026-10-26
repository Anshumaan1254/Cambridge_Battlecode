"""Show A-B-A episodes of our bodies near enemies: round, pos, nearest enemy (type, dist), action. python -I abalog.py SIDES.json DECDIR N SEED"""
import gzip, json, sys, os, random
S = json.load(open(sys.argv[1])); dec = sys.argv[2]; N = int(sys.argv[3]); random.seed(int(sys.argv[4]))
cheb = lambda a, b: max(abs(a[0]-b[0]), abs(a[1]-b[1]))
found = []
for k, v in S.items():
    d = json.load(gzip.open(os.path.join(dec, k + '.json.gz'))); side = v['ours']
    typ = {b['index']: b['type'] for b in d['meta']['bodies']}; cpos = {(c['x'], c['y']) for c in d['meta']['camps']}
    R = {s['r']: {c[0]: c for c in s['ch']} for s in d['rounds']}; rs = sorted(R)
    acts = {}
    for e in d['events']:
        if 'who' in e and e['k'] in ('Attack', 'Cast ability') and e.get('to'): acts[(e['r'], e['who'])] = ('camp' if tuple(e['to']) in cpos else 'champ') + (':c%d' % e.get('slot', 0) if e['k'] == 'Cast ability' else ':a')
    for w in [b['index'] for b in d['meta']['bodies'] if b['team'] == side]:
        for r in rs[3:-3]:
            p = [R.get(r - i, {}).get(w) for i in range(3)]
            if any(x is None or not x[7] for x in p): continue
            x0, x1, x2 = (p[2][3], p[2][4]), (p[1][3], p[1][4]), (p[0][3], p[0][4])
            if x0 == x2 and x1 != x0 and (r - 2, w) not in acts and (r - 1, w) not in acts and (r, w) not in acts:
                en = [c for c in R[r].values() if c[1] != side and c[7] and cheb((c[3], c[4]), x2) <= 8]
                if en: found.append((k, w, r))
print(len(found), 'A-B-A (no action) cases')
for k, w, r in random.sample(found, N):
    d = json.load(gzip.open(os.path.join(dec, k + '.json.gz'))); side = S[k]['ours']
    typ = {b['index']: b['type'] for b in d['meta']['bodies']}; cpos = {(c['x'], c['y']) for c in d['meta']['camps']}
    R = {s['r']: {c[0]: c for c in s['ch']} for s in d['rounds']}
    acts = {}
    for e in d['events']:
        if 'who' in e and e['k'] in ('Attack', 'Cast ability') and e.get('to'): acts[(e['r'], e['who'])] = ('camp' if tuple(e['to']) in cpos else 'champ')
    print('=== %s %s %s %s round %d' % (k[:8], S[k]['map'], S[k]['opp'][:12], typ[w], r))
    for rr in range(r - 6, r + 4):
        c = R.get(rr, {}).get(w)
        if not c: continue
        en = sorted(((cheb((q[3], q[4]), (c[3], c[4])), typ[q[0]][:4], q[5]) for q in R[rr].values() if q[1] != side and q[7]))[:3]
        al = sorted(((cheb((q[3], q[4]), (c[3], c[4])), typ[q[0]][:4]) for q in R[rr].values() if q[1] == side and q[7] and q[0] != w))[:2]
        nc = min((cheb(p, (c[3], c[4])) for p in cpos), default=99)
        print('  r%d pos(%d,%d) hp%d act=%s camp_d=%d enemies(d,type,hp)=%s allies=%s' % (rr, c[3], c[4], c[5], acts.get((rr, w), '-'), nc, en, al))
