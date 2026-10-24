# Aggregate tools/live/strat_extract.mjs output (an_strategy): per-map results and gem curves for us vs the top 10, fight vs farm
# maps, gems by zone, top-vs-top winner/loser differences (cohesion, objectives, invasion), stuck metrics and worst episodes.
#   python tools/live/strat_agg.py OUTDIR EXT.jsonl [EXT2.jsonl ...]   -> OUTDIR/agg.txt (+ agg.json with the tables)
import json, os, sys, statistics as st, collections, math

OUT = sys.argv[1]
EXT = sys.argv[2:]
ROOT = 'C:/battlecode/Cambridge_Battlecode/experiments/live/lists/'
CACHE = 'C:/battlecode/cache/'
US = 'HouseOfCoders'
CP = [50, 100, 150, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1200, 1400, 1600, 1800, 2000]
ci = {r: i for i, r in enumerate(CP)}


def load(p):
    return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]


meta = {}
for p in (ROOT + 'groups_matches.jsonl', ROOT + 'top10_oct23/ours_bb4_ft52.jsonl', ROOT + 'top10_oct23/top_vs_top.jsonl'):
    for m in load(p):
        meta[m['matchId'][:8]] = m
src = {}
for d, tag in (('rp_bb4D', 'bb4D'), ('rp_ft52D', 'ft52D'), ('rp_top', 'top')):
    for f in os.listdir(CACHE + d):
        src[f] = tag
geo = {g['map']: g for g in load(CACHE + 'an_strategy/mapgeo2.jsonl')}
games = {}
for p in EXT:
    for g in load(p):
        if 'err' in g or g['file'] not in src:
            continue
        games[g['file']] = g
ours, tops = [], []
for f, g in games.items():
    m = meta.get(f.split('_')[-1][:8])
    if not m:
        continue
    names = {0 if t['side'] == 'a' else 1: t['name'] for t in m['teams']}
    g['names'] = names
    g['src'] = src[f]
    win = 0 if g['outcome'] == 1 else 1
    g['win'] = win
    if src[f] == 'top':
        tops.append(g)
    else:
        us = [k for k, v in names.items() if v == US]
        if not us:
            continue
        g['us'] = us[0]
        g['opp'] = names[1 - us[0]]
        ours.append(g)

L = []


def P(*a):
    L.append(' '.join(str(x) for x in a))


def med(v):
    v = [x for x in v if x is not None]
    return round(st.median(v), 1) if v else None


def mean(v, k=2):
    v = [x for x in v if x is not None]
    return round(sum(v) / len(v), k) if v else None


def sub_at(g, t, r):
    return g['T'][str(t)]['sub'][ci[r]]


def caps_of(g, t, zone=None, cls=None, rmax=None):
    return [c for c in g['caps'] if c['t'] == t and (zone is None or c['zone'] == zone) and (cls is None or c['cls'] == cls) and (rmax is None or c['r'] < rmax)]


def gems(cs):
    return sum(c['gems'] for c in cs)


def T(g, t):
    return g['T'][str(t)]


P(f'# an_strategy aggregate: {len(ours)} of our games vs top 10 (bb4D {sum(g["src"]=="bb4D" for g in ours)}, ft52D {sum(g["src"]=="ft52D" for g in ours)}), {len(tops)} top-vs-top games')
P()

