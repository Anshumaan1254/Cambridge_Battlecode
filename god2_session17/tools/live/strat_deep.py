# Deep dives for an_strategy on tools/live/strat_extract.mjs output: (1) per fight map, winner vs loser (top-vs-top) and us vs them;
# (2) what long stand-stills are (top teams vs us): zone, next to a camp group, recaptured right after (respawn camping), bush, altar;
# (3) loops / A-B-A episodes next to holes or walls, by body type; (4) a runtime map-contest score from static features.
#   python tools/live/strat_deep.py EXT.jsonl MAPGEO.jsonl > deep.txt
import json, sys, collections, statistics as st, math, os

EXT, GEO = sys.argv[1], sys.argv[2]
ROOT = 'C:/battlecode/Cambridge_Battlecode/experiments/live/lists/'
CACHE = 'C:/battlecode/cache/'
US = 'HouseOfCoders'


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
geo = {g['map']: g for g in load(GEO)}
ours, tops = [], []
for g in load(EXT):
    if 'err' in g or g['file'] not in src:
        continue
    m = meta.get(g['file'].split('_')[-1][:8])
    if not m:
        continue
    names = {0 if t['side'] == 'a' else 1: t['name'] for t in m['teams']}
    g['names'] = names
    g['win'] = 0 if g['outcome'] == 1 else 1
    if src[g['file']] == 'top':
        tops.append(g)
    else:
        us = [k for k, v in names.items() if v == US]
        if us:
            g['us'] = us[0]
            ours.append(g)
agg = json.load(open(CACHE + 'an_strategy/agg.json', encoding='utf-8'))
rows = agg['rows']


def T(g, t):
    return g['T'][str(t)]


def mean(v, k=2):
    v = [x for x in v if x is not None]
    return round(sum(v) / len(v), k) if v else None


def med(v):
    v = [x for x in v if x is not None]
    return round(st.median(v), 1) if v else None


def gems(g, t, zone=None, rmax=None, cls=None):
    return sum(c['gems'] for c in g['caps'] if c['t'] == t and (zone is None or c['zone'] == zone) and (rmax is None or c['r'] < rmax) and (cls is None or c['cls'] == cls))


def coh(g, t, w, k):
    c = T(g, t)['coh'].get(w)
    return c[k] if c else None


def pres(g, t, w, i):
    p = T(g, t)['pres'].get(w)
    return p[i] if p else None


# ------------------------------------------------------------------ (1) fight maps, one line per map per side
print('## (1) Fight / mixed maps: top-vs-top winner (W) vs loser (L) and us (U) vs them (O)')
print('cols: games | first cap | gems mid r<300 | gems mid game | gems own game | kills | deaths | big cluster r1-150 | >=3 together r150-400 | mid time r150-400 | heavy caps | elk caps | steals | banks')
def line(G, sel):
    return [len(G),
            med([min([c['r'] for c in g['caps'] if c['t'] == sel(g)] or [2001]) for g in G]),
            mean([gems(g, sel(g), 'mid', 300) for g in G], 0), mean([gems(g, sel(g), 'mid') for g in G], 0), mean([gems(g, sel(g), 'own') for g in G], 0),
            mean([T(g, sel(g))['kills'] for g in G], 1), mean([T(g, sel(g))['deaths'] for g in G], 1),
            mean([coh(g, sel(g), '1-150', 'big') for g in G]), mean([coh(g, sel(g), '150-400', 'g3') for g in G]), mean([pres(g, sel(g), '150-400', 1) for g in G]),
            mean([len([c for c in g['caps'] if c['t'] == sel(g) and c['cls'] in ('mono', 'golem')]) for g in G], 2),
            mean([len([c for c in g['caps'] if c['t'] == sel(g) and c['cls'] == 'elk']) for g in G], 1),
            mean([len([c for c in g['caps'] if c['t'] == sel(g) and c['enemyHitters'] > 0]) for g in G], 1),
            mean([T(g, sel(g))['banks'] for g in G], 1)]
for mp in sorted(rows, key=lambda m: -(rows[m]['fight'] or 0)):
    if rows[mp]['type'] == 'farm':
        continue
    Gt = [g for g in tops if g['map'] == mp]; Go = [g for g in ours if g['map'] == mp]
    print(f"### {mp} ({rows[mp]['type']}, fight index {rows[mp]['fight']})")
    if Gt:
        print('  W', line(Gt, lambda g: g['win']))
        print('  L', line(Gt, lambda g: 1 - g['win']))
    if Go:
        print('  U', line(Go, lambda g: g['us']), f"wins {sum(g['win'] == g['us'] for g in Go)}")
        print('  O', line(Go, lambda g: 1 - g['us']))
