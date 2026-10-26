"""Trace one team's bodies in one game: positions, the group each is hitting, bag, captures and key events.
    python3 -I trace.py INDEX SET MAP {us|ic} [r_from r_to step]"""
import sys, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icx
idx, sset, mp, who = sys.argv[1:5]
r0, r1, stp = (int(x) for x in sys.argv[5:8]) if len(sys.argv) > 7 else (1, 130, 3)
for g in icx.games(idx, {sset}):
    if g.map != mp:
        continue
    T = g.ours if who == 'us' else g.ic
    tg = g.D['tile_group']
    hit = collections.defaultdict(dict); cap = {}
    for e in g.ev:
        if e['k'] in ('Attack', 'Cast ability') and 'who' in e and e.get('to'):
            if tuple(e['to']) in tg:
                hit[e['r']][e['who']] = 'G' + str(tg[tuple(e['to'])])
            else:
                hit[e['r']].setdefault(e['who'], 'X')
        if e['k'] == 'CaptureGems':
            cap[(e['r'], e['who'])] = (tg.get(tuple(e['at'])), e['gems'])
        if e['k'] in ('Submit gems', 'Shop', 'Death', 'Place altar lock', 'Teleport channel') and 'who' in e and g.team[e['who']] == T and r0 <= e['r'] <= r1:
            print('   ev', e['r'], e['k'], g.name[e['who']], e.get('to') or e.get('at'), e.get('bag', ''))
    print('team', T, 'spawn', g.D['spawn'][T], 'enemy spawn', g.D['spawn'][1 - T], 'result', g.res)
    for r in range(r0, r1 + 1, stp):
        s = g.R.get(r)
        if not s:
            continue
        row = []
        for c in s['ch']:
            if c[1] != T:
                continue
            h = next((hit[rr][c[0]] for rr in range(r, r + stp) if c[0] in hit[rr]), '')
            row.append(f"{g.name[c[0]][:4]}({c[3]:2d},{c[4]:2d}){'D' if not c[7] else ' '}{c[5]:4d} g{c[8]:<3d}{('>' + h) if h else '':5s}")
        caps = [(rr, g.name[w][:4], v) for (rr, w), v in cap.items() if r <= rr < r + stp and g.team[w] == T]
        print(f"r{r:3d} " + ' '.join(row), caps if caps else '')
    break