# ---------------------------------------------------------------- per-map table (ours) and fight intensity (top-vs-top + ours)
maps = sorted(set(g['map'] for g in ours) | set(g['map'] for g in tops))
rows = {}
for mp in maps:
    O = [g for g in ours if g['map'] == mp]
    Tg = [g for g in tops if g['map'] == mp]
    r = {'map': mp, 'n': len(O), 'w': sum(g['win'] == g['us'] for g in O), 'nt': len(Tg)}
    for R in (200, 400, 600):
        r[f'us{R}'] = med([sub_at(g, g['us'], R) for g in O])
        r[f'th{R}'] = med([sub_at(g, 1 - g['us'], R) for g in O])
        r[f'tw{R}'] = med([sub_at(g, g['win'], R) for g in Tg])
        r[f'tl{R}'] = med([sub_at(g, 1 - g['win'], R) for g in Tg])
    r['fin_us'] = med([g['final'] for g in O])
    r['fin_t'] = med([g['final'] for g in Tg])
    # deaths per 1000 rounds (both teams), contact share r1-400
    r['dk_t'] = mean([(T(g, 0)['deaths'] + T(g, 1)['deaths']) * 1000 / max(1, g['final']) for g in Tg], 1)
    r['dk_us'] = mean([(T(g, 0)['deaths'] + T(g, 1)['deaths']) * 1000 / max(1, g['final']) for g in O], 1)
    r['ct_t'] = mean([(g['fights']['contact']['1-150'] * 149 + (g['fights']['contact']['150-400'] or 0) * 250) / 399 for g in Tg], 3)
    r['ct_us'] = mean([(g['fights']['contact']['1-150'] * 149 + (g['fights']['contact']['150-400'] or 0) * 250) / 399 for g in O], 3)
    r['d_us'] = mean([T(g, g['us'])['deaths'] for g in O], 1)
    r['d_th'] = mean([T(g, 1 - g['us'])['deaths'] for g in O], 1)
    # mid gems share (of all mid gems captured in the game) by us / by the winner in top games
    def midshare(g, t):
        a = gems(caps_of(g, t, 'mid')); b = gems(caps_of(g, 1 - t, 'mid'))
        return a / (a + b) if a + b else None
    r['mid_us'] = mean([midshare(g, g['us']) for g in O])
    r['mid_tw'] = mean([midshare(g, g['win']) for g in Tg])
    # our gems by zone vs theirs (whole game)
    for who, key in (('us', lambda g: g['us']), ('th', lambda g: 1 - g['us'])):
        for z in ('own', 'mid', 'enemy'):
            r[f'{who}_{z}'] = mean([gems(caps_of(g, key(g), z)) for g in O], 0)
    for who, key in (('tw', lambda g: g['win']), ('tl', lambda g: 1 - g['win'])):
        for z in ('own', 'mid', 'enemy'):
            r[f'{who}_{z}'] = mean([gems(caps_of(g, key(g), z)) for g in Tg], 0)
    f = geo[mp]['feat']
    r.update({k: f[k] for k in ('s2s', 'mincut', 'midShare', 'mono', 'monoMid', 'golem', 'heavyMid', 'gemRate', 'groups', 'altarMid', 'hole', 'bush', 'wall')})
    r['area'] = geo[mp]['W'] * geo[mp]['H']
    rows[mp] = r

# fight index: deaths / 1000 rounds in top-vs-top games where available (>= 2 games), else in ours; plus contact
for r in rows.values():
    r['fight'] = r['dk_t'] if r['nt'] >= 2 and r['dk_t'] is not None else r['dk_us']
