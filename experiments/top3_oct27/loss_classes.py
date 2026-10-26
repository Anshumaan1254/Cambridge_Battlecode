"""Our ranked games (v18 / v20, /tmp/claude-0/rk2): build an index, then per game: deaths (opening r<120 / mid / late), kills, captures,
first capture, bag lost, banked; classify each loss: 'opening wipe' (>= 3 of our deaths before r120), 'outfought' (deaths >= kills + 4),
'outfarmed' (captured gems < 70% of theirs, deaths within 3 of kills), 'bag lost' (bag lost >= 150), 'close' (final margin < 150).
    python3 -I loss_classes.py"""
import collections, glob, gzip, json, os
US = '5a103c90-b00b-4d46-8ace-6a3bb058dc72'
L = json.load(open('/tmp/claude-0/rk2/list.json'))
by = {f"{m['_tag']}_{m['map']}_{m['matchId'][:8]}": m for m in L}
idx = {}
for p in glob.glob('/tmp/claude-0/rk2/dec/*.json.gz'):
    b = os.path.basename(p)[:-8]
    m = by.get(b)
    if not m:
        continue
    T = {t['side']: t for t in m['teams']}
    ours = 0 if T['a']['teamId'] == US else 1
    opp = T['b' if ours == 0 else 'a']['name']
    idx[p] = {'ours': ours, 'res': [T['a']['result'], T['b']['result']], 'map': m['map'], 'set': m['_tag'][:3], 'opp': opp}
json.dump(idx, open('/tmp/claude-0/rk2/index.json', 'w'))
C = collections.defaultdict(collections.Counter); rows = []
for p, v in idx.items():
    d = json.load(gzip.open(p)); o = v['ours']
    team = {b['index']: b['team'] for b in d['meta']['bodies']}
    s = collections.Counter()
    for e in d['events']:
        t = e.get('team', team.get(e.get('who')))
        if t is None: continue
        w = 'u' if t == o else 't'
        if e['k'] == 'Death':
            s[w + 'death'] += 1; s[w + 'bag'] += e.get('bag', 0)
            if e['r'] < 120: s[w + 'd_open'] += 1
        elif e['k'] == 'CaptureGems':
            s[w + 'cap'] += e['gems']
            if w + 'first' not in s: s[w + 'first'] = e['r']
    sub = d['meta']['submitted']; s['margin'] = sub[o] - sub[1 - o]
    win = v['res'][o] == 'win'
    cls = []
    if not win:
        if s['ud_open'] >= 3: cls.append('opening_wipe')
        if s['udeath'] >= s['tdeath'] + 4: cls.append('outfought')
        if s['ucap'] < 0.7 * max(1, s['tcap']) and abs(s['udeath'] - s['tdeath']) <= 3: cls.append('outfarmed')
        if s['ubag'] >= 150: cls.append('bag_lost')
        if abs(s['margin']) < 150: cls.append('close')
        if not cls: cls.append('other')
    key = (v['set'], 'W' if win else 'L')
    C[key]['n'] += 1
    for k, x in s.items(): C[key][k] += x
    for c in cls: C[key]['cls_' + c] += 1
    rows.append((v['set'], win, v['map'], v['opp'], s['margin'], cls, dict(s)))
for key in sorted(C):
    c = C[key]; n = c['n']
    print(key, n, ' '.join(f"{k}={c[k] / n:.1f}" for k in ('udeath', 'tdeath', 'ud_open', 'td_open', 'ucap', 'tcap', 'ufirst', 'tfirst', 'ubag', 'tbag', 'margin')))
    print('    classes:', {k[4:]: c[k] for k in c if k.startswith('cls_')})
json.dump(rows, open('/tmp/claude-0/rk2/rows.json', 'w'))
