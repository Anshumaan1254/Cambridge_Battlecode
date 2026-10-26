"""ASCII snapshots of one game: python -I ascii.py MATCHID R1 R2 ... ; uppercase = our team (A..), lowercase = theirs, # = camp tile alive (hp>0), . = camp dead"""
import gzip, json, sys, os
sides = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sides_all.json')))
mid = sys.argv[1]; key = [k for k in sides if k.startswith(mid)][0]; o = sides[key]['ours']
d = json.load(gzip.open('dec/%s.json.gz' % key)); W, H = d['meta']['width'], d['meta']['height']
R = {s['r']: s for s in d['rounds']}
print(key, sides[key]['map'], sides[key]['opp'], sides[key]['res'], 'ours', o, W, H, d['meta']['drafts'])
for r in map(int, sys.argv[2:]):
    s = R[r]; g = [['.'] * W for _ in range(H)]
    for i, c in enumerate(d['meta']['camps']):
        g[c['y']][c['x']] = '#' if s['campHp'][i] > 0 else ','
    for c in s['ch']:
        if not c[7]: continue
        ch = chr(ord('A') + c[0] % 26) if c[1] == o else chr(ord('a') + c[0] % 26)
        g[c[4]][c[3]] = ch
    print('--- r', r, 'sub', s['sub'], ' (us=%s)' % ('A' if o == 0 else 'B'))
    for y in range(H): print(''.join(g[y]))
    print([(('U' if c[1] == o else 'T') + d['meta']['bodies'][c[0]]['type'][:4], c[5], c[8]) for c in s['ch'] if c[7]])