fvals = sorted(r['fight'] for r in rows.values() if r['fight'] is not None)
q1, q2 = fvals[len(fvals) // 3], fvals[2 * len(fvals) // 3]
for r in rows.values():
    r['type'] = 'fight' if r['fight'] is not None and r['fight'] >= q2 else ('farm' if r['fight'] is not None and r['fight'] < q1 else 'mixed')
P(f'## Fight index terciles (deaths per 1000 rounds, both teams): farm < {q1:.1f} <= mixed < {q2:.1f} <= fight')
P()
P('## Per map (ours: n, W, win%; banked medians us/them at r200/r400/r600; top-vs-top winner/loser at r400; deaths/1000r; contact r1-400; our deaths/theirs; mid-gem share us / top winner; features)')
hdr = 'map | type | n | W | us200 th200 | us400 th400 | us600 th600 | TvT n | tw400 tl400 | fin us/t | dk tvt/us | contact tvt/us | deaths us/th | midsh us/tw | s2s cut midShare monoMid golem heavyMid area'
P(hdr)
for r in sorted(rows.values(), key=lambda r: -(r['fight'] or 0)):
    P(f"{r['map']} | {r['type']} | {r['n']} | {r['w']} ({(100*r['w']/r['n']) if r['n'] else 0:.0f}%) | {r['us200']} {r['th200']} | {r['us400']} {r['th400']} | {r['us600']} {r['th600']} | {r['nt']} | {r['tw400']} {r['tl400']} | {r['fin_us']}/{r['fin_t']} | {r['dk_t']}/{r['dk_us']} | {r['ct_t']}/{r['ct_us']} | {r['d_us']}/{r['d_th']} | {r['mid_us']}/{r['mid_tw']} | {r['s2s']} {r['mincut']} {r['midShare']} {r['monoMid']} {r['golem']} {r['heavyMid']} {r['area']}")
P()

# by type
P('## By map type (our games): win%, games, banked medians, gems by zone (mean per game) us vs them; top-vs-top winner vs loser')
bytype = {}
for ty in ('fight', 'mixed', 'farm'):
    mps = {m for m, r in rows.items() if r['type'] == ty}
    O = [g for g in ours if g['map'] in mps]
    Tg = [g for g in tops if g['map'] in mps]
    b = {'maps': sorted(mps), 'n': len(O), 'w': sum(g['win'] == g['us'] for g in O), 'nt': len(Tg)}
    for R in (200, 400, 600):
        b[f'us{R}'] = med([sub_at(g, g['us'], R) for g in O]); b[f'th{R}'] = med([sub_at(g, 1 - g['us'], R) for g in O])
        b[f'tw{R}'] = med([sub_at(g, g['win'], R) for g in Tg]); b[f'tl{R}'] = med([sub_at(g, 1 - g['win'], R) for g in Tg])
    for z in ('own', 'mid', 'enemy'):
        b[f'us_{z}'] = mean([gems(caps_of(g, g['us'], z)) for g in O], 0); b[f'th_{z}'] = mean([gems(caps_of(g, 1 - g['us'], z)) for g in O], 0)
        b[f'tw_{z}'] = mean([gems(caps_of(g, g['win'], z)) for g in Tg], 0); b[f'tl_{z}'] = mean([gems(caps_of(g, 1 - g['win'], z)) for g in Tg], 0)
        b[f'us_{z}300'] = mean([gems(caps_of(g, g['us'], z, rmax=300)) for g in O], 0); b[f'th_{z}300'] = mean([gems(caps_of(g, 1 - g['us'], z, rmax=300)) for g in O], 0)
        b[f'tw_{z}300'] = mean([gems(caps_of(g, g['win'], z, rmax=300)) for g in Tg], 0); b[f'tl_{z}300'] = mean([gems(caps_of(g, 1 - g['win'], z, rmax=300)) for g in Tg], 0)
    bytype[ty] = b
    P(f"### {ty}: {len(mps)} maps: {', '.join(sorted(mps))}")
    P(f"ours {b['n']} games, W {b['w']} ({100*b['w']/max(1,b['n']):.0f}%); banked us/them r200 {b['us200']}/{b['th200']} r400 {b['us400']}/{b['th400']} r600 {b['us600']}/{b['th600']}")
    P(f"  gems by zone (whole game) us own/mid/enemy {b['us_own']}/{b['us_mid']}/{b['us_enemy']} | them {b['th_own']}/{b['th_mid']}/{b['th_enemy']}")
    P(f"  gems by zone (r<300)      us {b['us_own300']}/{b['us_mid300']}/{b['us_enemy300']} | them {b['th_own300']}/{b['th_mid300']}/{b['th_enemy300']}")
    P(f"top-vs-top {b['nt']} games: banked winner/loser r200 {b['tw200']}/{b['tl200']} r400 {b['tw400']}/{b['tl400']} r600 {b['tw600']}/{b['tl600']}")
    P(f"  gems by zone winner {b['tw_own']}/{b['tw_mid']}/{b['tw_enemy']} | loser {b['tl_own']}/{b['tl_mid']}/{b['tl_enemy']}; r<300 winner {b['tw_own300']}/{b['tw_mid300']}/{b['tw_enemy300']} loser {b['tl_own300']}/{b['tl_mid300']}/{b['tl_enemy300']}")
P()

# feature correlations with the fight index (Spearman)
def rank(v):
    s = sorted(range(len(v)), key=lambda i: v[i]); r = [0] * len(v)
    for k, i in enumerate(s): r[i] = k
    return r


def spear(a, b):
    ra, rb = rank(a), rank(b); n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)); den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else 0


