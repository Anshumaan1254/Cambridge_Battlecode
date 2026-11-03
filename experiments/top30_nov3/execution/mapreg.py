#!/usr/bin/env python3
"""Map features vs our ranked win rate (all our ranked games in ladder_nov2/matches_me.jsonl, Oct 30 - Nov 3, 86-map pool) and vs the
top-30 teams' per-map win rate (lists/<team>.jsonl, each team's last 400 ranked games, deviation from the team's own average).
    nice -n 19 python3 -I execution/mapreg.py > execution/out/mapreg.txt     (also out/map_features.json, out/map_table.tsv)
Features per map: area, passable, spawn_dist (walk), narrow_frac, bush_frac, altars, champs, sym, groups, gems, gold, monoliths,
golems, wolves, elks, islands (passable components not reachable from spawn A), island_frac, mid_gem_share (group gems with centre in
the middle band dA/(dA+dB) in [0.42,0.58]), own_gem_share, near_gems (gems of groups within 15 walking tiles of spawn A), big_share
(largest group's gems / total), gems_per_champ, opp rating (top-100 ladder rating, else the median unlisted = 1850 assumed).
Model: logistic regression (Newton, ridge 1e-3) on standardised features, win = 1.  Also univariate split by feature tercile."""
import json, os, sys, glob
from collections import Counter, defaultdict, deque
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h30  # noqa: E402
sys.path.insert(0, f'{h30.L2}/agent_fights')
import extract as X  # noqa: E402

MAPS = sorted(f[:-7] for f in os.listdir(f'{h30.ROOT}/maps/s4') if f.endswith('.map26a'))
TYPES = ['wolf', 'elk', 'gem', 'gold', 'monolith', 'golem']


def components(rows, w, h):
    seen = [[False] * w for _ in range(h)]
    comps = []
    for y in range(h):
        for x in range(w):
            if seen[y][x] or rows[y][x] in '#oA':
                continue
            dq = deque([(x, y)])
            seen[y][x] = True
            n = 0
            while dq:
                cx, cy = dq.popleft()
                n += 1
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and rows[ny][nx] not in '#oA':
                            seen[ny][nx] = True
                            dq.append((nx, ny))
            comps.append(n)
    return sorted(comps, reverse=True)


def features(m):
    mj = h30.mapjson(m)
    mf, dA, dB = X.map_features(mj)
    W, H, rows = mj['width'], mj['height'], mj['rows']
    half = h30.mapgroups.HALF.get(m)
    f = dict(mf)
    f['sym'] = mj['sym']
    comps = components(rows, W, H)
    reach = sum(1 for y in range(H) for x in range(W) if dA[y][x] >= 0)
    f['islands'] = len(comps) - 1
    f['island_frac'] = round(1 - reach / max(1, mf['passable']), 3)
    if half is None:
        return f
    # full groups from the half table: mirror
    gems = gold = 0
    mono = golem = wolf = elk = 0
    mid = own = near = 0
    big = 0
    ng = 0
    for g in half['groups']:
        x0, y0 = g['camps'][0][1], g['camps'][0][2]
        mx, my = h30.mapgroups.mirror(x0, y0, W, H, mj['sym'])
        touch = max(abs(mx - x0), abs(my - y0)) <= 1
        mult = 1 if touch else 2
        ng += mult
        gg, go = g['raw'][0], g['raw'][1]
        gems += gg * mult
        gold += go * mult
        big = max(big, gg)
        for t, x, y in g['camps']:
            if t == 4:
                mono += mult
            elif t == 5:
                golem += mult
            elif t == 0:
                wolf += mult
            elif t == 1:
                elk += mult
        # band of this group's first camp (and its mirror)
        for (x, y) in ((x0, y0), (mx, my)) if not touch else ((x0, y0),):
            a = dA[y][x] if dA[y][x] >= 0 else None
            b = dB[y][x] if dB[y][x] >= 0 else None
            if a is None or b is None:
                # not reachable from a spawn: use the nearest reachable neighbour
                for rad in range(1, 6):
                    cand = [(dA[yy][xx], dB[yy][xx]) for yy in range(max(0, y - rad), min(H, y + rad + 1)) for xx in range(max(0, x - rad), min(W, x + rad + 1)) if dA[yy][xx] >= 0 and dB[yy][xx] >= 0]
                    if cand:
                        a, b = min(cand)
                        break
            if a is None or b is None:
                continue
            fr = a / max(1, a + b)
            share = gg * (1 if touch else 1)
            if 0.42 <= fr <= 0.58:
                mid += share
            elif fr < 0.42:
                own += share
            if a <= 15:
                near += share
    f.update({'groups': ng, 'gems': gems, 'gold': gold, 'monoliths': mono, 'golems': golem, 'wolves': wolf, 'elks': elk,
              'mid_gem_share': round(mid / max(1, gems), 3), 'own_gem_share': round(own / max(1, gems), 3), 'near_gems': near,
              'big_share': round(big / max(1, gems), 3), 'gems_per_champ': round(gems / max(1, mf['champs'] or 1), 1)})
    return f


