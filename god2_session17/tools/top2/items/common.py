# Shared helpers for the items-dimension aggregators (tools/top2/items/agg_*.py): study-team index, engine stats (3.0.4),
# item codes (family x stat; id = family*6 + stat*2 + emblem in the SDK), stat points from shard equivalents.
import json, os, collections, statistics

T2 = 'C:/battlecode/cache/t2'
KEYS = ['pbg', 'pbg14', 'ifish', 'pantheon', 'coo', 'cm', 'nyx']
SRC = ['pbg', 'ifish', 'pantheon', 'coo', 'cm', 'nyx']
# pbg changed its bot at ~14:00 UTC (Jungle-first openers on Vesper / HoR / Vendetta / Ryth): 'pbg14' = its games from 14:00 on
SPLIT = {'pbg14': ('pbg', '2026-10-23T14:00')}
FAM = 'MPDTJHB'   # Monster Power Durability Treasure Jungle Home Bruiser
STAT = 'sfh'      # strength focus health
# engine base stats and growth per shard (experiments/results/probe_v3_0_4/champions_engine_3_0_4.txt)
ENG = {
    'Ryth': (1200, 100, 45, 5, 100, 10), 'VesperVale': (1000, 100, 55, 5, 100, 10), 'Vendetta': (1000, 100, 70, 6, 100, 10),
    'Cassi': (600, 65, 30, 3, 70, 13), 'Issac': (900, 80, 40, 3, 100, 10), 'Stellar': (650, 65, 30, 3.5, 70, 7),
    'Prism': (700, 60, 35, 2.5, 80, 8), 'Marcella': (1200, 100, 45, 5, 60, 15), 'Willow': (700, 50, 55, 3, 120, 5),
    'Ren': (900, 100, 35, 5, 100, 9), 'Varg': (1000, 100, 40, 5, 100, 10), 'Tavi': (900, 75, 45, 5, 110, 10),
    'HeartOfRuin': (1000, 100, 30, 3.5, 100, 12),
}
SHORT = {'Ryth': 'Ryth', 'VesperVale': 'Vesper', 'Vendetta': 'Vendetta', 'Cassi': 'Cassi', 'Issac': 'Issac', 'Stellar': 'Stellar',
         'Prism': 'Prism', 'Marcella': 'Marcella', 'Willow': 'Willow', 'Ren': 'Ren', 'Varg': 'Varg', 'Tavi': 'Tavi', 'HeartOfRuin': 'HoR'}
# damage stat of the kit: spell casters scale with focus, the rest with strength
DMG_STAT = {'Prism': 1, 'Stellar': 1, 'Cassi': 1, 'Willow': 1, 'HeartOfRuin': 1}


def code(k):
    return FAM[k // 3] + STAT[k % 3]


def load_index():
    """file stem (map_matchId8) -> list of dicts {key, ti, win, opp, sdraft, odraft, created}"""
    out = collections.defaultdict(list)
    for key in SRC:
        rows = [json.loads(l) for l in open(f'{T2}/{key}/index.jsonl', encoding='utf-8')]
        names = collections.Counter(t['name'] for r in rows for t in r['teams'])
        me = names.most_common(1)[0][0]
        for r in rows:
            stem = f"{r['map']}_{r['matchId'][:8]}"
            ts = r['teams']
            mine = [t for t in ts if t['name'] == me][0]
            other = [t for t in ts if t['name'] != me]
            other = other[0] if other else mine
            ti = 0 if mine['side'] == 'a' else 1
            rec = {'key': key, 'name': me, 'ti': ti, 'win': mine['result'] == 'win', 'opp': other['name'],
                   'sdraft': mine.get('draftPicks'), 'odraft': other.get('draftPicks'), 'created': r['createdAt'], 'map': r['map']}
            out[stem].append(rec)
            for k2, (base, since) in SPLIT.items():
                if key == base and r['createdAt'] >= since:
                    out[stem].append(dict(rec, key=k2))
    return out


def points(se):
    """se: dict code-index (0..20) -> shard equivalents. returns [str, foc, hp] stat points and the emblem list (codes, ordered by index)"""
    pts = [0.0, 0.0, 0.0]
    for k, v in se.items():
        fam, st = k // 3, k % 3
        em, sh = v // 5, v % 5
        pts[st] += sh + em * (6 if fam == 1 else 5)
        if fam == 6:
            for o in range(3):
                if o != st:
                    pts[o] += em
    return pts


def stats(ty, se):
    hp0, hpg, s0, sg, f0, fg = ENG[ty]
    p = points(se)
    hp = hp0 + hpg * p[2]
    s = s0 + sg * p[0]
    if ty == 'Ryth':
        s += 0.01 * hpg * p[2]
    f = f0 + fg * p[1]
    return s, f, hp


def se_at(buys, sells, r):
    se = collections.Counter()
    for b in buys:
        if b[0] <= r and b[1] < 100:
            se[b[1]] += b[2]
    for s in sells:
        if s[0] <= r:
            se[s[1]] -= s[2]
    return se


def emblem_order(buys):
    """completion order of emblems: list of (round, code)"""
    se = collections.Counter()
    out = []
    for b in sorted(buys, key=lambda x: x[0]):
        if b[1] >= 100:
            continue
        before = se[b[1]] // 5
        se[b[1]] += b[2]
        after = se[b[1]] // 5
        for _ in range(after - before):
            out.append((b[0], code(b[1])))
    return out


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def fmt(x, d=0):
    if x is None:
        return '-'
    if d == 0:
        return f'{x:,.0f}'
    return f'{x:,.{d}f}'


def pct(a, b, d=0):
    return '-' if not b else f'{100 * a / b:.{d}f}%'
