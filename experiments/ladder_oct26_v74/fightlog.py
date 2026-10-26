"""Print the rounds before a death: every body within 9 tiles of the victim with hp, position and action. python -I fightlog.py MATCHID_PREFIX DEATH_INDEX [ROUNDS_BEFORE]"""
import gzip, json, sys
S = json.load(open('sides_all.json')); k = [x for x in S if x.startswith(sys.argv[1])][0]; o = S[k]['ours']
d = json.load(gzip.open('dec/%s.json.gz' % k)); typ = {b['index']: b['type'] for b in d['meta']['bodies']}
R = {s['r']: {c[0]: c for c in s['ch']} for s in d['rounds']}; cpos = {(c['x'], c['y']) for c in d['meta']['camps']}
deaths = [e for e in d['events'] if e['k'] == 'Death' and e['team'] == o]
i = int(sys.argv[2]); e = deaths[i]; nb = int(sys.argv[3]) if len(sys.argv) > 3 else 8
print(k[:8], S[k]['map'], S[k]['opp'], 'death', i, 'of', len(deaths), '->', typ[e['who']], 'at round', e['r'], e['at'], 'killed by', typ.get(e['by'], e['by']))
cheb = lambda a, b: max(abs(a[0]-b[0]), abs(a[1]-b[1]))
acts = {}
for ev in d['events']:
    if 'who' in ev and e['r'] - nb <= ev['r'] <= e['r'] and ev['k'] in ('Move', 'Attack', 'Cast ability', 'Recall', 'Shop', 'Place ward'):
        acts.setdefault((ev['r'], ev['who']), []).append(ev)
for r in range(e['r'] - nb, e['r'] + 1):
    if r not in R: continue
    v = R[r].get(e['who']); center = (v[3], v[4]) if v else tuple(e['at'])
    row = []
    for w, c in sorted(R[r].items()):
        if not c[7] or cheb((c[3], c[4]), center) > 9: continue
        a = ''.join(('M' if x['k'] == 'Move' else 'A>' + ('camp' if tuple(x['to']) in cpos else typ.get(next((q[0] for q in R[r].values() if (q[3], q[4]) == tuple(x['to'])), None), '?')[:4]) if x['k'] == 'Attack' else 'C%d>%s' % (x.get('slot', 0), 'camp' if tuple(x['to']) in cpos else '?') if x['k'] == 'Cast ability' else x['k'][:3]) + ' ' for x in acts.get((r, w), []) if x['k'] != 'Recall' and x['k'] != 'Place ward')
        row.append('%s%s(%d,%d) hp%d %s' % ('U' if c[1] == o else 't', typ[w][:4], c[3], c[4], c[5], a.strip()))
    print('r%d: ' % r + ' | '.join(row))