rv = [r for r in rows.values() if r['fight'] is not None]
P('## Spearman of static map features vs the fight index / our win rate (per map)')
for k in ('s2s', 'mincut', 'midShare', 'monoMid', 'golem', 'heavyMid', 'gemRate', 'groups', 'area', 'altarMid', 'hole', 'bush', 'wall'):
    a = [r[k] for r in rv]
    wr = [r['w'] / r['n'] if r['n'] else 0 for r in rv]
    P(f"{k}: fight {spear(a, [r['fight'] for r in rv]):+.2f}  our win% {spear(a, wr):+.2f}  contact(tvt) {spear([r[k] for r in rv if r['ct_t'] is not None], [r['ct_t'] for r in rv if r['ct_t'] is not None]):+.2f}")
P(f"fight index vs our win%: {spear([r['fight'] for r in rv], [r['w'] / r['n'] if r['n'] else 0 for r in rv]):+.2f}")
P()

# ---------------------------------------------------------------- top-vs-top: winner vs loser (P(winner > loser), means)
def wl_metric(name, fn, G):
    a = []
    for g in G:
        try:
            x, y = fn(g, g['win']), fn(g, 1 - g['win'])
        except (TypeError, KeyError, ZeroDivisionError):
            continue
        if x is None or y is None:
            continue
        a.append((x, y))
    if not a:
        return None
    gt = sum(x > y for x, y in a); eq = sum(x == y for x, y in a)
    return {'m': name, 'n': len(a), 'win': round(sum(x for x, _ in a) / len(a), 2), 'lose': round(sum(y for _, y in a) / len(a), 2), 'p_gt': round((gt + 0.5 * eq) / len(a), 2)}


def coh(g, t, w, k):
    c = T(g, t)['coh'].get(w)
    return c[k] if c else None


def pres(g, t, w, i):
    p = T(g, t)['pres'].get(w)
    return p[i] if p else None


def first_cap(g, t, cls):
    cs = [c['r'] for c in g['caps'] if c['t'] == t and c['cls'] == cls]
    return min(cs) if cs else 2001


