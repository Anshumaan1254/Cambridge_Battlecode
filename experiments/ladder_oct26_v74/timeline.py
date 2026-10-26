"""Every body's position / hp / action each round in a window, plus camp-cluster health. python -I timeline.py MATCHPREFIX R0 R1 [STEP]"""
import gzip, json, sys, collections
sys.path.insert(0, '../../tools/analysis'); import choice_model as cm
S = json.load(open('sides_all.json')); k = [x for x in S if x.startswith(sys.argv[1])][0]; o = S[k]['ours']
d = json.load(gzip.open('dec/%s.json.gz' % k)); typ = {b['index']: b['type'][:4] for b in d['meta']['bodies']}
camps = d['meta']['camps']; cl, n = cm.clusters_of(camps); cpos = {(c['x'], c['y']): i for i, c in enumerate(camps)}
mem = collections.defaultdict(list)
for i, c in enumerate(camps): mem[cl[i]].append(i)
big = [g for g, v in mem.items() if len(v) >= 4]
R = {s['r']: s for s in d['rounds']}
acts = collections.defaultdict(list)
for e in d['events']:
    if 'who' in e and e['k'] in ('Attack', 'Cast ability', 'Recall', 'Capture', 'CaptureGems', 'Death', 'Shop', 'Submit gems'):
        t = e.get('to')
        if e['k'] in ('Attack', 'Cast ability'):
            tgt = 'camp' if tuple(t) in cpos else next((typ[q[0]] for q in R[e['r']]['ch'] if (q[3], q[4]) == tuple(t)), '?')
            acts[(e['r'], e['who'])].append(('A' if e['k'] == 'Attack' else 'C%d' % e.get('slot', 0)) + '>' + tgt)
        elif e['k'] not in ('Recall',):
            acts[(e['r'], e['who'])].append(e['k'][:5] + ('%d' % e.get('gems', 0) if 'gems' in e else ''))
r0, r1 = int(sys.argv[2]), int(sys.argv[3]); st = int(sys.argv[4]) if len(sys.argv) > 4 else 1
print(k[:8], S[k]['map'], S[k]['opp'], 'we are side', 'A' if o == 0 else 'B', '| big clusters:', {g: (round(sum(camps[i]['x'] for i in mem[g]) / len(mem[g])), round(sum(camps[i]['y'] for i in mem[g]) / len(mem[g]))) for g in big})
for r in range(r0, r1 + 1, st):
    s = R.get(r)
    if not s: continue
    hpg = {g: sum(max(0, s['campHp'][i]) for i in mem[g]) for g in big}
    us = ' '.join('%s(%d,%d)%d%s' % (typ[c[0]], c[3], c[4], c[5], '[' + ','.join(acts[(r, c[0])]) + ']' if acts[(r, c[0])] else '') for c in s['ch'] if c[1] == o and c[7])
    th = ' '.join('%s(%d,%d)%d%s' % (typ[c[0]], c[3], c[4], c[5], '[' + ','.join(acts[(r, c[0])]) + ']' if acts[(r, c[0])] else '') for c in s['ch'] if c[1] != o and c[7])
    print('r%d big-hp %s\n   US: %s\n   IC: %s' % (r, hpg, us, th))
