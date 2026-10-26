"""Camp damage that never became a capture: per team, damage dealt on a cluster whose next capture (by anyone) did not come within 60 rounds
of the hit (the camp healed or was abandoned). python -I waste.py SIDES.json DECDIR [MAXR] [--flip]"""
import gzip, json, sys, os, collections, bisect
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools', 'analysis'))
import choice_model as cm
a = [x for x in sys.argv[1:] if not x.startswith('--')]
S = json.load(open(a[0])); dec = a[1]; MR = int(a[2]) if len(a) > 2 else 9999; cheb = cm.cheb
T = collections.Counter(); n = 0
for k, v in S.items():
    d = json.load(gzip.open(os.path.join(dec, k + '.json.gz'))); o = v['ours'] ^ (1 if '--flip' in sys.argv else 0); n += 1
    camps = d['meta']['camps']; cl, ncl = cm.clusters_of(camps); cpos = {(c['x'], c['y']): i for i, c in enumerate(camps)}
    R = {s['r']: s for s in d['rounds']}; rs = sorted(R)
    hits = collections.defaultdict(list)
    for e in d['events']:
        if e['k'] in ('Attack', 'Cast ability') and 'team' in e and e.get('to') and tuple(e['to']) in cpos:
            hits[e['r']].append((e['team'], cpos[tuple(e['to'])]))
    capr = collections.defaultdict(list)
    for e in d['events']:
        if e['k'] == 'CaptureGems' and 'team' in e:
            ci = min(range(len(camps)), key=lambda j: cheb(tuple(e['at']), (camps[j]['x'], camps[j]['y'])))
            capr[cl[ci]].append(e['r'])
    for g in capr: capr[g] = sorted(set(capr[g]))
    for i in range(1, len(rs)):
        r0, r1 = rs[i - 1], rs[i]
        if r1 > MR: break
        h0, h1 = R[r0]['campHp'], R[r1]['campHp']
        for c in range(len(camps)):
            dl = h0[c] - h1[c]
            if dl <= 0: continue
            who = [t for t, ci in hits.get(r1, []) if ci == c]
            if not who: continue
            L = capr.get(cl[c], []); j = bisect.bisect_left(L, r1)
            ok = j < len(L) and L[j] - r1 <= 60
            for t in who:
                s = 'us' if t == o else 'them'
                T[s + '_dmg'] += dl / len(who)
                if not ok: T[s + '_waste'] += dl / len(who)
for s in ('us', 'them'):
    print('%-4s camp damage/game %.0f, not followed by a capture within 60 rounds %.0f (%.0f%%)' % (s, T[s + '_dmg'] / n, T[s + '_waste'] / n, 100 * T[s + '_waste'] / max(1, T[s + '_dmg'])))