MET = [
    ('banked r200', lambda g, t: sub_at(g, t, 200)),
    ('caps r<300', lambda g, t: len(caps_of(g, t, rmax=300))),
    ('gems own r<300', lambda g, t: gems(caps_of(g, t, 'own', rmax=300))),
    ('gems mid r<300', lambda g, t: gems(caps_of(g, t, 'mid', rmax=300))),
    ('gems enemy r<300', lambda g, t: gems(caps_of(g, t, 'enemy', rmax=300))),
    ('gems mid (game)', lambda g, t: gems(caps_of(g, t, 'mid'))),
    ('gems enemy (game)', lambda g, t: gems(caps_of(g, t, 'enemy'))),
    ('kills', lambda g, t: T(g, t)['kills']),
    ('deaths', lambda g, t: T(g, t)['deaths']),
    ('deaths r<300', lambda g, t: T(g, t)['deathsEarly']),
    ('deaths in enemy zone', lambda g, t: T(g, t)['deathZ']['enemy']),
    ('bag lost', lambda g, t: T(g, t)['bagLost']),
    ('big cluster r1-150', lambda g, t: coh(g, t, '1-150', 'big')),
    ('big cluster r150-400', lambda g, t: coh(g, t, '150-400', 'big')),
    ('big cluster r400-800', lambda g, t: coh(g, t, '400-800', 'big')),
    ('>=3 together r1-150', lambda g, t: coh(g, t, '1-150', 'g3')),
    ('>=3 together r150-400', lambda g, t: coh(g, t, '150-400', 'g3')),
    ('ally within 6 r150-400', lambda g, t: coh(g, t, '150-400', 'ally')),
    ('spread r150-400', lambda g, t: coh(g, t, '150-400', 'spread')),
    ('max hp r150-400', lambda g, t: coh(g, t, '150-400', 'mhp')),
    ('max hp r400-800', lambda g, t: coh(g, t, '400-800', 'mhp')),
    ('alive r150-400', lambda g, t: coh(g, t, '150-400', 'alive')),
    ('own-zone time r1-150', lambda g, t: pres(g, t, '1-150', 0)),
    ('mid-zone time r1-150', lambda g, t: pres(g, t, '1-150', 1)),
    ('mid-zone time r150-400', lambda g, t: pres(g, t, '150-400', 1)),
    ('enemy-zone time r150-400', lambda g, t: pres(g, t, '150-400', 2)),
    ('enemy-zone time r400-800', lambda g, t: pres(g, t, '400-800', 2)),
    ('first capture round (2001 = none)', lambda g, t: min([c['r'] for c in g['caps'] if c['t'] == t] or [2001])),
    ('captures r<100', lambda g, t: len(caps_of(g, t, rmax=100))),
    ('captures shared (sharers>1) share', lambda g, t: (lambda cs: sum(c['sharers'] > 1 for c in cs) / len(cs) if cs else None)(caps_of(g, t))),
    ('mean bodies near at capture', lambda g, t: (lambda cs: sum(c['near'] for c in cs) / len(cs) if cs else None)(caps_of(g, t))),
    ('heavy caps (mono/golem)', lambda g, t: len([c for c in g['caps'] if c['t'] == t and c['cls'] in ('mono', 'golem')])),
    ('steals (enemy hit it first)', lambda g, t: len([c for c in g['caps'] if c['t'] == t and c['enemyHitters'] > 0])),
    ('recalls', lambda g, t: T(g, t)['recalls']),
    ('banks', lambda g, t: T(g, t)['banks']),
    ('stuck idle /body', lambda g, t: T(g, t)['stuck']['idle'] / T(g, t)['stuck']['nb']),
    ('stuck aba /body', lambda g, t: T(g, t)['stuck']['aba'] / T(g, t)['stuck']['nb']),
    ('stuck loop /body', lambda g, t: T(g, t)['stuck']['loop'] / T(g, t)['stuck']['nb']),
    ('camp stand-still /body', lambda g, t: T(g, t)['stuck']['campStand'] / T(g, t)['stuck']['nb']),
]
P('## Top-vs-top: winner vs loser (mean winner, mean loser, P(winner > loser) with ties 0.5), all maps and by type')
wl = {}
for ty in ('all', 'fight', 'mixed', 'farm'):
    G = tops if ty == 'all' else [g for g in tops if rows[g['map']]['type'] == ty]
    P(f'### {ty} ({len(G)} games)')
    wl[ty] = []
    for name, fn in MET:
        x = wl_metric(name, fn, G)
        if x:
            wl[ty].append(x)
            P(f"{name}: winner {x['win']} loser {x['lose']} P(w>l) {x['p_gt']} (n {x['n']})")
P()