print()

# ------------------------------------------------------------------ (2) stand-still episodes: what are they?
def fAt(mp, t, x, y):
    G = geo[mp]; W = G['W']
    if x < 0 or y < 0 or x >= W or y >= G['H']:
        return None
    a, b = G['dA'][y * W + x], G['dB'][y * W + x]
    if a < 0 or b < 0:
        return None
    f = a / (a + b or 1)
    return f if t == 0 else 1 - f


def zone(f):
    return None if f is None else ('own' if f < 0.4 else 'enemy' if f > 0.6 else 'mid')


def classify(g, t, e):
    mp = g['map']; G = geo[mp]
    x, y = e['at']
    z = zone(fAt(mp, t, x, y))
    # nearest group with a camp tile within 2
    best, bd = None, 99
    for gr in G['groups']:
        for c in gr['camps']:
            d = max(abs(c[0] - x), abs(c[1] - y))
            if d < bd:
                bd, best = d, gr
    near_g = best if bd <= 2 else None
    recap = near_g is not None and any(c['t'] == t and c['g'] == near_g['i'] and e['r0'] <= c['r'] <= e['r0'] + e['len'] + 20 for c in g['caps'])
    enemy_cap = near_g is not None and any(c['t'] != t and c['g'] == near_g['i'] and e['r0'] <= c['r'] <= e['r0'] + e['len'] + 20 for c in g['caps'])
    bush = G['grid'][y][x] == '"'
    altar = any(max(abs(a[0] - x), abs(a[1] - y)) <= 1 for a in G['altars'])
    on_camp = bd == 0
    return {'zone': z, 'nearG': near_g is not None, 'onCamp': on_camp, 'recap': recap, 'enemyCap': enemy_cap, 'bush': bush, 'altar': altar,
            'cls': None if near_g is None else ('mono' if any(c[2] == 'monolith' for c in near_g['camps']) else 'golem' if any(c[2] == 'golem' for c in near_g['camps']) else 'elk' if any(c[2] == 'elk' for c in near_g['camps']) else 'other'),
            'en': e.get('en')}


print('## (2) Long stand-stills (idle >= 10 rounds, camp stand >= 12): where and why. Per side: episodes/game, rounds/game, shares')
def standsum(label, G, sel):
    E = []
    for g in G:
        t = sel(g)
        for e in T(g, t)['eps']:
            if e['k'] in ('idle',) and e.get('at'):
                E.append((g, t, e, classify(g, t, e)))
    n = len(G)
    if not E:
        print(label, 'none'); return
    rounds = sum(e['len'] for _, _, e, _ in E)
    sh = lambda k: round(sum(e['len'] for _, _, e, c in E if c[k]) / max(1, rounds), 2)
    zs = collections.Counter()
    for _, _, e, c in E:
        zs[c['zone']] += e['len']
    print(f"{label}: {len(E)/n:.2f} episodes/game, {rounds/n:.0f} rounds/game (mean len {rounds/len(E):.0f}); share of rounds: next to a camp group {sh('nearG')}, on a camp tile {sh('onCamp')}, "
          f"group recaptured by them right after {sh('recap')}, taken by the enemy {sh('enemyCap')}, in a bush {sh('bush')}, at an altar {sh('altar')}, enemy within 8 at start {sh('en')}; zone own/mid/enemy "
          f"{zs['own']/max(1,rounds):.2f}/{zs['mid']/max(1,rounds):.2f}/{zs['enemy']/max(1,rounds):.2f}; group classes {dict(collections.Counter(c['cls'] for _,_,_,c in E))}")
standsum('top winners', tops, lambda g: g['win'])
standsum('top losers', tops, lambda g: 1 - g['win'])
standsum('us', ours, lambda g: g['us'])
standsum('them (vs us)', ours, lambda g: 1 - g['us'])
for ty in ('fight', 'mixed', 'farm'):
    standsum(f'  {ty} maps top winners', [g for g in tops if rows[g['map']]['type'] == ty], lambda g: g['win'])
    standsum(f'  {ty} maps us', [g for g in ours if rows[g['map']]['type'] == ty], lambda g: g['us'])
print()

# ------------------------------------------------------------------ (3) loops / A-B-A next to holes or walls, by body
print('## (3) Loop (>= 16 rounds) and A-B-A (>= 6) episodes: next to a hole (within 2), a wall (within 1), with an enemy within 8 (A-B-A only), by body type')
def terr(mp, x, y, ch, r):
    G = geo[mp]
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            xx, yy = x + dx, y + dy
            if 0 <= xx < G['W'] and 0 <= yy < G['H'] and G['grid'][yy][xx] == ch:
                return True
    return False
