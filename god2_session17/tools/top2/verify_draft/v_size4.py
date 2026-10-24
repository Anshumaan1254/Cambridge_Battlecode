"""v_size4.py (verify_draft): size-4 excess wins (vs per-size rating fit) by HoR presence and by team; pbg H2H by size.
Usage: python v_size4.py [--dedup]"""
import sys, collections, math, numpy as np
sys.path.insert(0, 'C:/battlecode/Cambridge_Battlecode/tools/top2/verify_draft')
from vcommon import *
from vlogit import *
args = sys.argv[1:]
M = load_matches(); R, NM, RK = ratings()
rows = [(m,) + side_teams(m) for m in M.values()]
rows = [(m, a, b) for m, a, b in rows if a['teamId'] in R and b['teamId'] in R]
for s in (3, 4, 5):
    rs = [r for r in rows if len(picks(r[1])) == s]
    y = np.array([1.0 if a['result'] == 'win' else 0.0 for m, a, b in rs]); dr = np.array([(R[a['teamId']] - R[b['teamId']]) / 100 for m, a, b in rs])
    w, se, _ = fit(np.column_stack([np.ones(len(y)), dr]), y)
    grp = collections.defaultdict(lambda: [0.0, 0.0, 0]); team = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for i, (m, a, b) in enumerate(rs):
        pa = 1 / (1 + math.exp(-(w[0] + w[1] * dr[i])))
        for t, pw, yy in ((a, pa, y[i]), (b, 1 - pa, 1 - y[i])):
            hasH = 11 in picks(t); hasV = 1 in picks(t)
            for gk in (('HoR' if hasH else 'noHoR'), ('Ve' if hasV else 'noVe')):
                g = grp[gk]; g[0] += yy - pw; g[1] += pw * (1 - pw); g[2] += 1
            tk = t['name'] + (' [HoR]' if hasH else ' [noHoR]')
            e = team[tk]; e[0] += yy - pw; e[1] += pw * (1 - pw); e[2] += 1
    print(f'size {s}: k {w[1]:.2f}; ' + '; '.join(f'{k}: n {g[2]} excess {g[0]:+.1f} z {g[0]/math.sqrt(g[1]):+.1f} per-100-games {100*g[0]/g[2]:+.1f}' for k, g in sorted(grp.items())))
    if s == 4:
        for nm in ('prism best girl', 'Pantheon', 'Intercontinental Fish', 'policy wonk', ':3', 'procless', 'OneTap', 'KratosMessi', 'Trzy Kwaterki', 'Nyx'):
            for tk, e in team.items():
                if tk.startswith(nm + ' ['): print(f'    {tk:32s} n {e[2]:4d} excess {e[0]:+5.1f} z {e[0]/math.sqrt(e[1]):+.1f}')
    if s in (3, 5):
        for nm in ('prism best girl', 'Pantheon', 'Intercontinental Fish'):
            for tk, e in team.items():
                if tk.startswith(nm + ' ['): print(f'    {tk:32s} n {e[2]:4d} excess {e[0]:+5.1f} z {e[0]/math.sqrt(e[1]):+.1f}')
