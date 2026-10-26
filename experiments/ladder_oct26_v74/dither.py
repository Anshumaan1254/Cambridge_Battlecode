"""Dithering near enemies: consecutive near-enemy turns of one body (enemy within 8 both rounds) where the step toward/away from the nearest enemy flips sign;
also oscillation A-B-A. python -I dither.py SIDES.json DECDIR"""
import gzip, json, sys, os, collections
S = json.load(open(sys.argv[1])); dec = sys.argv[2]
cheb = lambda a, b: max(abs(a[0]-b[0]), abs(a[1]-b[1]))
for lab, flip in (('us', 0), ('them', 1)):
    C = collections.Counter(); n = len(S)
    for k, v in S.items():
        d = json.load(gzip.open(os.path.join(dec, k + '.json.gz'))); side = v['ours'] ^ flip
        cpos = {(c['x'], c['y']) for c in d['meta']['camps']}
        acts = {}
        for e in d['events']:
            if 'who' in e and e['k'] in ('Attack', 'Cast ability') and e.get('to'): acts[(e['r'], e['who'])] = 1
        rs = sorted(s['r'] for s in d['rounds']); R = {s['r']: {c[0]: c for c in s['ch']} for s in d['rounds']}
        body = [b['index'] for b in d['meta']['bodies'] if b['team'] == side]
        for w in body:
            hist = []   # (round, pos, step_kind)
            for r in rs[1:]:
                a = R.get(r - 1, {}).get(w); b = R.get(r, {}).get(w)
                if not a or not b or not a[7] or not b[7]: hist = []; continue
                pa = (a[3], a[4]); pb = (b[3], b[4])
                en = [c for c in R[r - 1].values() if c[1] != side and c[7]]
                if not en: hist = []; continue
                near = min(en, key=lambda c: cheb((c[3], c[4]), pa)); dn = cheb((near[3], near[4]), pa)
                if dn > 8: hist = []; continue
                dn2 = cheb((near[3], near[4]), pb)
                kind = 'hit' if acts.get((r, w)) else ('still' if pa == pb else ('toward' if dn2 < dn else ('away' if dn2 > dn else 'side')))
                hist.append((r, pb, kind, pa))
                C['turns'] += 1; C[kind] += 1
                if len(hist) >= 2:
                    p, q = hist[-2], hist[-1]
                    if {p[2], q[2]} == {'toward', 'away'}: C['flip'] += 1
                if len(hist) >= 3:
                    x, y, z = hist[-3], hist[-2], hist[-1]
                    if z[1] == x[1] and y[1] != x[1] and z[2] not in ('hit', 'still') and y[2] not in ('hit', 'still'): C['ABA'] += 1
    t = C['turns']
    print('%-5s near-enemy turns/game %.0f | hit %.2f still %.2f toward %.2f away %.2f side %.2f | toward<->away flips %.1f/game (%.1f%% of turns) | A-B-A %.1f/game (%.1f%%)' % (
        lab, t / n, C['hit'] / t, C['still'] / t, C['toward'] / t, C['away'] / t, C['side'] / t, C['flip'] / n, 100 * C['flip'] / t, C['ABA'] / n, 100 * C['ABA'] / t))