for kind in ('loop', 'aba'):
    for label, G, sel in (('us', ours, lambda g: g['us']), ('them (vs us)', ours, lambda g: 1 - g['us']), ('top winners', tops, lambda g: g['win']), ('top losers', tops, lambda g: 1 - g['win'])):
        E = [(g, e) for g in G for e in T(g, sel(g))['eps'] if e['k'] == kind and e.get('at')]
        if not E:
            continue
        n = len(G)
        rounds = sum(e['len'] for _, e in E)
        hole = sum(e['len'] for g, e in E if terr(g['map'], e['at'][0], e['at'][1], 'o', 2)) / rounds
        wall = sum(e['len'] for g, e in E if terr(g['map'], e['at'][0], e['at'][1], '#', 1)) / rounds
        en = sum(e['len'] for g, e in E if e.get('en')) / rounds if kind == 'aba' else None
        bt = collections.Counter()
        for _, e in E:
            bt[e['ty']] += e['len']
        print(f"{kind} {label}: {rounds/n:.0f} episode-rounds/game ({len(E)/n:.2f} episodes), near hole {hole:.2f}, near wall {wall:.2f}, enemy near {en}, by body (rounds/game) " + ', '.join(f'{k} {v/n:.0f}' for k, v in bt.most_common(6)))
print()
# per-body loop rate (rounds per body-game) for our bodies vs top teams' bodies of the same type
print('### loop+A-B-A episode rounds per body-game by champion type (us vs top teams in top-vs-top)')
cnt_u, cnt_t, bod_u, bod_t = collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
for g in ours:
    for ty in g['types'][g['us']]:
        bod_u[ty] += 1
    for e in T(g, g['us'])['eps']:
        if e['k'] in ('loop', 'aba'):
            cnt_u[e['ty']] += e['len']
for g in tops:
    for t in (0, 1):
        for ty in g['types'][t]:
            bod_t[ty] += 1
        for e in T(g, t)['eps']:
            if e['k'] in ('loop', 'aba'):
                cnt_t[e['ty']] += e['len']
for ty in sorted(set(bod_u) | set(bod_t), key=lambda k: -(cnt_u[k] / max(1, bod_u[k]))):
    print(f"{ty}: us {cnt_u[ty]/max(1,bod_u[ty]):.0f} (bodies {bod_u[ty]}), top {cnt_t[ty]/max(1,bod_t[ty]):.0f} (bodies {bod_t[ty]})")
print()

# ------------------------------------------------------------------ (4) a runtime contest score from static features
print('## (4) Runtime "contested map" score from static features (no map names): per map value and fight index')
def zs(vals):
    m = sum(vals) / len(vals); s = math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals)) or 1
    return [(v - m) / s for v in vals]
mps = [m for m in rows if rows[m]['fight'] is not None]
F = {m: geo[m]['feat'] for m in mps}
# candidate features: short spawn-to-spawn walk, scarce gems per walking distance, share of gem rate in the middle band, heavy mid groups
cand = {
    'inv_s2s': [1 / max(5, F[m]['s2s']) for m in mps],
    'gemRate': [F[m]['gemRate'] for m in mps],
    'midShare': [F[m]['midShare'] for m in mps],
    'midGems_per_s2s': [F[m]['midGems'] / max(5, F[m]['s2s']) for m in mps],
    'allGems': [F[m]['allGems'] for m in mps],
    'area': [geo[m]['W'] * geo[m]['H'] for m in mps],
    'groups': [F[m]['groups'] for m in mps],
}
fi = [rows[m]['fight'] for m in mps]
def rank(v):
    s = sorted(range(len(v)), key=lambda i: v[i]); r = [0] * len(v)
    for k, i in enumerate(s):
        r[i] = k
    return r
def spear(a, b):
    ra, rb = rank(a), rank(b); n = len(a); ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb)); den = math.sqrt(sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb))
    return num / den if den else 0
for k, v in cand.items():
    print(f"{k}: Spearman with fight index {spear(v, fi):+.2f}")
z1, z2, z3 = zs(cand['inv_s2s']), zs([-x for x in cand['gemRate']]), zs(cand['midShare'])
score = [a + b + c for a, b, c in zip(z1, z2, z3)]
print(f"score = z(1/s2s) + z(-gemRate) + z(midShare): Spearman {spear(score, fi):+.2f}")
for s_, m in sorted(zip(score, mps), reverse=True):
    print(f"  {m}: score {s_:+.2f} fight {rows[m]['fight']} type {rows[m]['type']} our W {rows[m]['w']}/{rows[m]['n']} s2s {F[m]['s2s']} gemRate {F[m]['gemRate']} midShare {F[m]['midShare']}")
