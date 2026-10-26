"""Real recalls (the body lands on its spawn 3-6 rounds after a Recall, from more than 6 tiles away), with health share, bag and
gold at the start, and the reason guess (bag >= 20: bank, gold >= 150: shop, hp < 50%: heal, else 'none').
    python3 -I recalls.py INDEX set..."""
import collections, gzip, json, sys
idx = json.load(open(sys.argv[1])); want = set(sys.argv[2:])
C = collections.Counter(); H = collections.defaultdict(list); n = collections.Counter()
for p, v in idx.items():
    if v['set'] not in want: continue
    d = json.load(gzip.open(p)); o = v['ours']
    team = {b['index']: b['team'] for b in d['meta']['bodies']}
    R = {r['r']: {c[0]: c for c in r['ch']} for r in d['rounds']}
    # spawn = position at round 2
    r2 = min(R); sp = {b: (c[3], c[4]) for b, c in R[r2].items()}
    n[v['set']] += 1
    last = {}
    deaths = collections.defaultdict(list)
    for e in d['events']:
        if e['k'] == 'Death': deaths[e['who']].append(e['r'])
    for e in d['events']:
        if e['k'] != 'Recall' or e.get('who') not in team: continue
        b, r = e['who'], e['r']
        if last.get(b, -99) >= r - 6: continue
        c = R.get(r, {}).get(b)
        if not c or not c[7]: continue
        far = max(abs(c[3] - sp[b][0]), abs(c[4] - sp[b][1]))
        if far <= 6: continue
        landed = any((R.get(rr, {}).get(b) or [0] * 12)[7] and max(abs(R[rr][b][3] - sp[b][0]), abs(R[rr][b][4] - sp[b][1])) <= 2 for rr in range(r + 3, r + 7) if rr in R)
        if not landed or any(r - 1 <= x <= r + 7 for x in deaths[b]): continue
        last[b] = r
        w = 'us' if team[b] == o else 'them'
        hp = c[5] / max(1, c[6]); bag = c[8]; gold = c[9]
        why = 'bank' if bag >= 20 else 'shop' if gold >= 150 else 'heal' if hp < 0.5 else 'none'
        C[(v['set'], w, why)] += 1; H[(v['set'], w)].append(hp)
for s in sorted(want):
    for w in ('us', 'them'):
        h = H[(s, w)]
        print(s, w, f"real recalls/game {len(h) / n[s]:.1f}  mean hp {sum(h) / max(1, len(h)):.2f}  hp>=80% {sum(x >= 0.8 for x in h) / n[s]:.1f}/game", {k[2]: round(x / n[s], 1) for k, x in C.items() if k[:2] == (s, w)})
