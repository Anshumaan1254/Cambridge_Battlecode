"""Timeline of a local replay (team A = 'US'). python -I ltimeline.py REPLAY R0 R1 STEP"""
import json, os, subprocess, sys, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools', 'analysis')); import choice_model as cm
f = sys.argv[1]; out = f + '.json'
if not os.path.exists(out): subprocess.run(['node', 'tools/replay/decode.mjs', f, '--out', out], check=True, capture_output=True)
d = json.load(open(out)); typ = {b['index']: b['type'][:4] for b in d['meta']['bodies']}
camps = d['meta']['camps']; cl, n = cm.clusters_of(camps); cpos = {(c['x'], c['y']) for c in camps}
mem = collections.defaultdict(list)
for i, c in enumerate(camps): mem[cl[i]].append(i)
big = [g for g, v in mem.items() if len(v) >= 4]
R = {s['r']: s for s in d['rounds']}; acts = collections.defaultdict(list)
for e in d['events']:
    if 'who' in e and e['k'] in ('Attack', 'Cast ability', 'CaptureGems'):
        acts[(e['r'], e['who'])].append(('camp' if e['k'] != 'CaptureGems' and tuple(e['to']) in cpos else ('CAP%d' % e['gems'] if e['k'] == 'CaptureGems' else 'champ')))
for r in range(int(sys.argv[2]), int(sys.argv[3]) + 1, int(sys.argv[4])):
    s = R.get(r)
    if not s: continue
    f2 = lambda t: ' '.join('%s(%d,%d)%d%s' % (typ[c[0]], c[3], c[4], c[5], ('[' + ','.join(acts[(r, c[0])]) + ']') if acts[(r, c[0])] else '') for c in s['ch'] if c[1] == t and c[7])
    print('r%d big-hp %s\n   A: %s\n   B: %s' % (r, {g: sum(max(0, s['campHp'][i]) for i in mem[g]) for g in big}, f2(0), f2(1)))
