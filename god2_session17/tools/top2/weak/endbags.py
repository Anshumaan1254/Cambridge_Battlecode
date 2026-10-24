"""Unbanked gems at the end of each game (an_weak): per study game, the study team's and the opponent's carried gems at the final round
   (sum and the biggest bag + its carrier), and whether the loser's carried gems would have covered the margin.
   python tools/top2/weak/endbags.py KEY..."""
import json, gzip, sys, collections
G = [json.loads(l) for l in open('C:/battlecode/cache/an_weak/wx.jsonl', encoding='utf-8')]
for key in sys.argv[1:]:
    A = [g for g in G if g['key'] == key]
    rows = []
    for g in A:
        d = json.loads(gzip.open(f"C:/battlecode/cache/t2dump/{key}/{g['file']}").read())
        team = {b['index']: b['team'] for b in d['meta']['bodies']}; ty = {b['index']: b['type'] for b in d['meta']['bodies']}
        last = d['R'][-1][3]
        S = g['S']
        car = [sum(c[6] for c in last if team[c[0]] == t) for t in (S, 1 - S)]
        big = max(((c[6], ty[c[0]]) for c in last if team[c[0]] == S), default=(0, '-'))
        # peak bag of the study team during the game and its time
        peak = (0, '-', 0)
        for e in d['R']:
            for c in e[3]:
                if team[c[0]] == S and c[6] > peak[0]: peak = (c[6], ty[c[0]], e[0])
        rows.append((g, car, big, peak))
    for lab, sel in [('wins', 1), ('losses', 0)]:
        R = [r for r in rows if r[0]['win'] == sel]
        n = len(R)
        print(f'{key} {lab} n={n}: carried at end S {sum(r[1][0] for r in R)/n:.0f} O {sum(r[1][1] for r in R)/n:.0f}; S biggest end bag >= 200 in {sum(1 for r in R if r[2][0] >= 200)} games; peak bag mean {sum(r[3][0] for r in R)/n:.0f}, peak >= 300 in {sum(1 for r in R if r[3][0] >= 300)}')
        if not sel:
            cover = [r for r in R if r[0]['sub'][0] + r[1][0] > r[0]['sub'][1]]
            print(f'   losses where S sub + S carried > O sub: {len(cover)} of {n}')
            for r in sorted(R, key=lambda r: -r[1][0])[:12]:
                g = r[0]
                print(f'     {g["file"]} vs {g["opp"]}: {g["sub"][0]}-{g["sub"][1]} r{g["final"]} carried S {r[1][0]} (biggest {r[2][1]} {r[2][0]}) O {r[1][1]}; peak {r[3][1]} {r[3][0]} at r{r[3][2]}')
    c = collections.Counter(r[3][1] for r in rows if r[3][0] >= 200)
    print('   peak-bag carrier (peak >= 200):', dict(c))