# us vs them in our games, same metrics (us, them, P(us > them)) and split by win/loss
P('## Our games: us vs them (mean us, mean them, P(us > them)); then in our wins / losses')
usm = {}
for ty in ('all', 'fight', 'mixed', 'farm'):
    G = ours if ty == 'all' else [g for g in ours if rows[g['map']]['type'] == ty]
    P(f'### {ty} ({len(G)} games, W {sum(g["win"] == g["us"] for g in G)})')
    usm[ty] = []
    for name, fn in MET:
        a = []
        for g in G:
            try:
                x, y = fn(g, g['us']), fn(g, 1 - g['us'])
            except (TypeError, KeyError, ZeroDivisionError):
                continue
            if x is None or y is None:
                continue
            a.append((x, y))
        if a:
            gt = sum(x > y for x, y in a) + 0.5 * sum(x == y for x, y in a)
            usm[ty].append({'m': name, 'us': round(sum(x for x, _ in a) / len(a), 2), 'them': round(sum(y for _, y in a) / len(a), 2), 'p_gt': round(gt / len(a), 2), 'n': len(a)})
            P(f"{name}: us {usm[ty][-1]['us']} them {usm[ty][-1]['them']} P(us>them) {usm[ty][-1]['p_gt']} (n {len(a)})")
P()

# ---------------------------------------------------------------- objectives: monolith / golem groups (who, when, with how many)
P('## Heavy objectives (monolith / golem groups): captures per game, first capture round, bodies near / hitters, steals; top winner vs loser vs us vs them')
for cls in ('mono', 'golem', 'elk'):
    mps = sorted({g['map'] for g in tops + ours if any(c['cls'] == cls for c in g['caps'])})
    Gt = [g for g in tops if any(gg['camps'] and any(c[2] == ({'mono': 'monolith'}.get(cls, cls)) for c in gg['camps']) for gg in geo[g['map']]['groups'])]
    Go = [g for g in ours if any(gg['camps'] and any(c[2] == ({'mono': 'monolith'}.get(cls, cls)) for c in gg['camps']) for gg in geo[g['map']]['groups'])]
    def summ(G, sel, label):
        n = len(G)
        if not n:
            return
        cs = [c for g in G for c in g['caps'] if c['cls'] == cls and c['t'] == sel(g)]
        fc = [min([c['r'] for c in g['caps'] if c['cls'] == cls and c['t'] == sel(g)] or [None]) if any(c['cls'] == cls and c['t'] == sel(g) for c in g['caps']) else None for g in G]
        got = sum(1 for x in fc if x is not None)
        P(f"{cls} {label}: games {n}, caps/game {len(cs)/n:.2f}, gems/game {sum(c['gems'] for c in cs)/n:.0f}, took >=1 in {got}/{n}, median first r {med([x for x in fc if x is not None])}, "
          f"near {mean([c['near'] for c in cs])}, hitters {mean([c['hitters'] for c in cs])}, sharers {mean([c['sharers'] for c in cs])}, enemy near {mean([c['enemyNear'] for c in cs])}, steals {sum(c['enemyHitters'] > 0 for c in cs)}, zone own/mid/enemy {sum(c['zone']=='own' for c in cs)}/{sum(c['zone']=='mid' for c in cs)}/{sum(c['zone']=='enemy' for c in cs)}")
    summ(Gt, lambda g: g['win'], 'top winner')
    summ(Gt, lambda g: 1 - g['win'], 'top loser')
    summ(Go, lambda g: g['us'], 'us')
    summ(Go, lambda g: 1 - g['us'], 'them (vs us)')
    # attempts
    for label, G, sel in (('top winner', Gt, lambda g: g['win']), ('top loser', Gt, lambda g: 1 - g['win']), ('us', Go, lambda g: g['us']), ('them', Go, lambda g: 1 - g['us'])):
        at = [a for g in G for a in g.get('att', []) if a['cls'] == cls and a['t'] == sel(g)]
        if at:
            c = collections.Counter(a['res'] for a in at)
            P(f"  attempts {label}: {len(at)} ({len(at)/max(1,len(G)):.1f}/game) won {c['won']} stolen {c['stolen']} none {c['none']}; bodies/attempt {mean([a['n'] for a in at])}; won-attempt bodies {mean([a['n'] for a in at if a['res']=='won'])}")
