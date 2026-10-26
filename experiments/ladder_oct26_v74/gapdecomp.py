"""Where the rounds between two farm episodes of a body go: dead, fighting champions, walking (enemy near / not), standing, home (on spawn).
python -I gapdecomp.py SIDES.json DECDIR [--maxgap 300]"""
import gzip, json, sys, os, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools', 'analysis'))
import choice_model as cm
S = json.load(open(sys.argv[1])); dec = sys.argv[2]
cheb = cm.cheb
for lab, flip in (('us', 0), ('them', 1)):
    A = collections.Counter(); ng = 0; tot = 0
    for k, v in S.items():
        d = json.load(gzip.open(os.path.join(dec, k + '.json.gz'))); side = v['ours'] ^ flip
        camps = d['meta']['camps']; cl, ncl = cm.clusters_of(camps); cpos = {(c['x'], c['y']): i for i, c in enumerate(camps)}
        team = {b['index']: b['team'] for b in d['meta']['bodies']}
        R = {s['r']: s for s in d['rounds']}; rs = sorted(R)
        act = {}
        for e in d['events']:
            if 'who' in e and e['k'] in ('Attack', 'Cast ability') and e.get('to'):
                act.setdefault((e['r'], e['who']), 'camp' if tuple(e['to']) in cpos else 'champ')
                if tuple(e['to']) not in cpos: act[(e['r'], e['who'])] = 'champ'
        hits = collections.defaultdict(list)
        for (r, w), a in act.items():
            if a == 'camp' and team.get(w) == side: hits[w].append(r)
        spawn = [(c[3], c[4]) for c in R[rs[0]]['ch'] if c[1] == side]
        for w, hs in hits.items():
            hs.sort(); eps = []
            for r in hs:
                if eps and r - eps[-1][1] <= 12: eps[-1][1] = r
                else: eps.append([r, r])
            for a, b in zip(eps, eps[1:]):
                ng += 1; tot += b[0] - a[1] - 1
                for r in range(a[1] + 1, b[0]):
                    if r not in R or r - 1 not in R: continue
                    c = [x for x in R[r]['ch'] if x[0] == w][0]; o = [x for x in R[r - 1]['ch'] if x[0] == w][0]
                    if not c[7]: cat = 'dead'
                    elif act.get((r, w)) == 'champ': cat = 'champ'
                    else:
                        en = any(q[1] != side and q[7] and cheb((q[3], q[4]), (c[3], c[4])) <= 8 for q in R[r]['ch'])
                        moved = (o[3], o[4]) != (c[3], c[4])
                        if moved: cat = 'walkE' if en else 'walk'
                        elif min(cheb(p, (c[3], c[4])) for p in spawn) <= 2: cat = 'home'
                        else: cat = 'standE' if en else 'stand'
                    A[cat] += 1
    print('%-5s gaps %6d  mean gap %.1f rounds: ' % (lab, ng, tot / ng) + '  '.join('%s %.1f' % (c, A[c] / ng) for c in ('dead', 'champ', 'walkE', 'walk', 'standE', 'stand', 'home')))
