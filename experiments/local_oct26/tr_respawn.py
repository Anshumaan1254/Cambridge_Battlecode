"""After each respawn of our bodies (side a): rounds to first camp hit, and the decision paths (G17_TRACE) used in between."""
import glob, json, os, re, sys, zipfile, collections, statistics as st
CH = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin']
PATH = {0: 'none', 1: 'combat-fight', 2: 'combat-other', 3: 'safety', 4: 'tribute', 5: 'home_trip', 6: 'shop_trip', 7: 'alert', 8: 'farm', 9: 'regroup', 10: 'gank', 11: 'deny', 12: 'pocket', 13: 'lock', 14: 'hunt'}
T = []; P = collections.Counter(); first = []
for f in sorted(glob.glob(sys.argv[1])):
    d = json.load(open(os.path.join('experiments/local_oct26/trdec', os.path.basename(f) + '.json')))
    txt = zipfile.ZipFile(f).read('team-a.stdout').decode('latin1')
    tr = {}
    for m in re.finditer(r'G7 r=(\d+) ch=(\d+) path=(\d+) task=(\d+) nd=(\d+)', txt):
        tr[(int(m.group(1)), CH[int(m.group(2))])] = int(m.group(3))
    body = {b['index']: b['type'] for b in d['meta']['bodies'] if b['team'] == 0}
    cpos = {(c['x'], c['y']) for c in d['meta']['camps']}
    hits = collections.defaultdict(list); resp = collections.defaultdict(list)
    for e in d['events']:
        if e.get('who') in body:
            if e['k'] in ('Attack', 'Cast ability') and e.get('to') and tuple(e['to']) in cpos: hits[e['who']].append(e['r'])
            if e['k'] == 'Respawn': resp[e['who']].append(e['r'])
    for w in body:
        h = sorted(hits[w]); first.append(h[0] if h else 999)
        for r in resp[w]:
            nh = [x for x in h if x > r]
            if not nh: continue
            T.append(nh[0] - r)
            for rr in range(r, nh[0]): P[PATH.get(tr.get((rr, body[w]), -1), 'none')] += 1
print('respawns', len(T), 'to first camp hit mean %.1f median %d' % (st.mean(T), st.median(T)), '| game start -> first hit median', st.median(first))
n = sum(P.values()); print({k: '%.2f' % (v / n) for k, v in P.most_common()})