P()

# ---------------------------------------------------------------- stuck
P('## Stuck per body per game (rounds): idle (>=4 still, off spawn, no action, no capture; tribute/recall channels excluded), A-B-A, loops, camp stand-still (>=8 on a camp tile without capture), spawn wait (full hp, still on spawn >=3)')
def stuckrow(G, sel):
    k = ('idle', 'aba', 'abaE', 'loop', 'loopE', 'campStand', 'campStandE', 'spawnWait')
    return {x: mean([T(g, sel(g))['stuck'][x] / T(g, sel(g))['stuck']['nb'] for g in G], 1) for x in k}
for label, G, sel in (('us', ours, lambda g: g['us']), ('them (vs us)', ours, lambda g: 1 - g['us']), ('top winners', tops, lambda g: g['win']), ('top losers', tops, lambda g: 1 - g['win'])):
    P(label, len(G), stuckrow(G, sel))
P()
P('### per map: our stuck (idle/aba/loop/campStand/spawnWait per body) vs theirs')
smap = []
for mp in maps:
    O = [g for g in ours if g['map'] == mp]
    if not O:
        continue
    a, b = stuckrow(O, lambda g: g['us']), stuckrow(O, lambda g: 1 - g['us'])
    tot_a = a['idle'] + a['aba'] + a['loop'] + a['campStand']; tot_b = b['idle'] + b['aba'] + b['loop'] + b['campStand']
    smap.append((tot_a - tot_b, mp, len(O), a, b))
for d, mp, n, a, b in sorted(smap, reverse=True):
    P(f"{mp} n{n}: us {a['idle']}/{a['aba']}/{a['loop']}/{a['campStand']}/{a['spawnWait']} them {b['idle']}/{b['aba']}/{b['loop']}/{b['campStand']}/{b['spawnWait']} (diff {d:+.0f})")
P()
P('### worst episodes (ours), by kind: file, body, start round, length, position, enemy near, group class')
eps = []
for g in ours:
    for e in T(g, g['us'])['eps']:
        eps.append((e['len'], g['file'], e))
for kind in ('camp', 'idle', 'loop', 'aba', 'spawn'):
    E = sorted([x for x in eps if x[2]['k'] == kind], key=lambda x: -x[0])
    P(f"#### {kind}: {len(E)} episodes (>= threshold) in {len(ours)} games, rounds total {sum(x[0] for x in E)}")
    for ln, f, e in E[:14]:
        P(f"  {f} {e['ty']} r{e['r0']} len {ln} at {e.get('at')} enemyNear {e.get('en')} cls {e.get('cls')} camp {e.get('camp', e.get('g'))}")
    # per-map count
    c = collections.Counter(f.rsplit('_', 1)[0] for _, f, _ in E)
    P('   by map: ' + ', '.join(f'{k} {v}' for k, v in c.most_common(10)))
    c2 = collections.Counter(e['ty'] for _, _, e in E)
    P('   by body: ' + ', '.join(f'{k} {v}' for k, v in c2.most_common(8)))
# the same for top teams (for contrast)
epsT = []
for g in tops:
    for t in (0, 1):
        for e in T(g, t)['eps']:
            epsT.append((e['len'], g['file'], e))