def logit(Xm, y, ridge=1e-3, it=30):
    n, k = Xm.shape
    w = np.zeros(k)
    for _ in range(it):
        p = 1 / (1 + np.exp(-Xm @ w))
        grad = Xm.T @ (y - p) - ridge * w
        Wd = p * (1 - p)
        Hs = (Xm * Wd[:, None]).T @ Xm + ridge * np.eye(k)
        step = np.linalg.solve(Hs, grad)
        w += step
        if np.abs(step).max() < 1e-8:
            break
    p = 1 / (1 + np.exp(-Xm @ w))
    Wd = p * (1 - p)
    Hs = (Xm * Wd[:, None]).T @ Xm + ridge * np.eye(k)
    se = np.sqrt(np.diag(np.linalg.inv(Hs)))
    ll = np.sum(y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12))
    return w, se, ll


def main():
    # ensure half groups for every map (one replay per map from either replay folder)
    need = {}
    for m in MAPS:
        if m in h30.mapgroups.HALF:
            continue
        c = glob.glob(f'{h30.T30}/replays/{m}_*.repl26a')
        if c:
            need[m] = c[0]
    h30.ensure_groups(need)
    feats = {m: features(m) for m in MAPS}
    json.dump(feats, open(f'{h30.EXE}/out/map_features.json', 'w'), indent=1)
    missing = [m for m in MAPS if 'groups' not in feats[m]]
    if missing:
        print('no group table for', missing)
    # ---- our ranked games
    rows = [json.loads(l) for l in open(f'{h30.L2}/matches_me.jsonl')]
    games = []
    for m in rows:
        if m['kind'] != 'ranked' or m['status'] != 'finished' or m['createdAt'] < '2026-10-27' or m['map'] not in feats:
            continue
        us = [t for t in m['teams'] if t['teamId'] == h30.ME][0]
        th = [t for t in m['teams'] if t['teamId'] != h30.ME][0]
        games.append({'map': m['map'], 'win': 1 if us['result'] == 'win' else 0, 'opp': th['teamId'], 'opp_name': th['name'],
                      'created': m['createdAt'], 'opp_rating': h30.RATING.get(th['teamId']), 'opp_top30': th['teamId'] in h30.STRONG})
    print(f'OUR RANKED GAMES since Oct 27 (matches_me.jsonl): n={len(games)}, {min(g["created"] for g in games)[:16]} .. {max(g["created"] for g in games)[:16]}, win rate {np.mean([g["win"] for g in games]):.3f}')
    print(f'  opponents on the top-100 ladder: {sum(1 for g in games if g["opp_rating"] is not None)} games (win rate {np.mean([g["win"] for g in games if g["opp_rating"] is not None]):.3f});'
          f' vs top-30 {sum(1 for g in games if g["opp_top30"])} games (win rate {np.mean([g["win"] for g in games if g["opp_top30"]] or [0]):.3f});'
          f' unlisted opponents win rate {np.mean([g["win"] for g in games if g["opp_rating"] is None]):.3f}')
    # ---- top-30 teams' per-map deviation
    tw = defaultdict(lambda: [0, 0])      # map -> [wins, games] over the top-30 teams
    tdev = defaultdict(list)             # map -> list of (team deviation weighted)
    team_avg = {}
    per_team_map = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for f in glob.glob(f'{h30.T30}/lists/*.jsonl'):
        tid8 = os.path.basename(f)[:-6]
        ms = [json.loads(l) for l in open(f)]
        tid = next((t['teamId'] for m in ms for t in m['teams'] if t['teamId'].startswith(tid8)), None)
        if tid is None:
            continue
        wins = n = 0
        for m in ms:
            if m.get('kind') != 'ranked' or m.get('status') != 'finished' or m['map'] not in feats:
                continue
            me = [t for t in m['teams'] if t['teamId'] == tid]
            if not me:
                continue
            w = 1 if me[0]['result'] == 'win' else 0
            wins += w
            n += 1
            per_team_map[tid][m['map']][0] += w
            per_team_map[tid][m['map']][1] += 1
        team_avg[tid] = wins / max(1, n)
    for tid, mm in per_team_map.items():
        for m, (w, n) in mm.items():
            tw[m][0] += w
            tw[m][1] += n
            tdev[m].append((w - n * team_avg[tid], n))
    top_dev = {m: sum(a for a, n in v) / max(1, sum(n for a, n in v)) for m, v in tdev.items()}
    top_n = {m: sum(n for a, n in v) for m, v in tdev.items()}
    # ---- per map table
    pm = defaultdict(lambda: [0, 0])
    for g in games:
        pm[g['map']][0] += g['win']
        pm[g['map']][1] += 1
    overall = np.mean([g['win'] for g in games])
    tab = []
    for m in MAPS:
        w, n = pm[m]
        f = feats[m]
        tab.append({'map': m, 'n': n, 'wr': w / max(1, n), 'dev': w / max(1, n) - overall, 'top_dev': top_dev.get(m, 0), 'top_n': top_n.get(m, 0),
                    **{k: f.get(k) for k in ('area', 'passable', 'spawn_dist', 'altars', 'champs', 'groups', 'gems', 'gold', 'monoliths', 'golems', 'islands', 'island_frac', 'mid_gem_share', 'own_gem_share', 'near_gems', 'big_share', 'narrow_frac', 'bush_frac', 'sym')}})
    with open(f'{h30.EXE}/out/map_table.tsv', 'w') as fo:
        keys = list(tab[0].keys())
        fo.write('\t'.join(keys) + '\n')
        for t in sorted(tab, key=lambda t: t['wr']):
            fo.write('\t'.join(str(t[k]) if not isinstance(t[k], float) else f'{t[k]:.3f}' for k in keys) + '\n')
    print(f'\nPER-MAP WIN RATE (ours, n games) vs the top-30 teams\' deviation from their own average on that map (top_dev, n team-games).  Our overall {overall:.3f}')
    print('  lowest 20 maps for us:')
    print(f"  {'map':24} {'n':>3} {'wr':>5} {'dev':>6} {'top_dev':>7} {'top_n':>5} {'area':>5} {'pass':>5} {'s2s':>4} {'alt':>3} {'ch':>2} {'grp':>3} {'gems':>5} {'gold':>5} {'mono':>4} {'gol':>3} {'isl':>3} {'islf':>5} {'mid':>5} {'own':>5} {'near':>4} {'big':>5}")
    for t in sorted(tab, key=lambda t: t['wr'])[:20]:
        print(f"  {t['map']:24} {t['n']:3} {t['wr']:5.2f} {t['dev']:+6.2f} {t['top_dev']:+7.3f} {t['top_n']:5} {t['area']:5} {t['passable']:5} {t['spawn_dist']:4} {t['altars']:3} {t['champs']:2} {t['groups']:3} {t['gems']:5} {t['gold']:5} {t['monoliths']:4} {t['golems']:3} {t['islands']:3} {t['island_frac']:5.2f} {t['mid_gem_share']:5.2f} {t['own_gem_share']:5.2f} {t['near_gems']:4} {t['big_share']:5.2f}")
    print('  highest 10 maps for us:')
    for t in sorted(tab, key=lambda t: -t['wr'])[:10]:
        print(f"  {t['map']:24} {t['n']:3} {t['wr']:5.2f} {t['dev']:+6.2f} {t['top_dev']:+7.3f} {t['top_n']:5} {t['area']:5} {t['passable']:5} {t['spawn_dist']:4} {t['altars']:3} {t['champs']:2} {t['groups']:3} {t['gems']:5} {t['gold']:5} {t['monoliths']:4} {t['golems']:3} {t['islands']:3} {t['island_frac']:5.2f} {t['mid_gem_share']:5.2f} {t['own_gem_share']:5.2f} {t['near_gems']:4} {t['big_share']:5.2f}")
    xs = np.array([t['dev'] for t in tab if t['n'] >= 10])
    ys = np.array([t['top_dev'] for t in tab if t['n'] >= 10])
    print(f'  correlation of our per-map deviation with the top-30 teams\' per-map deviation (maps with n>=10): r = {np.corrcoef(xs, ys)[0, 1]:+.3f} (n maps {len(xs)})')
    # ---- logistic regression per game
    fkeys = ['area', 'spawn_dist', 'altars', 'champs', 'groups', 'gems', 'gold', 'monoliths', 'golems', 'islands', 'island_frac', 'mid_gem_share', 'own_gem_share', 'near_gems', 'big_share', 'narrow_frac', 'bush_frac']
    Xr = []
    y = []
    for g in games:
        f = feats[g['map']]
        if 'groups' not in f:
            continue
        opp = g['opp_rating'] if g['opp_rating'] is not None else 1850
        Xr.append([f[k] for k in fkeys] + [opp, 1 if g['opp_rating'] is None else 0])
        y.append(g['win'])
    Xr = np.array(Xr, dtype=float)
    y = np.array(y, dtype=float)
    names = fkeys + ['opp_rating', 'opp_unlisted']
    mu, sd = Xr.mean(0), Xr.std(0) + 1e-9
    Z = (Xr - mu) / sd
    Z = np.hstack([np.ones((len(Z), 1)), Z])
    w, se, ll = logit(Z, y)
    w0, se0, ll0 = logit(np.ones((len(y), 1)), y)
    print(f'\nLOGISTIC REGRESSION of win (n={len(y)}) on standardised map features + opponent rating; coefficient = log-odds change per 1 sd; ll {ll:.1f} vs null {ll0:.1f}')
    print(f"  {'feature':16} {'coef':>7} {'se':>6} {'z':>6}   {'mean':>8} {'sd':>8}")
    for i, nm in enumerate(['intercept'] + names):
        m_ = mu[i - 1] if i else 0
        s_ = sd[i - 1] if i else 0
        print(f'  {nm:16} {w[i]:+7.3f} {se[i]:6.3f} {w[i] / se[i]:+6.2f}   {m_:8.2f} {s_:8.2f}')
    # map-only model (no opponent)
    Z2 = Z[:, :len(fkeys) + 1]
    w2, se2, ll2 = logit(Z2, y)
    print(f'  map-features-only model ll {ll2:.1f}; |z|>=2: ' + ', '.join(f'{names[i - 1]} {w2[i]:+.3f} (z {w2[i] / se2[i]:+.1f})' for i in range(1, len(w2)) if abs(w2[i] / se2[i]) >= 2))
    # univariate terciles
    print('\n  UNIVARIATE: win rate by feature tercile (low / mid / high), games')
    for i, k in enumerate(fkeys):
        col = Xr[:, i]
        qs = np.quantile(col, [1 / 3, 2 / 3])
        lo = y[col <= qs[0]]
        mi = y[(col > qs[0]) & (col <= qs[1])]
        hi = y[col > qs[1]]
        print(f'  {k:16} <= {qs[0]:7.2f}: {lo.mean() if len(lo) else 0:.3f} (n {len(lo):4})   mid: {mi.mean() if len(mi) else 0:.3f} (n {len(mi):4})   > {qs[1]:7.2f}: {hi.mean() if len(hi) else 0:.3f} (n {len(hi):4})')
    # top-30 deviation regressed on the same features (per map, weighted by n)
    tm = [t for t in tab if t['top_n'] >= 20 and 'groups' in feats[t['map']]]
    Xt = np.array([[feats[t['map']][k] for k in fkeys] for t in tm], dtype=float)
    yt = np.array([t['top_dev'] for t in tm])
    wt = np.array([t['top_n'] for t in tm], dtype=float)
    Zt = (Xt - Xt.mean(0)) / (Xt.std(0) + 1e-9)
    Zt = np.hstack([np.ones((len(Zt), 1)), Zt])
    Wm = np.sqrt(wt)[:, None]
    beta, *_ = np.linalg.lstsq(Zt * Wm, yt * Wm[:, 0], rcond=None)
    print(f'\n  TOP-30 per-map deviation (weighted least squares on the same standardised features, {len(tm)} maps): ' + ', '.join(f'{k} {beta[i + 1]:+.3f}' for i, k in enumerate(fkeys)))
    # ours per map deviation on the same features (map-level, weighted)
    om = [t for t in tab if t['n'] >= 10 and 'groups' in feats[t['map']]]
    Xo = np.array([[feats[t['map']][k] for k in fkeys] for t in om], dtype=float)
    yo = np.array([t['dev'] for t in om])
    wo = np.array([t['n'] for t in om], dtype=float)
    Zo = (Xo - Xo.mean(0)) / (Xo.std(0) + 1e-9)
    Zo = np.hstack([np.ones((len(Zo), 1)), Zo])
    Wo = np.sqrt(wo)[:, None]
    bo, *_ = np.linalg.lstsq(Zo * Wo, yo * Wo[:, 0], rcond=None)
    print(f'  OUR per-map deviation (same, {len(om)} maps): ' + ', '.join(f'{k} {bo[i + 1]:+.3f}' for i, k in enumerate(fkeys)))


if __name__ == '__main__':
    main()
