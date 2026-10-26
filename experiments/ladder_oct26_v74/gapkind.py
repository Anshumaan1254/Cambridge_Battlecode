"""Gaps between farm episodes split by what else the body did inside the gap (bank = 'Submit gems', shop / home = 'Shop' or 'Teleport complete', fight = champion hit,
death) vs pure farm-to-farm walks. python -I gapkind.py SIDES.json DECDIR"""
import gzip, json, sys, os, collections, statistics as st
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools', 'analysis'))
import choice_model as cm
S = json.load(open(sys.argv[1])); dec = sys.argv[2]; cheb = cm.cheb
for lab, flip in (('us', 0), ('them', 1)):
    K = collections.defaultdict(list); ng = len(S)
    for k, v in S.items():
        d = json.load(gzip.open(os.path.join(dec, k + '.json.gz'))); side = v['ours'] ^ flip
        camps = d['meta']['camps']; cl, ncl = cm.clusters_of(camps); cpos = {(c['x'], c['y']): i for i, c in enumerate(camps)}
        team = {b['index']: b['team'] for b in d['meta']['bodies']}
        R = {s['r']: {c[0]: c for c in s['ch']} for s in d['rounds']}
        ev = collections.defaultdict(lambda: collections.defaultdict(list))
        hits = collections.defaultdict(list)
        for e in d['events']:
            if 'who' not in e or team.get(e['who']) != side: continue
            ev[e['who']][e['k']].append(e['r'])
            if e['k'] in ('Attack', 'Cast ability'):
                if tuple(e.get('to', (0, 0))) in cpos: hits[e['who']].append((e['r'], cl[cpos[tuple(e['to'])]]))
                else: ev[e['who']]['champhit'].append(e['r'])
        for w, hs in hits.items():
            hs.sort(); eps = []
            for r, c in hs:
                if eps and eps[-1][0] == c and r - eps[-1][2] <= 12: eps[-1][2] = r
                else: eps.append([c, r, r])
            for a, b in zip(eps, eps[1:]):
                has = lambda kk: any(a[2] < r < b[1] for r in ev[w][kk])
                if has('Death'): kind = 'death'
                elif has('Teleport complete') or has('Shop'): kind = 'home/shop'
                elif has('Submit gems'): kind = 'bank'
                elif has('champhit'): kind = 'fight'
                else: kind = 'farm->farm'
                K[kind].append(b[1] - a[2])
    tot = sum(len(x) for x in K.values())
    print(lab, 'gaps', tot, ' | '.join('%s n/game %.1f mean %.0f rounds (total %.0f/game)' % (k, len(x) / ng, st.mean(x), sum(x) / ng) for k, x in sorted(K.items(), key=lambda kv: -sum(kv[1]))))