P('#### top teams (both sides) episodes per game by kind: ' + ', '.join(f"{k} {sum(1 for x in epsT if x[2]['k']==k)/max(1,2*len(tops)):.2f} (rounds {sum(x[0] for x in epsT if x[2]['k']==k)/max(1,2*len(tops)):.0f})" for k in ('camp', 'idle', 'loop', 'aba', 'spawn')))
P('#### ours per game by kind: ' + ', '.join(f"{k} {sum(1 for x in eps if x[2]['k']==k)/max(1,len(ours)):.2f} (rounds {sum(x[0] for x in eps if x[2]['k']==k)/max(1,len(ours)):.0f})" for k in ('camp', 'idle', 'loop', 'aba', 'spawn')))
P()

# per team style (all games the team played in this sample)
P('## Team styles (all sampled games of each team): cohesion within 6, zones, mid-gem share, kills/deaths, heavy caps, capture sharing')
style = collections.defaultdict(list)
for g in ours + tops:
    for t in (0, 1):
        style[g['names'][t]].append((g, t))
def mid_share_t(g, t):
    a = gems(caps_of(g, t, 'mid')); b = gems(caps_of(g, 1 - t, 'mid'))
    return a / (a + b) if a + b else None
P('team | games | W% | big r1-150 | big r150-400 | >=3 r1-150 | >=3 r150-400 | ally6 r150-400 | spread | mid time r150-400 | enemy time r150-400 / r400-800 | mid gem share | kills | deaths | heavy caps/g | shared caps | recall starts/1000r | recall events/1000r')
for name, L2 in sorted(style.items(), key=lambda x: -len(x[1])):
    if len(L2) < 5:
        continue
    f = lambda fn: mean([fn(g, t) for g, t in L2])
    P(f"{name} | {len(L2)} | {100*sum(g['win']==t for g,t in L2)/len(L2):.0f} | {f(lambda g,t: coh(g,t,'1-150','big'))} | {f(lambda g,t: coh(g,t,'150-400','big'))} | {f(lambda g,t: coh(g,t,'1-150','g3'))} | {f(lambda g,t: coh(g,t,'150-400','g3'))} | {f(lambda g,t: coh(g,t,'150-400','ally'))} | {f(lambda g,t: coh(g,t,'150-400','spread'))} | {f(lambda g,t: pres(g,t,'150-400',1))} | {f(lambda g,t: pres(g,t,'150-400',2))} / {f(lambda g,t: pres(g,t,'400-800',2))} | {f(mid_share_t)} | {f(lambda g,t: T(g,t)['kills'])} | {f(lambda g,t: T(g,t)['deaths'])} | {f(lambda g,t: len([c for c in g['caps'] if c['t']==t and c['cls'] in ('mono','golem')]))} | {f(lambda g,t: (lambda cs: sum(c['sharers']>1 for c in cs)/len(cs) if cs else None)(caps_of(g,t)))} | {f(lambda g,t: T(g,t)['recalls']*1000/max(1,g['final']))} | {f(lambda g,t: T(g,t).get('recallEv',0)*1000/max(1,g['final']))}")
P()

# per opponent
P('## Per opponent (our games): n, W, banked r400 us/them, deaths us/them, mid gems us/them')
for opp in sorted(set(g['opp'] for g in ours)):
    O = [g for g in ours if g['opp'] == opp]
    P(f"{opp}: n {len(O)} W {sum(g['win']==g['us'] for g in O)} r400 {med([sub_at(g,g['us'],400) for g in O])}/{med([sub_at(g,1-g['us'],400) for g in O])} deaths {mean([T(g,g['us'])['deaths'] for g in O],1)}/{mean([T(g,1-g['us'])['deaths'] for g in O],1)} mid gems {mean([gems(caps_of(g,g['us'],'mid')) for g in O],0)}/{mean([gems(caps_of(g,1-g['us'],'mid')) for g in O],0)}")

os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'agg.txt'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
json.dump({'rows': rows, 'bytype': bytype, 'wl': wl, 'usm': usm}, open(os.path.join(OUT, 'agg.json'), 'w', encoding='utf-8'))
print('\n'.join(L[:5]))
