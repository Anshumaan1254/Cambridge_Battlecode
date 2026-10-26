"""Join G17_TRACE lines (decision path per body-turn) with decoded replay actions: near-enemy turns by path and action.
python -I tr_analyze.py REPLAY_GLOB [SIDE=a]"""
import glob, gzip, json, os, re, subprocess, sys, zipfile, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CH = ['Ryth', 'VesperVale', 'Vendetta', 'Cassi', 'Issac', 'Stellar', 'Prism', 'Marcella', 'Willow', 'Ren', 'Varg', 'Tavi', 'HeartOfRuin']
PATH = {0: 'none', 1: 'combat-fight', 2: 'combat-other', 3: 'safety', 4: 'tribute', 5: 'home_trip', 6: 'shop_trip', 7: 'alert', 8: 'farm', 9: 'regroup', 10: 'gank', 11: 'deny', 12: 'pocket', 13: 'lock', 14: 'hunt'}
cheb = lambda a, b: max(abs(a[0]-b[0]), abs(a[1]-b[1]))
side = sys.argv[2] if len(sys.argv) > 2 else 'a'; ti = 0 if side == 'a' else 1
A = collections.defaultdict(collections.Counter); tot = collections.Counter()
for f in sorted(glob.glob(sys.argv[1])):
    out = os.path.join(os.path.dirname(f), '..', '..', '..', 'local_oct26', 'trdec', os.path.basename(f) + '.json')
    if not os.path.exists(out):
        subprocess.run(['node', os.path.join(ROOT, 'tools', 'replay', 'decode.mjs'), f, '--out', out], check=True, capture_output=True)
    d = json.load(open(out))
    txt = zipfile.ZipFile(f).read('team-%s.stdout' % side).decode('latin1')
    tr = {}
    for m in re.finditer(r'G7 r=(\d+) ch=(\d+) path=(\d+) task=(\d+) nd=(\d+) mv=(\d) hit=(\d) hp=([\d.]+)', txt):
        r, ch, p, t, nd = (int(m.group(i)) for i in range(1, 6))
        tr[(r, CH[ch])] = (p, t, nd)
    body = {b['index']: b['type'] for b in d['meta']['bodies'] if b['team'] == ti}
    cpos = {(c['x'], c['y']) for c in d['meta']['camps']}
    R = {s['r']: {c[0]: c for c in s['ch']} for s in d['rounds']}
    acts = {}
    for e in d['events']:
        if 'who' in e and e['who'] in body and e['k'] in ('Attack', 'Cast ability') and e.get('to'):
            acts[(e['r'], e['who'])] = 'hitcamp' if tuple(e['to']) in cpos else ('hitchamp' if acts.get((e['r'], e['who'])) != 'hitcamp' else 'hitcamp')
    for (r, typ), (p, t, nd) in tr.items():
        w = [k for k, v in body.items() if v == typ]
        if not w or nd > 8: continue
        w = w[0]; cur = R.get(r, {}).get(w); prev = R.get(r - 1, {}).get(w)
        if not cur or not prev or not cur[7]: continue
        a = acts.get((r, w))
        if not a:
            en = [q for q in R[r - 1].values() if q[1] != ti and q[7]]
            if not en: continue
            pa, pb = (prev[3], prev[4]), (cur[3], cur[4])
            near = min(en, key=lambda q: cheb((q[3], q[4]), pa)); d0 = cheb((near[3], near[4]), pa); d1 = cheb((near[3], near[4]), pb)
            a = 'still' if pa == pb else ('toward' if d1 < d0 else ('away' if d1 > d0 else 'side'))
        A[PATH.get(p, p)][a] += 1; tot[a] += 1
n = sum(tot.values()); print('near-enemy body-turns', n, {k: '%.2f' % (v / n) for k, v in tot.most_common()})
for p, c in sorted(A.items(), key=lambda kv: -sum(kv[1].values())):
    m = sum(c.values()); print('  %-13s %5d (%.0f%%): ' % (p, m, 100 * m / n) + ' '.join('%s %.2f' % (k, v / m) for k, v in c.most_common()))
